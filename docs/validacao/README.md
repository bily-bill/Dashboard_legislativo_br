# Como ler a validação exploratória

Execute os notebooks `03` a `08` em ordem, com um kernel que tenha `requests`, `pandas` e `pypdf`. O notebook `03` cria `manifesto_amostra.csv`; os seguintes o reutilizam. O manifesto foi congelado para que novas execuções testem os mesmos IDs. `resultados_checks.csv` contém uma linha atual por check; `resumo.md` é regenerado pelo notebook `08`.

`PASSOU` confirma apenas a regra aplicada à amostra. `INCONCLUSIVO` cobre fonte sem denominador, código sem semântica, falha de rede, resposta acima do limite ou amostra insuficiente; leia `motivo` e `contagens`. `FALHOU` fica reservado a violação demonstrada de uma regra contratual. Nenhum desses estados autoriza sozinho uma métrica pública. A decisão em `resumo.md` explicita as dependências de cada funcionalidade.

O arquivo `candidatos_rotulos.csv` contém trechos localizados por palavras-chave, com URL e página, para revisão humana. Direção de medida fica `indeterminado`; nenhum candidato é publicado automaticamente.

As consultas são limitadas a 120 por notebook (ou menos), com uma por segundo e downloads de até 80 MB. Respostas HTTP inesperadas e amostras vazias são registradas separadamente. Para mudar a amostra, primeiro revise o método de seleção no gerador e preserve uma cópia do manifesto anterior; não sobrescreva os IDs sem registrar a mudança.
