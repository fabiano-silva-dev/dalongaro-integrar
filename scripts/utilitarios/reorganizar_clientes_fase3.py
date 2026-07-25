#!/usr/bin/env python3
"""Reorganização Fase 3: move pastas de clientes para clientes/ com nomenclatura padronizada."""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
from paths import ROOT, p  # noqa: E402

CLIENTES = p("clientes")

# pastas na raiz → clientes/nome-codigo
PASTAS_CLIENTE = {
    "credit": "credit-578",
    "carlos-pj-668": "carlos-668",
    "claudio-pj-666": "claudio-666",
    "fabiane-pj-667": "fabiane-667",
    "luciano-pj-664": "luciano-664",
    "limarin-208": "limarin-208",
    "cootrafax-181": "cootrafax-181",
    "Busanelo": "busanelo",
    "Elenise": "elenise",
    "Milanesa": "milanesa",
    "posto pilecco": "posto-pilecco",
}

# arquivos na raiz → destino relativo a clientes/
ARQUIVOS_RAIZ = {
    "clientes.csv": "_indice/clientes.csv",
    "ANO TODO SICREDI (1).pdf": "posto-pilecco/entrada/ANO TODO SICREDI (1).pdf",
    "ANO TODO SICREDI (1).ofx": "posto-pilecco/entrada/ANO TODO SICREDI (1).ofx",
    "comparacao_sicredi_razao.csv": "posto-pilecco/saida/comparacao_sicredi_razao.csv",
    "comparacao_entradas_por_historico.csv": "posto-pilecco/saida/comparacao_entradas_por_historico.csv",
    "historico_por_dia.csv": "posto-pilecco/saida/historico_por_dia.csv",
    "entradas_registro_a_registro.csv": "posto-pilecco/saida/entradas_registro_a_registro.csv",
    "contas_analiticas_balancete-luciano-rj-filial-02-2025-01.xlsx": "luciano-664/contas_analiticas_balancete-rj-filial-02-2025-01.xlsx",
    "Relatório Credit.pdf": "credit-578/saida/Relatório Credit.pdf",
    "relatorio_fiscal.xlsx": "credit-578/saida/relatorio_fiscal.xlsx",
    "relatorio_fiscal2025-05.xlsx": "credit-578/saida/relatorio_fiscal2025-05.xlsx",
    "relatorio_fiscal2025-06.xlsx": "credit-578/saida/relatorio_fiscal2025-06.xlsx",
    "relatorio_fiscal_entradas_2025-06.xlsx": "credit-578/saida/relatorio_fiscal_entradas_2025-06.xlsx",
    "relatorio_operacoes.xlsx": "credit-578/saida/relatorio_operacoes.xlsx",
    "relatorio_recebimentos_fiscal_2025-04.xlsx": "credit-578/saida/relatorio_recebimentos_fiscal_2025-04.xlsx",
    "relatorio_recebimentos_fiscal_2025-05.xlsx": "credit-578/saida/relatorio_recebimentos_fiscal_2025-05.xlsx",
    "relatorio_resumido2025-04.xlsx": "credit-578/saida/relatorio_resumido2025-04.xlsx",
    "relatorio_resumido2025-05.xlsx": "credit-578/saida/relatorio_resumido2025-05.xlsx",
    "relatorio_resumido2025-06.xlsx": "credit-578/saida/relatorio_resumido2025-06.xlsx",
    "parcelas_por_nota_35_42_49.xlsx": "credit-578/saida/parcelas_por_nota_35_42_49.xlsx",
}

CCB_RE = re.compile(r"(\d{2})\.(\d{4})")


def periodo_ccb(nome: str) -> str | None:
    m = CCB_RE.search(nome)
    if m:
        return f"{m.group(2)}-{m.group(1)}"
    return None


def mover_seguro(origem: Path, destino: Path) -> None:
    if not origem.exists():
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        print(f"  ⚠ já existe, pulando: {destino}")
        return
    print(f"  → {origem.relative_to(ROOT)} → {destino.relative_to(ROOT)}")
    shutil.move(str(origem), str(destino))


def reorganizar_credit(credit_dir: Path, destino: Path) -> None:
    """Organiza credit/ em entrada, ccb, fiscal, balancetes, saida, _arquivo."""
    subdirs = {
        "entrada": destino / "entrada",
        "ccb": destino / "ccb",
        "fiscal/nfe": destino / "fiscal" / "nfe",
        "fiscal/dominio": destino / "fiscal" / "dominio",
        "fiscal/notas_entradas": destino / "fiscal" / "notas_entradas",
        "fiscal/planilhas": destino / "fiscal" / "planilhas",
        "balancetes": destino / "balancetes",
        "saida": destino / "saida",
        "_arquivo/zips": destino / "_arquivo" / "zips",
    }
    for d in subdirs.values():
        d.mkdir(parents=True, exist_ok=True)

    # CCB: achatar pastas
    for item in sorted(credit_dir.iterdir()):
        nome = item.name
        if not nome.startswith("CCB"):
            continue
        if item.suffix.lower() == ".zip":
            mover_seguro(item, subdirs["_arquivo/zips"] / nome)
            continue
        periodo = periodo_ccb(nome)
        if not periodo:
            continue
        pasta_dest = subdirs["ccb"] / periodo
        pasta_dest.mkdir(parents=True, exist_ok=True)
        if item.is_dir():
            fontes = list(item.rglob("*"))
            arquivos = [f for f in fontes if f.is_file()]
            for arq in arquivos:
                alvo = pasta_dest / arq.name
                if alvo.exists():
                    alvo = pasta_dest / f"{item.stem}_{arq.name}"
                mover_seguro(arq, alvo)
            shutil.rmtree(item, ignore_errors=True)
            print(f"  CCB {nome} → ccb/{periodo}/ ({len(arquivos)} arquivos)")

    # Classificar demais arquivos
    for item in sorted(credit_dir.iterdir()):
        if not item.exists():
            continue
        nome = item.name
        lower = nome.lower()

        if item.is_dir():
            if nome == "notas_fiscais_de_entradas_excel":
                for f in item.rglob("*"):
                    if f.is_file():
                        mover_seguro(f, subdirs["fiscal/notas_entradas"] / f.name)
                shutil.rmtree(item, ignore_errors=True)
            else:
                mover_seguro(item, subdirs["entrada"] / nome)
            continue

        if lower.endswith(".zip"):
            mover_seguro(item, subdirs["_arquivo/zips"] / nome)
        elif lower.endswith(".xml") and ("nfe" in lower or "proc" in lower or "estorno" in lower or "danfe" in lower):
            mover_seguro(item, subdirs["fiscal/nfe"] / nome)
        elif lower.endswith(".xml"):
            mover_seguro(item, subdirs["fiscal/planilhas"] / nome)
        elif "contabil_dominio" in lower or lower.endswith("sped_diario") or nome.startswith("sped_"):
            mover_seguro(item, subdirs["fiscal/dominio"] / nome)
        elif "balancete" in lower or "balanço" in lower or lower == "balanço.pdf":
            mover_seguro(item, subdirs["balancetes"] / nome)
        elif lower.startswith("relatorio") and lower.endswith((".xlsx", ".pdf", ".docx")):
            mover_seguro(item, subdirs["saida"] / nome)
        elif lower.endswith((".xlsx", ".xls", ".xlsm", ".ods")) and "ccb" not in lower:
            mover_seguro(item, subdirs["fiscal/planilhas"] / nome)
        elif lower.endswith((".pdf", ".docx", ".csv", ".txt")):
            mover_seguro(item, subdirs["entrada"] / nome)
        else:
            mover_seguro(item, subdirs["entrada"] / nome)

    if credit_dir.exists() and not any(credit_dir.iterdir()):
        credit_dir.rmdir()


def reorganizar_posto_pilecco(destino: Path) -> None:
    """Organiza arquivos do posto pilecco em entrada/ e saida/."""
    (destino / "entrada").mkdir(parents=True, exist_ok=True)
    (destino / "saida").mkdir(parents=True, exist_ok=True)

    entrada_raiz = ROOT / "entradas_por_historico"
    if entrada_raiz.is_dir():
        dest_hist = destino / "saida" / "entradas_por_historico"
        if not dest_hist.exists():
            print(f"  → entradas_por_historico/ → {dest_hist.relative_to(ROOT)}")
            shutil.move(str(entrada_raiz), str(dest_hist))

    for nome in ("sicredi-pilecco-ofx.ods", "Razão.xls", "Razão.csv", "SICREDI.pdf"):
        mover_seguro(destino / nome, destino / "entrada" / nome)


def criar_mapa() -> None:
    linhas = [
        "# Mapa de pastas — Fase 3",
        "# Formato: antigo → novo",
        "",
    ]
    for antigo, novo in PASTAS_CLIENTE.items():
        linhas.append(f"{antigo}/ → clientes/{novo}/")
    linhas.append("")
    linhas.append("# Arquivos da raiz movidos — ver ARQUIVOS_RAIZ no script")
    mapa = CLIENTES / "_indice" / "mapa_pastas.txt"
    mapa.parent.mkdir(parents=True, exist_ok=True)
    mapa.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"Mapa salvo em: {mapa.relative_to(ROOT)}")


def main() -> None:
    print(f"Reorganizando clientes em: {CLIENTES}")
    CLIENTES.mkdir(parents=True, exist_ok=True)
    (CLIENTES / "_indice").mkdir(parents=True, exist_ok=True)

    # Mover pastas de clientes (exceto credit — tratamento especial)
    for antigo, novo in PASTAS_CLIENTE.items():
        origem = ROOT / antigo
        destino = CLIENTES / novo
        if not origem.exists():
            print(f"⚠ pasta não encontrada: {antigo}")
            continue
        if antigo == "credit":
            print("\n=== Reorganizando credit → credit-578 ===")
            reorganizar_credit(origem, destino)
        elif destino.exists():
            print(f"⚠ destino já existe: {destino}")
        else:
            print(f"\n=== {antigo} → {novo} ===")
            mover_seguro(origem, destino)

    # posto-pilecco: subpastas entrada/saida
    posto = CLIENTES / "posto-pilecco"
    if posto.exists():
        print("\n=== Organizando posto-pilecco ===")
        reorganizar_posto_pilecco(posto)

    # Arquivos soltos na raiz
    print("\n=== Arquivos da raiz ===")
    for nome, rel_dest in ARQUIVOS_RAIZ.items():
        mover_seguro(ROOT / nome, CLIENTES / rel_dest)

    criar_mapa()
    print("\n✅ Fase 3 concluída.")


if __name__ == "__main__":
    main()
