"""Small, bounded, auditable API probes for the validation notebooks.

This is exploratory code, not a production ingestion client.
"""

from __future__ import annotations

import csv
import io
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "validacao"
OUT.mkdir(parents=True, exist_ok=True)
CHECKS = OUT / "resultados_checks.csv"
MANIFEST = OUT / "manifesto_amostra.csv"
CHECK_FIELDS = ["notebook", "check", "fonte", "url_parametros", "coletado_em_utc", "amostra_n", "regra", "contagens", "estado", "motivo"]
MANIFEST_FIELDS = ["fonte", "entidade", "tipo", "ano", "id", "url", "selecao"]
STATES = {"PASSOU", "FALHOU", "INCONCLUSIVO"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Result:
    url: str
    status: int | None
    data: object | None = None
    content: bytes | None = None
    headers: dict | None = None
    error: str = ""
    collected_at: str = ""

    @property
    def ok(self) -> bool:
        return self.status == 200 and not self.error


class Probe:
    def __init__(self, notebook: str, max_calls: int = 120, max_bytes: int = 80_000_000):
        self.notebook = notebook
        self.max_calls = max_calls
        self.max_bytes = max_bytes
        self.calls = 0
        self.last_call = 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "painel-legislativo-validation/0.1", "Accept": "application/json, text/csv, application/pdf, */*"})

    def fetch(self, url: str, params: dict | None = None, method: str = "GET", limit: int | None = None) -> Result:
        limit = min(limit or self.max_bytes, self.max_bytes)
        last = Result(url=url, status=None, error="não executado", collected_at=utc_now())
        for attempt in range(3):
            if self.calls >= self.max_calls:
                return Result(url=url, status=None, error="limite de chamadas do notebook", collected_at=utc_now())
            # One request per second, conservatively across both public APIs.
            pause = 1.0 - (time.monotonic() - self.last_call)
            if pause > 0:
                time.sleep(pause)
            self.last_call = time.monotonic()
            self.calls += 1
            try:
                with self.session.request(method, url, params=params, timeout=(10, 45), allow_redirects=True, stream=True) as response:
                    final_url = response.url
                    headers = dict(response.headers)
                    status = response.status_code
                    if status in (429, 503) and attempt < 2:
                        retry = response.headers.get("Retry-After", "")
                        try:
                            delay = min(float(retry), 30)
                        except ValueError:
                            try:
                                delay = min(max((parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds(), 0), 30)
                            except (TypeError, ValueError, OverflowError):
                                delay = 2 ** attempt
                        time.sleep(delay)
                        continue
                    if method == "HEAD":
                        return Result(final_url, status, headers=headers, error="" if status == 200 else f"HTTP {status}", collected_at=utc_now())
                    if status != 200:
                        return Result(final_url, status, headers=headers, error=f"HTTP {status}", collected_at=utc_now())
                    declared = headers.get("Content-Length")
                    if declared and declared.isdigit() and int(declared) > limit:
                        return Result(final_url, status, headers=headers, error=f"arquivo acima do limite ({declared} > {limit} bytes)", collected_at=utc_now())
                    chunks, size = [], 0
                    for chunk in response.iter_content(chunk_size=65536):
                        if not chunk:
                            continue
                        size += len(chunk)
                        if size > limit:
                            return Result(final_url, status, headers=headers, error=f"resposta acima do limite de {limit} bytes", collected_at=utc_now())
                        chunks.append(chunk)
                    body = b"".join(chunks)
                    return Result(final_url, status, content=body, headers=headers, collected_at=utc_now())
            except requests.RequestException as exc:
                last = Result(url=url, status=None, error=f"{type(exc).__name__}: {exc}", collected_at=utc_now())
                if attempt < 2:
                    time.sleep(2 ** attempt)
        return last

    def json(self, url: str, params: dict | None = None, limit: int = 2_000_000) -> Result:
        result = self.fetch(url, params=params, limit=limit)
        if result.ok:
            try:
                result.data = json.loads(result.content or b"")
            except (ValueError, UnicodeDecodeError) as exc:
                result.error = f"JSON inválido: {type(exc).__name__}"
        result.content = None
        return result


def record(notebook: str, check: str, fonte: str, url_parametros: str, amostra_n: int,
           regra: str, contagens: dict, estado: str, motivo: str = "") -> dict:
    if estado not in STATES:
        raise ValueError(f"estado inválido: {estado}")
    row = dict(notebook=notebook, check=check, fonte=fonte, url_parametros=url_parametros,
               coletado_em_utc=utc_now(), amostra_n=amostra_n, regra=regra,
               contagens=json.dumps(contagens, ensure_ascii=False, sort_keys=True), estado=estado, motivo=motivo)
    rows = []
    if CHECKS.exists():
        with CHECKS.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
    rows = [old for old in rows if (old["notebook"], old["check"]) != (notebook, check)]
    rows.append(row)
    with CHECKS.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CHECK_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return row


def manifest_rows() -> list[dict[str, str]]:
    if not MANIFEST.exists():
        return []
    with MANIFEST.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def save_manifest(rows: list[dict[str, str]]) -> None:
    if MANIFEST.exists():
        raise FileExistsError("Manifesto já congelado; remova manualmente somente se quiser nova amostra.")
    with MANIFEST.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def api_camara(path: str) -> str:
    return "https://dadosabertos.camara.leg.br/api/v2/" + path.lstrip("/")


def api_senado(path: str) -> str:
    return "https://legis.senado.leg.br/dadosabertos/" + path.lstrip("/")


def rows_camara(data: object) -> list[dict]:
    return data.get("dados", []) if isinstance(data, dict) else []


def count_values(rows: list[dict], field: str) -> dict:
    values = [row.get(field) for row in rows]
    return {"linhas": len(values), "nulos": sum(v in (None, "") for v in values),
            "distintos_nao_nulos": len({str(v) for v in values if v not in (None, "")})}


def csv_head(content: bytes, n: int = 6) -> list[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    sample = text[:4096]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","
    return list(row for _, row in zip(range(n), csv.DictReader(io.StringIO(text), delimiter=delimiter)))


def domain(url: str) -> str:
    return urlparse(url).netloc
