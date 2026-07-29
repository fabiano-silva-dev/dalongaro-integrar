#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fluxo 2 — validar/exportar Domínio a partir das planilhas de conferência."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.caminhos import CONFIG, CONFERENCIAS, PENDENCIAS, garantir_dirs, listar_conferencias  # noqa: E402
from src.conferencia import ler_conferencias  # noqa: E402
from src.dominio import gerar_arquivo_dominio, registrar_historico, salvar_relatorio  # noqa: E402
from src.plano_contas import carregar_ou_extrair  # noqa: E402
from src.validacao import validar_exportacao  # noqa: E402


def _resolver_arquivos(arg: str | None) -> list[Path]:
    if not arg:
        arquivos = listar_conferencias()
        if not arquivos:
            raise FileNotFoundError(
                f"Nenhuma conferência em {CONFERENCIAS}. Execute analisar_planilhas.py primeiro."
            )
        return arquivos
    caminho = Path(arg)
    if caminho.is_dir():
        return sorted(p for p in caminho.glob("CTG-326-*.xlsx") if not p.name.startswith("~$"))
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    return [caminho]


def main() -> int:
    parser = argparse.ArgumentParser(description="Exportar Domínio CTG-326")
    parser.add_argument(
        "--arquivo",
        default=None,
        help="Planilha de conferência, pasta, ou omitir para processar todas",
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

    try:
        caminhos = _resolver_arquivos(args.arquivo)
    except FileNotFoundError as exc:
        print(exc)
        return 1

    cfg = json.loads((CONFIG / "configuracao.json").read_text(encoding="utf-8"))
    plano = carregar_ou_extrair()
    linhas = ler_conferencias(caminhos)
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
        "arquivos_conferencia": [str(c) for c in caminhos],
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
    # histórico: usa o primeiro arquivo como referência da revisão
    registrar_historico(meta, caminhos[0], len(pendencias))
    rel.update(meta)
    rel_path = salvar_relatorio("exportacao", rel)
    print(json.dumps(rel, ensure_ascii=False, indent=2))
    print(f"Arquivo Domínio: {arquivo}")
    print(f"Pendências: {pend_path}")
    print(f"Relatório: {rel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
