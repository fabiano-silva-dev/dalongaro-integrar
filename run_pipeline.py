#!/usr/bin/env python3
"""Atalho na raiz para executar o pipeline de produtividade."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PIPELINE = ROOT / "scripts" / "produtividade" / "executar_pipeline_completo.py"

if __name__ == "__main__":
    raise SystemExit(
        subprocess.call([sys.executable, str(PIPELINE)], cwd=ROOT)
    )
