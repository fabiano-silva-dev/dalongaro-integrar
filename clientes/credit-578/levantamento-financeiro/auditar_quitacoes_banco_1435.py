#!/usr/bin/env python3
"""Auditoria de contrapartidas entre Direitos Creditórios (1435) e bancos.

Lê os XLS anuais originais somente em memória, sem atualizar lançamentos.
Gera JSON e Markdown reprodutíveis no diretório levantamento-financeiro.
"""
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import subprocess

from indexar_razao_geral import parse_workbook

BASE = Path(__file__).resolve().parent
SOURCE = BASE.parent / "balancetes"
OUTPUT = BASE / "auditoria_quitacoes_1435"
YEARS = (2025, 2026)


def read_year(year):
    path = SOURCE / f"Razão{year}.xls"
    converted_dir = BASE / "qa" / "auditoria_1435"
    converted_dir.mkdir(parents=True, exist_ok=True)
    converted = converted_dir / f"Razão{year}.xlsx"
    if not converted.exists():
        result = subprocess.run(
            ["libreoffice", "-env:UserInstallation=file:///tmp/csg-auditoria-1435",
             "--headless", "--convert-to", "xlsx", "--outdir", str(converted_dir), str(path)],
            capture_output=True, text=True, check=True
        )
        if not converted.exists():
            raise RuntimeError(f"Falha na conversão {path}: {result.stdout} / {result.stderr}")
    parsed = parse_workbook(converted)
    expected = {2022: 1055, 2023: 5863, 2024: 8912, 2025: 27185, 2026: 19036}[year]
    if len(parsed["events"]) != expected or len(parsed["unknown"]) > 2 or parsed["balance_failures"]:
        raise RuntimeError(
            f"Leitura sem integridade no ano {year}: "
            f"{len(parsed['events'])} eventos, "
            f"{len(parsed['unknown'])} linhas desconhecidas, "
            f"{len(parsed['balance_failures'])} divergências de saldo"
        )
    if parsed["unknown"]:
        print("Linhas extras de conversão sem evento contábil:", json.dumps(parsed["unknown"][:2], ensure_ascii=False))
    accounts, events = {}, []
    for ev in parsed["events"]:
        account = ev["codigo_conta"]
        accounts[account] = {"name": ev["nome_conta"], "classification": ev["classificacao"]}
        events.append({
            "year": year, "date": ev["data"], "lot": ev["lote"],
            "account": account, "classification": ev["classificacao"],
            "name": ev["nome_conta"], "debit": ev["debito_centavos"],
            "credit": ev["credito_centavos"],
            "cp": ev.get("contrapartida_codigo") or ev.get("contrapartida") or "",
            "history": ev["historico"],
            "origin": f"{path.name}:{ev['aba']}:{ev['linha']}",
        })
    return events, accounts


def money(v):
    return f"R$ {v/100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def metric(rows, field="credit"):
    return {"events": len(rows), "centavos": sum(r[field] for r in rows)}


def by_cp(rows, accounts):
    d = defaultdict(lambda: {"events": 0, "centavos": 0})
    for e in rows:
        key = e["cp"] or "(sem contrapartida explícita)"
        d[key]["events"] += 1
        d[key]["centavos"] += e["credit"]
    return [
        {"conta": k, "nome": accounts.get(k, {}).get("name", "não informada no razão"),
         **v} for k, v in sorted(d.items(), key=lambda x: -x[1]["centavos"])
    ]


def reconcile(year, events, accounts):
    rights = [e for e in events if e["account"] == "1435" and e["credit"] > 0]
    bank = [e for e in events if e["classification"].startswith("1.1.1.02.") and e["debit"] > 0]
    debtor = [e for e in events if e["classification"].startswith("1.1.2.01.") and e["debit"] > 0]
    bank_codes = {e["account"] for e in bank}
    bank_by_key = defaultdict(list)
    debtor_by_key = defaultdict(list)
    bank_by_date_amount = defaultdict(list)
    for i, b in enumerate(bank):
        bank_by_key[(b["date"], b["lot"], b["debit"])].append(i)
        bank_by_date_amount[(b["date"], b["debit"])].append(i)
    for i, a in enumerate(debtor):
        debtor_by_key[(a["date"], a["lot"], a["debit"])].append(i)

    used_bank = set()
    groups = defaultdict(list)
    matches = []
    samples_by_class = defaultdict(list)
    for e in rights:
        group = "sem vínculo financeiro direto comprovado"
        peer = None
        # Preferir a contrapartida explícita, mas só classificar como bancária
        # se houve efetivamente um débito bancário correspondente.
        candidates = bank_by_key.get((e["date"], e["lot"], e["credit"]), [])
        if e["cp"] in bank_codes:
            candidates = sorted(candidates, key=lambda k: bank[k]["account"] != e["cp"])
        eligible = [k for k in candidates if k not in used_bank]
        if eligible:
            k = eligible[0]
            used_bank.add(k)
            peer = bank[k]
            group = "banco direto / mesmo lote e valor"
        elif e["cp"] in bank_codes:
            group = "contrapartida bancária explícita / sem par exato de valor"
        elif debtor_by_key.get((e["date"], e["lot"], e["credit"])):
            k = debtor_by_key[(e["date"], e["lot"], e["credit"])][0]
            peer = debtor[k]
            group = "possível reclassificação para devedor / mesmo lote e valor"
        elif any(k not in used_bank for k in bank_by_date_amount.get((e["date"], e["credit"]), [])):
            group = "possível banco / mesma data e valor, lote diferente"
        groups[group].append(e)
        item = {
                "classificacao": group, "data": e["date"], "lote": e["lot"],
                "valor_centavos": e["credit"], "contrapartida_explicita": e["cp"],
                "historico": e["history"][:320], "origem_1435": e["origin"],
                "conta_par": peer["account"] if peer else None,
                "historico_par": peer["history"][:320] if peer else None,
                "origem_par": peer["origin"] if peer else None,
            }
        if len(samples_by_class[group]) < 30:
            samples_by_class[group].append(item)
        if len(matches) < 2000:
            matches.append(item)

    result = {
        "year": year,
        "events_total": len(events),
        "rights_1435_all": metric([e for e in events if e["account"] == "1435"], "credit"),
        "rights_1435_credit": metric(rights),
        "rights_1435_debit": metric([e for e in events if e["account"] == "1435" and e["debit"] > 0], "debit"),
        "bank_debits": metric(bank, "debit"),
        "bank_codes": {k: accounts.get(k, {}) for k in sorted(bank_codes)},
        "right_counterparties": by_cp(rights, accounts),
        "bank_entries_cp_1435": metric([x for x in bank if x["cp"] == "1435"], "debit"),
        "classification": {k: metric(v) for k, v in groups.items()},
        "examples": matches[:150],
        "amostras_por_classificacao": dict(samples_by_class),
        "sample_unmatched": samples_by_class.get("sem vínculo financeiro direto comprovado", []),
    }
    return result


def report(data):
    lines = [
        "# CSG — conferência da conta 1435 contra bancos",
        "",
        "**Data-base:** 30/09/2026. **Fontes:** razões anuais originais 2025/2026.",
        "Teste de lançamentos em **1435 — DIREITOS CREDITORIOS**,"
        " comparados a contas bancárias (grupo 1.1.1.02) por data, lote, valor e contrapartida.",
        "",
        "A correspondência contábil não substitui a comprovação da liquidação no extrato e o vínculo ao contrato.",
        "",
    ]
    for r in data["years"]:
        lines.extend([
            f"## {r['year']}",
            "",
            f"- Créditos em 1435: **{money(r['rights_1435_credit']['centavos'])}**"
            f", em **{r['rights_1435_credit']['events']} linhas positivas**.",
            f"- Débitos de bancos analisados: {money(r['bank_debits']['centavos'])}"
            f", em {r['bank_debits']['events']} movimentos.",
            f"- Lançamentos a débito de bancos com contrapartida 1435 explícita:"
            f" {r['bank_entries_cp_1435']['events']} / {money(r['bank_entries_cp_1435']['centavos'])}.",
            "",
            "### Classificação dos créditos da 1435",
        ])
        for k, v in r["classification"].items():
            lines.append(f"- {k}: {v['events']} eventos, **{money(v['centavos'])}**.")
        lines.extend(["", "### Contrapartidas explícitas mais relevantes"])
        for x in r["right_counterparties"][:16]:
            lines.append(f"- Conta {x['conta']} ({x['nome']}): {x['events']} linhas, {money(x['centavos'])}.")
        lines.extend(["", "### Amostras de lançamentos (até 18)"])
        for e in r["examples"][:18]:
            lines.append(
                f"- {e['data']} | lote {e['lote']} | {money(e['valor_centavos'])} | "
                f"{e['classificacao']} | CP {e['contrapartida_explicita'] or 'n.i.'} "
                f"| {e['historico'][:95]} | {e['origem_1435']}"
                + (f" | banco/devedor {e['conta_par']} ({e['origem_par']})" if e['conta_par'] else "")
            )
        lines.extend([""])
    lines.extend([
        "## Critérios de cautela",
        "",
        "- Um match de mesmo dia/lote/valor é evidência contábil de possível contrapartida direta, "
        "mas partidas compostas e coincidência de valores exigem conferência individual.",
        "- Contrapartida explícita sem evento de mesmo valor pode ser lançamento composto; não classificá-lo como não pago.",
        "- Ausência de correspondência com bancos não prova inadimplência: a baixa pode ter sido reclassificação "
        "para outra conta, compensação ou recebimento agrupado.",
        "- Não abater esses créditos novamente do ativo: já estão contabilizados.",
        "- Os arquivos de 2024 incluem saldos de implantação e não devem entrar automaticamente na análise de quitações.",
        ""
    ])
    return "\n".join(lines)


def main():
    results = []
    for year in YEARS:
        events, accounts = read_year(year)
        result = reconcile(year, events, accounts)
        results.append(result)
    payload = {"data_base": "2026-09-30", "years": results}
    OUTPUT.with_suffix(".json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT.with_suffix(".md").write_text(report(payload), encoding="utf-8")
    for r in results:
        print(json.dumps({
            "ano": r["year"], "creditos_1435": r["rights_1435_credit"],
            "contrapartidas": r["right_counterparties"][:10],
            "classes": r["classification"],
            "banco_cp1435": r["bank_entries_cp_1435"]}, ensure_ascii=False))
    print("AUDITORIA_TERMINADA")


if __name__ == "__main__":
    main()
