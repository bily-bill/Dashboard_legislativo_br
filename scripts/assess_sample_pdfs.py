"""Measure text extractability in the small project sample, without saving PDFs.

Run after build_feature_sample.py. Requires pypdf:
    python scripts/assess_sample_pdfs.py
"""

from __future__ import annotations

import csv
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from pypdf import PdfReader


CSV_PATH = Path(__file__).resolve().parents[1] / "docs" / "amostra_projetos.csv"
MAX_BYTES = 10_000_000
EXTRA_FIELDS = ["pdf_paginas", "pdf_caracteres_3_paginas", "pdf_avaliacao_extracao"]


def inspect_pdf(url: str) -> tuple[str, str, str]:
    if not url:
        return "", "", "sem documento"
    if url.startswith("http://legis.senado.leg.br/"):
        url = "https://" + url[len("http://") :]
    try:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=35) as response:
            content = response.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            return "", "", "acima de 10 MB; nao avaliado"
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            return str(len(reader.pages)), "", "PDF criptografado"
        char_count = sum(len(page.extract_text() or "") for page in reader.pages[:3])
        assessment = "texto extraivel" if char_count >= 100 else "possivel OCR necessario"
        return str(len(reader.pages)), str(char_count), assessment
    except Exception as exc:
        return "", "", f"erro: {type(exc).__name__}"


def main() -> None:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    fields += [name for name in EXTRA_FIELDS if name not in fields]
    for row in rows:
        pages, characters, assessment = inspect_pdf(row["url_documento"])
        row["pdf_paginas"] = pages
        row["pdf_caracteres_3_paginas"] = characters
        row["pdf_avaliacao_extracao"] = assessment
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row["fonte"], row["identificacao"], row["pdf_paginas"],
              row["pdf_caracteres_3_paginas"], row["pdf_avaliacao_extracao"])


if __name__ == "__main__":
    main()
