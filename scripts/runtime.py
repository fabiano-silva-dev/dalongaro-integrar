"""Inicialização comum para scripts executados fora da raiz do workspace."""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent


def setup_workspace():
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    from paths import ensure_root_cwd

    return ensure_root_cwd()
