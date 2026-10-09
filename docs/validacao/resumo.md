# Validação exploratória — relatório de decisão

Este relatório reflete somente a amostra. PASSOU não prova completude histórica.

## Funcionalidades

| Funcionalidade | Decisão | Evidência |
| --- | --- | --- |
| composição atual | apto para iniciar | 03/contrato_camara: PASSOU, 03/contrato_senado: PASSOU, 04/composicao_atual: PASSOU |
| exploração de projetos | apto para iniciar | 03/estratos_manifesto: PASSOU, 04/ids_projeto: PASSOU, 08/reconciliacao_projetos: PASSOU |
| presença Câmara | pendente | 05/presenca_camara: INCONCLUSIVO |
| presença Senado | bloqueado | 05/presenca_senado: INCONCLUSIVO |
| participação em votações | pendente | 05/votos_camara: INCONCLUSIVO, 05/codigos_voto_senado: INCONCLUSIVO |
| aprovação e norma | pendente | 06/aprovacao_votacao: INCONCLUSIVO, 06/conclusao_casa: INCONCLUSIVO, 06/norma_publicada: INCONCLUSIVO |
| classificação ideológica | bloqueado | 07/ideologia_atual: INCONCLUSIVO |
| direção de medida | bloqueado | 07/temas_e_rotulos: INCONCLUSIVO |

## Checks

| Notebook/check | Estado | Amostra | Motivo |
| --- | --- | ---: | --- |
| 03/ano_vs_apresentacao | PASSOU | 10 | Filtro de apresentação explícito obrigatório; registros de projeto podem ter ano de identificação diferente |
| 03/contrato_camara | PASSOU | 79 |  |
| 03/contrato_senado | PASSOU | 157 |  |
| 03/estados_erro_e_vazio | PASSOU | 2 | Não converter falha em zero observado |
| 03/estratos_manifesto | PASSOU | 34 | Amostra não substitui cobertura histórica; estratos faltantes requerem investigação |
| 03/limite_janela_camara | PASSOU | 2 | Respeitar limite da API, inclusive na paginação |
| 03/presenca_camara_2026 | PASSOU | 1 |  |
| 03/temas_camara_2026 | PASSOU | 1 |  |
| 03/votos_camara_2025 | PASSOU | 1 |  |
| 04/composicao_atual | PASSOU | 594 | Apenas retrato atual; histórico exige vigência. []  |
| 04/filiacao_temporal | PASSOU | 4 | Um senador não valida todos os mandatos/licenças nem todas as mudanças históricas |
| 04/ids_projeto | PASSOU | 12 | [] |
| 04/relacoes_camara | PASSOU | 8 | []; unicidade global não demonstrada |
| 04/vinculo_entre_casas | INCONCLUSIVO | 6 | Campos observados não bastam sem confirmar identificador nativo da Câmara; nenhum join automático |
| 05/codigos_voto_senado | INCONCLUSIVO | 1 | Votou e demais códigos ainda não determinam direção ou ausência;  |
| 05/presenca_camara | INCONCLUSIVO | 16 | Comparar IDs e regras de tipos de sessão, mandato e licença antes de taxa; falha:  |
| 05/presenca_senado | INCONCLUSIVO | 4 | Candidatos identificados são tipos de comparecimento em votação, não registros de presença em sessão; taxa bloqueada |
| 05/votos_camara | INCONCLUSIVO | 6 | Voto ausente no endpoint não identifica abstenção; nominalidade e cobertura a validar.  |
| 06/aprovacao_votacao | INCONCLUSIVO | 8 | Não gerar taxa ou funil público até validar regra e cobertura por Casa |
| 06/arquivos_relacao_votacao | PASSOU | 2 | Documentação antiga cita outro nome; usar o nome efetivo do portal após conferir cabeçalhos |
| 06/conclusao_casa | INCONCLUSIVO | 8 | Não gerar taxa ou funil público até validar regra e cobertura por Casa |
| 06/norma_publicada | INCONCLUSIVO | 8 | Não gerar taxa ou funil público até validar regra e cobertura por Casa |
| 06/vinculo_camara | INCONCLUSIVO | 7 | Cobertura e objeto real exigem comparação com arquivos e ficha de tramitação |
| 06/vinculo_e_norma_senado | INCONCLUSIVO | 2 | Um caso positivo não estabelece cobertura nem regra de conclusão na Casa;   |
| 07/ideologia_atual | INCONCLUSIVO | 2 | Acesso à página não comprova cobertura da 57ª legislatura; indicador desativado |
| 07/pdfs | PASSOU | 18 |  |
| 07/temas_e_rotulos | INCONCLUSIVO | 12 | Candidatos aguardam leitura e revisão; não inferir direção de ementa ou palavras-chave |
| 08/paginacao_camara | PASSOU | 10 | Páginas podem mudar durante atualização da fonte; amostra não prova snapshot estável |
| 08/reconciliacao_projetos | PASSOU | 30 | [] |

Pendências não autorizam taxa, ranking ou rótulo público. Revisar docs/especificacao_funcional.md antes da implementação.
