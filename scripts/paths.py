"""Caminhos do workspace dalongaro-integrar."""
from __future__ import annotations

import os
from pathlib import Path


def get_root() -> Path:
    """Retorna a raiz do workspace (onde ficam produtividade/, clientes/, etc.)."""
    here = Path(__file__).resolve().parent
    for candidate in (here.parent, *here.parents):
        if (candidate / "produtividade").is_dir() and (candidate / "requirements.txt").is_file():
            return candidate
    return here.parent


ROOT = get_root()
CLIENTES = ROOT / "clientes"
DOCS = ROOT / "docs"
REFERENCIA = ROOT / "referencia"


def ensure_root_cwd() -> Path:
    """Garante que o diretório de trabalho seja a raiz do workspace."""
    os.chdir(ROOT)
    return ROOT


def p(*parts: str) -> Path:
    """Monta caminho relativo à raiz do workspace."""
    return ROOT.joinpath(*parts)


def cliente(*parts: str) -> Path:
    """Monta caminho relativo à pasta clientes/."""
    return CLIENTES.joinpath(*parts)
