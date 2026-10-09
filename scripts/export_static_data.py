"""Export public, read-only JSON for the legislative dashboard.

Usage: python scripts/export_static_data.py
       python scripts/export_static_data.py --from-year 2026 --to-date 2026-10-09

The complete 57th legislature is the default scope. All HTTP collection and
validation finish before any public file is replaced. No PDFs are downloaded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "public" / "dados" / "v1"
CAMARA = "https://dadosabertos.camara.leg.br/api/v2"
SENADO = "https://legis.senado.leg.br/dadosabertos"
TYPES = ("PL", "PLP", "PEC")
SCHEMA_VERSION = 1


class CollectionError(RuntimeError):
    pass


class Client:
    def __init__(self, delay: float, max_calls: int):
        self.delay = delay
        self.max_calls = max_calls
        self.calls = 0
        self.last = 0.0
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "painel-legislativo-static-export/0.1"})

    def get(self, url: str, params: dict | None = None, max_bytes: int = 15_000_000):
        for attempt in range(3):
            if self.calls >= self.max_calls:
                raise CollectionError(f"Limite de {self.max_calls} requisições atingido")
            pause = self.delay - (time.monotonic() - self.last)
            if pause > 0:
                time.sleep(pause)
            self.last = time.monotonic()
            self.calls += 1
            try:
                with self.session.get(url, params=params, timeout=(10, 60), stream=True) as response:
                    if response.status_code in (429, 503) and attempt < 2:
                        value = response.headers.get("Retry-After", "")
                        time.sleep(min(int(value), 30) if value.isdigit() else 2 ** attempt)
                        continue
                    if response.status_code != 200:
                        raise CollectionError(f"HTTP {response.status_code}: {response.url}")
                    if int(response.headers.get("Content-Length", "0")) > max_bytes:
                        raise CollectionError(f"Resposta acima de {max_bytes} bytes: {response.url}")
                    chunks, total = [], 0
                    for chunk in response.iter_content(65536):
                        if chunk:
                            total += len(chunk)
                            if total > max_bytes:
                                raise CollectionError(f"Resposta acima de {max_bytes} bytes: {response.url}")
                            chunks.append(chunk)
                    try:
                        return json.loads(b"".join(chunks)), response.url
                    except (ValueError, UnicodeDecodeError) as exc:
                        raise CollectionError(f"JSON inválido em {response.url}: {exc}") from exc
            except requests.RequestException as exc:
                if attempt == 2:
                    raise CollectionError(f"Falha de rede em {url}: {exc}") from exc
                time.sleep(2 ** attempt)
        raise CollectionError(f"Falha ao obter {url}")


def quarters(start_year: int, end: date):
    for year in range(start_year, end.year + 1):
        for month, final in ((1, 3), (4, 6), (7, 9), (10, 12)):
            first_day = date(year, month, 1)
            if first_day > end:
                return
            last_day = date(year, final, 31 if final in (3, 12) else 30)
            yield first_day, min(last_day, end)


def normalize_camara(row: dict) -> dict:
    year = str(row.get("ano") or "")
    number = str(row.get("numero") or "")
    typ = row.get("siglaTipo")
    return {
        "casa": "camara", "id": str(row["id"]), "tipo": typ,
        "numero": int(number) if number.isdigit() else None,
        "ano_identificacao": int(year) if year.isdigit() else None,
        "identificacao": f"{typ} {number}/{year}",
        "data_apresentacao": row.get("dataApresentacao"),
        "ementa": row.get("ementa"),
        "situacao_resumo": None, "autoria_resumo": None,
        "url_documento": None, "url_fonte": row.get("uri"),
        "data_ultima_atualizacao": None,
    }


def normalize_senado(row: dict) -> dict:
    title = row.get("identificacao") or ""
    match = re.match(r"^(PLP|PL|PEC)\s+(\d+)/(\d{4})", title)
    if not match:
        raise CollectionError(f"Identificação inesperada do Senado: {title!r}, id={row.get('id')}")
    return {
        "casa": "senado", "id": str(row["id"]), "tipo": match.group(1),
        "numero": int(match.group(2)), "ano_identificacao": int(match.group(3)),
        "identificacao": title, "data_apresentacao": row.get("dataApresentacao"),
        "ementa": row.get("ementa"), "situacao_resumo": row.get("situacaoAtual"),
        "autoria_resumo": row.get("autoria"), "url_documento": row.get("urlDocumento"),
        "url_fonte": f"{SENADO}/processo/{row['id']}.json",
        "data_ultima_atualizacao": row.get("dataUltimaAtualizacao"),
    }


def collect_projects(client: Client, start_year: int, end: date):
    projects = {}
    windows = []
    for first, last in quarters(start_year, end):
        for typ in TYPES:
            # Senado returns the complete filtered list; Câmara paginates it.
            params = {"sigla": typ, "dataInicioApresentacao": first.isoformat(),
                      "dataFimApresentacao": last.isoformat()}
            senate_rows, senate_url = client.get(f"{SENADO}/processo", params)
            if not isinstance(senate_rows, list):
                raise CollectionError(f"Formato inesperado do Senado: {senate_url}")
            seen_window = set()
            for raw in senate_rows:
                item = normalize_senado(raw)
                check_project(item, typ, first, last, senate_url)
                key = ("senado", item["id"])
                if key in seen_window or key in projects:
                    raise CollectionError(f"Projeto repetido no Senado: {key}")
                seen_window.add(key)
                projects[key] = item
            windows.append({"casa": "senado", "tipo": typ, "inicio": first.isoformat(),
                            "fim": last.isoformat(), "quantidade": len(senate_rows), "url": senate_url})

            page = 1
            seen_window.clear()
            while True:
                params = {"siglaTipo": typ, "dataApresentacaoInicio": first.isoformat(),
                          "dataApresentacaoFim": last.isoformat(), "itens": 100,
                          "pagina": page, "ordem": "ASC", "ordenarPor": "id"}
                body, camara_url = client.get(f"{CAMARA}/proposicoes", params)
                if not isinstance(body, dict) or not isinstance(body.get("dados"), list):
                    raise CollectionError(f"Formato inesperado da Câmara: {camara_url}")
                rows = body["dados"]
                for raw in rows:
                    item = normalize_camara(raw)
                    check_project(item, typ, first, last, camara_url)
                    key = ("camara", item["id"])
                    if key in seen_window or key in projects:
                        raise CollectionError(f"Projeto repetido na Câmara: {key}")
                    seen_window.add(key)
                    projects[key] = item
                has_next = any(link.get("rel") == "next" for link in body.get("links", []))
                if not has_next:
                    break
                page += 1
                if page > 200:
                    raise CollectionError(f"Mais de 200 páginas: {typ}, {first}–{last}")
            windows.append({"casa": "camara", "tipo": typ, "inicio": first.isoformat(),
                            "fim": last.isoformat(), "quantidade": len(seen_window), "paginas": page})
        print(f"{first} a {last}: {sum(w['quantidade'] for w in windows if w['inicio']==first.isoformat())} projetos", flush=True)
    return list(projects.values()), windows


def check_project(item: dict, typ: str, first: date, last: date, url: str):
    stamp = item.get("data_apresentacao") or ""
    try:
        presented = date.fromisoformat(stamp[:10])
    except ValueError as exc:
        raise CollectionError(f"Data de apresentação inválida: {item['casa']}/{item['id']}, {url}") from exc
    if item["tipo"] != typ or not first <= presented <= last:
        raise CollectionError(f"Filtro incoerente: {item['casa']}/{item['id']}, {item['tipo']}, {stamp}, {url}")


def collect_members(client: Client):
    camara = []
    page = 1
    while True:
        body, url = client.get(f"{CAMARA}/deputados", {"itens": 100, "pagina": page,
                                                      "ordem": "ASC", "ordenarPor": "id"})
        if not isinstance(body, dict) or not isinstance(body.get("dados"), list):
            raise CollectionError(f"Formato inesperado de deputados: {url}")
        for row in body["dados"]:
            camara.append({"casa": "camara", "id": str(row["id"]), "nome": row.get("nome"),
                           "partido": row.get("siglaPartido"), "uf": row.get("siglaUf"),
                           "url_foto": row.get("urlFoto"), "url_fonte": row.get("uri")})
        if not any(link.get("rel") == "next" for link in body.get("links", [])):
            break
        page += 1
        if page > 10:
            raise CollectionError("Mais de 10 páginas de deputados atuais")
    body, url = client.get(f"{SENADO}/senador/lista/atual.json")
    try:
        senate_raw = body["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"]
    except (TypeError, KeyError) as exc:
        raise CollectionError(f"Formato inesperado de senadores: {url}") from exc
    senate = []
    for row in senate_raw:
        person = row["IdentificacaoParlamentar"]
        senate.append({"casa": "senado", "id": str(person["CodigoParlamentar"]),
                       "nome": person.get("NomeParlamentar"),
                       "partido": person.get("SiglaPartidoParlamentar"),
                       "uf": person.get("UfParlamentar"),
                       "url_foto": person.get("UrlFotoParlamentar"),
                       "url_fonte": person.get("UrlPaginaParlamentar")})
    for house, rows in (("camara", camara), ("senado", senate)):
        ids = [row["id"] for row in rows]
        if not rows or len(ids) != len(set(ids)):
            raise CollectionError(f"Composição {house} vazia ou com IDs repetidos")
    return camara, senate


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")


def prepare_files(projects: list[dict], members: tuple[list[dict], list[dict]], windows: list[dict],
                  start_year: int, end: date):
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    files = {}
    monthly = Counter()
    composition = Counter()
    by_type = Counter()
    by_party = Counter()
    by_uf = Counter()
    for item in projects:
        monthly[(item["casa"], item["data_apresentacao"][:7], item["tipo"])] += 1
        by_type[(item["casa"], item["tipo"])] += 1
    for rows in members:
        for item in rows:
            house, party, uf = item["casa"], item["partido"] or "sem partido", item["uf"] or "sem UF"
            composition[(house, party, uf)] += 1
            by_party[(house, party)] += 1
            by_uf[(house, uf)] += 1
    for house in ("camara", "senado"):
        for year in range(start_year, end.year + 1):
            for typ in TYPES:
                subset = sorted((x for x in projects if x["casa"] == house and
                                 x["data_apresentacao"][:4] == str(year) and x["tipo"] == typ),
                                key=lambda x: (x["data_apresentacao"], x["id"]))
                path = f"projetos/{house}/{year}/{typ.lower()}.json"
                files[path] = json_bytes({"meta": {"schema_version": SCHEMA_VERSION, "casa": house,
                    "ano_apresentacao": year, "tipo": typ, "quantidade": len(subset)}, "dados": subset})
    for house, rows in zip(("camara", "senado"), members):
        path = f"parlamentares/{house}/atuais.json"
        files[path] = json_bytes({"meta": {"schema_version": SCHEMA_VERSION, "casa": house,
            "referencia_utc": generated_at, "quantidade": len(rows), "recorte": "em exercicio na coleta"},
            "dados": sorted(rows, key=lambda x: x["id"])})
    files["indicadores/projetos_por_mes.json"] = json_bytes({"meta": {"schema_version": SCHEMA_VERSION,
        "unidade": "projetos apresentados"},
        "dados": [{"casa": house, "mes": month, "tipo": typ, "quantidade": n}
                  for (house, month, typ), n in sorted(monthly.items())]})
    files["indicadores/composicao_atual.json"] = json_bytes({"meta": {"schema_version": SCHEMA_VERSION,
        "unidade": "parlamentares em exercicio"},
        "dados": [{"casa": house, "partido": party, "uf": uf, "quantidade": n}
                  for (house, party, uf), n in sorted(composition.items())]})
    for name, counts, field in (("composicao_por_partido", by_party, "partido"),
                                ("composicao_por_uf", by_uf, "uf")):
        files[f"indicadores/{name}.json"] = json_bytes({"meta": {"schema_version": SCHEMA_VERSION,
            "unidade": "parlamentares em exercicio"},
            "dados": [{"casa": house, field: category, "quantidade": n}
                      for (house, category), n in sorted(counts.items())]})
    files["indicadores/resumo.json"] = json_bytes({"meta": {"schema_version": SCHEMA_VERSION,
        "inicio": f"{start_year}-01-01", "fim": end.isoformat()},
        "dados": [{"casa": house, "parlamentares_atuais": len(rows),
                   "projetos_apresentados": sum(by_type[(house, typ)] for typ in TYPES),
                   "projetos_por_tipo": {typ: by_type[(house, typ)] for typ in TYPES}}
                  for house, rows in zip(("camara", "senado"), members)]})
    files["cobertura.json"] = json_bytes({"meta": {"schema_version": SCHEMA_VERSION,
        "gerado_em_utc": generated_at, "inicio": f"{start_year}-01-01", "fim": end.isoformat(),
        "estado": "completo_para_listagens_de_projetos_e_composicao_atual"},
        "janelas": windows,
        "campos_nao_coletados": ["temas oficiais em escala completa", "autoria detalhada da Camara",
                                 "tramitacoes", "votacoes", "texto/PDF", "filiacao historica"],
        "indicadores_nao_publicados": ["presenca", "participacao em votacoes", "aprovacao final",
                                      "ideologia partidaria", "direcao de medida"]})
    entries = [{"caminho": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                "quantidade": json.loads(data).get("meta", {}).get("quantidade")}
               for path, data in sorted(files.items())]
    files["manifesto.json"] = json_bytes({"schema_version": SCHEMA_VERSION, "gerado_em_utc": generated_at,
        "inicio": f"{start_year}-01-01", "fim": end.isoformat(),
        "totais": {"projetos_camara": sum(x["casa"] == "camara" for x in projects),
                   "projetos_senado": sum(x["casa"] == "senado" for x in projects),
                   "deputados_atuais": len(members[0]), "senadores_atuais": len(members[1])},
        "arquivos": entries, "cobertura": "cobertura.json"})
    return files


def publish(files: dict[str, bytes], target: Path):
    target = target.resolve()
    if not target.is_relative_to(ROOT.resolve()):
        raise CollectionError(f"Destino fora do workspace: {target}")
    target.mkdir(parents=True, exist_ok=True)
    previous = target / "manifesto.json"
    old_paths = []
    if previous.exists():
        try:
            old_paths = [entry["caminho"] for entry in json.loads(previous.read_text(encoding="utf-8")).get("arquivos", [])]
        except (ValueError, KeyError, TypeError) as exc:
            raise CollectionError(f"Manifesto anterior inválido; não substituir arquivos: {exc}") from exc
    # Git commits/deploys publish the complete set together. Write manifest last locally.
    with TemporaryDirectory(prefix="legislativo-static-", dir=target.parent) as temporary:
        staging = Path(temporary)
        if not staging.resolve().is_relative_to(ROOT.resolve()):
            raise CollectionError(f"Diretório temporário fora do workspace: {staging}")
        for path, data in files.items():
            destination = staging / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        for path in sorted(files, key=lambda p: p == "manifesto.json"):
            destination = target / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            (staging / path).replace(destination)
        for path in old_paths:
            if path in files:
                continue
            stale = (target / path).resolve()
            if stale.is_relative_to(target) and stale.suffix == ".json" and stale.exists():
                stale.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-year", type=int, default=2023)
    parser.add_argument("--to-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--max-calls", type=int, default=1500)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.from_year < 2023 or args.to_date < date(args.from_year, 1, 1) or args.to_date > date.today():
        parser.error("Recorte deve começar em 2023 e terminar até hoje")
    client = Client(delay=args.delay, max_calls=args.max_calls)
    projects, windows = collect_projects(client, args.from_year, args.to_date)
    members = collect_members(client)
    files = prepare_files(projects, members, windows, args.from_year, args.to_date)
    publish(files, args.output_dir)
    total = sum(len(data) for data in files.values())
    print(f"Publicado: {len(projects)} projetos, {len(members[0])} deputados, {len(members[1])} senadores")
    print(f"Arquivos: {len(files)}, {total/1_000_000:.2f} MB, {client.calls} chamadas, destino: {args.output_dir}")


if __name__ == "__main__":
    try:
        main()
    except CollectionError as exc:
        print(f"Exportação interrompida; dados públicos anteriores preservados: {exc}", file=sys.stderr)
        raise SystemExit(1)
