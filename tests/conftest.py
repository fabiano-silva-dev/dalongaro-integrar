"""Configuração dos testes: adiciona pastas de scripts ao PYTHONPATH."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

for script_dir in sorted({p.parent for p in SCRIPTS.rglob("*.py") if p.name != "paths.py"}):
    path = str(script_dir)
    if path not in sys.path:
        sys.path.insert(0, path)
