#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sugere novas regras a partir de correções manuais na conferência."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.caminhos import CONFIG, CONFERENCIA_XLSX, RELATORIOS, garantir_dirs  # noqa: E402
from src.conferencia import ler_conferencia  # noqa: E402
from src.normalizacao import normalizar_chave  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Atualizar regras a partir da conferência")
    parser.add_argument("--arquivo", default=str(CONFERENCIA_XLSX))
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Grava sugestões em regras-sugeridas.json (não altera regras ativas automaticamente)",
    )
    args = parser.parse_args()
    garantir_dirs()

    linhas = ler_conferencia(Path(args.arquivo))
    regras_path = CONFIG / "regras-classificacao.json"
    atuais = json.loads(regras_path.read_text(encoding="utf-8")).get("regras", [])
    nomes = {normalizar_chave(r.get("nome")) for r in atuais}

    sugestoes = []
    vistos = set()
    for l in linhas:
        origem = str(l.get("origem_classificacao") or "")
        if origem not in {"MANUAL", "IMPORTADA DA REVISÃO ANTERIOR"} and int(l.get("confianca") or 0) >= 80:
            # ainda assim considera se status revisado
            if str(l.get("status") or "").upper() not in {"REVISADO", "MANUAL"}:
                continue
        hist = normalizar_chave(l.get("historico_original") or "")
        deb = str(l.get("codigo_conta_debito") or "").strip()
        cred = str(l.get("codigo_conta_credito") or "").strip()
        tipo = str(l.get("tipo_movimento") or "").strip()
        if not hist or not deb or not cred or not tipo:
            continue
        chave = (hist, tipo, deb, cred)
        if chave in vistos:
            continue
        vistos.add(chave)
        nome = f"Sugestão: {hist[:60]}"
        if normalizar_chave(nome) in nomes:
            continue
        sugestoes.append(
            {
                "nome": nome,
                "prioridade": 50,
                "tipo_movimento": tipo,
                "palavras": [hist[:80]],
                "favorecidos": [l.get("favorecido_original")] if l.get("favorecido_original") else [],
                "codigo_conta_debito": deb,
                "codigo_conta_credito": cred,
                "historico_padrao": str(l.get("historico_contabil") or "").upper(),
                "confianca": 80,
                "origem_id": l.get("id_lancamento"),
            }
        )

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = RELATORIOS / f"regras-sugeridas-{stamp}.json"
    payload = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "quantidade": len(sugestoes),
        "aviso": "Revise antes de copiar para regras-classificacao.json",
        "regras": sugestoes,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.aplicar:
        dest = CONFIG / "regras-sugeridas.json"
        dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Sugestões gravadas em {dest}")
    print(f"{len(sugestoes)} sugestões em {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
