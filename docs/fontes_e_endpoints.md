# Fontes oficiais e mapa inicial de endpoints

Levantamento atualizado em 9 de outubro de 2026. O inventário é uma hipótese de exploração, não uma especificação de ingestão. O snapshot de **496 registros** está em [`catalogo_recursos.csv`](catalogo_recursos.csv): 79 endpoints da Câmara, 157 do Senado, 32 modelos de URL de arquivos da Câmara e 228 links de arquivos/feeds observados nos portais. Links repetidos em grupos distintos são preservados por contexto. Atualize-o com `python scripts/refresh_catalog.py`. A Câmara publica OpenAPI e pagina as listagens; o Senado também tem OpenAPI, mas seus caminhos e formatos diferem. Conferir sempre a especificação atual antes de ampliar a coleta.

## Câmara dos Deputados

- Portal: [Dados Abertos da Câmara](https://dadosabertos.camara.leg.br/)
- Swagger UI: [documentação interativa](https://dadosabertos.camara.leg.br/swagger/api.html)
- OpenAPI JSON: [api/v2/api-docs](https://dadosabertos.camara.leg.br/api/v2/api-docs)
- Base URL: `https://dadosabertos.camara.leg.br/api/v2/`
- Respostas JSON ou XML; envelope padrão com `dados` e `links`. Listagens são paginadas; documentação consultada informa 15 por padrão e máximo 100 itens por requisição.
- Há também arquivos para download de grandes conjuntos. Os 32 modelos de URL publicados na aba `Arquivos` aparecem como `bulk_url_template` no catálogo, com `{ano}` e `{formato}` quando aplicável. Exemplos para indicadores do painel estão em [`viabilidade_features.md`](viabilidade_features.md). Confirmar o arquivo concreto antes de ingeri-lo.

| Domínio | Rotas para explorar | Questões para o experimento |
| --- | --- | --- |
| Deputados | `/deputados`, `/deputados/{id}`, `/deputados/{id}/historico`, `/deputados/{id}/orgaos` | IDs persistentes? Diferença entre exercício atual e histórico por legislatura? |
| Despesas | `/deputados/{id}/despesas` | A rota sem datas retorna apenas seis meses; mapear anos, campos monetários, fornecedor e paginação. |
| Proposições | `/proposicoes`, `/proposicoes/{id}`, `/proposicoes/{id}/autores`, `/proposicoes/{id}/tramitacoes`, `/proposicoes/{id}/temas` | Identificador, tipos, situação e relação com votações/comissões. |
| Votações | `/votacoes`, `/votacoes/{id}`, `/votacoes/{id}/votos` | Distinguir orientação/resultado do voto individual e mapear IDs ligados à proposição. |
| Eventos e órgãos | `/eventos`, `/eventos/{id}`, `/eventos/{id}/deputados`, `/orgaos`, `/partidos`, `/legislaturas` | Participação, composição temporal, legislatura e semântica de órgãos. |
| Referências | `/referencias/...` | Baixar vocabulários de situações, tipos, UFs e despesas para decodificar códigos. |

Esta tabela não pretende enumerar todos os caminhos. A lista atual e os parâmetros devem ser extraídos do OpenAPI no notebook, que também imprime as rotas por tag.

O extrator do catálogo inclui todos os GET das especificações, parâmetros e esquemas de resposta, inclusive recursos depreciados do Senado, além dos links de arquivos/feeds expostos pelo portal da Câmara e pelos seis grupos legislativos do catálogo do Senado.

## Senado Federal

- Portal e catálogo: [Dados Abertos do Senado](https://www12.senado.leg.br/dados-abertos)
- Catálogo legislativo: [conjuntos de dados](https://www12.senado.leg.br/dados-abertos/conjuntos?portal=Legislativo)
- Swagger UI: [API Dados Abertos Legislativos](https://legis.senado.leg.br/dadosabertos/api-docs/swagger-ui/index.html)
- OpenAPI 3 JSON (conferido por HTTP): `https://legis.senado.leg.br/dadosabertos/v3/api-docs`
- Base URL para serviços de API: `https://legis.senado.leg.br/dadosabertos/`
- Exemplo oficial que respondeu JSON durante o levantamento: `/senador/lista/atual.json`. O Senado também distribui conjuntos por arquivos e páginas informativas de webservices.

| Domínio | Família a localizar no OpenAPI/catálogo | Questões para o experimento |
| --- | --- | --- |
| Senadores e mandatos | lista atual/histórica, detalhes, mandatos e filiações | IDs/códigos, estrutura XML/JSON, datas de início e fim. |
| Matérias legislativas | pesquisa/lista e detalhe de matéria | Chave de matéria e correspondência com proposições da Câmara quando remetidas entre Casas. |
| Tramitação e votação | tramitações, votações, resultados e presença | Granularidade, resultado vs. voto nominal e identificadores de sessão. |
| Comissões e sessões | composição, reuniões e pauta | Membros no tempo, eventos e relações com matérias. |
| Pronunciamentos | discursos e metadados | Cobertura temporal, campos de texto e volume; avaliar separadamente por tamanho. |
| Catálogo de arquivos | CSV/XML/JSON/ZIP disponibilizados por conjunto | Frequência, URL estável, histórico completo e melhor caminho para cargas em lote. |

Os caminhos exatos do Senado serão lidos diretamente do OpenAPI, evitando fixar rotas presumidas. O Swagger UI deve ser consultado quando o JSON não estiver acessível ou o catálogo apontar para arquivos mais completos.

## Chaves e junções a validar

- Preservar sempre `fonte` (camara/senado) junto ao identificador: IDs de casas diferentes não devem ser tratados como uma chave global.
- Comparar chaves cruzadas explícitas (número/código de matéria, origem, ano e vínculos declarados pela API); evitar junção apenas por título/ementa.
- Capturar atributos temporais (legislatura, vigência de mandato, partido e composição) como relações que mudam no tempo.
- Guardar a resposta bruta, URL, parâmetros, horário UTC de coleta, status HTTP e hash do conteúdo para rastreabilidade e reprocessamento.

## Referências consultadas

- [API e arquivos da Câmara](https://dadosabertos.camara.leg.br/swagger/api.html)
- [Especificação OpenAPI da Câmara](https://dadosabertos.camara.leg.br/api/v2/api-docs)
- [Tutorial oficial de paginação da Câmara](https://dadosabertos.camara.leg.br/howtouse/2017-05-16-js-resultados-paginados.html)
- [Portal de Dados Abertos do Senado](https://www12.senado.leg.br/dados-abertos)
- [Catálogo de dados legislativos do Senado](https://www12.senado.leg.br/dados-abertos/conjuntos?portal=Legislativo)
- [OpenAPI / Swagger do Senado](https://legis.senado.leg.br/dadosabertos/api-docs/swagger-ui/index.html)
- [Webservice oficial: senadores em exercício](https://www12.senado.leg.br/dados-abertos/legislativo/parlamentares/senadores-em-exercicio/info/webservice-de-senadores-em-exercicio)
