"""Bootstrap común: raíz del repo en sys.path."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def install(caller: str | Path) -> Path:
    """Añade la raíz del repo a sys.path (desde app.py o demo/pages/*.py)."""
    p = Path(caller).resolve()
    root = p.parent.parent if p.parent.name != "pages" else p.parent.parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
