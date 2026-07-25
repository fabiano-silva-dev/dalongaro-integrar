#!/usr/bin/env python3
"""Reorganização Fase 4: escritório interno, documentação e referências."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
from paths import ROOT, p  # noqa: E402

ESCRITORIO = p("escritorio")
DOCS = p("docs")
REFERENCIA = p("referencia")

PASTAS = {
    "dalongaro-financeiro": ESCRITORIO / "financeiro",
    "documentos diversos": ESCRITORIO / "rh-trabalhista",
}

DOCS_MD = [
    "README_PRODUTIVIDADE.md",
    "README_EXCEL.md",
    "README_enriquecimento.md",
    "output.md",
    "relatorio_auditoria_gabriel.md",
    "relatorio_consistencia_dados.md",
    "relatorio_correcoes_aplicadas.md",
    "relatorio_top_10_empresas.md",
    "resumo_divergencias_simples.md",
]

REFERENCIA_ARQUIVOS = {
    "layout_balancete_exemplo.xlsx": REFERENCIA / "layout_balancete_exemplo.xlsx",
    "Leiaute - Registros.pdf": REFERENCIA / "Leiaute - Registros.pdf",
    "Empresas.pdf": REFERENCIA / "cadastro" / "Empresas.pdf",
    "Contas.pdf": REFERENCIA / "cadastro" / "Contas.pdf",
    "4. Listagem Analítica III Terceiros (Cadastro+Endereço).csv": REFERENCIA / "cadastro" / "listagem_terceiros.csv",
    "dados_cliente.xlsx": REFERENCIA / "cadastro" / "dados_cliente.xlsx",
}

PRODUTIVIDADE_ARQUIVOS = {
    "dados_atividades_estruturados_ClienteTempo Gasto.csv": p("produtividade/processados/dados_atividades_estruturados_ClienteTempo Gasto.csv"),
    "ranking_completo_empresas_tempo.csv": p("produtividade/relatorios/ranking_completo_empresas_tempo.csv"),
    "top_10_empresas_tempo.csv": p("produtividade/relatorios/top_10_empresas_tempo.csv"),
    "relatorio_funcionarios_tempo.txt": p("produtividade/relatorio_funcionarios_tempo.txt"),
    "relatorio_clientes.xlsx": p("produtividade/relatorio_clientes.xlsx"),
}

ESCRITORIO_ARQUIVOS = {
    "extrato_sicoob.xlsx": ESCRITORIO / "financeiro" / "extrato_sicoob.xlsx",
    "My workflow 2.json": ESCRITORIO / "operacional" / "My workflow 2.json",
    "Relatorio_Contabil_Fazendas.docx": DOCS / "relatorios" / "Relatorio_Contabil_Fazendas.docx",
}

ARQUIVO = {
    "processar_dados_produtividade.py.backup": p("_arquivo/processar_dados_produtividade.py.backup"),
}


def mover_seguro(origem: Path, destino: Path) -> None:
    if not origem.exists():
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        print(f"  ⚠ já existe: {destino.relative_to(ROOT)}")
        return
    print(f"  → {origem.relative_to(ROOT)} → {destino.relative_to(ROOT)}")
    shutil.move(str(origem), str(destino))


def criar_mapa() -> None:
    linhas = [
        "# Mapa Fase 4 — Escritório e documentação",
        "",
        "dalongaro-financeiro/ → escritorio/financeiro/",
        "documentos diversos/ → escritorio/rh-trabalhista/",
        "",
        "README_*.md → docs/",
        "relatorio_*.md → docs/relatorios/",
        "layouts e cadastro → referencia/",
        "CSVs de produtividade soltos → produtividade/",
    ]
    destino = DOCS / "mapa_fase4.txt"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"Mapa salvo em: {destino.relative_to(ROOT)}")


def main() -> None:
    print("=== Fase 4: escritório e documentação ===\n")

    for origem_nome, destino in PASTAS.items():
        origem = ROOT / origem_nome
        if not origem.exists():
            print(f"⚠ não encontrado: {origem_nome}")
            continue
        print(f"Movendo {origem_nome}/")
        if destino.exists():
            print(f"  ⚠ destino já existe: {destino.relative_to(ROOT)}")
        else:
            mover_seguro(origem, destino)

    print("\n=== Documentação (docs/) ===")
    (DOCS / "relatorios").mkdir(parents=True, exist_ok=True)
    for nome in DOCS_MD:
        origem = ROOT / nome
        destino = DOCS / "relatorios" / nome if nome.startswith("relatorio_") or nome.startswith("resumo_") else DOCS / nome
        if nome == "output.md":
            destino = DOCS / "relatorios" / nome
        mover_seguro(origem, destino)

    print("\n=== Referência ===")
    (REFERENCIA / "cadastro").mkdir(parents=True, exist_ok=True)
    for nome, destino in REFERENCIA_ARQUIVOS.items():
        mover_seguro(ROOT / nome, destino)

    print("\n=== Produtividade (arquivos soltos) ===")
    for nome, destino in PRODUTIVIDADE_ARQUIVOS.items():
        mover_seguro(ROOT / nome, destino)

    print("\n=== Escritório (arquivos soltos) ===")
    for nome, destino in ESCRITORIO_ARQUIVOS.items():
        mover_seguro(ROOT / nome, destino)

    print("\n=== Arquivo histórico ===")
    for nome, destino in ARQUIVO.items():
        mover_seguro(ROOT / nome, destino)

    criar_mapa()
    print("\n✅ Fase 4 concluída.")


if __name__ == "__main__":
    main()
