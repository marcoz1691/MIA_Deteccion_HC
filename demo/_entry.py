"""Inserta la raíz del repo en sys.path. Cargar vía importlib desde app.py y pages/."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def setup(caller_file: str | Path) -> Path:
    caller = Path(caller_file).resolve()
    demo_dir = Path(__file__).resolve().parent
    bootstrap = demo_dir / "bootstrap.py"
    spec = importlib.util.spec_from_file_location("_demo_bootstrap", bootstrap)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {bootstrap}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.install(caller)
