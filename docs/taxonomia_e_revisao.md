# Taxonomia comum e revisão de rótulos

Esta é uma proposta de **camada de exploração**, separada dos temas publicados pelas Casas. O nome e a hierarquia oficiais permanecem intactos e visíveis. Um projeto pode receber vários temas; a camada comum permite comparar assuntos entre Casas, mas não cria equivalência legal entre PL, PLP e PEC. A amostra em `amostra_projetos.csv` contém 12 projetos e nenhum rótulo de posição publicado.

## Dois níveis de classificação

| Nível | Origem | Exemplos na amostra | Regra de exibição |
| --- | --- | --- | --- |
| Tema oficial | Campo `temas` da Câmara ou `classificacoes` do Senado | Câmara: `Meio Ambiente e Desenvolvimento Sustentável`; Senado: `Política Social / Saúde / Saúde Pública` | Exibir com nome da Casa. Se ausente, `tema oficial ainda não informado`. Não supor `outros`. |
| Tema comum | Tabela de correspondência versionada e revisada | Ambiente e clima; saúde; trabalho; economia e tributos; administração pública; segurança e justiça; direitos e cidadania; educação; infraestrutura e mobilidade; organização do Estado | Mostrar `categoria do painel`, com método/versão. Uma classificação oficial pode mapear a mais de um tema; conflitos vão para revisão. |
| Subtema | Ementa + texto oficial com evidência | Proteção ambiental; acesso à saúde; remuneração; processo penal | Só publicar com trecho de suporte e revisão humana. `Indeterminado` quando texto/escopo não sustentam granularidade. |
| Direção de medida | Texto oficial e critério jurídico/político explícito | Para **uma medida definida**, `amplia`, `restringe`, `mantém`, `misto` ou `indeterminado` | Nunca exibir `a favor/contra mulheres` ou equivalente amplo. Exemplo de dimensão: `proteção ambiental` ou `acesso a benefício X`. Informar que descreve efeito proposto no texto, não impacto final. |

Correspondência inicial de temas oficiais para temas comuns será uma tabela revisável de pares `(casa, codigo_ou_caminho_oficial, versao_da_fonte) → [tema_comum]`. A correspondência não deve ser feita apenas por similaridade de texto. Quando a origem omitir tema, o painel pode ter um tema comum derivado da leitura do documento, identificado como tal, mas nunca fingir que é oficial.

## Registro mínimo por rótulo

`casa`, `id_projeto`, `id_documento`, `url_documento`, `data_coleta_utc`, `hash_ou_versao_documento`, `pagina`, `trecho_literal_curto`, `tema_oficial`, `tema_comum`, `subtema`, `dimensao_da_medida`, `direcao`, `justificativa`, `metodo_versao`, `confianca`, `status_revisao`, `revisor`, `data_revisao` e `motivo_de_alteracao`. Guardar também a URL da página oficial do projeto. O trecho deve apontar para texto legível do documento oficial; ementa isolada só é suficiente para tema amplo quando o escopo for inequívoco.

## Fluxo de revisão

1. Coletar metadados e documento oficial; registrar URL, horário, versão/hash e tipo. Extrair texto por página e marcar páginas sem texto para inspeção/OCR. A extração de 12/12 PDFs da amostra **não** dispensa esse controle histórico.
2. Preservar classificação oficial. Propor tema comum, subtema e, se solicitado, dimensão/direção. `Indeterminado` é resposta válida. Um modelo pode ajudar a localizar trechos, mas não publica o rótulo.
3. Revisor lê ementa, trecho citado e contexto do artigo alterado, confere página/documento e decide `aprovado`, `corrigido`, `rejeitado` ou `pendente`. Toda direção de medida exige revisão humana; divergência ou evidência ambígua permanece `pendente`.
4. Ao mudar versão do documento, texto substitutivo ou taxonomia, invalidar ou reabrir os rótulos afetados. Manter histórico de decisão e permitir correção pública com data.
5. Auditar uma amostra estratificada por Casa, tipo, tema, ano e método. Medir concordância entre revisores e erro por categoria antes de escolher regras, embeddings ou classificador. Não automatizar publicação só por confiança alta do modelo.

## Critérios de validação da pequena amostra

Os 12 projetos (2 PL, 2 PLP e 2 PEC por Casa) tiveram PDF acessível e texto extraível nas primeiras três páginas. A Câmara trouxe temas oficiais em 4 de 6; o Senado, em 6 de 6. A amostra cobre temas como ambiente, saúde, trabalho, tributos e organização estatal, suficientes para testar a estrutura de campos e a interface de revisão. Ela é pequena e concentrada em 2026: **não** estima acurácia do classificador nem frequência temática. O próximo experimento deve revisar manualmente esses 12 textos e comparar rótulos propostos com evidências antes de escolher o método de classificação.
