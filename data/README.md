# Dados de trabalho

`bronze/` receberá respostas e arquivos originais comprimidos; `silver/` receberá tabelas tratadas em Parquet; `tmp/` é temporário. Essas pastas não entram no Git. A primeira exportação pública fica em [`../public/dados/v1/`](../public/dados/v1/).

O script `scripts/export_static_data.py` busca listagens oficiais, valida tipo e data de apresentação e só então substitui os JSONs públicos. Não baixa PDFs nem publica rótulos sem revisão. O manifesto descreve a cobertura e os campos ainda não coletados.
