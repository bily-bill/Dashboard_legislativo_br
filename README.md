# Painel Legislativo Brasileiro

Projeto exploratório para coletar dados públicos da Câmara dos Deputados e do Senado Federal, preservá-los em uma camada bronze, preparar tabelas analíticas e publicar visualizações interativas.

## Etapa atual: primeiro site estático

As APIs, arquivos e relações candidatas foram explorados nos notebooks. A primeira exportação pública contém listagens de PL, PLP e PEC apresentados desde 2023, a composição atual de cada Casa e agregados para o painel. Os JSONs estão em [`public/dados/v1/`](public/dados/v1/) e ocupam cerca de 16 MB. O site em [`public/`](public/) apresenta composição atual, séries de projetos, busca e detalhe com fontes e limitações. Bronze/Silver persistentes, temas completos, tramitações e votações ainda não foram implementados.

## Abrir o site localmente

Na raiz do repositório, execute `python -m http.server 8000 --directory public` e abra `http://localhost:8000/`. Use um servidor HTTP; abrir o HTML diretamente como arquivo impede as leituras `fetch` dos JSONs. Não é necessário instalar pacotes JavaScript nem executar um build. A versão de Plotly.js usada nos gráficos está fixada em `public/assets/vendor/`, acompanhada da licença.

O navegador lê apenas o snapshot JSON v1. O ano nos filtros de projetos é o **ano da apresentação**; composição é sempre o retrato da coleta mais recente. Presença, votações, aprovação final, ideologia e categorias temáticas não aparecem como indicadores porque sua cobertura ou interpretação ainda depende de validação.

## Publicar no Netlify

Conecte este repositório do GitHub ao Netlify. O arquivo [`netlify.toml`](netlify.toml) define `public` como pasta de publicação e o site não exige comando de build. Após cada commit na branch publicada, o Netlify entrega os HTMLs, a biblioteca Plotly e os JSONs do mesmo snapshot. A conexão da conta e o domínio devem ser configurados no painel do Netlify.

Comece por:

1. `docs/fontes_e_endpoints.md` — documentação oficial e mapa inicial de recursos.
2. `notebooks/exploracao/00_camara_api.ipynb` — amostras da API da Câmara.
3. `notebooks/exploracao/01_senado_api.ipynb` — amostras da API do Senado.
4. `docs/catalogo_recursos.csv` — snapshot de endpoints e arquivos oficiais; atualize com `python scripts/refresh_catalog.py`.
5. `docs/chaves_relacionamentos.md` — observações de chaves candidatas e diagrama ER preliminar.
6. `notebooks/exploracao/02_chaves_e_relacionamentos.ipynb` — consultas pequenas para conferir relações entre entidades.
7. `docs/especificacao_funcional.md` — matriz de funcionalidades, fórmulas, filtros e disponibilidade.
8. `docs/viabilidade_features.md` — evidências dirigidas, arquivos anuais e verificações pendentes.
9. `docs/taxonomia_e_revisao.md` — temas oficiais, taxonomia comum e revisão de rótulos.
10. `docs/mapa_telas.md` — navegação e prioridade dos visuais.
11. `docs/amostra_projetos.csv` — 12 projetos amostrados; gere novamente com `python scripts/build_feature_sample.py` e avalie PDFs com o Python que tenha `pypdf` usando `python scripts/assess_sample_pdfs.py`.
12. `notebooks/exploracao/03_contratos_e_coleta.ipynb` até `08_reconciliacao_e_decisao.ipynb` — validação estratificada antes da aplicação. Execute em ordem; o manifesto, checks e decisão ficam em `docs/validacao/`.
13. `docs/arquitetura_armazenamento.md` — proposta de Bronze/Silver/Gold, GitHub Actions, banco gratuito e Netlify.
14. `public/dados/v1/manifesto.json` — índice, período, totais e hashes dos arquivos publicados; `cobertura.json` explicita o que falta.

## Hipótese de fluxo (a validar)

`fontes oficiais → exportador Python → JSONs públicos por Casa/ano/tipo + agregados → HTML e Plotly no navegador`

A exportação atual é reconstruída integralmente fora do website e publicada após validar tipo, data e IDs. Não presumir que tabelas das duas Casas compartilham chaves ou semântica sem validar os identificadores e esquemas.

## Ambiente inicial

Os notebooks usam Python, `requests` e `pandas`. Instale JupyterLab ou Notebook no ambiente de trabalho e essas dependências antes de executá-los. Os endpoints são públicos e não exigem token segundo a documentação consultada. Use chamadas de amostra e paginação cuidadosa; os limites e condições de uso precisam ser confirmados antes de uma carga ampla.

Para a bateria 03–08, instale também `pypdf` no kernel (`%pip install requests pandas pypdf`); `plotly` é opcional nesta validação. O notebook 03 verifica o ambiente sem instalar pacotes automaticamente. Cada notebook impõe até 80 MB por arquivo e não armazena PDFs ou respostas brutas completas. O código compartilhado está em `scripts/validation_utils.py`; para regerar os seis notebooks a partir da fonte, execute `python scripts/build_validation_notebooks.py`.

Para recriar os JSONs públicos: `python -m pip install -r requirements.txt` e `python scripts/export_static_data.py`. Use `--from-year 2026` para um recorte menor. O workflow `.github/workflows/refresh-data.yml` permite atualização **manual** no GitHub após criar o repositório. Os JSONs são versionados; `data/bronze/` e `data/silver/` permanecem fora do Git.

## Próxima etapa

Validar separadamente denominadores de presença, códigos de voto, vínculos projeto–votação, classificação ideológica e direção de medida antes de expor esses indicadores. Aprimorar a busca se o volume de JSONs deixar a leitura no navegador lenta.
