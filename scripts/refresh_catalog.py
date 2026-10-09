"""Refresh the endpoint and official bulk-file inventory in docs/catalogo_recursos.csv.

Usage: python scripts/refresh_catalog.py
Requires only `requests` (HTML parsing uses the Python standard library).
"""

from __future__ import annotations

import csv
import html
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import requests


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "catalogo_recursos.csv"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "painel-legislativo-api-catalog/0.1"})


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.current: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.current = [dict(attrs).get("href") or "", ""]

    def handle_data(self, data: str) -> None:
        if self.current is not None:
            self.current[1] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.current is not None:
            self.links.append((self.current[0], " ".join(self.current[1].split())))
            self.current = None


FIELDS = [
    "source",
    "resource_type",
    "group",
    "name",
    "method",
    "route_or_url",
    "format",
    "parameters",
    "response_schema",
    "deprecated",
    "temporal_coverage",
    "update_frequency",
    "key_map_reference",
    "catalog_checked_at_utc",
    "source_page",
    "notes",
]


def fetch_json(url: str) -> dict:
    response = SESSION.get(url, timeout=45)
    response.raise_for_status()
    return response.json()


def endpoint_rows(source: str, spec_url: str, root_url: str) -> list[dict[str, str]]:
    spec = fetch_json(spec_url)
    rows: list[dict[str, str]] = []
    for path, operations in spec.get("paths", {}).items():
        for method, operation in operations.items():
            if method.lower() != "get":
                continue
            response = operation.get("responses", {}).get("200", {})
            content = response.get("content", {})
            schema = next(
                (value.get("schema") for value in content.values() if value.get("schema")),
                {},
            )
            rows.append(
                {
                    "source": source,
                    "resource_type": "api_endpoint",
                    "group": "; ".join(operation.get("tags", [])),
                    "name": operation.get("summary", ""),
                    "method": "GET",
                    "route_or_url": urljoin(root_url, path.lstrip("/")) if root_url.endswith("/") else root_url + path,
                    "format": "; ".join(content.keys()),
                    "parameters": json.dumps(operation.get("parameters", []), ensure_ascii=False, separators=(",", ":")),
                    "response_schema": json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
                    "deprecated": str(bool(operation.get("deprecated", False))).lower(),
                    "temporal_coverage": "Nao declarada de forma uniforme na especificacao OpenAPI",
                    "update_frequency": "Nao declarada de forma uniforme na especificacao OpenAPI",
                    "key_map_reference": "docs/chaves_relacionamentos.md (exploratorio)",
                    "catalog_checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "source_page": spec_url,
                    "notes": "Paginacao, filtros, autenticacao e limites devem ser interpretados pela especificacao; nao coletar sem escopo.",
                }
            )
    return rows


def html_links(url: str) -> list[tuple[str, str]]:
    response = SESSION.get(url, timeout=45)
    response.raise_for_status()
    parser = LinkParser()
    parser.feed(response.text)
    return [(urljoin(response.url, href), text) for href, text in parser.links if href]


def camara_template_rows(page_url: str) -> list[dict[str, str]]:
    """Read the URL patterns printed in Câmara's official Arquivos tab."""
    response = SESSION.get(page_url, timeout=45)
    response.raise_for_status()
    pattern = r"https?://[^\s\"<>]*?/arquivos/[^\s\"<>]*"
    urls = dict.fromkeys(html.unescape(url) for url in re.findall(pattern, response.text))
    rows = []
    for url in urls:
        if "{formato}" not in url:
            continue
        family = url.split("/arquivos/", 1)[1].split("/", 1)[0]
        placeholders = sorted(set(re.findall(r"\{([^{}]+)\}", url)))
        rows.append(
            {
                "source": "camara",
                "resource_type": "bulk_url_template",
                "group": family,
                "name": family,
                "method": "GET",
                "route_or_url": url,
                "format": "Definido por {formato}; consultar pagina de origem",
                "parameters": json.dumps(placeholders, ensure_ascii=False),
                "response_schema": "",
                "deprecated": "",
                "temporal_coverage": "Por {ano}" if "ano" in placeholders else "Consultar metadados do conjunto",
                "update_frequency": "Consultar metadados do conjunto",
                "key_map_reference": "docs/chaves_relacionamentos.md (exploratorio)",
                "catalog_checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source_page": page_url,
                "notes": "Modelo publicado pela Camara; substituir parametros e confirmar arquivo concreto antes da ingestao.",
            }
        )
    return rows


def file_rows(source: str, group: str, page_url: str, links: list[tuple[str, str]], predicate) -> list[dict[str, str]]:
    rows = []
    for url, link_text in links:
        if not predicate(url):
            continue
        basename = url.rstrip("/").split("/")[-1]
        suffix = re.search(r"\.(csv|json|xml|xlsx|ods|zip)(?:\.zip)?(?:\?|$)", url, re.I)
        fmt = suffix.group(0).lstrip(".").upper() if suffix else link_text.upper()
        year = re.search(r"Ano-(\d{4})", url, re.I)
        rows.append(
            {
                "source": source,
                "resource_type": "bulk_file_or_feed",
                "group": group,
                "name": basename,
                "method": "GET",
                "route_or_url": url,
                "format": fmt,
                "parameters": "[]",
                "response_schema": "",
                "deprecated": "",
                "temporal_coverage": year.group(1) if year else "Consultar metadados do conjunto",
                "update_frequency": "Diaria (arquivo de cotas da Camara)" if "/cotas/" in url.lower() else "Consultar metadados do conjunto",
                "key_map_reference": "docs/chaves_relacionamentos.md (exploratorio)",
                "catalog_checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source_page": page_url,
                "notes": f"Rotulo do catalogo/portal: {link_text or 'sem rotulo textual'}; validar cobertura e atualizacao antes da ingestao.",
            }
        )
    return rows


def main() -> None:
    rows: list[dict[str, str]] = []
    rows += endpoint_rows(
        "camara",
        "https://dadosabertos.camara.leg.br/api/v2/api-docs",
        "https://dadosabertos.camara.leg.br/api/v2/",
    )
    rows += endpoint_rows(
        "senado",
        "https://legis.senado.leg.br/dadosabertos/v3/api-docs",
        "https://legis.senado.leg.br",
    )

    camara_page = "https://dadosabertos.camara.leg.br/swagger/api.html?tab=staticfile"
    rows += file_rows(
        "camara",
        "arquivos estaticos da API",
        camara_page,
        html_links(camara_page),
        lambda url: "/cotas/" in url.lower() or any(url.lower().endswith(ext) for ext in (".csv", ".json", ".xml", ".xlsx", ".ods", ".zip")),
    )
    rows += camara_template_rows(camara_page)

    groups = {
        "projetos-e-materias": "Projetos e Matérias",
        "senadores": "Senadores",
        "plenario": "Plenário",
        "composicao": "Composição",
        "comissoes": "Comissões",
        "legislacao": "Legislação",
    }
    base = "https://www12.senado.leg.br/dados-abertos/conjuntos"
    for slug, label in groups.items():
        page = f"{base}?portal=Legislativo&grupo={slug}"
        rows += file_rows(
            "senado",
            label,
            page,
            html_links(page),
            lambda url: "/dadosabertos/" in url.lower() and bool(re.search(r"\.(csv|json|xml|xlsx|ods|zip)(?:\?|$)", url, re.I)),
        )

    rows.sort(key=lambda row: (row["source"], row["resource_type"], row["group"], row["route_or_url"]))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (row["source"], row["resource_type"])
        counts[key] = counts.get(key, 0) + 1
    print(f"Snapshot UTC: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    for (source, kind), count in sorted(counts.items()):
        print(f"{source}: {count} {kind}")
    print(f"Wrote {len(rows)} records to {OUTPUT}")


if __name__ == "__main__":
    main()
