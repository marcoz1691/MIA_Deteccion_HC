"""Extracción de texto clínico desde PDF buscable (sin OCR)."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # PyMuPDF < 1.24
    import fitz

from s11.extraer_corpus import _limpiar, es_oracion_util, extraer_paginas, segmentar

ROOT = Path(__file__).resolve().parent.parent
ANON_ROOT = ROOT / "s11" / "anonimizador_ocr"
CARPETAS_MUESTRA = ("salidas", "salidas_buscable")
MAX_ORACIONES_PDF = 300
MAX_BYTES = 20 * 1024 * 1024
MENSAJE_SIN_TEXTO = (
    "Este PDF no tiene texto extraíble (es imagen tachada, no buscable). "
    "Use el chip «· buscable» o el archivo en "
    "s11/anonimizador_ocr/salidas_buscable/, no el de salidas/."
)


class PdfExtractError(Exception):
    def __init__(self, message: str, status: int = 400):
        self.status = status
        super().__init__(message)


def _asegurar_path_anonimizador() -> None:
    ruta = str(ANON_ROOT)
    if ruta not in sys.path:
        sys.path.insert(0, ruta)


def _detector_por_defecto(oracion: str) -> bool:
    _asegurar_path_anonimizador()
    try:
        from anonimizador_ocr import deteccion
    except ImportError:
        return False
    return bool(deteccion.detectar(oracion, usar_ner=False, fechas="nacimiento"))


def _paginas_desde_bytes(data: bytes) -> list[tuple[int, str]]:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise PdfExtractError("El archivo no es un PDF válido.", 400) from exc
    try:
        paginas: list[tuple[int, str]] = []
        for indice, pagina in enumerate(doc, start=1):
            paginas.append((indice, _limpiar(pagina.get_text("text"))))
        return paginas
    finally:
        doc.close()


def extraer_de_paginas(
    paginas: list[tuple[int, str]],
    origen: str,
    tiene_identificador=None,
) -> dict:
    if tiene_identificador is None:
        tiene_identificador = _detector_por_defecto

    if not paginas or not any(texto for _, texto in paginas):
        raise PdfExtractError(MENSAJE_SIN_TEXTO, 400)

    utiles: list[str] = []
    n_ruido = 0
    n_ids = 0
    for _, texto in paginas:
        for oracion in segmentar(texto):
            if not es_oracion_util(oracion):
                n_ruido += 1
                continue
            if tiene_identificador(oracion):
                n_ids += 1
                continue
            utiles.append(oracion)

    n_truncadas = 0
    if len(utiles) > MAX_ORACIONES_PDF:
        n_truncadas = len(utiles) - MAX_ORACIONES_PDF
        utiles = utiles[:MAX_ORACIONES_PDF]

    if not utiles:
        raise PdfExtractError(
            "No quedaron oraciones clínicas útiles tras filtrar ruido e identificadores.",
            400,
        )

    return {
        "texto": " ".join(utiles),
        "n_paginas": len(paginas),
        "n_oraciones_utiles": len(utiles),
        "n_omitidas_ruido": n_ruido,
        "n_omitidas_identificadores": n_ids,
        "n_truncadas": n_truncadas,
        "origen": origen,
    }


def extraer_de_bytes(
    data: bytes,
    origen: str,
    tiene_identificador=None,
) -> dict:
    if len(data) > MAX_BYTES:
        raise PdfExtractError("El archivo supera 20 MB.", 413)
    return extraer_de_paginas(
        _paginas_desde_bytes(data),
        origen=origen,
        tiene_identificador=tiene_identificador,
    )


def extraer_de_ruta(ruta: Path, tiene_identificador=None) -> dict:
    if not ruta.is_file():
        raise PdfExtractError("Muestra no encontrada.", 404)
    return extraer_de_paginas(
        extraer_paginas(ruta),
        origen=ruta.name,
        tiene_identificador=tiene_identificador,
    )


def resolver_muestra(muestra_id: str, *, anon_root: Path | None = None) -> Path:
    raiz = (anon_root or ANON_ROOT).resolve()
    bruto = (muestra_id or "").replace("\\", "/").strip()
    if not bruto or bruto.startswith("/") or ".." in Path(bruto).parts:
        raise PdfExtractError("Muestra no encontrada.", 404)
    rel = Path(bruto)
    if len(rel.parts) != 2 or rel.parts[0] not in CARPETAS_MUESTRA:
        raise PdfExtractError("Muestra no encontrada.", 404)
    if not rel.name.endswith("_anon.pdf"):
        raise PdfExtractError("Muestra no encontrada.", 404)
    destino = (raiz / rel).resolve()
    try:
        destino.relative_to(raiz)
    except ValueError as exc:
        raise PdfExtractError("Muestra no encontrada.", 404) from exc
    if not destino.is_file():
        raise PdfExtractError("Muestra no encontrada.", 404)
    return destino


def listar_muestras(*, anon_root: Path | None = None) -> list[dict]:
    raiz = anon_root or ANON_ROOT
    muestras: list[dict] = []
    for carpeta in CARPETAS_MUESTRA:
        directorio = raiz / carpeta
        if not directorio.is_dir():
            continue
        for pdf in sorted(directorio.glob("*_anon.pdf")):
            n_paginas = 0
            try:
                with fitz.open(pdf) as doc:
                    n_paginas = doc.page_count
                    if n_paginas == 0 or not any(
                        _limpiar(pagina.get_text("text")) for pagina in doc
                    ):
                        continue
            except Exception:
                continue
            muestras.append(
                {
                    "id": f"{carpeta}/{pdf.name}",
                    "nombre": pdf.name,
                    "carpeta": carpeta,
                    "n_paginas": n_paginas,
                }
            )
    return muestras
