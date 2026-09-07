#!/usr/bin/env python3
"""Launch eqFX using a local or sibling PopStream PySide6 install."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
candidates = [
    ROOT / ".venv",
    ROOT.parent / "popstream" / ".venv",
]
for extra in candidates:
    if extra.is_dir():
        sys.path.insert(0, str(extra))
sys.path.insert(0, str(ROOT / "src"))

from eqfx.app import main  # noqa: E402

if __name__ == "__main__":
    sys.argv[0] = "eqfx"
    raise SystemExit(main())
