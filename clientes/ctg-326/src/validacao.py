"""Validações obrigatórias antes da exportação Domínio."""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Tuple

from .normalizacao import parse_data
from .plano_contas import PlanoContas


def validar_linha(linha: Dict, plano: PlanoContas) -> List[str]:
    erros: List[str] = []
    data = parse_data(linha.get("data"))
    if not data:
        erros.append("data inválida")

    valor = linha.get("valor")
    if not isinstance(valor, Decimal) or valor <= 0:
        erros.append("valor deve ser maior que zero")

    deb = str(linha.get("codigo_conta_debito") or "").strip()
    cred = str(linha.get("codigo_conta_credito") or "").strip()
    if not deb:
        erros.append("débito não preenchido")
    if not cred:
        erros.append("crédito não preenchido")
    if deb and cred and deb == cred:
        erros.append("débito igual ao crédito")
    if deb and not plano.existe(deb):
        erros.append(f"conta débito inexistente: {deb}")
    if cred and not plano.existe(cred):
        erros.append(f"conta crédito inexistente: {cred}")
    if deb and plano.existe(deb) and not plano.eh_analitica(deb):
        erros.append(f"conta débito sintética: {deb}")
    if cred and plano.existe(cred) and not plano.eh_analitica(cred):
        erros.append(f"conta crédito sintética: {cred}")

    hist = str(linha.get("historico_contabil") or "").strip()
    if not hist:
        erros.append("histórico contábil vazio")
    elif len(hist) > 512:
        erros.append("histórico excede 512 caracteres")

    return erros


def validar_exportacao(
    linhas: List[Dict], plano: PlanoContas
) -> Tuple[List[Dict], List[Dict]]:
    """Retorna (validos, pendencias)."""
    validos: List[Dict] = []
    pendencias: List[Dict] = []
    vistos = set()

    for linha in linhas:
        if str(linha.get("exportar") or "").upper() != "SIM":
            pendencias.append({**linha, "motivo_pendencia": "Exportar != SIM"})
            continue
        erros = validar_linha(linha, plano)
        lid = str(linha.get("id_lancamento") or "")
        if lid and lid in vistos:
            erros.append("ID duplicado na planilha")
        if lid:
            vistos.add(lid)
        if erros:
            pendencias.append({**linha, "motivo_pendencia": "; ".join(erros)})
        else:
            validos.append(linha)
    return validos, pendencias
