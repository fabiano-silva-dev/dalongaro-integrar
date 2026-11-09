#!/usr/bin/env python3
"""Auditoria documental dos históricos de ajustes e créditos em banco da CSG."""
import json
import re
from collections import defaultdict, Counter
from pathlib import Path
from auditar_quitacoes_banco_1435 import read_year, money

BASE=Path(__file__).resolve().parent
P_OUT=BASE/"auditoria_ajustes_historicos_CSG.md"
P_JSON=BASE/"auditoria_ajustes_historicos_CSG.json"
YEARS=[2022,2023,2024,2025,2026]
PAT=re.compile(r"AJUST|EXERC[IÍ]CIOS? ANTER|RECLASS|RETIFIC|CORRE[CÇ]|DIFEREN[CÇ]|ACERTO|SALDO FINAL|SALDO INICIAL|REGULARIZ|BAIXA DE|ESTORNO",re.I)

def grp(account):
    return ("banco" if account.startswith("1.1.1.02.") else 
            "duplicatas" if account.startswith("1.1.2.01.") else
            "direitos genericos" if account.startswith("1.1.2.02.") else
            "outro ativo" if account.startswith("1.") else
            "passivo" if account.startswith("2.1.") else
            "patrimonio" if account.startswith(("2.4.","2.5.")) else
            "despesa" if account.startswith("3.") else
            "receita" if account.startswith("4.") else "outro")

def line(e):
    return f"- {e['date']} | lote {e['lot']} | conta {e['account']} ({e['name'][:52]}) | D {money(e['debit'])} / C {money(e['credit'])} | CP {e['cp'] or 'n.i.'} | {e['history'][:150]} | {e['origin']}"

def audit_year(y):
    ev,ac=read_year(y)
    bylot=defaultdict(list)
    for e in ev: bylot[(e["date"],e["lot"])].append(e)
    relevant=[e for e in ev if PAT.search(e["history"]) and (grp(e["classification"]) in ("duplicatas","direitos genericos","banco","patrimonio","passivo"))]
    adjustments=[e for e in relevant if not ("SALDO FINAL EM" in e["history"].upper() and y==2024)]
    groups=defaultdict(lambda: {"n":0,"debit":0,"credit":0})
    for e in adjustments:
        k=(grp(e["classification"]),e["account"],e["name"][:80])
        groups[k]["n"]+=1;groups[k]["debit"]+=e["debit"];groups[k]["credit"]+=e["credit"]
    # select true high signal adjustments
    signal=[e for e in adjustments if re.search(r"AJUST|EXERC[IÍ]CIOS? ANTER|RECLASS|REGULARIZ|ACERTO|DIFEREN[CÇ]",e["history"],re.I)]
    signal.sort(key=lambda e:max(e["debit"],e["credit"]),reverse=True)
    # count all BANK DEBITS by cp/account categories
    bank=[e for e in ev if grp(e["classification"])=="banco" and e["debit"]>0]
    bank_by_cp=defaultdict(lambda:{"count":0,"amount":0,"samples":[]})
    for e in bank:
        cp=e["cp"]
        acp=ac.get(cp,{}).get("classification","")
        cat=grp(acp) if acp else "sem codigo ou mapa"
        d=bank_by_cp[(cat,cp,ac.get(cp,{}).get("name","não identificada"))]
        d["count"]+=1;d["amount"]+=e["debit"]
        if len(d["samples"])<4:d["samples"].append({k:e[k] for k in ("date","lot","debit","history","origin")})
    # inspect prior-period equity corrections
    equity=[e for e in ev if grp(e["classification"])=="patrimonio" and (PAT.search(e["history"]) or "267"==e["account"])]
    equity.sort(key=lambda e:max(e["debit"],e["credit"]),reverse=True)
    # counterpart pair of relevant adjustments
    pairs=[]
    for e in signal[:60]:
        siblings=[s for s in bylot[(e["date"],e["lot"])] if s is not e]
        pairs.append({"event":e,"related":sorted(siblings,key=lambda x:max(x["debit"],x["credit"]),reverse=True)[:10],"total_related":len(siblings)})
    return {
      "year":y,"events":len(ev),"accounts":len(ac),
      "bank_inflows":sum(x["debit"] for x in bank),
      "bank_debits_by_cp":[{"kind":k[0],"cp":k[1],"name":k[2],**v} for k,v in sorted(bank_by_cp.items(),key=lambda z:-z[1]["amount"])],
      "adjustment_candidates":len(adjustments),
      "high_signal":len(signal),
      "top_adj_groups":[{"kind":k[0],"account":k[1],"name":k[2],**v} for k,v in sorted(groups.items(),key=lambda z:-(z[1]["debit"]+z[1]["credit"]))[:100]],
      "sample_adj_with_pair":pairs,
      "equity_adjustments":equity[:100]
    }

def main():
    years=[audit_year(y) for y in YEARS]
    lines=["# CSG — auditoria de ajustes históricos de saldos e contrapartidas bancárias",
    "","**Fontes:** cinco razões anuais originais 2022–2026, convertidos e validados pelo indexador do levantamento.",
    "**Escopo:** pesquisa de históricos de ajuste/reclassificação e classificação dos débitos bancários por contrapartida.",
    "Esta auditoria **não recomenda lançamentos sem documentação**; eventos em lote composto exigem análise do diário.",""]
    for r in years:
        lines.extend([f"## {r['year']}","",
            f"- Eventos no razão: {r['events']}. Créditos nos bancos (débito contábil): {money(r['bank_inflows'])}.",
            f"- Linhas não-implantação com palavras de ajuste em ativo/passivo/PL/bancos: {r['adjustment_candidates']}, das quais {r['high_signal']} com termos de correção/reclassificação.","",
            "### Entradas em bancos por contrapartida predominante"])
        for z in r["bank_debits_by_cp"][:28]:
            lines.append(f"- CP {z['cp'] or 'n.i.'}: **{z['name'][:85]}** [{z['kind']}]; {z['count']} lançamentos, **{money(z['amount'])}**.")
        lines.append("")
        lines.append("### Lançamentos de ajuste com pares no mesmo lote (amostras)")
        for p in r["sample_adj_with_pair"][:22]:
            e=p["event"]
            lines.append(line(e))
            for s in p["related"][:5]:
                lines.append("  "+line(s)[2:])
        lines.append("")
        lines.append("### Ajustes patrimoniais e conta 267, quando presentes")
        for e in r["equity_adjustments"][:20]:
            lines.append(line(e))
        lines.append("")
    lines.extend(["## Conclusão metodológica",
      "- Recebimento em banco já debitado **não pode ser debitado novamente** por ajuste. Corrige-se a contrapartida efetivamente errada, se comprovada.",
      "- Crédito de banco para 1435 está comprovado na auditoria específica, mas **não equivale** a baixa de conta individual.",
      "- Transferência de saldos entre direitos genéricos e clientes individuais **não reduz ativo total**.",
      "- Se a diferença se origina de erro de período anterior, o CPC 23 disciplina ajustes retrospectivos e divulgação; não usar a diferença residual como contrapartida automática.",
      "- Se a diferença representa risco de crédito, avaliar a provisão pelo CPC 48. Diferença da planilha, sozinha, não é perda esperada.",
      ""])
    P_OUT.write_text("\n".join(lines),encoding="utf-8")
    # To keep repository light, store summary, not all individual client events
    P_JSON.write_text(json.dumps({"years":[{
        "year":r["year"],"events":r["events"],"bank_inflows":r["bank_inflows"],
        "bank_debits_by_cp":r["bank_debits_by_cp"][:100],
        "adjustment_candidates":r["adjustment_candidates"],"high_signal":r["high_signal"],
        "top_adj_groups":r["top_adj_groups"][:80],
        "sample_adj_with_pair":r["sample_adj_with_pair"][:35],
        "equity_adjustments":r["equity_adjustments"][:35]
    } for r in years]},ensure_ascii=False,indent=2),encoding="utf-8")
    for r in years:
        print(json.dumps({"year":r["year"],"bank_inflows":r["bank_inflows"],
        "top_bank_cp":r["bank_debits_by_cp"][:12],"adjustment_candidates":r["adjustment_candidates"],
        "high_signal":r["high_signal"],"top_adj_groups":r["top_adj_groups"][:8],
        "top_adj_examples":[{"date":x["event"]["date"],"lot":x["event"]["lot"],"account":x["event"]["account"],
        "value":max(x["event"]["debit"],x["event"]["credit"]),"history":x["event"]["history"],
        "related":[{"account":e["account"],"debit":e["debit"],"credit":e["credit"]} for e in x["related"][:3]]} for x in r["sample_adj_with_pair"][:8]]},ensure_ascii=False))
    print("AUDITORIA_AJUSTES_CONCLUIDA")

if __name__=="__main__":
    main()
