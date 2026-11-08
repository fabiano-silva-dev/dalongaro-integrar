#!/usr/bin/env python3
"""Indexa, sem alterar a fonte, a exportação de razão convertida em XLSX.

Os valores são inteiros em centavos; nenhum saldo/contrapartida é inventado.
O contexto da conta e do histórico atravessa abas. Veja razao-geral/README.md.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile

from openpyxl import Workbook, load_workbook

VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parent
CLIENT = ROOT.parent
CHUNK_SIZE = 5000
STATUS_INCOMPLETE = "INCOMPLETO / CORTE NA EXPORTAÇÃO XLS"


def dump_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(CLIENT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def code(value: object) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and float(value).is_integer():
        return str(int(value))
    return str(value).strip()


def cents(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        s = value.strip().replace("\u00a0", "").replace(" ", "")
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        value = s
    amount = Decimal(str(value)) * 100
    rounded = amount.quantize(Decimal(1), rounding=ROUND_HALF_UP)
    # Values with extra decimal places are not silently rounded.
    if abs(amount - rounded) > Decimal("0.000001"):
        raise ValueError(f"Valor não expresso em centavos exatos: {value!r}")
    return int(rounded)


def iso_date(value: object) -> str | None:
    if isinstance(value, (datetime, date)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, str) and re.fullmatch(r"\d{2}/\d{2}/\d{4}", value.strip()):
        return datetime.strptime(value.strip(), "%d/%m/%Y").date().isoformat()
    return None


def saldo_info(value: object, number_format: str) -> dict:
    n = cents(value)
    # Excel's positive/negative format sections affect display, not the stored sign.
    sections = (number_format or "General").split(";")
    selected = sections[1] if n is not None and n < 0 and len(sections) > 1 else sections[0]
    if n == 0 and len(sections) > 2:
        selected = sections[2]
    explicit = re.search(r'"([DC])"', selected, re.I)
    return {
        "saldo_centavos": n,
        "saldo_natureza": ("D" if n > 0 else "C" if n < 0 else "ZERO") if n is not None else None,
        "saldo_formato": number_format,
        "saldo_formato_secao": selected,
        "saldo_parenteses_visuais": "(" in selected and ")" in selected,
        "saldo_natureza_explicita_formato": explicit.group(1).upper() if explicit else None,
        "saldo_sinal_metodo": "sinal numérico da célula; débito positivo/crédito negativo, validado por recorrência" if n is not None else "ausente",
    }


def parse_workbook(path: Path) -> dict:
    """Return events, sections, metadata and row audit (independent of output writer)."""
    wb = load_workbook(path, read_only=True, data_only=True)
    events, sections, unknown, sheets = [], [], [], []
    row_types = Counter()
    meta = {"empresas": set(), "cnpjs": set(), "periodos_declarados": set()}
    current = None
    pending = None
    prev_balance = None
    balance_checks, balance_failures, source_events = 0, [], 0
    current_page = None

    def close_event():
        nonlocal pending
        if pending is not None:
            pending["historico"] = "\n".join(pending["historico_partes"])
            pending["linha_final"] = pending["origens"][-1]["linha"]
            pending["aba_final"] = pending["origens"][-1]["aba"]
            events.append(pending)
            pending = None

    for ws in wb:
        sd = {"aba": ws.title, "linhas": ws.max_row, "colunas": ws.max_column, "movimentos": 0}
        sheets.append(sd)
        for rn, cells in enumerate(ws.iter_rows(), 1):
            values = [c.value for c in cells]
            values += [None] * max(0, 15 - len(values))
            if not any(v is not None for v in values):
                row_types["vazia"] += 1
                continue
            origin = {"aba": ws.title, "linha": rn, "folha_impressa": current_page}
            a = str(values[0]).strip() if values[0] is not None else ""
            texts = [str(v) for v in values if isinstance(v, str)]
            if a == "Empresa:":
                meta["empresas"].add(str(values[2]))
                current_page = code(values[14])
                row_types["cabecalho_empresa"] += 1
                continue
            if a in ("C.N.P.J.:", "Período:"):
                meta["cnpjs" if a == "C.N.P.J.:" else "periodos_declarados"].add(str(values[2]))
                row_types["cabecalho_identificacao"] += 1
                continue
            if a in ("CONSOLIDADO", "RAZÃO", "Data") or a.startswith("Sistema licenciado"):
                row_types["cabecalho_rodape"] += 1
                continue
            if a == "Conta:":
                close_event()
                account_code = code(values[1])
                classification = code(values[2])
                name = "\n".join(str(v) for v in values[5:8] if v is not None)
                same_account = current and current["codigo_conta"] == account_code and current["classificacao"] == classification and current["total_fonte"] is None
                if same_account:
                    current["cabecalhos"].append(origin)
                else:
                    current = {
                        "secao_id": len(sections) + 1, "codigo_conta": account_code,
                        "classificacao": classification, "nome_conta": name,
                        "cabecalhos": [origin], "saldo_anterior_fonte": None,
                        "movimentos": 0, "debito_centavos": 0, "credito_centavos": 0,
                        "total_fonte": None, "ultima_origem": origin,
                    }
                    sections.append(current)
                    prev_balance = None
                row_types["conta"] += 1
                continue
            if any("total da conta:" in t.casefold() for t in texts):
                close_event()
                if not current:
                    raise ValueError(f"Total sem contexto de conta: {origin}")
                current["total_fonte"] = {**origin, "debito_centavos": cents(values[9]) or 0, "credito_centavos": cents(values[10]) or 0}
                row_types["total_conta"] += 1
                continue
            if any(t.strip().upper() == "SALDO ANTERIOR" for t in texts):
                close_event()
                if not current:
                    raise ValueError(f"Saldo anterior sem contexto: {origin}")
                fmt = cells[13].number_format if len(cells) > 13 else "General"
                opening = {**origin, **saldo_info(values[13], fmt)}
                if current["saldo_anterior_fonte"] is None:
                    current["saldo_anterior_fonte"] = opening
                    prev_balance = opening["saldo_centavos"]
                else:
                    current.setdefault("saldos_anteriores_repetidos", []).append(opening)
                    # A repeated page header must not reset the running balance.
                row_types["saldo_anterior"] += 1
                continue
            dt = iso_date(values[0])
            if dt:
                close_event()
                source_events += 1
                sd["movimentos"] += 1
                if current is None:
                    raise ValueError(f"Movimento sem conta: {origin}")
                debit, credit = cents(values[9]) or 0, cents(values[10]) or 0
                fmt = cells[13].number_format if len(cells) > 13 else "General"
                balance = saldo_info(values[13], fmt)
                classification = current["classificacao"] or ""
                parts = classification.split(".")
                cp = code(values[8])
                pending = {
                    "id": source_events, "secao_id": current["secao_id"], "ano": int(dt[:4]), "data": dt,
                    "lote": code(values[1]), "codigo_conta": current["codigo_conta"],
                    "classificacao": classification, "nome_conta": current["nome_conta"],
                    "grupo_1": ".".join(parts[:1]), "grupo_2": ".".join(parts[:2]), "grupo_3": ".".join(parts[:3]),
                    "historico_partes": [str(v) for v in values[2:8] if v is not None],
                    "contrapartida": cp, "contrapartida_codigo": cp if cp and re.fullmatch(r"\d+", cp) else None,
                    "debito_centavos": debit, "credito_centavos": credit, **balance,
                    "aba": ws.title, "linha": rn, "origens": [origin],
                }
                current["movimentos"] += 1
                current["debito_centavos"] += debit
                current["credito_centavos"] += credit
                current["ultima_origem"] = origin
                if prev_balance is not None and balance["saldo_centavos"] is not None:
                    balance_checks += 1
                    expected = prev_balance + debit - credit
                    if expected != balance["saldo_centavos"]:
                        balance_failures.append({**origin, "codigo_conta": current["codigo_conta"], "calculado_centavos": expected, "fonte_centavos": balance["saldo_centavos"], "diferenca_centavos": balance["saldo_centavos"] - expected})
                prev_balance = balance["saldo_centavos"]
                row_types["movimento"] += 1
                continue
            # A continuation has history, no date/lot or money. Do not silently
            # absorb unidentified financial rows into the previous history.
            continuation = values[0] is None and values[1] is None and any(v is not None for v in values[2:8]) and all(values[i] is None for i in (9, 10, 13))
            if continuation and pending is not None:
                pending["historico_partes"].extend(str(v) for v in values[2:8] if v is not None)
                if values[8] is not None:
                    extra = code(values[8])
                    pending["contrapartida"] = "\n".join(x for x in (pending["contrapartida"], extra) if x)
                    pending["contrapartida_codigo"] = None
                pending["origens"].append(origin)
                row_types["continuacao"] += 1
                continue
            unknown.append({**origin, "celulas": {str(i + 1): str(v) for i, v in enumerate(values) if v is not None}})
            row_types["nao_classificada"] += 1
    close_event()
    wb.close()
    return {"events": events, "sections": sections, "sheets": sheets,
            "metadata": {k: sorted(v) for k, v in meta.items()},
            "row_types": dict(row_types), "unknown": unknown, "source_events": source_events,
            "balance_checks": balance_checks, "balance_failures": balance_failures}


def write_sqlite(path: Path, events: list[dict], sections: list[dict], source: dict) -> bool:
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    columns = [
        ("id", "INTEGER PRIMARY KEY"), ("secao_id", "INTEGER"), ("ano", "INTEGER"),
        ("data", "TEXT"), ("lote", "TEXT"), ("codigo_conta", "TEXT"), ("classificacao", "TEXT"),
        ("nome_conta", "TEXT"), ("grupo_1", "TEXT"), ("grupo_2", "TEXT"), ("grupo_3", "TEXT"),
        ("historico", "TEXT"), ("historico_partes_json", "TEXT"), ("contrapartida", "TEXT"),
        ("contrapartida_codigo", "TEXT"), ("debito_centavos", "INTEGER"), ("credito_centavos", "INTEGER"),
        ("saldo_centavos", "INTEGER"), ("saldo_natureza", "TEXT"), ("saldo_formato", "TEXT"),
        ("saldo_formato_secao", "TEXT"), ("saldo_parenteses_visuais", "INTEGER"),
        ("saldo_natureza_explicita_formato", "TEXT"), ("saldo_sinal_metodo", "TEXT"),
        ("aba", "TEXT"), ("linha", "INTEGER"), ("aba_final", "TEXT"), ("linha_final", "INTEGER"),
        ("origens_json", "TEXT"), ("arquivo", "TEXT"), ("arquivo_sha256", "TEXT"),
        ("convertido", "TEXT"), ("convertido_sha256", "TEXT"),
    ]
    con.execute("CREATE TABLE eventos (" + ",".join(f"{k} {t}" for k, t in columns) + ")")
    keys = [k for k, _ in columns]
    rows = []
    for e in events:
        e["historico_partes_json"] = json.dumps(e["historico_partes"], ensure_ascii=False)
        e["origens_json"] = json.dumps(e["origens"], ensure_ascii=False)
        rows.append(tuple(e.get(k) for k in keys))
    con.executemany("INSERT INTO eventos VALUES (" + ",".join("?" for _ in keys) + ")", rows)
    con.execute("CREATE TABLE contas (codigo_conta TEXT, classificacao TEXT, nome_conta TEXT, grupo_1 TEXT, grupo_2 TEXT, grupo_3 TEXT, PRIMARY KEY(codigo_conta,classificacao,nome_conta))")
    con.execute("INSERT INTO contas SELECT DISTINCT codigo_conta,classificacao,nome_conta,grupo_1,grupo_2,grupo_3 FROM eventos")
    con.execute("CREATE TABLE secoes (secao_id INTEGER PRIMARY KEY, codigo_conta TEXT, dados_json TEXT)")
    con.executemany("INSERT INTO secoes VALUES (?,?,?)", [(s["secao_id"], s["codigo_conta"], json.dumps(s, ensure_ascii=False)) for s in sections])
    con.execute("CREATE TABLE fonte (chave TEXT PRIMARY KEY, valor_json TEXT)")
    con.executemany("INSERT INTO fonte VALUES (?,?)", [(k, json.dumps(v, ensure_ascii=False)) for k, v in source.items()])
    for fields in ("data", "ano", "codigo_conta,data", "classificacao,data", "grupo_3,data", "lote", "contrapartida_codigo"):
        con.execute(f"CREATE INDEX idx_{fields.replace(',', '_')} ON eventos({fields})")
    fts = True
    try:
        con.execute("CREATE VIRTUAL TABLE busca USING fts5(historico,nome_conta,codigo_conta UNINDEXED,content='eventos',content_rowid='id',tokenize='unicode61 remove_diacritics 2')")
        con.execute("INSERT INTO busca(busca) VALUES ('rebuild')")
    except sqlite3.OperationalError:
        fts = False
    con.commit()
    con.execute("VACUUM")
    con.close()
    # These helpers are SQLite-only; the JSONL retains structured arrays.
    for e in events:
        e.pop("historico_partes_json", None)
        e.pop("origens_json", None)
    return fts


def aggregate(events: list[dict], fields: list[str]) -> list[dict]:
    result = {}
    for e in events:
        key = tuple(e[f] for f in fields)
        d = result.setdefault(key, {**dict(zip(fields, key)), "eventos": 0, "debito_centavos": 0, "credito_centavos": 0, "data_inicial": e["data"], "data_final": e["data"], "sem_contrapartida": 0})
        d["eventos"] += 1
        d["debito_centavos"] += e["debito_centavos"]
        d["credito_centavos"] += e["credito_centavos"]
        d["data_inicial"] = min(d["data_inicial"], e["data"])
        d["data_final"] = max(d["data_final"], e["data"])
        d["sem_contrapartida"] += not bool(e["contrapartida"])
    return sorted(result.values(), key=lambda d: tuple(str(d[f]) for f in fields))


def build(original: Path, converted: Path, output: Path, partial: bool = True) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    source = {
        "arquivo": rel(original), "arquivo_sha256": sha256(original),
        "arquivo_bytes": original.stat().st_size,
        "convertido": rel(converted), "convertido_sha256": sha256(converted),
        "convertido_bytes": converted.stat().st_size,
        "parser_versao": VERSION, "parser_sha256": sha256(Path(__file__)),
    }
    parsed = parse_workbook(converted)
    events, sections = parsed["events"], parsed["sections"]
    for e in events:
        e.update({k: source[k] for k in ("arquivo", "arquivo_sha256", "convertido", "convertido_sha256")})
    missing_totals = [s["secao_id"] for s in sections if s["total_fonte"] is None]
    total_checks = []
    for s in sections:
        if s["total_fonte"] is not None:
            t = s["total_fonte"]
            dif_d = s["debito_centavos"] - t["debito_centavos"]
            dif_c = s["credito_centavos"] - t["credito_centavos"]
            total_checks.append({"secao_id": s["secao_id"], "codigo_conta": s["codigo_conta"], "classificacao": s["classificacao"], "aba": t["aba"], "linha": t["linha"], "eventos": s["movimentos"], "debito_extraido_centavos": s["debito_centavos"], "debito_fonte_centavos": t["debito_centavos"], "credito_extraido_centavos": s["credito_centavos"], "credito_fonte_centavos": t["credito_centavos"], "diferenca_debito_centavos": dif_d, "diferenca_credito_centavos": dif_c, "status": "OK" if dif_d == dif_c == 0 else "DIVERGENTE"})
    limit = any(s["linhas"] == 65536 for s in parsed["sheets"])
    incomplete = partial or bool(limit and missing_totals)
    status = STATUS_INCOMPLETE if incomplete else "CONTEÚDO DISPONÍVEL INDEXADO; COMPLETUDE DOCUMENTAL NÃO CERTIFICADA"
    source["status_documental"] = status
    sqlite_path = output / "razao_geral.sqlite"
    fts = write_sqlite(sqlite_path, events, sections, source)
    # Delete only chunks produced by this indexer; a rerun cannot retain stale years.
    for path in output.glob("eventos-????-parte-*.jsonl"):
        path.unlink()
    chunks = []
    by_year = defaultdict(list)
    for e in events:
        by_year[e["ano"]].append(e)
    for year, year_events in sorted(by_year.items()):
        for i in range(0, len(year_events), CHUNK_SIZE):
            chunk = year_events[i:i + CHUNK_SIZE]
            p = output / f"eventos-{year}-parte-{i // CHUNK_SIZE + 1:03}.jsonl"
            with p.open("w", encoding="utf-8", newline="\n") as f:
                for e in chunk:
                    f.write(json.dumps(e, ensure_ascii=False, separators=(",", ":")) + "\n")
            chunks.append({"arquivo": p.name, "ano": year, "eventos": len(chunk), "sha256": sha256(p), "bytes": p.stat().st_size})
    with sqlite3.connect(sqlite_path) as con:
        nsql, dsql, csql = con.execute("SELECT COUNT(*),COALESCE(SUM(debito_centavos),0),COALESCE(SUM(credito_centavos),0) FROM eventos").fetchone()
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    njson = dj = cj = 0
    for chunk in chunks:
        with (output / chunk["arquivo"]).open(encoding="utf-8") as f:
            for line in f:
                e = json.loads(line)
                njson += 1; dj += e["debito_centavos"]; cj += e["credito_centavos"]
    dsource = sum(e["debito_centavos"] for e in events)
    csource = sum(e["credito_centavos"] for e in events)
    invariant_ok = nsql == njson == parsed["source_events"] == len(events) and dsql == dj == dsource and csql == cj == csource
    warnings = [
        "A fonte recebida é parcial: termina na linha 65.536, dentro da conta 1434 (VIA CAPITAL), sem total da última conta e sem a conta 642. O limite também foi confirmado no XLS original; não é falha da conversão LibreOffice." if incomplete else "A completude documental exige comparação com a exportação contábil de origem.",
        "Não somar este índice aos razões de disponível/ativo/passivo: há sobreposição de contas e lançamentos. Uma futura exportação completa deve substituir esta fonte no índice, após revisão de cobertura/deduplicação; não acrescentá-la automaticamente.",
        "Cada evento é uma linha de uma conta do razão, não um lançamento contábil completo. Somar débitos/créditos de todas as contas não mede fluxo financeiro nem elimina partidas recíprocas.",
        "Cta.C.Part. vazia foi mantida nula. Não foi inferida contrapartida por lote, histórico ou conta; partidas compostas podem exigir o diário ou outras contas.",
        "O sinal armazenado no saldo foi preservado. D positivo/C negativo é verificado pela identidade saldo anterior + débito − crédito = saldo; parênteses visuais do formato não alteram o sinal numérico.",
        "Não foi fabricado saldo anterior. As posições iniciais são exclusivamente as células SALDO ANTERIOR presentes na fonte; não se somam saldos de diferentes datas.",
        "Cobertura de datas global não significa cobertura completa de todas as contas/anos. Consulte os intervalos por conta no catálogo.",
    ]
    catalog = {
        "schema_versao": 1, "parser_versao": VERSION, "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "status_documental": status, "fonte": source, "metadados": parsed["metadata"],
        "abas": parsed["sheets"], "limite_xls_65536": limit,
        "conta_642_presente": any(e["codigo_conta"] == "642" for e in events),
        "secoes_sem_total_fonte": missing_totals,
        "intervalo_movimentos": {"inicio": min((e["data"] for e in events), default=None), "fim": max((e["data"] for e in events), default=None)},
        "contagens": {"eventos": len(events), "contas": len({(s["codigo_conta"], s["classificacao"], s["nome_conta"]) for s in sections}), "secoes": len(sections), "linhas_por_tipo": parsed["row_types"], "sem_contrapartida": sum(not e["contrapartida"] for e in events)},
        "totais_centavos": {"debito": dsource, "credito": csource},
        "por_ano": aggregate(events, ["ano"]),
        "por_grupo": aggregate(events, ["grupo_1", "grupo_2", "grupo_3"]),
        "por_conta": aggregate(events, ["codigo_conta", "classificacao", "nome_conta"]),
        "verificacoes": {"contagem_origem_sqlite_jsonl": "OK" if invariant_ok else "DIVERGENTE", "eventos_origem": parsed["source_events"], "eventos_sqlite": nsql, "eventos_jsonl": njson, "totais_origem_sqlite_jsonl": "OK" if dsql == dj == dsource and csql == cj == csource else "DIVERGENTE", "sqlite_integrity_check": integrity, "recorrencias_saldo_verificadas": parsed["balance_checks"], "recorrencias_saldo_divergentes": parsed["balance_failures"], "totais_de_conta_verificados": len(total_checks), "totais_de_conta_divergentes": sum(t["status"] != "OK" for t in total_checks), "linhas_nao_classificadas": parsed["unknown"]},
        "arquivos_jsonl": chunks, "sqlite": {"arquivo": sqlite_path.name, "busca_fts5": fts},
        "avisos": warnings,
    }
    dump_json(output / "catalogo.json", catalog)
    dump_json(output / "checagens_contas.json", total_checks)
    manifest = {"schema_versao": 1, "parser_versao": VERSION, "fonte": source, "status_documental": status,
                "arquivos": [{"arquivo": p.name, "sha256": sha256(p), "bytes": p.stat().st_size} for p in [sqlite_path, output / "catalogo.json", output / "checagens_contas.json"]] + chunks}
    dump_json(output / "manifesto.json", manifest)
    (output / ".gitignore").write_text("# Derivados grandes, recomputáveis a partir da fonte local.\n*.sqlite\n*.sqlite-*\neventos-*.jsonl\n__pycache__/\n", encoding="utf-8")
    write_readme(output, catalog)
    if not invariant_ok or integrity != "ok" or parsed["unknown"] or parsed["balance_failures"] or any(t["status"] != "OK" for t in total_checks):
        raise RuntimeError("Extração gravada com divergências de QA; veja catalogo.json e checagens_contas.json")
    return catalog


def write_readme(output: Path, c: dict) -> None:
    counts, v = c["contagens"], c["verificacoes"]
    text = f"""# Índice pesquisável do razão geral CSG

**{c['status_documental']}**

O XLS original e o XLSX convertido terminam na linha 65.536, dentro da conta 1434 — VIA CAPITAL, em 10/02/2026, sem total dessa conta. A conta 642 (debêntures) não aparece. Há movimentos de 2022 a setembro de 2026 em outras contas; isso não torna a exportação completa. Dividir o arquivo não recupera o trecho ausente. Os razões separados já disponíveis continuam sendo fontes próprias.

## Conteúdo desta versão

- {counts['eventos']:,} eventos de razão, {counts['contas']:,} contas; valores exatos em centavos inteiros.
- Intervalo global dos movimentos: {c['intervalo_movimentos']['inicio']} a {c['intervalo_movimentos']['fim']}.
- {len(c['arquivos_jsonl'])} fragmentos JSONL, por ano, com no máximo {CHUNK_SIZE} eventos cada.
- {counts['sem_contrapartida']:,} eventos sem Cta.C.Part.; campo preservado nulo, sem inferência.
- {v['totais_de_conta_verificados']:,} totais de conta comparados aos totais impressos, {v['totais_de_conta_divergentes']} divergências.
- {v['recorrencias_saldo_verificadas']:,} recorrências de saldo verificadas, {len(v['recorrencias_saldo_divergentes'])} divergências.
- Contagem origem = SQLite = JSONL e totais de débito/crédito: {v['contagem_origem_sqlite_jsonl']}; integridade SQLite: {v['sqlite_integrity_check']}.

## Arquivos e origem

`catalogo.json` contém SHA-256 das fontes, metadados, contagens por ano/grupo/conta, intervalos por conta, avisos, classificação completa e QA. `checagens_contas.json` contém a comparação de cada total de conta à fonte. `manifesto.json` contém os hashes dos derivados. Esses arquivos e este README são versionáveis. O SQLite e os fragmentos JSONL são grandes e ficam ignorados pelo `.gitignore` local.

Fonte: `{c['fonte']['arquivo']}`. Conversão lida: `{c['fonte']['convertido']}`. Nenhuma fonte foi modificada. A leitura usa `openpyxl`, todas as abas, mantendo contexto de conta e histórico entre abas. Linhas de continuação são concatenadas sem truncamento e guardadas também em partes originais. Cabeçalhos, saldos anteriores e totais são classificados separadamente; linhas não reconhecidas fazem o QA falhar.

O saldo numérico da célula mantém seu sinal, com D positivo e C negativo, verificado a cada movimento por saldo anterior + débito − crédito. O formato de Excel e a seção visual utilizada ficam preservados; parênteses visuais, que variam com a natureza da conta, não são usados para inverter o número. Saldo anterior só existe no índice quando consta na fonte.

## Pesquisa

O SQLite tem tabelas `eventos`, `contas`, `secoes` e `fonte`, índices por conta/classificação/grupo/data/ano/lote/contrapartida e busca textual `busca` (FTS5, quando disponível). `secoes.dados_json` preserva cabeçalho, saldo anterior e total da fonte. Exemplos com Python padrão:

```python
import sqlite3
con = sqlite3.connect('razao_geral.sqlite')
con.row_factory = sqlite3.Row
rows = con.execute("SELECT * FROM eventos WHERE codigo_conta=? AND ano=? ORDER BY data,id", ('1434', 2026)).fetchall()
rows = con.execute("SELECT e.* FROM busca b JOIN eventos e ON e.id=b.rowid WHERE busca MATCH ? ORDER BY e.data,e.id", ('EMPRESTIMO',)).fetchall()
```

Cada evento possui `id`, `secao_id`, `data`, `ano`, `lote`, `codigo_conta`, `classificacao`, `nome_conta`, `grupo_1/2/3`, `historico`, `historico_partes`, `contrapartida`, `contrapartida_codigo`, `debito_centavos`, `credito_centavos`, `saldo_centavos`, natureza/sinal/formato do saldo, `aba`, `linha`, `aba_final`, `linha_final`, `origens` (aba/linha/folha impressa), caminhos e SHA-256 original/convertido. No SQLite, as listas estruturadas ficam em `historico_partes_json` e `origens_json`. Contrapartida numérica é texto para preservar identificadores.

Um evento representa uma linha de uma conta, **não uma partida completa**. Lotes podem ser compostos. Não interpretar a soma de débitos/créditos de todas as contas como fluxo de caixa, nem somar posições de datas distintas. Cta.C.Part. ausente não prova ausência de contrapartida na escrituração.

## Regerar

Requer Python 3 e `openpyxl`. A conversão prévia requer LibreOffice; preservar o XLS original:

```sh
cd clientes/credit-578/levantamento-financeiro
mkdir -p qa/razao_geral
libreoffice -env:UserInstallation=file:///tmp/csg-razao-conversao --headless --convert-to xlsx --outdir qa/razao_geral '../balancetes/Razão - geral.xls'
python indexar_razao_geral.py --self-test
python indexar_razao_geral.py
```

O comando padrão assume esta fonte parcial. Uma futura exportação completa, em XLSX/CSV/TXT ou dividida na origem por ano/grupo, exige revisão de cobertura antes de substituir o índice; o script aceita `--original`, `--xlsx`, `--out` e `--fonte-completa`. Este último apenas retira a marca manual de fonte parcial; limite de 65.536 linhas com conta sem total continua detectado automaticamente. A ausência desse limite não certifica completude documental.

**Não somar nem concatenar este índice aos razões de disponível/ativo/passivo**, pois há sobreposição de contas/movimentos. Substituir a fonte após revisão de cobertura e deduplicação; não executar append automático. A execução regrava somente os derivados com nomes conhecidos na pasta de saída. O script não acessa serviços remotos nem modifica relatórios financeiros.
"""
    (output / "README.md").write_text(text, encoding="utf-8")


def self_test() -> None:
    # Independent fixture: a continuation crosses sheets, a repeated heading
    # must preserve the prior balance, and an explicit total must reconcile.
    with tempfile.TemporaryDirectory(prefix="csg-razao-test-") as tmp:
        p = Path(tmp) / "test.xlsx"
        w = Workbook(); a = w.active; a.title = "Parte 1"
        def put(s, r, values):
            for c, v in values.items():
                s.cell(r, c, v)
        put(a, 1, {1: "Conta:", 2: 42, 3: "2.1.3.01.001", 6: "TESTE"})
        put(a, 2, {3: "SALDO ANTERIOR", 14: 0})
        put(a, 3, {1: datetime(2023, 1, 1), 2: 7, 3: "Histórico integral", 11: 12.34, 14: -12.34})
        b = w.create_sheet("Parte 2")
        put(b, 1, {3: "continuação sem corte"})
        put(b, 2, {1: "Conta:", 2: 42, 3: "2.1.3.01.001", 6: "TESTE"})
        put(b, 3, {1: datetime(2023, 1, 2), 2: 8, 3: "Pagamento", 9: 11, 10: 2.34, 14: -10})
        put(b, 4, {5: "Total da conta:", 10: 2.34, 11: 12.34})
        w.save(p)
        r = parse_workbook(p)
        assert len(r["events"]) == r["source_events"] == 2
        assert r["events"][0]["historico"] == "Histórico integral\ncontinuação sem corte"
        assert r["events"][0]["aba_final"] == "Parte 2"
        assert r["events"][0]["saldo_centavos"] == -1234
        assert r["events"][0]["contrapartida"] is None
        assert len(r["sections"]) == 1 and len(r["sections"][0]["cabecalhos"]) == 2
        assert r["balance_checks"] == 2 and not r["balance_failures"] and not r["unknown"]
        assert r["sections"][0]["debito_centavos"] == 234
        assert r["sections"][0]["credito_centavos"] == 1234
        assert cents("1.234,56") == 123456
        assert saldo_info(1, "\\(#,##0.00\\);#,##0.00")["saldo_centavos"] == 100
    print("Self-test: OK (continuidade entre abas, histórico integral, centavos, contrapartida ausente, saldos e totais).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, default=CLIENT / "balancetes" / "Razão - geral.xls")
    parser.add_argument("--xlsx", type=Path, default=ROOT / "qa" / "razao_geral" / "Razão - geral.xlsx")
    parser.add_argument("--out", type=Path, default=ROOT / "razao-geral")
    parser.add_argument("--fonte-completa", action="store_true", help="Retira apenas a marca manual de fonte parcial; não certifica completude")
    parser.add_argument("--self-test", action="store_true", help="Executa somente fixture de regressão, sem alterar o índice")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    c = build(args.original, args.xlsx, args.out, partial=not args.fonte_completa)
    print(json.dumps({"status": c["status_documental"], "eventos": c["contagens"]["eventos"], "contas": c["contagens"]["contas"], "jsonl": len(c["arquivos_jsonl"]), "qa": c["verificacoes"]["contagem_origem_sqlite_jsonl"], "saida": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
