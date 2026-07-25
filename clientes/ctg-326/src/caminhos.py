"""Caminhos absolutos relativos à raiz CTG-326."""

from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

ENTRADA = RAIZ / "entrada"
PLANILHAS = ENTRADA / "planilhas"
PLANO_CONTAS_PDF = ENTRADA / "plano-contas" / "contas.pdf"

TRABALHO = RAIZ / "trabalho"
EXTRAIDO = TRABALHO / "extraido"
CONFERENCIAS = TRABALHO / "conferencias"
TEMPORARIOS = TRABALHO / "temporarios"

SAIDA = RAIZ / "saida"
DOMINIO = SAIDA / "dominio"
RELATORIOS = SAIDA / "relatorios"
PENDENCIAS = SAIDA / "pendencias"

CONFIG = RAIZ / "configuracoes"
LOGS = RAIZ / "logs"

PLANO_CONTAS_JSON = EXTRAIDO / "plano-contas.json"
CONFERENCIA_XLSX = CONFERENCIAS / "CTG-326-classificacao.xlsx"
HISTORICO_EXPORTACOES = RELATORIOS / "historico-exportacoes.json"


def garantir_dirs() -> None:
    for p in (
        PLANILHAS,
        ENTRADA / "plano-contas",
        EXTRAIDO,
        CONFERENCIAS,
        TEMPORARIOS,
        DOMINIO,
        RELATORIOS,
        PENDENCIAS,
        CONFIG,
        LOGS,
    ):
        p.mkdir(parents=True, exist_ok=True)
