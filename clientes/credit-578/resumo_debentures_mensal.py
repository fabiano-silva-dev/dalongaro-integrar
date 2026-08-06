#!/usr/bin/env python3
"""Resumo mês a mês de debêntures em todos os CONTABIL* do Credit-578."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT_RESUMO = BASE / "debentures_resumo_mensal.txt"
OUT_CSV = BASE / "debentures_resumo_mensal.csv"
OUT_POR_ARQ = BASE / "debentures_por_arquivo_mes.csv"

# Conta de despesa de rendimento — líquido = D − C (estorno credita 369)
CONTA_RENDIMENTO = "369"

TIPOS = ("RENDIMENTO", "ESTORNO", "IRRF", "INTEGRALIZACAO", "OUTROS")


def brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def is_debentures(hist: str) -> bool:
    h = hist.upper()
    return "DEB" in h and "NTUR" in h


def classify(hist: str) -> str:
    h = hist.upper()
    if "ESTORN" in h:
        return "ESTORNO"
    if "INTEGRAL" in h:
        return "INTEGRALIZACAO"
    if "IRRF" in h:
        return "IRRF"
    if "RENDIMENTO" in h:
        return "RENDIMENTO"
    return "OUTROS"


def normalize_date(d: str) -> str | None:
    m = re.match(r"^(\d{2})/(\d{2})/(\d{2}|\d{4})$", d.strip())
    if not m:
        return None
    dd, mm, yy = m.groups()
    if len(yy) == 2:
        yy = "20" + yy
    return f"{dd}/{mm}/{yy}"


def ym_key(d: str) -> str:
    dd, mm, yy = d.split("/")
    return f"{yy}-{mm}"


def ym_label(key: str) -> str:
    yy, mm = key.split("-")
    return f"{mm}/{yy}"


def parse_valor(s: str) -> float:
    s = s.strip()
    if not s:
        return 0.0
    return float(s.replace(".", "").replace(",", "."))


def file_sha1(path: Path) -> str:
    h = hashlib.sha1()
    h.update(path.read_bytes())
    return h.hexdigest()[:12]


def extract_rows(path: Path) -> list[dict]:
    """Extrai movimentos de debêntures sem duplicar partidas D+C.

    Regras:
    - RENDIMENTO: só débito na conta 369 (ou D369 em arquivo só-débito)
    - ESTORNO: só crédito na conta 369 (D1327/C369); se arquivo só tiver
      o lado D1327 do estorno, usa esse valor
    - IRRF / INTEGRALIZACAO / OUTROS: lado débito
    """
    text = path.read_bytes().decode("latin-1")
    rows: list[dict] = []
    # buffer estornos por (data, valor) para preferir C369 quando houver os dois lados
    estorno_c369: set[tuple[str, float]] = set()
    pending_estorno_d: list[dict] = []

    for line in text.splitlines():
        parts = line.split("|")
        if len(parts) < 8 or parts[1] != "6100":
            continue
        hist = parts[7] if len(parts) > 7 else ""
        if not is_debentures(hist):
            continue
        data = normalize_date(parts[2])
        if not data:
            continue
        cdeb, ccred = parts[3], parts[4]
        valor = parse_valor(parts[5])
        tipo = classify(hist)
        m = re.search(r"INT-(\d+)", hist, re.I)
        ref = f"INT-{m.group(1)}" if m else ""
        base = {
            "data": data,
            "ym": ym_key(data),
            "tipo": tipo,
            "ref": ref,
            "hist": hist.strip(),
        }

        if tipo == "ESTORNO":
            if ccred == CONTA_RENDIMENTO:
                estorno_c369.add((data, round(valor, 2)))
                rows.append({**base, "conta": ccred, "lado": "C", "valor": valor})
            elif cdeb:
                pending_estorno_d.append(
                    {**base, "conta": cdeb, "lado": "D", "valor": valor}
                )
            continue

        if tipo == "RENDIMENTO":
            # só D369 — evita somar D1327 de qualquer coisa
            if cdeb == CONTA_RENDIMENTO:
                rows.append({**base, "conta": cdeb, "lado": "D", "valor": valor})
            continue

        # demais tipos: lado débito
        if cdeb:
            rows.append({**base, "conta": cdeb, "lado": "D", "valor": valor})

    # estornos só-débito (arquivo sem lado C): inclui D se não houver C369 equivalente
    for r in pending_estorno_d:
        key = (r["data"], round(r["valor"], 2))
        if key not in estorno_c369:
            rows.append(r)

    return rows


def main() -> None:
    files = sorted(
        {p.resolve(): p for p in BASE.rglob("CONTABIL_DOMINIO*.TXT")}.values(),
        key=lambda p: str(p.relative_to(BASE)).lower(),
    )

    by_hash: dict[str, list[Path]] = defaultdict(list)
    for f in files:
        by_hash[file_sha1(f)].append(f)

    representatives: list[Path] = []
    for group in by_hash.values():
        group_sorted = sorted(
            group,
            key=lambda p: (0 if "fiscal" not in p.parts else 1, len(str(p)), str(p)),
        )
        representatives.append(group_sorted[0])
    rep_set = {p.resolve() for p in representatives}

    per_file: dict[str, dict] = {}
    for f in files:
        rows = extract_rows(f)
        rel = str(f.relative_to(BASE))
        by_ym_tipo: dict[tuple[str, str], float] = defaultdict(float)
        for r in rows:
            by_ym_tipo[(r["ym"], r["tipo"])] += r["valor"]
        per_file[rel] = {
            "sha1": file_sha1(f),
            "rows": rows,
            "by_ym_tipo": by_ym_tipo,
            "is_rep": f.resolve() in rep_set,
        }

    months = sorted({r["ym"] for info in per_file.values() for r in info["rows"]})

    consolidado: dict[str, dict] = {}
    for ym in months:
        candidatos = []
        for rel, info in per_file.items():
            if not info["is_rep"]:
                continue
            rows_ym = [r for r in info["rows"] if r["ym"] == ym]
            if not rows_ym:
                continue
            # prioriza arquivo com mais linhas de rendimento/estorno
            score = len(rows_ym)
            candidatos.append((score, rel, rows_ym))
        if not candidatos:
            continue
        candidatos.sort(key=lambda x: (-x[0], x[1]))
        _, fonte, rows_ym = candidatos[0]
        by_tipo: dict[str, float] = defaultdict(float)
        for r in rows_ym:
            by_tipo[r["tipo"]] += r["valor"]
        liquido = by_tipo.get("RENDIMENTO", 0.0) - by_tipo.get("ESTORNO", 0.0)
        consolidado[ym] = {
            "fonte": fonte,
            "linhas": len(rows_ym),
            "by_tipo": dict(by_tipo),
            "liquido_rend": liquido,
            "total": liquido
            + by_tipo.get("IRRF", 0.0)
            + by_tipo.get("INTEGRALIZACAO", 0.0)
            + by_tipo.get("OUTROS", 0.0),
        }

    lines_out: list[str] = []
    w = lines_out.append
    w("CREDIT 578 — Debêntures — resumo mês a mês")
    w(f"Pasta base: {BASE}")
    w(f"Arquivos CONTABIL_DOMINIO*: {len(files)} | conteúdos únicos: {len(by_hash)}")
    w("Critério rendimento líquido: D369 − C369 (estorno)")
    w("=" * 90)
    w("")
    w("DUPLICATAS (mesmo conteúdo):")
    for sha, group in sorted(by_hash.items(), key=lambda x: str(x[1][0])):
        if len(group) < 2:
            continue
        w(f"  [{sha}]")
        for p in group:
            w(f"    - {p.relative_to(BASE)}")
    w("")
    w("CONSOLIDADO MÊS A MÊS")
    w("-" * 90)
    w(
        f"{'Mês':<10} {'Rend.bruto':>12} {'Estorno':>10} {'Rend.líq.':>12} "
        f"{'IRRF':>10} {'Integral.':>12} {'TOTAL':>12}  Fonte"
    )
    tot = defaultdict(float)
    for ym in months:
        c = consolidado[ym]
        bt = c["by_tipo"]
        rend = bt.get("RENDIMENTO", 0.0)
        est = bt.get("ESTORNO", 0.0)
        liq = c["liquido_rend"]
        irrf = bt.get("IRRF", 0.0)
        integ = bt.get("INTEGRALIZACAO", 0.0)
        tot["rend"] += rend
        tot["est"] += est
        tot["liq"] += liq
        tot["irrf"] += irrf
        tot["integ"] += integ
        tot["total"] += c["total"]
        w(
            f"{ym_label(ym):<10} {brl(rend):>12} {brl(est):>10} {brl(liq):>12} "
            f"{brl(irrf):>10} {brl(integ):>12} {brl(c['total']):>12}  "
            f"{Path(c['fonte']).name}"
        )
    w("-" * 90)
    w(
        f"{'TOTAL':<10} {brl(tot['rend']):>12} {brl(tot['est']):>10} {brl(tot['liq']):>12} "
        f"{brl(tot['irrf']):>10} {brl(tot['integ']):>12} {brl(tot['total']):>12}"
    )
    w("")
    w("DETALHE POR ARQUIVO")
    w("-" * 90)
    for rel in sorted(per_file):
        info = per_file[rel]
        marca = " *fonte*" if info["is_rep"] else " (dup)"
        yms = sorted({r["ym"] for r in info["rows"]})
        w(f"\n{rel}{marca}  sha1={info['sha1']}")
        for ym in yms:
            bt = defaultdict(float)
            for r in info["rows"]:
                if r["ym"] == ym:
                    bt[r["tipo"]] += r["valor"]
            liq = bt["RENDIMENTO"] - bt["ESTORNO"]
            partes = [f"REND.bruto={brl(bt['RENDIMENTO'])}"]
            if bt["ESTORNO"]:
                partes.append(f"ESTORNO={brl(bt['ESTORNO'])}")
            partes.append(f"REND.líq={brl(liq)}")
            for t in ("IRRF", "INTEGRALIZACAO", "OUTROS"):
                if bt[t]:
                    partes.append(f"{t}={brl(bt[t])}")
            w(f"  {ym_label(ym)}: {', '.join(partes)}")

    text = "\n".join(lines_out) + "\n"
    OUT_RESUMO.write_text(text, encoding="utf-8")
    print(text)

    def v(x: float) -> str:
        return f"{x:.2f}".replace(".", ",")

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="\n") as f:
        f.write(
            "mes;rendimento_bruto;estorno;rendimento_liquido;irrf;"
            "integralizacao;total;fonte;linhas\n"
        )
        for ym in months:
            c = consolidado[ym]
            bt = c["by_tipo"]
            f.write(
                f"{ym_label(ym)};{v(bt.get('RENDIMENTO', 0))};"
                f"{v(bt.get('ESTORNO', 0))};{v(c['liquido_rend'])};"
                f"{v(bt.get('IRRF', 0))};{v(bt.get('INTEGRALIZACAO', 0))};"
                f"{v(c['total'])};{c['fonte']};{c['linhas']}\n"
            )

    with OUT_POR_ARQ.open("w", encoding="utf-8-sig", newline="\n") as f:
        f.write("arquivo;sha1;representante;mes;tipo;valor;linhas\n")
        for rel in sorted(per_file):
            info = per_file[rel]
            agg: dict[tuple[str, str], list] = defaultdict(list)
            for r in info["rows"]:
                agg[(r["ym"], r["tipo"])].append(r)
            for (ym, tipo), rs in sorted(agg.items()):
                total = sum(x["valor"] for x in rs)
                f.write(
                    f"{rel};{info['sha1']};"
                    f"{'SIM' if info['is_rep'] else 'NAO'};"
                    f"{ym_label(ym)};{tipo};{v(total)};{len(rs)}\n"
                )

    print(f"Gerados:\n  {OUT_RESUMO.name}\n  {OUT_CSV.name}\n  {OUT_POR_ARQ.name}")


if __name__ == "__main__":
    main()
