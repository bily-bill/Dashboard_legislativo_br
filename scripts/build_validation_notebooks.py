"""Generate the bounded validation notebooks 03–08 with Python's standard library."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "notebooks" / "exploracao"


def cell(kind: str, source: str) -> dict:
    item = {"cell_type": kind, "metadata": {}, "source": source.strip("\n").splitlines(keepends=True)}
    if kind == "code":
        item.update(execution_count=None, outputs=[])
    return item


def notebook(name: str, cells: list[tuple[str, str]]) -> None:
    data = {"cells": [cell(kind, source) for kind, source in cells],
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                         "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    (DEST / name).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


COMMON = """
from pathlib import Path
import sys
import pandas as pd
root = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'scripts' / 'validation_utils.py').exists())
sys.path.insert(0, str(root / 'scripts'))
from validation_utils import (Probe, OUT, CHECKS, MANIFEST, MANIFEST_FIELDS, api_camara, api_senado,
                              record, manifest_rows, save_manifest, rows_camara, count_values, csv_head)
pd.set_option('display.max_colwidth', 90)
"""


def build_03() -> None:
    notebook("03_contratos_e_coleta.ipynb", [
        ("markdown", """# 03 — Contratos, coleta limitada e manifesto

Execute primeiro. Instalação no kernel atual, se faltar algo: `%pip install requests pandas plotly pypdf`. Para gerar/abrir notebooks fora do editor, instale também `jupyterlab`. Nenhuma dependência é instalada automaticamente.

Limites: 120 chamadas, uma por segundo, três tentativas somente para falhas transitórias, 80 MB por arquivo e 2 MB para JSON. O manifesto é congelado no primeiro ciclo sem erros de rede nas consultas de seleção. Para repetir a mesma amostra, não o remova.
"""),
        ("code", COMMON + """
import importlib.util
from collections import Counter
print('Python:', sys.version.split()[0], 'kernel:', sys.executable)
print({m: bool(importlib.util.find_spec(m)) for m in ('requests','pandas','plotly','pypdf','jupyterlab')})
probe = Probe('03', max_calls=120)
"""),
        ("markdown", "## Contratos OpenAPI e divergências com o catálogo local"),
        ("code", """
import csv, json
catalog = list(csv.DictReader((root/'docs/catalogo_recursos.csv').open(encoding='utf-8-sig', newline='')))
specs = {'camara': probe.json(api_camara('api-docs'), limit=8_000_000),
         'senado': probe.json(api_senado('v3/api-docs'), limit=8_000_000)}
summary = []
for house, response in specs.items():
    if not response.ok:
        record('03', f'contrato_{house}', house, response.url, 0, 'OpenAPI acessível e GETs comparáveis ao catálogo', {}, 'INCONCLUSIVO', response.error)
        continue
    ops = [(path, op) for path, methods in response.data.get('paths', {}).items() for method, op in methods.items() if method.lower()=='get']
    previous = [r for r in catalog if r['source']==house and r['resource_type']=='api_endpoint']
    # Compare stable path suffixes because base URLs differ across providers.
    new_paths = {p.lstrip('/') for p,_ in ops}
    old_map={r['route_or_url'].split('/api/v2/',1)[-1] if house=='camara' else r['route_or_url'].split('legis.senado.leg.br/',1)[-1]:r for r in previous}
    old_paths=set(old_map)
    changed = sorted(new_paths ^ old_paths)[:10]
    param_diffs=[]; schema_diffs=[]
    for path,op in ops:
        old=old_map.get(path.lstrip('/'))
        if old:
            new_names={p.get('name') for p in op.get('parameters',[])}
            old_names={p.get('name') for p in json.loads(old['parameters'] or '[]')}
            if new_names != old_names: param_diffs.append(path)
            content=op.get('responses',{}).get('200',{}).get('content',{})
            schema=next((v.get('schema') for v in content.values() if v.get('schema')),{})
            if schema != json.loads(old['response_schema'] or '{}'): schema_diffs.append(path)
    deprecated = sum(bool(op.get('deprecated')) for _,op in ops)
    summary.append({'casa':house,'versao':response.data.get('openapi') or response.data.get('swagger'), 'GET':len(ops), 'GET_catalogo':len(previous), 'depreciados':deprecated,'rotas_divergentes_exemplos':changed,'parametros_divergentes':len(param_diffs),'esquemas_divergentes':len(schema_diffs)})
    record('03', f'contrato_{house}', house, response.url, len(ops), 'GETs, parâmetros e deprecação confrontados com snapshot local',
           {'GET':len(ops),'GET_catalogo':len(previous),'depreciados':deprecated,'rotas_divergentes':len(new_paths ^ old_paths),'parametros_divergentes':len(param_diffs),'esquemas_divergentes':len(schema_diffs)},
           'PASSOU' if not changed and not param_diffs and not schema_diffs and len(ops)==len(previous) else 'INCONCLUSIVO', 'Revisar rotas/parâmetros/esquemas antes da coleta' if changed or param_diffs or schema_diffs else '')
display(pd.DataFrame(summary))
"""),
        ("markdown", "## Arquivos, redirecionamento, falha e resposta vazia"),
        ("code", """
files = {
 'presenca_camara_2026':'http://dadosabertos.camara.leg.br/arquivos/eventosPresencaDeputados/csv/eventosPresencaDeputados-2026.csv',
 'votos_camara_2025':'http://dadosabertos.camara.leg.br/arquivos/votacoesVotos/csv/votacoesVotos-2025.csv',
 'temas_camara_2026':'http://dadosabertos.camara.leg.br/arquivos/proposicoesTemas/csv/proposicoesTemas-2026.csv'}
file_results = []
for label,url in files.items():
    r = probe.fetch(url, method='HEAD')
    file_results.append({'arquivo':label,'HTTP':r.status,'URL_final':r.url,'Content-Type':(r.headers or {}).get('Content-Type'),'Content-Length':(r.headers or {}).get('Content-Length')})
    record('03', label, 'camara', r.url, 1, 'Arquivo anual concreto responde HEAD e redireciona corretamente',
           {'HTTP':r.status,'bytes_declarados':(r.headers or {}).get('Content-Length')}, 'PASSOU' if r.ok else 'INCONCLUSIVO', r.error)
display(pd.DataFrame(file_results))
invalid = probe.json(api_camara('rota-inexistente-validacao'), limit=200_000)
empty = probe.json(api_camara('proposicoes'), {'siglaTipo':'PL','ano':2099,'itens':2}, limit=200_000)
display(pd.DataFrame([{'caso':'rota inválida','HTTP':invalid.status,'erro':invalid.error},
                      {'caso':'intervalo futuro','HTTP':empty.status,'linhas':len(rows_camara(empty.data)) if empty.ok else None,'erro':empty.error}]))
record('03','estados_erro_e_vazio','camara',f'{invalid.url} | {empty.url}',2,
       'HTTP não 200 e resposta 200 vazia devem ter estados diferentes',
       {'HTTP_invalido':invalid.status,'HTTP_futuro':empty.status,'linhas_futuro':len(rows_camara(empty.data)) if empty.ok else None},
       'PASSOU' if invalid.status not in (None,200) and empty.ok else 'INCONCLUSIVO', 'Não converter falha em zero observado')
wide=probe.json(api_camara('proposicoes'),{'siglaTipo':'PL','dataApresentacaoInicio':'2023-01-01','dataApresentacaoFim':'2023-12-31','itens':2})
narrow=probe.json(api_camara('proposicoes'),{'siglaTipo':'PL','dataApresentacaoInicio':'2023-01-01','dataApresentacaoFim':'2023-03-31','itens':2})
display(pd.DataFrame([{'janela':'ano inteiro','HTTP':wide.status,'erro':wide.error},
                      {'janela':'trimestre','HTTP':narrow.status,'linhas':len(rows_camara(narrow.data)) if narrow.ok else None}]))
record('03','limite_janela_camara','camara',f'{wide.url} | {narrow.url}',2,
       'Filtro de data anual é recusado; dividir coleta em janelas de até três meses',
       {'HTTP_ano':wide.status,'HTTP_trimestre':narrow.status},
       'PASSOU' if wide.status==400 and narrow.ok else 'INCONCLUSIVO','Respeitar limite da API, inclusive na paginação')
by_year=probe.json(api_camara('proposicoes'),{'ano':2026,'siglaTipo':'PL','itens':10,'ordem':'ASC','ordenarPor':'id'})
year_rows=rows_camara(by_year.data) if by_year.ok else []
mismatch=sum(str(x.get('dataApresentacao',''))[:4]!='2026' for x in year_rows)
display(pd.DataFrame([{'linhas_ano_2026':len(year_rows),'apresentadas_em_outro_ano':mismatch}]))
record('03','ano_vs_apresentacao','camara',by_year.url,len(year_rows),
       'Campo ano da identificação não substitui dataApresentacao no indicador de iniciativas',
       {'linhas':len(year_rows),'data_de_outro_ano':mismatch},'PASSOU' if by_year.ok else 'INCONCLUSIVO',
       'Filtro de apresentação explícito obrigatório; registros de projeto podem ter ano de identificação diferente')
"""),
        ("markdown", "## Amostra congelada: 2026 dirigido + 2023–2025 estratificado"),
        ("code", """
if MANIFEST.exists():
    manifest = manifest_rows()
    print('Manifesto existente preservado:', MANIFEST)
else:
    existing = list(csv.DictReader((root/'docs/amostra_projetos.csv').open(encoding='utf-8-sig', newline='')))
    manifest = [{'fonte':r['fonte'],'entidade':'projeto','tipo':r['tipo'],'ano':'2026','id':r['identificador'],
                 'url':api_camara('proposicoes/'+r['identificador']) if r['fonte']=='camara' else api_senado('processo/'+r['identificador']+'.json'),
                 'selecao':'caso dirigido 2026'} for r in existing]
    manifest += [
      {'fonte':'camara','entidade':'evento','tipo':'presenca','ano':'2026','id':'82870','url':api_camara('eventos/82870'),'selecao':'caso dirigido'},
      {'fonte':'camara','entidade':'votacao','tipo':'resultado','ano':'2026','id':'2611313-34','url':api_camara('votacoes/2611313-34'),'selecao':'caso dirigido'},
      {'fonte':'senado','entidade':'processo','tipo':'vinculo_votacao','ano':'2023','id':'8361684','url':api_senado('processo/8361684.json'),'selecao':'caso dirigido'},
      {'fonte':'senado','entidade':'senador','tipo':'filiacao','ano':'2023','id':'5672','url':api_senado('senador/5672.json'),'selecao':'caso dirigido'}]
    selection_errors=[]; missing=[]
    for year in (2023,2024,2025):
      for typ in ('PL','PLP','PEC'):
        c=probe.json(api_camara('proposicoes'), {'ano':year,'siglaTipo':typ,
                    'dataApresentacaoInicio':f'{year}-01-01','dataApresentacaoFim':f'{year}-03-31',
                    'itens':10,'ordem':'DESC','ordenarPor':'id'})
        if not c.ok: selection_errors.append(f'camara {typ}/{year}: {c.error}')
        else:
          valid=next((x for x in rows_camara(c.data) if str(x.get('dataApresentacao',''))[:4]==str(year)),None)
          if valid:
            manifest.append({'fonte':'camara','entidade':'projeto','tipo':typ,'ano':str(year),'id':str(valid['id']),
                             'url':api_camara('proposicoes/'+str(valid['id'])),'selecao':'ID recente com dataApresentacao no ano'})
          else: missing.append(f'camara {typ}/{year}: sem dataApresentacao coerente nas 10 linhas')
        s=probe.json(api_senado('processo'), {'sigla':typ,'ano':year,'dataInicioApresentacao':f'{year}-01-01','dataFimApresentacao':f'{year}-03-31'}, limit=2_000_000)
        if not s.ok: selection_errors.append(f'senado {typ}/{year}: {s.error}')
        elif isinstance(s.data,list) and s.data:
          item=sorted(s.data,key=lambda x:str(x.get('id','')))[0]
          manifest.append({'fonte':'senado','entidade':'projeto','tipo':typ,'ano':str(year),'id':str(item['id']),
                           'url':api_senado('processo/'+str(item['id'])+'.json'),'selecao':'menor ID da lista jan–mar'})
        else: missing.append(f'senado {typ}/{year}')
    if not selection_errors:
      save_manifest(manifest)
      print('Manifesto congelado:', MANIFEST)
    else:
      print('Manifesto NÃO gravado devido a falhas de coleta:', selection_errors[:5])
    print('Estratos sem linha:',missing)
project_strata={(x['fonte'],x['ano'],x['tipo']) for x in manifest if x['entidade']=='projeto'}
missing_strata=[f'{house} {typ}/{year}' for house in ('camara','senado') for year in ('2023','2024','2025','2026') for typ in ('PL','PLP','PEC') if (house,year,typ) not in project_strata]
coverage_years=all(any(x['fonte']==house and x['ano']==str(year) and x['entidade']=='projeto' for x in manifest)
                   for house in ('camara','senado') for year in (2023,2024,2025,2026))
record('03','estratos_manifesto','ambas',str(MANIFEST),len(manifest),'Ambas as Casas nos anos 2023–2026; tipos ausentes explicitados',
       {'projetos':sum(x['entidade']=='projeto' for x in manifest),'estratos_ausentes':missing_strata},
       'PASSOU' if MANIFEST.exists() and coverage_years else 'INCONCLUSIVO',
       'Amostra não substitui cobertura histórica; estratos faltantes requerem investigação')
display(pd.DataFrame(manifest).groupby(['fonte','ano','tipo']).size().rename('n').reset_index().head(30))
"""),
    ])


def build_04() -> None:
    notebook("04_chaves_joins_e_tempo.ipynb", [
        ("markdown", """# 04 — Chaves, cardinalidade, filiação no tempo

Requer `03` e seu manifesto congelado. Testes sobre amostras não provam unicidade global. Nenhuma junção entre Casas é feita por número, nome ou ementa.
"""),
        ("code", COMMON + """
from collections import Counter
probe=Probe('04',max_calls=100)
manifest=manifest_rows()
assert manifest, 'Execute 03 para congelar o manifesto.'
projects=[r for r in manifest if r['entidade']=='projeto']
print('Projetos no manifesto:',len(projects),'| limite de detalhe:',min(12,len(projects)))
"""),
        ("markdown", "## IDs de projeto, campos nulos e detalhes"),
        ("code", """
sample=projects[:12]
details=[]; failures=[]
for row in sample:
    r=probe.json(row['url'])
    if not r.ok: failures.append((row['fonte'],row['id'],r.error)); continue
    d=r.data.get('dados',{}) if row['fonte']=='camara' else r.data
    details.append({'fonte':row['fonte'],'id_manifesto':row['id'],'id_resposta':str(d.get('id','')),
                    'tipo':d.get('siglaTipo') or d.get('sigla'),'ano_manifesto':row['ano'],
                    'data':d.get('dataApresentacao') or (d.get('documento') or {}).get('dataApresentacao')})
frame=pd.DataFrame(details)
display(frame)
counts={'consultados':len(sample),'detalhes':len(frame),'IDs_distintos':len(set((x['fonte'],x['id_resposta']) for x in details)),
        'id_divergente':sum(x['id_manifesto']!=x['id_resposta'] for x in details),'data_nula':sum(not x['data'] for x in details)}
record('04','ids_projeto','ambas','IDs do manifesto → endpoints de detalhe',len(frame),
       'ID nativo do detalhe coincide com manifesto e não repete na amostra',counts,
       'PASSOU' if not failures and counts['id_divergente']==0 and counts['IDs_distintos']==len(frame) else 'INCONCLUSIVO',str(failures[:3]))
"""),
        ("markdown", "## Autoria e tramitação da Câmara: chaves compostas, órfãos e multiplicação"),
        ("code", """
cam=[x for x in projects if x['fonte']=='camara'][:4]
relation_rows=[]; errors=[]
for p in cam:
    for relation in ('autores','tramitacoes'):
        r=probe.json(api_camara(f"proposicoes/{p['id']}/{relation}"),limit=2_000_000)
        if not r.ok: errors.append(f"{p['id']}/{relation}: {r.error}"); continue
        for item in rows_camara(r.data):
            key=(item.get('uri'),item.get('ordemAssinatura')) if relation=='autores' else (item.get('sequencia'),)
            relation_rows.append({'projeto':p['id'],'relacao':relation,'chave_local':str(key),'sem_chave':all(v is None for v in key)})
rel=pd.DataFrame(relation_rows)
display(rel.groupby(['projeto','relacao']).size().rename('linhas').reset_index() if not rel.empty else rel)
dups=int(rel.duplicated(['projeto','relacao','chave_local']).sum()) if not rel.empty else 0
record('04','relacoes_camara','camara','/proposicoes/{id}/autores e /tramitacoes',len(rel),
       'Unicidade das chaves locais e filhos com pai conhecido na amostra',
       {'projetos':len(cam),'filhos':len(rel),'duplicatas_chave_candidata':dups,'sem_chave':int(rel['sem_chave'].sum()) if not rel.empty else 0},
       'INCONCLUSIVO' if errors or dups else 'PASSOU',str(errors[:3])+'; unicidade global não demonstrada')
"""),
        ("markdown", "## Retrato atual: composição por partido e UF nas duas Casas"),
        ("code", """
deputies=[]; page_errors=[]
for page in range(1,8):
    r=probe.json(api_camara('deputados'),{'itens':100,'pagina':page,'ordem':'ASC','ordenarPor':'id'})
    if not r.ok: page_errors.append(r.error); break
    items=rows_camara(r.data)
    deputies.extend(items)
    if len(items)<100: break
sen_current=probe.json(api_senado('senador/lista/atual.json'))
senators=(sen_current.data or {}).get('ListaParlamentarEmExercicio',{}).get('Parlamentares',{}).get('Parlamentar',[]) if sen_current.ok else []
dc=Counter(str(x.get('id')) for x in deputies)
sc=Counter(str(x.get('IdentificacaoParlamentar',{}).get('CodigoParlamentar')) for x in senators)
display(pd.DataFrame([{'casa':'camara','linhas':len(deputies),'IDs_distintos':len(dc),
                       'partido_nulo':sum(not x.get('siglaPartido') for x in deputies),'UF_nula':sum(not x.get('siglaUf') for x in deputies)},
                      {'casa':'senado','linhas':len(senators),'IDs_distintos':len(sc),
                       'partido_nulo':sum(not x.get('IdentificacaoParlamentar',{}).get('SiglaPartidoParlamentar') for x in senators),
                       'UF_nula':sum(not x.get('IdentificacaoParlamentar',{}).get('UfParlamentar') for x in senators)}]))
good=not page_errors and sen_current.ok and len(deputies)>0 and len(senators)>0 and len(dc)==len(deputies) and len(sc)==len(senators)
record('04','composicao_atual','ambas','/deputados e /senador/lista/atual.json',len(deputies)+len(senators),
       'Listagens atuais paginadas sem IDs duplicados e com partido/UF observados',
       {'deputados':len(deputies),'senadores':len(senators),'duplicatas_camara':len(deputies)-len(dc),
        'duplicatas_senado':len(senators)-len(sc)},'PASSOU' if good else 'INCONCLUSIVO',
       'Apenas retrato atual; histórico exige vigência. '+str(page_errors[:2])+' '+sen_current.error)
"""),
        ("markdown", "## Senado: mandato e filiações têm vigência; partido atual não serve para voto antigo"),
        ("code", """
senator_id='5672'
responses={kind:probe.json(api_senado(f'senador/{senator_id}/{kind}.json')) for kind in ('mandatos','filiacoes')}
for kind,r in responses.items():
    if r.ok:
        print(kind,'envelope:',list(r.data),'parlamentar:',list(next(iter(r.data.values())).get('Parlamentar',{})))
    else: print(kind,r.error)
aff=responses['filiacoes']
filiacoes=[]
if aff.ok:
    parlamentar=next(iter(aff.data.values())).get('Parlamentar',{})
    raw=parlamentar.get('Filiacoes',{}).get('Filiacao',[]) if isinstance(parlamentar.get('Filiacoes'),dict) else []
    filiacoes=raw if isinstance(raw,list) else [raw]
display(pd.json_normalize(filiacoes).head(8) if filiacoes else pd.DataFrame())
party_at={}
for date in ('2023-10-21','2026-09-01'):
    valid=[x for x in filiacoes if (x.get('DataFiliacao') or '9999')<=date<= (x.get('DataDesfiliacao') or '9999')]
    party_at[date]=[x.get('Partido',{}).get('SiglaPartido') for x in valid]
print('Partido nas datas amostradas:',party_at)
record('04','filiacao_temporal','senado',api_senado(f'senador/{senator_id}/filiacoes.json'),len(filiacoes),
       'Identificar intervalos de filiação e partido vigente em duas datas',
       {'filiacoes':len(filiacoes),'partido_por_data':party_at},
       'PASSOU' if all(len(v)==1 for v in party_at.values()) else 'INCONCLUSIVO',
       'Um senador não valida todos os mandatos/licenças nem todas as mudanças históricas')
"""),
        ("markdown", "## Cruzamento entre Casas: somente identificador oficial resolvido"),
        ("code", """
sen=[x for x in projects if x['fonte']=='senado'][:6]
candidates=[]
for p in sen:
    r=probe.json(p['url'])
    if not r.ok: continue
    d=r.data
    candidates.append({'idProcesso':d.get('id'),'identificacao':d.get('identificacao'),
                       'identificacaoExterna':d.get('identificacaoExterna'),
                       'idProcessoCasaInicial':d.get('idProcessoCasaInicial'),
                       'siglaCasaIniciadora':d.get('siglaCasaIniciadora')})
display(pd.DataFrame(candidates))
explicit=sum(bool(x['identificacaoExterna'] or x['idProcessoCasaInicial']) for x in candidates)
record('04','vinculo_entre_casas','ambas','campos de origem nos detalhes do Senado',len(candidates),
       'Usar somente identificador cruzado documentado e resolvido na Câmara',
       {'candidatos_com_campo':explicit,'vinculos_resolvidos':0},'INCONCLUSIVO',
       'Campos observados não bastam sem confirmar identificador nativo da Câmara; nenhum join automático')
"""),
    ])


def build_05() -> None:
    notebook("05_presenca_e_votos.ipynb", [
        ("markdown", """# 05 — Presença em sessões e participação em votações

São medidas diferentes. Arquivos anuais são limitados a 80 MB. A ausência de voto individual não significa falta à sessão. O notebook não calcula taxa enquanto elegibilidade ou códigos forem incertos.
"""),
        ("code", COMMON + """
import csv, io
from collections import Counter
probe=Probe('05',max_calls=100)
assert manifest_rows(), 'Execute 03 primeiro.'
"""),
        ("markdown", "## Câmara: evento concluído, presença em API e arquivo"),
        ("code", """
event_id='82870'
event=probe.json(api_camara(f'eventos/{event_id}'))
att=probe.json(api_camara(f'eventos/{event_id}/deputados'))
url='https://dadosabertos.camara.leg.br/arquivos/eventosPresencaDeputados/csv/eventosPresencaDeputados-2026.csv'
bulk=probe.fetch(url)
api_ids={str(x.get('id')) for x in rows_camara(att.data)} if att.ok else set()
head=csv_head(bulk.content) if bulk.ok else []
columns=list(head[0]) if head else []
matches=[]
if bulk.ok:
    text=bulk.content.decode('utf-8-sig',errors='replace')
    delimiter=';' if text[:4096].count(';')>text[:4096].count(',') else ','
    reader=csv.DictReader(io.StringIO(text),delimiter=delimiter)
    event_col=next((c for c in reader.fieldnames if c.lower() in ('idevento','evento_id')),None)
    if event_col: matches=[r for r in reader if r.get(event_col)==event_id]
file_ids={str(r.get('idDeputado')) for r in matches if r.get('idDeputado')}
display(pd.DataFrame([{'evento':event_id,'situacao':(event.data or {}).get('dados',{}).get('situacao') if event.ok else None,
                      'API_presentes':len(api_ids),'arquivo_linhas_evento':len(matches),
                      'IDs_somente_API':len(api_ids-file_ids),'IDs_somente_arquivo':len(file_ids-api_ids),
                      'arquivo_colunas':columns}]))
record('05','presenca_camara','camara',url,len(matches),'Mesmo evento concluído em API e arquivo; denominador requer elegibilidade',
       {'API_presentes':len(api_ids),'arquivo_linhas_evento':len(matches),'IDs_somente_API':len(api_ids-file_ids),
        'IDs_somente_arquivo':len(file_ids-api_ids),'colunas':columns},
       'INCONCLUSIVO','Comparar IDs e regras de tipos de sessão, mandato e licença antes de taxa; falha: '+(bulk.error or att.error))
"""),
        ("markdown", "## Senado: localizar fonte oficial de presença antes de qualquer taxa"),
        ("code", """
catalog=list(csv.DictReader((root/'docs/catalogo_recursos.csv').open(encoding='utf-8-sig',newline='')))
import re
possible=[r for r in catalog if r['source']=='senado' and re.search(r'presen[çc]a|frequ[êe]ncia|comparecimento',
          (r['name']+' '+r['route_or_url']).lower())]
display(pd.DataFrame([{'tipo':r['resource_type'],'nome':r['name'],'url':r['route_or_url']} for r in possible]).head(20))
record('05','presenca_senado','senado','catálogo local e OpenAPI oficial',len(possible),
       'Fonte de presença e denominador de elegibilidade documentados',{'candidatos_catalogo':len(possible),'fonte_validada':0},
       'INCONCLUSIVO','Candidatos identificados são tipos de comparecimento em votação, não registros de presença em sessão; taxa bloqueada')
"""),
        ("markdown", "## Votos: cobertura individual, arquivo e códigos brutos"),
        ("code", """
votes_list=probe.json(api_camara('votacoes'),{'dataInicio':'2025-10-21','dataFim':'2025-10-22','itens':8})
ids=[x.get('id') for x in rows_camara(votes_list.data) if x.get('id')] if votes_list.ok else []
detail=[]
for vid in ids[:6]:
    d=probe.json(api_camara(f'votacoes/{vid}'))
    v=probe.json(api_camara(f'votacoes/{vid}/votos'))
    detail.append({'id':vid,'aprovacao':(d.data or {}).get('dados',{}).get('aprovacao') if d.ok else None,
                   'votos_individuais':len(rows_camara(v.data)) if v.ok else None,'erro':v.error})
display(pd.DataFrame(detail))
url='https://dadosabertos.camara.leg.br/arquivos/votacoesVotos/csv/votacoesVotos-2025.csv'
bulk=probe.fetch(url)
head=csv_head(bulk.content) if bulk.ok else []
columns=list(head[0]) if head else []
target_id=head[0].get('idVotacao') if head else None
file_votes=0
if bulk.ok and target_id:
    text=bulk.content.decode('utf-8-sig',errors='replace')
    delimiter=';' if text[:4096].count(';')>text[:4096].count(',') else ','
    file_votes=sum(row.get('idVotacao')==target_id for row in csv.DictReader(io.StringIO(text),delimiter=delimiter))
target_api=probe.json(api_camara(f'votacoes/{target_id}/votos')) if target_id else None
target_api_votes=len(rows_camara(target_api.data)) if target_api and target_api.ok else None
display(pd.DataFrame([{'votacao_positiva_arquivo':target_id,'votos_arquivo':file_votes,'votos_API':target_api_votes}]))
record('05','votos_camara','camara',url,len(detail),'Identificar votações com votos individuais; arquivo anual e endpoint reconciliáveis',
       {'votacoes_amostradas':len(detail),'com_votos':sum((x['votos_individuais'] or 0)>0 for x in detail),
        'exemplo_positivo_id':target_id,'votos_arquivo_exemplo':file_votes,'votos_API_exemplo':target_api_votes,'colunas_arquivo':columns},
       'INCONCLUSIVO','Voto ausente no endpoint não identifica abstenção; nominalidade e cobertura a validar. '+bulk.error)
sen=probe.json(api_senado('votacao.json'),{'dataInicio':'2025-10-21','dataFim':'2025-10-21'})
records=sen.data if sen.ok and isinstance(sen.data,list) else []
codes=Counter(v.get('siglaVotoParlamentar') for x in records for v in x.get('votos',[]))
display(pd.DataFrame([{'codigo_bruto':k,'n':v} for k,v in codes.items()]))
record('05','codigos_voto_senado','senado',sen.url,len(records),'Preservar todos os códigos; mapear apenas após dicionário oficial',
       {'votacoes':len(records),'codigos':dict(codes)},'INCONCLUSIVO',
       'Votou e demais códigos ainda não determinam direção ou ausência; '+sen.error)
"""),
    ])


def build_06() -> None:
    notebook("06_projeto_votacao_norma.ipynb", [
        ("markdown", """# 06 — Projeto → votação → decisão → norma

Uma aprovação na votação não prova conclusão na Casa; uma proposição afetada não é necessariamente o objeto votado. Inspecionar exemplos com e sem vínculos e preservar incertezas do registro oficial.

Referência: [limitações documentadas da Câmara](https://dadosabertos.camara.leg.br/howtouse/2020-02-07-dados-votacoes.html).
"""),
        ("code", COMMON + """
from collections import Counter
probe=Probe('06',max_calls=100)
manifest=manifest_rows()
assert manifest, 'Execute 03 primeiro.'
"""),
        ("markdown", "## Câmara: projeto sem vínculo e votação com objeto/afetados"),
        ("code", """
projects=[x for x in manifest if x['fonte']=='camara' and x['entidade']=='projeto'][:6]
projects += [{'id':'117992','tipo':'caso sem voto amostrado','fonte':'camara'}]
counts=[]
for p in projects:
    r=probe.json(api_camara(f"proposicoes/{p['id']}/votacoes"))
    counts.append({'id_projeto':p['id'],'tipo':p['tipo'],'votacoes_vinculadas':len(rows_camara(r.data)) if r.ok else None,'erro':r.error})
display(pd.DataFrame(counts))
vote=probe.json(api_camara('votacoes/2611313-34'))
d=(vote.data or {}).get('dados',{}) if vote.ok else {}
print('Campos do detalhe:',list(d))
print('Objeto/afetadas:',{k:len(v) if isinstance(v,list) else bool(v) for k,v in d.items() if 'propos' in k.lower() or 'objeto' in k.lower()})
record('06','vinculo_camara','camara','/proposicoes/{id}/votacoes + /votacoes/{id}',len(counts),
       'Distinguir objeto possível e proposições afetadas; não inferir inexistência de voto de lista vazia',
       {'projetos':len(counts),'com_vinculo':sum((x['votacoes_vinculadas'] or 0)>0 for x in counts),
        'campos_detalhe':list(d)},'INCONCLUSIVO','Cobertura e objeto real exigem comparação com arquivos e ficha de tramitação')
"""),
        ("markdown", "## Arquivos de objetos possíveis e proposições afetadas"),
        ("code", """
base='https://dadosabertos.camara.leg.br/arquivos'
names=('votacoesObjetos','votacoesProposicoes')
results=[]
for name in names:
    url=f'{base}/{name}/csv/{name}-2025.csv'
    r=probe.fetch(url,limit=80_000_000)
    sample=csv_head(r.content) if r.ok else []
    results.append({'relação':name,'HTTP':r.status,'URL':r.url,'bytes':len(r.content or b''),
                    'colunas':list(sample[0]) if sample else [],'erro':r.error})
display(pd.DataFrame(results))
record('06','arquivos_relacao_votacao','camara',base,len(results),
       'Confirmar nomes, cabeçalhos e disponibilidade dos dois conjuntos distintos',
       {'arquivos':{x['relação']:{'HTTP':x['HTTP'],'colunas':x['colunas'],'erro':x['erro']} for x in results}},
       'PASSOU' if all(x['HTTP']==200 and x['colunas'] for x in results) else 'INCONCLUSIVO',
       'Documentação antiga cita outro nome; usar o nome efetivo do portal após conferir cabeçalhos')
"""),
        ("markdown", "## Senado: idProcesso, voto, tramitação e normaGerada"),
        ("code", """
v=probe.json(api_senado('votacao.json'),{'codigoParlamentar':'5672','dataInicio':'2023-02-01','dataFim':'2023-02-28'})
votes=v.data if v.ok and isinstance(v.data,list) else []
links=[]
for vote in votes[:3]:
    pid=vote.get('idProcesso')
    p=probe.json(api_senado(f'processo/{pid}.json')) if pid else None
    links.append({'idProcesso_votacao':pid,'id_detalhe':p.data.get('id') if p and p.ok else None,
                  'codigoMateria_votacao':vote.get('codigoMateria'),
                  'codigoMateria_detalhe':p.data.get('codigoMateria') if p and p.ok else None})
display(pd.DataFrame(links))
norm=probe.json(api_senado('processo/9105948.json'))
norma=norm.data.get('normaGerada') if norm.ok else None
display(pd.DataFrame([{'processo':9105948,'norma_tipo':(norma or {}).get('siglaTipo'),
                      'numero':(norma or {}).get('numero'),'publicacao':(norma or {}).get('dataPublicacao')}]))
record('06','vinculo_e_norma_senado','senado','/votacao.json + /processo/{id}.json',len(links)+1,
       'idProcesso resolve detalhe; normaGerada é etapa separada da votação',
       {'vinculos_confirmados':sum(x['idProcesso_votacao']==x['id_detalhe'] for x in links),
        'norma_exemplo':bool(norma)},'INCONCLUSIVO',
       'Um caso positivo não estabelece cobertura nem regra de conclusão na Casa; '+v.error+' '+norm.error)
"""),
        ("markdown", "## Gate semântico: aprovação específica, conclusão na Casa e publicação"),
        ("code", """
for check,rule in [('aprovacao_votacao','Resultado válido somente para a decisão específica'),
                   ('conclusao_casa','Vocabulários e tramitação final por Casa'),
                   ('norma_publicada','Tipo de norma, publicação e vínculo de origem')]:
    record('06',check,'ambas','detalhes e tramitações amostrados',len(counts)+len(links),rule,{},
           'INCONCLUSIVO','Não gerar taxa ou funil público até validar regra e cobertura por Casa')
print('Três etapas mantidas separadas. Nenhuma taxa de aprovação calculada.')
"""),
    ])


def build_07() -> None:
    notebook("07_documentos_e_enriquecimento.ipynb", [
        ("markdown", """# 07 — PDFs, temas e evidência para enriquecimento

Extrai no máximo as três primeiras páginas de até 18 documentos, sem salvar os PDFs. `pypdf` é opcional: se faltar, o check fica inconclusivo. Rótulos candidatos **não são publicados**; todos requerem revisão humana, inclusive direção de medida.
"""),
        ("code", COMMON + """
import csv, hashlib, importlib.util, json
probe=Probe('07',max_calls=90)
manifest=manifest_rows()
assert manifest, 'Execute 03 primeiro.'
pdf_available=bool(importlib.util.find_spec('pypdf'))
print('pypdf disponível:',pdf_available)
"""),
        ("markdown", "## Seleção de documentos e versões"),
        ("code", """
import re
existing=list(csv.DictReader((root/'docs/amostra_projetos.csv').open(encoding='utf-8-sig',newline='')))
selected=existing[:12]
# Add up to one historical project per Casa/year. Missing URL remains explicit.
historical=[]
for house in ('camara','senado'):
  for year in ('2023','2024','2025'):
    item=next((x for x in manifest if x['entidade']=='projeto' and x['fonte']==house and x['ano']==year),None)
    if not item: continue
    detail=probe.json(item['url'])
    url=''
    if detail.ok and house=='camara': url=(detail.data.get('dados') or {}).get('urlInteiroTeor') or ''
    if detail.ok and house=='senado':
        doc=probe.json(api_senado('processo/documento.json'),{'idProcesso':item['id']})
        docs_data=doc.data if doc.ok and isinstance(doc.data,list) else []
        url=next((d.get('urlDocumento') for d in docs_data if d.get('urlDocumento')),'')
    historical.append({'fonte':house,'identificador':item['id'],'tipo':item['tipo'],
                       'url_documento':url,'temas_oficiais':'[]','ano_amostra':year})
selected += historical
docs=[]; snippets=[]
for row in selected:
    url=row['url_documento']
    r=probe.fetch(url,limit=15_000_000) if url else None
    pages=text_chars=0; evidence=''; error=r.error if r else 'sem URL'
    if r and r.ok and pdf_available:
        try:
            from pypdf import PdfReader
            from io import BytesIO
            reader=PdfReader(BytesIO(r.content))
            pages=len(reader.pages)
            page_texts=[reader.pages[i].extract_text() or '' for i in range(min(3,pages))]
            text_chars=sum(map(len,page_texts))
            evidence=hashlib.sha256(r.content).hexdigest()[:16]
            for page_num,text_page in enumerate(page_texts,1):
                for pattern,topic in ((r'meio ambiente|ambiental|floresta','ambiente e clima'),
                                      (r'saúde|hospital|medicamento','saúde'),
                                      (r'tribut|imposto|contribuição','economia e tributos'),
                                      (r'trabalho|emprego|salário','trabalho')):
                    match=re.search(pattern,text_page,re.IGNORECASE)
                    if match:
                        snippet=' '.join(text_page[max(0,match.start()-55):match.end()+90].split())[:170]
                        snippets.append({'fonte':row['fonte'],'id_projeto':row['identificador'],'url_documento':r.url,
                                         'pagina':page_num,'trecho':snippet,'tema_comum_candidato':topic,
                                         'dimensao':'','direcao':'indeterminado','status_revisao':'pendente',
                                         'motivo':'Palavra-chave localizou trecho; contexto e proposta ainda não revisados'})
                        break
                if any(s['id_projeto']==row['identificador'] for s in snippets): break
        except Exception as exc: error=f'extração: {type(exc).__name__}: {exc}'
    docs.append({'fonte':row['fonte'],'id':row['identificador'],'tipo':row['tipo'],
                 'ano':row.get('ano_amostra','2026'),
                 'HTTP':r.status if r else None,'mime':(r.headers or {}).get('Content-Type') if r else None,
                 'bytes':len(r.content or b'') if r else 0,'paginas':pages,'caracteres_3_paginas':text_chars,
                 'hash_prefixo':evidence,'url':r.url if r else url,'erro':error})
display(pd.DataFrame(docs).drop(columns=['url','erro']))
record('07','pdfs','ambas','URLs oficiais do manifesto 2026',len(docs),
       'HTTP/PDF, limite, versão/hash e texto por página medidos sem assumir extração universal',
       {'acessiveis':sum(x['HTTP']==200 for x in docs),'texto_extraivel':sum(x['caracteres_3_paginas']>0 for x in docs),
        'anos':sorted(set(x['ano'] for x in docs)),
        'falhas':[x['id'] for x in docs if x['erro']]},
       'PASSOU' if pdf_available and all(x['HTTP']==200 and x['caracteres_3_paginas']>0 for x in docs) else 'INCONCLUSIVO',
       'Páginas sem texto e PDFs históricos ainda exigem amostra; pypdf ausente' if not pdf_available else '')
"""),
        ("markdown", "## Temas oficiais faltantes e candidatos sem classificação publicada"),
        ("code", """
theme_rows=[{'fonte':x['fonte'],'tipo':x['tipo'],'id':x['identificador'],
             'temas':json.loads(x['temas_oficiais'] or '[]')} for x in existing]
display(pd.DataFrame([{'fonte':x['fonte'],'tipo':x['tipo'],'id':x['id'],'n_temas':len(x['temas'])} for x in theme_rows]))
candidate_path=OUT/'candidatos_rotulos.csv'
with candidate_path.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['fonte','id_projeto','url_documento','pagina','trecho','tema_comum_candidato',
                                    'dimensao','direcao','status_revisao','motivo'])
    w.writeheader()
    w.writerows(snippets)
display(pd.DataFrame(snippets)[['fonte','id_projeto','pagina','tema_comum_candidato','trecho']] if snippets else pd.DataFrame())
record('07','temas_e_rotulos','ambas',str(candidate_path),len(theme_rows),
       'Preservar tema oficial; rótulo derivado só com documento, página, trecho e revisão',
       {'temas_faltantes':sum(not x['temas'] for x in theme_rows),'candidatos_para_revisao':len(snippets),'rotulos_publicados':0},
       'INCONCLUSIVO','Candidatos aguardam leitura e revisão; não inferir direção de ementa ou palavras-chave')
"""),
        ("markdown", "## Ideologia partidária: disponibilidade não equivale a cobertura atual"),
        ("code", """
sources={'Pesquisa Legislativa Brasileira':'https://doi.org/10.7910/DVN/WM9IZ8',
         'V-Party':'https://v-dem.net/data/v-party-dataset/'}
heads=[]
for name,url in sources.items():
    r=probe.fetch(url,method='HEAD')
    heads.append({'fonte':name,'HTTP':r.status,'URL_final':r.url,'erro':r.error})
display(pd.DataFrame(heads))
record('07','ideologia_atual','externa',' | '.join(sources.values()),len(heads),
       'Escala, ano, partidos atuais e correspondência partidária precisam ser verificáveis',
       {'fontes_acessiveis':sum(x['HTTP']==200 for x in heads),'partidos_atuais_mapeados':0},
       'INCONCLUSIVO','Acesso à página não comprova cobertura da 57ª legislatura; indicador desativado')
"""),
    ])


def build_08() -> None:
    notebook("08_reconciliacao_e_decisao.ipynb", [
        ("markdown", """# 08 — Reconciliação e decisão de construção

Execute após 03–07. Este notebook simula bronze → silver → contagens apenas para a amostra. `PASSOU` é evidência restrita à amostra e não prova completude histórica. A decisão por funcionalidade usa checks obrigatórios explícitos; checks inconclusivos mantêm a funcionalidade pendente ou bloqueada.
"""),
        ("code", COMMON + """
import csv, json
from collections import Counter
probe=Probe('08',max_calls=70)
manifest=manifest_rows()
assert manifest, 'Execute 03 primeiro.'
"""),
        ("markdown", "## Respostas brutas → linhas tipadas → agregação sem multiplicação"),
        ("code", """
projects=[x for x in manifest if x['entidade']=='projeto']
raw=[]; failures=[]
for item in projects:
    r=probe.json(item['url'])
    if not r.ok: failures.append({'id':item['id'],'erro':r.error}); continue
    d=r.data.get('dados',{}) if item['fonte']=='camara' else r.data
    raw.append({'fonte':item['fonte'],'id':str(d.get('id','')),'objeto':d,'url':r.url,'horario':r.collected_at})
silver=[]
for item in raw:
    d=item['objeto']
    silver.append({'fonte':item['fonte'],'id':item['id'],
                   'tipo':d.get('siglaTipo') if item['fonte']=='camara' else d.get('sigla'),
                   'data_apresentacao':d.get('dataApresentacao') if item['fonte']=='camara' else (d.get('documento') or {}).get('dataApresentacao')})
frame=pd.DataFrame(silver)
if not frame.empty:
    frame['ano']=frame['data_apresentacao'].fillna('').str[:4]
    gold=frame.drop_duplicates(['fonte','id']).groupby(['fonte','ano','tipo'],dropna=False).size().rename('projetos_unicos').reset_index()
else: gold=pd.DataFrame()
display(frame.head(18))
display(gold)
duplicate=int(frame.duplicated(['fonte','id']).sum()) if not frame.empty else 0
counts={'solicitados':len(projects),'bronze':len(raw),'silver':len(frame),'gold_total':int(gold['projetos_unicos'].sum()) if not gold.empty else 0,
        'IDs_duplicados':duplicate,'falhas':len(failures),
        'ano_apresentacao_divergente_manifesto':sum((item['data_apresentacao'] or '')[:4]!=next((p['ano'] for p in projects if p['fonte']==item['fonte'] and p['id']==item['id']),'') for item in silver)}
record('08','reconciliacao_projetos','ambas','detalhes do manifesto',len(raw),
       'Linhas brutas e normalizadas preservam projetos únicos sem multiplicação no agregado',counts,
       'PASSOU' if not failures and duplicate==0 and counts['ano_apresentacao_divergente_manifesto']==0 and counts['bronze']==counts['silver']==counts['gold_total'] else 'INCONCLUSIVO',str(failures[:3]))
"""),
        ("markdown", "## Paginação e incerteza de cobertura"),
        ("code", """
page1=probe.json(api_camara('proposicoes'),{'ano':2026,'siglaTipo':'PL','dataApresentacaoInicio':'2026-07-01',
          'dataApresentacaoFim':'2026-09-30','itens':5,'pagina':1,'ordem':'ASC','ordenarPor':'id'})
page2=probe.json(api_camara('proposicoes'),{'ano':2026,'siglaTipo':'PL','dataApresentacaoInicio':'2026-07-01',
          'dataApresentacaoFim':'2026-09-30','itens':5,'pagina':2,'ordem':'ASC','ordenarPor':'id'})
ids1=[str(x.get('id')) for x in rows_camara(page1.data)] if page1.ok else []
ids2=[str(x.get('id')) for x in rows_camara(page2.data)] if page2.ok else []
overlap=len(set(ids1)&set(ids2))
wrong_year=sum(str(x.get('dataApresentacao',''))[:4]!='2026' for x in rows_camara(page1.data)+rows_camara(page2.data))
display(pd.DataFrame([{'pagina':1,'linhas':len(ids1),'IDs':ids1},{'pagina':2,'linhas':len(ids2),'IDs':ids2}]))
record('08','paginacao_camara','camara',f'{page1.url} | {page2.url}',len(ids1)+len(ids2),
       'Páginas adjacentes não repetem IDs e respeitam data de apresentação',{'pagina1':len(ids1),'pagina2':len(ids2),'sobreposicao':overlap,'ano_incoerente':wrong_year},
       'PASSOU' if page1.ok and page2.ok and ids1 and ids2 and overlap==0 and wrong_year==0 else 'INCONCLUSIVO',
       'Páginas podem mudar durante atualização da fonte; amostra não prova snapshot estável')
"""),
        ("markdown", "## Matriz de decisão e relatório pequeno"),
        ("code", """
with CHECKS.open(encoding='utf-8-sig',newline='') as f: checks=list(csv.DictReader(f))
latest={(x['notebook'],x['check']):x for x in checks}
requirements={
 'composição atual': [('03','contrato_camara'),('03','contrato_senado'),('04','composicao_atual')],
 'exploração de projetos': [('03','estratos_manifesto'),('04','ids_projeto'),('08','reconciliacao_projetos')],
 'presença Câmara': [('05','presenca_camara')],
 'presença Senado': [('05','presenca_senado')],
 'participação em votações': [('05','votos_camara'),('05','codigos_voto_senado')],
 'aprovação e norma': [('06','aprovacao_votacao'),('06','conclusao_casa'),('06','norma_publicada')],
 'classificação ideológica': [('07','ideologia_atual')],
 'direção de medida': [('07','temas_e_rotulos')]}
blocked={'presença Senado','classificação ideológica','direção de medida'}
decisions=[]
for feature,keys in requirements.items():
    states=[latest.get(k,{}).get('estado','AUSENTE') for k in keys]
    state='apto para iniciar' if all(x=='PASSOU' for x in states) else ('bloqueado' if feature in blocked else 'pendente')
    decisions.append({'funcionalidade':feature,'decisão':state,'checks':', '.join(f'{a}/{b}: {latest.get((a,b),{}).get("estado","AUSENTE")}' for a,b in keys)})
display(pd.DataFrame(decisions))
report=OUT/'resumo.md'
lines=['# Validação exploratória — relatório de decisão','',
       'Este relatório reflete somente a amostra. PASSOU não prova completude histórica.','',
       '## Funcionalidades','',
       '| Funcionalidade | Decisão | Evidência |','| --- | --- | --- |']
for x in decisions: lines.append(f"| {x['funcionalidade']} | {x['decisão']} | {x['checks']} |")
lines += ['', '## Checks', '', '| Notebook/check | Estado | Amostra | Motivo |','| --- | --- | ---: | --- |']
for x in sorted(checks,key=lambda r:(r['notebook'],r['check'])):
    reason=x['motivo'].replace('|','/')[:180]
    lines.append(f"| {x['notebook']}/{x['check']} | {x['estado']} | {x['amostra_n']} | {reason} |")
lines += ['', 'Pendências não autorizam taxa, ranking ou rótulo público. Revisar docs/especificacao_funcional.md antes da implementação.']
report.write_text('\\n'.join(lines)+'\\n',encoding='utf-8')
print('Relatório:',report,'| checks:',len(checks),'| chamadas deste notebook:',probe.calls)
"""),
    ])


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    for builder in (build_03, build_04, build_05, build_06, build_07, build_08):
        builder()
    print("Generated notebooks 03–08 in", DEST)


if __name__ == "__main__":
    main()
