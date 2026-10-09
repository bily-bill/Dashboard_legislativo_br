# JSONs públicos — esquema v1

- `manifesto.json`: data de geração, totais, lista de arquivos e hashes SHA-256. Leia este arquivo primeiro.
- `cobertura.json`: janelas consultadas, contagens e funcionalidades que ainda não devem aparecer como métricas.
- `projetos/{camara|senado}/{ano_apresentacao}/{pl|plp|pec}.json`: projetos separados pelo **ano de apresentação**, com `meta` e `dados`. O `ano_identificacao` permanece em campo distinto.
- `parlamentares/{camara|senado}/atuais.json`: retrato dos parlamentares em exercício no momento da coleta; não representa composição histórica.
- `indicadores/resumo.json`, `projetos_por_mes.json`, `composicao_atual.json`, `composicao_por_partido.json` e `composicao_por_uf.json`: cartões e séries prontos para Plotly, sem joins no navegador.

IDs são texto e só são únicos dentro da Casa. Campos não coletados são descritos em `cobertura.json`, em vez de publicados como arrays vazios. A aplicação deve exibir período e `gerado_em_utc` do manifesto e tratar falha de atualização sem converter dados ausentes em zero.

Para atualizar localmente: `python scripts/export_static_data.py`. O script usa `requests` e consulta a 57ª legislatura desde 2023 até hoje. Para uma execução menor: `python scripts/export_static_data.py --from-year 2026`.
