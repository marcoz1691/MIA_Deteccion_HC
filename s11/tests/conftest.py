"""Convención de omisión (skip) para pruebas que dependen de Tesseract OCR.

Motivación: el binario de Tesseract no es una dependencia de Python y no puede
instalarse con `pip`. Para que la suite completa siga en verde en la máquina de
un evaluador que no lo tenga instalado, toda prueba que invoque OCR debe
marcarse y omitirse de forma automática en lugar de fallar.

Uso recomendado en un archivo de pruebas:

    import pytest

    @pytest.mark.requiere_ocr
    def test_ocr_extrae_texto(tesseract_cmd):
        ...

Alternativa autocontenida, válida en cualquier archivo sin importar este
conftest:

    import shutil, pytest

    requiere_ocr = pytest.mark.skipif(
        shutil.which("tesseract") is None,
        reason="Tesseract OCR no está instalado",
    )
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

# Rutas de instalación habituales cuando el binario no está en el PATH.
_RUTAS_HABITUALES = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    Path("/usr/bin/tesseract"),
    Path("/usr/local/bin/tesseract"),
    Path("/opt/homebrew/bin/tesseract"),
)

_MOTIVO_SKIP = (
    "Tesseract OCR no está disponible en esta máquina; "
    "véase s11/fragmentos/track-a.md para instalarlo."
)


def ruta_tesseract() -> str | None:
    """Ruta al binario de Tesseract, o None si no se encuentra."""
    explicita = os.environ.get("TESSERACT_CMD", "").strip()
    if explicita and Path(explicita).exists():
        return explicita
    en_path = shutil.which("tesseract")
    if en_path:
        return en_path
    for ruta in _RUTAS_HABITUALES:
        if ruta.exists():
            return str(ruta)
    return None


def ocr_disponible() -> bool:
    return ruta_tesseract() is not None


#: Decorador listo para usar: `@requiere_ocr` sobre una función de prueba.
requiere_ocr = pytest.mark.skipif(not ocr_disponible(), reason=_MOTIVO_SKIP)


@pytest.fixture(scope="session")
def tesseract_cmd() -> str:
    """Ruta al binario de Tesseract; omite la prueba si no está instalado."""
    ruta = ruta_tesseract()
    if ruta is None:
        pytest.skip(_MOTIVO_SKIP)
    return ruta


def pytest_collection_modifyitems(config, items):
    """Omite automáticamente lo marcado con `requiere_ocr` si no hay binario."""
    if ocr_disponible():
        return
    skip = pytest.mark.skip(reason=_MOTIVO_SKIP)
    for item in items:
        if "requiere_ocr" in item.keywords:
            item.add_marker(skip)
