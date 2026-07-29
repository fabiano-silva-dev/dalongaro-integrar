#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fluxo 1 — ler planilhas, classificar e gerar conferências (uma por arquivo)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.caminhos import (  # noqa: E402
    CONFERENCIA_XLSX,
    PENDENCIAS,
    PLANILHAS,
    RELATORIOS,
    caminho_conferencia_origem,
    garantir_dirs,
)
from src.classificacao import classificar_lista  # noqa: E402
from src.conferencia import (  # noqa: E402
    gerar_conferencias_por_arquivo,
    ler_conferencia,
    ler_conferencias,
    mesclar_com_revisao_anterior,
)
from src.leitura_planilhas import listar_planilhas, ler_arquivo  # noqa: E402
from src.plano_contas import carregar_ou_extrair  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Analisar planilhas CTG-326")
    parser.add_argument(
        "--reprocessar",
        action="store_true",
        help="Regenera as conferências preservando ajustes manuais (com backup)",
    )
    parser.add_argument(
        "--forcar-plano",
        action="store_true",
        help="Reextrai o plano de contas do PDF",
    )
    args = parser.parse_args()
    garantir_dirs()

    plano = carregar_ou_extrair(forcar=args.forcar_plano or True)
    arquivos = listar_planilhas(PLANILHAS)
    if not arquivos:
        print(f"Nenhuma planilha em {PLANILHAS}")
        return 1

    lancamentos = []
    abas = 0
    for arq in arquivos:
        lidos = ler_arquivo(arq)
        lancamentos.extend(lidos)
        abas += len({l.aba_origem for l in lidos})
        print(f"  {arq.name}: {len(lidos)} lançamentos")

    # revisões anteriores: por arquivo + legado único, se existir
    anteriores = ler_conferencias()
    if CONFERENCIA_XLSX.exists():
        ids = {a.get("id_lancamento") for a in anteriores}
        for linha in ler_conferencia(CONFERENCIA_XLSX):
            if linha.get("id_lancamento") not in ids:
                anteriores.append(linha)

    classificados = classificar_lista(lancamentos, plano)
    if anteriores:
        classificados = mesclar_com_revisao_anterior(classificados, anteriores)

    caminhos = gerar_conferencias_por_arquivo(classificados, plano)

    pend = [l for l in classificados if l.status in {"PENDENTE", "REVISAR"} or l.exportar != "SIM"]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    pend_path = PENDENCIAS / f"pendencias-analise-{stamp}.json"
    pend_path.write_text(
        json.dumps([l.to_dict() for l in pend], ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    entradas = sum((l.valor for l in classificados if l.tipo_movimento == "ENTRADA"), Decimal("0"))
    saidas = sum((l.valor for l in classificados if l.tipo_movimento == "SAIDA"), Decimal("0"))
    status_count = Counter(l.status for l in classificados)
    conf_baixa = sum(1 for l in classificados if l.confianca < 80)

    por_arquivo = []
    for arq in arquivos:
        itens = [l for l in classificados if l.arquivo_origem == arq.name]
        por_arquivo.append(
            {
                "arquivo": arq.name,
                "conferencia": str(caminho_conferencia_origem(arq.name)),
                "lancamentos": len(itens),
                "classificados": sum(1 for l in itens if l.status == "CLASSIFICADO"),
                "pendentes_ou_revisar": sum(
                    1 for l in itens if l.status in {"PENDENTE", "REVISAR"}
                ),
            }
        )

    relatorio = {
        "executado_em": datetime.now().isoformat(timespec="seconds"),
        "arquivos_lidos": [a.name for a in arquivos],
        "quantidade_abas": abas,
        "lancamentos_identificados": len(classificados),
        "status": dict(status_count),
        "nao_classificados_ou_revisar": len(pend),
        "baixa_confianca": conf_baixa,
        "total_entradas": str(entradas),
        "total_saidas": str(saidas),
        "plano_contas_contas": len(plano.contas),
        "conferencias": [str(c) for c in caminhos],
        "por_arquivo": por_arquivo,
        "pendencias": str(pend_path),
        "reprocessar": args.reprocessar,
        "observacao": (
            "Exportação definitiva NÃO executada. "
            "Revise as planilhas de conferência e use scripts/exportar_dominio.py."
        ),
    }
    rel_path = RELATORIOS / f"analise-{stamp}.json"
    rel_path.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== Resumo ===")
    print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    print("\nConferências geradas:")
    for c in caminhos:
        print(f"  {c}")
    print(f"Pendências: {pend_path}")
    print(f"Relatório: {rel_path}")
    if conf_baixa or pend:
        print(
            "\nHá classificações duvidosas/pendentes. "
            "NÃO execute a exportação definitiva até revisar as planilhas."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
