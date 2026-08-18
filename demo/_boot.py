"""Arranque sin paquete demo en sys.path (Streamlit ejecuta desde demo/)."""
from __future__ import annotations

import importlib.util
from pathlib import Path


def repo_root(caller_file: str) -> Path:
    demo_dir = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("_demo_entry", demo_dir / "_entry.py")
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar demo/_entry.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.setup(caller_file)
