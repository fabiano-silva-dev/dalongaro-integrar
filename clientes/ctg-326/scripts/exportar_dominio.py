#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fluxo 2 — validar/exportar Domínio a partir da planilha de conferência."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.caminhos import CONFIG, CONFERENCIA_XLSX, PENDENCIAS, garantir_dirs  # noqa: E402
from src.conferencia import ler_conferencia  # noqa: E402
from src.dominio import gerar_arquivo_dominio, registrar_historico, salvar_relatorio  # noqa: E402
from src.plano_contas import carregar_ou_extrair  # noqa: E402
from src.validacao import validar_exportacao  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Exportar Domínio CTG-326")
    parser.add_argument(
        "--arquivo",
        default=str(CONFERENCIA_XLSX),
        help="Planilha de conferência revisada",
    )
    parser.add_argument(
        "--validar",
        action="store_true",
        help="Somente valida — não gera arquivo definitivo",
    )
    parser.add_argument(
        "--forcar",
        action="store_true",
        help="Permite exportar mesmo com classificações de baixa confiança já marcadas SIM",
    )
    args = parser.parse_args()
    garantir_dirs()

    caminho = Path(args.arquivo)
    if not caminho.exists():
        print(f"Arquivo não encontrado: {caminho}")
        return 1

    cfg = json.loads((CONFIG / "configuracao.json").read_text(encoding="utf-8"))
    plano = carregar_ou_extrair()
    linhas = ler_conferencia(caminho)
    validos, pendencias = validar_exportacao(linhas, plano)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    pend_path = PENDENCIAS / f"pendencias-exportacao-{stamp}.json"
    pend_path.write_text(
        json.dumps(pendencias, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    total_validos = sum((v["valor"] for v in validos), Decimal("0"))
    duvidosos = [
        v
        for v in validos
        if int(v.get("confianca") or 0) < int(cfg.get("confianca_minima_exportacao", 80))
    ]

    rel = {
        "executado_em": datetime.now().isoformat(timespec="seconds"),
        "arquivo_conferencia": str(caminho),
        "linhas_lidas": len(linhas),
        "validos": len(validos),
        "pendencias": len(pendencias),
        "valor_total_validos": str(total_validos),
        "duvidosos_marcados_sim": len(duvidosos),
        "arquivo_pendencias": str(pend_path),
        "modo": "validar" if args.validar else "exportar",
    }

    if args.validar:
        rel_path = salvar_relatorio("validacao", rel)
        print(json.dumps(rel, ensure_ascii=False, indent=2))
        print(f"Relatório: {rel_path}")
        print(f"Pendências: {pend_path}")
        return 0 if not pendencias else 2

    if duvidosos and not args.forcar:
        rel["bloqueado"] = True
        rel["motivo"] = (
            "Existem linhas Exportar=SIM com confiança baixa. "
            "Revise a planilha ou use --forcar."
        )
        rel_path = salvar_relatorio("exportacao-bloqueada", rel)
        print(json.dumps(rel, ensure_ascii=False, indent=2))
        print(f"Relatório: {rel_path}")
        return 3

    if not validos:
        print("Nenhum lançamento válido para exportar.")
        salvar_relatorio("exportacao-vazia", rel)
        return 4

    arquivo, meta = gerar_arquivo_dominio(
        validos,
        codigo_empresa=str(cfg.get("codigo_empresa", "326")),
        cnpj=str(cfg.get("cnpj", "87445102000107")),
        usuario=str(cfg.get("usuario_exportacao", "CTG326")),
    )
    registrar_historico(meta, caminho, len(pendencias))
    rel.update(meta)
    rel_path = salvar_relatorio("exportacao", rel)
    print(json.dumps(rel, ensure_ascii=False, indent=2))
    print(f"Arquivo Domínio: {arquivo}")
    print(f"Pendências: {pend_path}")
    print(f"Relatório: {rel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
