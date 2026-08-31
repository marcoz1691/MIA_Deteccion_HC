"""Ejemplo ejecutable de la convención de omisión para pruebas con Tesseract.

Sirve como referencia para las pruebas de `s11/anonimizador_ocr` que necesiten
el binario de OCR: se marcan con `requiere_ocr` y reciben la ruta del binario
por la fixture `tesseract_cmd`. En una máquina sin Tesseract la prueba se omite
en lugar de fallar.
"""

from __future__ import annotations

import subprocess

import pytest


@pytest.mark.requiere_ocr
def test_tesseract_reporta_version(tesseract_cmd: str) -> None:
    proceso = subprocess.run(
        [tesseract_cmd, "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "tesseract" in (proceso.stdout + proceso.stderr).lower()
