"""Build a small, fixed sample for feature design; no production ingestion.

Usage: python scripts/build_feature_sample.py
The sample contains two PL, two PLP and two PEC from each house in 2026.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "amostra_projetos.csv"
CAMARA = "https://dadosabertos.camara.leg.br/api/v2"
SENADO = "https://legis.senado.leg.br/dadosabertos"
SAMPLE = {
    "camara": [2647384, 2647345, 2599994, 2600175, 2604173, 2623400],
    "senado": [9101538, 9101917, 9104876, 9105948, 8986903, 9104654],
}
SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json", "User-Agent": "painel-legislativo-feature-discovery/0.1"})
FIELDS = [
    "fonte", "tipo", "identificador", "identificacao", "data_apresentacao",
    "ementa", "temas_oficiais", "url_documento", "status_http_documento",
    "tipo_http_documento", "bytes_documento", "norma_gerada", "revisao_conteudo",
]


def get_json(url: str, params: dict | None = None):
    response = SESSION.get(url, params=params, timeout=45)
    response.raise_for_status()
    return response.json()


def document_headers(url: str | None) -> tuple[str, str, str]:
    if not url:
        return "sem URL", "", ""
    try:
        response = SESSION.head(url, timeout=25, allow_redirects=True)
        return str(response.status_code), response.headers.get("Content-Type", ""), response.headers.get("Content-Length", "")
    except requests.RequestException as exc:
        return f"erro: {type(exc).__name__}", "", ""


def camara_row(identifier: int) -> dict[str, str]:
    detail = get_json(f"{CAMARA}/proposicoes/{identifier}")["dados"]
    themes = get_json(f"{CAMARA}/proposicoes/{identifier}/temas").get("dados", [])
    url = detail.get("urlInteiroTeor")
    status, mime, size = document_headers(url)
    return {
        "fonte": "camara",
        "tipo": detail.get("siglaTipo", ""),
        "identificador": str(detail["id"]),
        "identificacao": f"{detail.get('siglaTipo', '')} {detail.get('numero', '')}/{detail.get('ano', '')}",
        "data_apresentacao": detail.get("dataApresentacao", ""),
        "ementa": detail.get("ementa", ""),
        "temas_oficiais": json.dumps([x.get("tema") for x in themes], ensure_ascii=False),
        "url_documento": url or "",
        "status_http_documento": status,
        "tipo_http_documento": mime,
        "bytes_documento": size,
        "norma_gerada": "nao avaliada nesta amostra da Camara",
        "revisao_conteudo": "pendente; nenhum rotulo de posicao publicado",
    }


def senado_row(identifier: int) -> dict[str, str]:
    detail = get_json(f"{SENADO}/processo/{identifier}.json")
    documents = get_json(f"{SENADO}/processo/documento.json", {"idProcesso": identifier})
    main_document_id = (detail.get("documento") or {}).get("id")
    document = next((item for item in documents if item.get("id") == main_document_id), None)
    document = document or (documents[0] if documents else {})
    url = document.get("urlDocumento")
    status, mime, size = document_headers(url)
    return {
        "fonte": "senado",
        "tipo": detail.get("sigla", ""),
        "identificador": str(detail["id"]),
        "identificacao": detail.get("identificacao", ""),
        "data_apresentacao": (detail.get("documento") or {}).get("dataApresentacao", ""),
        "ementa": (detail.get("conteudo") or {}).get("ementa", ""),
        "temas_oficiais": json.dumps([x.get("descricaoHierarquia") or x.get("descricao") for x in detail.get("classificacoes", [])], ensure_ascii=False),
        "url_documento": url or "",
        "status_http_documento": status,
        "tipo_http_documento": mime,
        "bytes_documento": size,
        "norma_gerada": json.dumps(detail.get("normaGerada") or {}, ensure_ascii=False),
        "revisao_conteudo": "pendente; nenhum rotulo de posicao publicado",
    }


def main() -> None:
    rows = [camara_row(identifier) for identifier in SAMPLE["camara"]]
    rows += [senado_row(identifier) for identifier in SAMPLE["senado"]]
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Recorded {len(rows)} projects in {OUTPUT}")
    for source in ("camara", "senado"):
        subset = [row for row in rows if row["fonte"] == source]
        print(source, "document URLs", sum(bool(row["url_documento"]) for row in subset),
              "HTTP 200", sum(row["status_http_documento"] == "200" for row in subset),
              "official themes", sum(row["temas_oficiais"] != "[]" for row in subset))


if __name__ == "__main__":
    main()
