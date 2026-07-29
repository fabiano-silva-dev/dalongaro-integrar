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
CONFERENCIA_XLSX = CONFERENCIAS / "CTG-326-classificacao.xlsx"  # legado (única)
HISTORICO_EXPORTACOES = RELATORIOS / "historico-exportacoes.json"


def caminho_conferencia_origem(arquivo_origem: str) -> Path:
    """Gera o caminho da conferência correspondente a uma planilha de entrada."""
    stem = Path(arquivo_origem).stem.strip()
    seguro = "".join(ch if ch.isalnum() or ch in "-_ " else "-" for ch in stem)
    seguro = "-".join(seguro.split())
    return CONFERENCIAS / f"CTG-326-{seguro}.xlsx"


def listar_conferencias() -> list[Path]:
    """Lista planilhas de conferência por arquivo (exclui legado único, se houver outras)."""
    arquivos = sorted(CONFERENCIAS.glob("CTG-326-*.xlsx"))
    arquivos = [a for a in arquivos if not a.name.startswith("~$")]
    por_arquivo = [a for a in arquivos if a.name != CONFERENCIA_XLSX.name]
    return por_arquivo or arquivos


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
