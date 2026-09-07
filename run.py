#!/usr/bin/env python3
"""Launch eqFX using a local or sibling PopStream PySide6 install."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
candidates = [
    ROOT / ".venv",
    ROOT.parent / "popstream" / ".venv",
]
for extra in candidates:
    if not extra.is_dir():
        continue
    sys.path.insert(0, str(extra))
    for pattern in ("lib/python*/site-packages", "lib64/python*/site-packages"):
        for site in extra.glob(pattern):
            sys.path.insert(0, str(site))

from eqfx.app import main  # noqa: E402

if __name__ == "__main__":
    sys.argv[0] = "eqfx"
    raise SystemExit(main())
