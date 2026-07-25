#!/usr/bin/env python3
"""Redistribui escritorio/ para pastas de clientes (Grupo Bianchi e demais)."""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
from paths import ROOT, cliente  # noqa: E402

ESCRITORIO = ROOT / "escritorio"
RH = ESCRITORIO / "rh-trabalhista"
WHATS = RH / "whats" / "GRUPO BIANCHI"

WHATS_MAP = {
    "CARLOS BIANCHI": cliente("carlos-668", "entrada", "whatsapp"),
    "CLAUDIO BINCHI RJ": cliente("claudio-666", "entrada", "whatsapp"),
    "FABIANE BIANCHI": cliente("fabiane-667", "entrada", "whatsapp"),
    "LUCIANO BIANCHI": cliente("luciano-664", "entrada", "whatsapp"),
    "BENITO BIANCHI": cliente("grupo-bianchi", "benito", "whatsapp"),
    "ADENIR BIANCHI": cliente("grupo-bianchi", "adenir", "whatsapp"),
    "CRISTIANO BIANCHI": cliente("grupo-bianchi", "cristiano", "whatsapp"),
    "ELENICE BIANCHI": cliente("grupo-bianchi", "elenice", "whatsapp"),
    "CRISTIANE BIANCHI": cliente("grupo-bianchi", "cristiane", "whatsapp"),
}

# (substrings no nome do arquivo, pasta destino relativa a clientes/)
ARQUIVO_RULES: list[tuple[list[str], str]] = [
    (["grafeno claudio", "grafevo", "secagem claudio"], "claudio-666/entrada/extratos-grafeno"),
    (["recuperacao judicial", "recuperação judicial", "plano-de-recuperacao"], "fabiane-667/entrada/recuperacao-judicial"),
    (["benito"], "grupo-bianchi/benito/entrada"),
    (["fabiane"], "fabiane-667/entrada"),
    (["grafeno claudio", "claudio"], "claudio-666/entrada"),
    (["carlos bianchi", "carlos"], "carlos-668/entrada"),
    (["luciano bianchi", "luciano"], "luciano-664/entrada"),
    (["movimentação de grãos", "movimentacao de graos", "declaração biabchi", "declaracao biabchi"], "grupo-bianchi/compartilhado"),
    (["gilnei", "joão v", "joao v", "aviso prévio", "aviso previo", "termo de rescisão", "termo de rescicao",
      "termo de quitação", "termo de quitacao", "seguro desemprego"], "grupo-bianchi/rh-funcionarios"),
    (["american express", "hipercard", "amemican express"], "grupo-bianchi/cielo"),
    (["connectere"], "grupo-bianchi/entrada"),
    (["bianchi"], "grupo-bianchi/compartilhado"),
]


def mover_seguro(origem: Path, destino: Path) -> bool:
    if not origem.exists():
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    alvo = destino
    if alvo.exists():
        stem, suffix = alvo.stem, alvo.suffix
        n = 2
        while alvo.exists():
            alvo = alvo.with_name(f"{stem}_{n}{suffix}")
            n += 1
    print(f"  → {origem.relative_to(ROOT)} → {alvo.relative_to(ROOT)}")
    shutil.move(str(origem), str(alvo))
    return True


def mover_arvore(origem: Path, destino: Path) -> None:
    if not origem.exists():
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        for item in origem.rglob("*"):
            if item.is_file():
                rel = item.relative_to(origem)
                mover_seguro(item, destino / rel)
        shutil.rmtree(origem, ignore_errors=True)
    else:
        print(f"  → {origem.relative_to(ROOT)}/ → {destino.relative_to(ROOT)}/")
        shutil.move(str(origem), str(destino))


def destino_por_nome(nome: str) -> Path:
    lower = nome.lower()
    for termos, rel in ARQUIVO_RULES:
        if any(t in lower for t in termos):
            return cliente(*rel.split("/"))
    return cliente("grupo-bianchi", "entrada", "a-classificar")


def redistribuir_whatsapp() -> None:
    if not WHATS.exists():
        return
    print("\n=== WhatsApp Grupo Bianchi → clientes ===")
    for pasta_nome, destino in WHATS_MAP.items():
        origem = WHATS / pasta_nome
        if origem.is_dir():
            mover_arvore(origem, destino)

    # .rar e pasta vazia
    for extra in WHATS.parent.glob("GRUPO BIANCHI*"):
        if extra.is_file():
            mover_seguro(extra, cliente("grupo-bianchi", "compartilhado", extra.name))


def redistribuir_cielo() -> None:
    cielo = RH / "cielo"
    if cielo.is_dir():
        print("\n=== cielo/ → grupo-bianchi/cielo ===")
        mover_arvore(cielo, cliente("grupo-bianchi", "cielo"))


def redistribuir_arquivos_soltos() -> None:
    if not RH.exists():
        return
    print("\n=== Arquivos soltos rh-trabalhista/ ===")
    for item in sorted(RH.iterdir()):
        if item.name in ("cielo", "whats"):
            continue
        if item.is_dir():
            dest = destino_por_nome(item.name)
            mover_arvore(item, dest / item.name)
            continue
        dest = destino_por_nome(item.name)
        mover_seguro(item, dest / item.name)


def redistribuir_financeiro() -> None:
    fin = ESCRITORIO / "financeiro"
    if not fin.exists():
        return
    print("\n=== financeiro/ → grupo-bianchi/entrada/financeiro ===")
    dest = cliente("grupo-bianchi", "entrada", "financeiro")
    for item in list(fin.iterdir()):
        mover_seguro(item, dest / item.name)
    fin.rmdir()


def redistribuir_operacional() -> None:
    op = ESCRITORIO / "operacional"
    if not op.exists():
        return
    print("\n=== operacional/ → scripts/operacional ===")
    dest = ROOT / "scripts" / "operacional"
    dest.mkdir(parents=True, exist_ok=True)
    for item in list(op.iterdir()):
        mover_seguro(item, dest / item.name)
    op.rmdir()


def remover_escritorio_vazio() -> None:
    for path in sorted(ESCRITORIO.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    if ESCRITORIO.exists() and not any(ESCRITORIO.iterdir()):
        ESCRITORIO.rmdir()
        print("\n✓ Pasta escritorio/ removida (vazia)")


def criar_indice() -> None:
    texto = """# Grupo Bianchi — mapa de pastas

Família Bianchi com clientes no Domínio e membros sem código próprio.

## Clientes com código Domínio

| Membro | Pasta | Código |
|--------|-------|--------|
| Carlos Bianchi | clientes/carlos-668/ | 668 |
| Cláudio Bianchi RJ | clientes/claudio-666/ | 666 |
| Fabiane Bianchi | clientes/fabiane-667/ | 667 |
| Luciano Bianchi | clientes/luciano-664/ | 664 |

## Membros em grupo-bianchi/

| Membro | Pasta |
|--------|-------|
| Benito | grupo-bianchi/benito/ |
| Adenir | grupo-bianchi/adenir/ |
| Cristiano | grupo-bianchi/cristiano/ |
| Elenice | grupo-bianchi/elenice/ |
| Cristiane | grupo-bianchi/cristiane/ |
| Compartilhado | grupo-bianchi/compartilhado/ |
| Cartões (Cielo) | grupo-bianchi/cielo/ |
| RH funcionários | grupo-bianchi/rh-funcionarios/ |
| A classificar | grupo-bianchi/entrada/a-classificar/ |

Origem: antiga pasta `documentos diversos/` (erroneamente em `escritorio/rh-trabalhista/`).
"""
    dest = cliente("_indice", "grupo_bianchi.md")
    dest.write_text(texto, encoding="utf-8")
    print(f"Índice salvo em: {dest.relative_to(ROOT)}")


def main() -> None:
    if not ESCRITORIO.exists():
        print("Pasta escritorio/ não encontrada — nada a fazer.")
        return

    print("Redistribuindo escritorio/ → clientes/")
    redistribuir_whatsapp()
    redistribuir_cielo()
    redistribuir_arquivos_soltos()
    redistribuir_financeiro()
    redistribuir_operacional()
    remover_escritorio_vazio()
    criar_indice()
    print("\n✅ Redistribuição concluída.")


if __name__ == "__main__":
    main()
