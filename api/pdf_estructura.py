"""Extracción estructurada de historias clínicas escaneadas.

Devuelve una lista de evoluciones con sus columnas separadas
(NOTAS DE EVOLUCIÓN y ORDENES MEDICAS GENERALES), no un volcado de la página.

Cascada de motores:
  1. "vision"      — modelo multimodal sobre las páginas rasterizadas (mejor con
                     manuscrito y con la maqueta de dos columnas).
  2. "ocr"         — Tesseract local (s11/anonimizador_ocr) sobre la página
                     completa; no separa columnas, entrega una sola evolución.
  3. "capa_texto"  — capa de texto del PDF (solo PDFs buscables); reutiliza el
                     filtro de ruido/identificadores de pdf_extract.
Si ninguno aplica, se lanza PdfExtractError 422.
"""
from __future__ import annotations

import re
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # PyMuPDF < 1.24
    import fitz

from api.pdf_extract import (
    MAX_BYTES,
    PdfExtractError,
    _asegurar_path_anonimizador,
    _detector_por_defecto,
    extraer_de_paginas,
)
from api.vision_client import Transcriptor

MAX_PAGINAS = 12
DPI_RASTER = 200

RE_FECHA = re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b")
RE_HORA = re.compile(r"\b([01]?\d|2[0-3]):[0-5]\d\b")
RE_NOTA_CORTADA = re.compile(
    r"\b(AL|DEL|DE|EN|CON|POR|PARA|SIN|HACIA|HASTA|SEGÚN|SEGUN|SOBRE|ENTRE|DURANTE|TRAS)\s*$",
    re.IGNORECASE,
)
AVISO_NOTA_CORTADA = (
    "La última nota de evolución termina a media frase "
    "(corte de página o de columna). Revise si el resto está en la hoja siguiente "
    "(p. ej. EVOLUCIÓN HOSPITALARIA con signos vitales, examen físico y análisis)."
)


# --------------------------------------------------------------------------- raster

def rasterizar(doc, max_paginas: int = MAX_PAGINAS, dpi: int = DPI_RASTER) -> list[bytes]:
    imagenes: list[bytes] = []
    for pagina in doc:
        if len(imagenes) >= max_paginas:
            break
        pix = pagina.get_pixmap(dpi=dpi)
        imagenes.append(pix.tobytes("png"))
    return imagenes


def _tiene_capa_texto(doc) -> bool:
    return any(pagina.get_text("text").strip() for pagina in doc)


# --------------------------------------------------------------------------- fidelidad de corte de página


def nota_parece_cortada(texto: str) -> bool:
    """True si la nota muere en una preposición típica de salto de columna/página."""
    t = (texto or "").strip()
    if not t:
        return False
    if t.endswith("[corte]"):
        return True
    if t[-1] in ".!?:;)]}»\"'":
        return False
    return bool(RE_NOTA_CORTADA.search(t))


def _cerrar_si_cortada(notas: str) -> str:
    t = (notas or "").rstrip()
    if nota_parece_cortada(t) and not t.endswith("[corte]"):
        return f"{t} [corte]"
    return notas


# --------------------------------------------------------------------------- normalización

_RE_ID_NUMERICO = re.compile(r"\d[\d\s.\-]{6,}\d")


def _hallazgos_identificadores(texto: str):
    _asegurar_path_anonimizador()
    try:
        from anonimizador_ocr import deteccion
    except ImportError:
        return []
    return list(deteccion.detectar(texto, usar_ner=True, fechas="nacimiento"))


def _redactar_spans(texto: str, spans: list[tuple[int, int]]) -> str:
    if not spans:
        return texto
    chars = list(texto)
    for ini, fin in sorted(spans, key=lambda s: -s[0]):
        ini = max(0, min(ini, len(chars)))
        fin = max(ini, min(fin, len(chars)))
        chars[ini:fin] = list("[dato omitido]")
    return "".join(chars)


def _redactar_por_callback(linea: str, tiene_identificador) -> str:
    """Si el callback marca la línea, tapa números de ID y conserva el resto clínico."""
    redactada = _RE_ID_NUMERICO.sub("[dato omitido]", linea)
    if redactada != linea and not tiene_identificador(redactada):
        return redactada
    return "[dato omitido]"


def _scrub(texto: str, tiene_identificador) -> str:
    """Enmascara nombres e identificadores residuales sin borrar el resto clínico."""
    if not texto:
        return ""
    limpias = []
    for linea in texto.splitlines():
        if not linea.strip():
            limpias.append(linea)
            continue
        hallazgos = _hallazgos_identificadores(linea)
        if hallazgos:
            linea = _redactar_spans(linea, [(h.ini, h.fin) for h in hallazgos])
        if tiene_identificador(linea):
            linea = _redactar_por_callback(linea, tiene_identificador)
        limpias.append(linea)
    return "\n".join(limpias).strip()


def _normalizar_entradas(crudo: dict, tiene_identificador) -> list[dict]:
    entradas: list[dict] = []
    for i, bruto in enumerate(crudo.get("entries", []) or [], start=1):
        if not isinstance(bruto, dict):
            continue
        notas = _cerrar_si_cortada(
            _scrub(str(bruto.get("notas_evolucion", "") or ""), tiene_identificador)
        )
        ordenes_bruto = bruto.get("ordenes_medicas", []) or []
        if isinstance(ordenes_bruto, str):
            ordenes_bruto = [ordenes_bruto]
        ordenes = []
        for item in ordenes_bruto:
            limpio = _scrub(str(item), tiene_identificador)
            if limpio:
                ordenes.append(limpio)
        if not notas and not ordenes:
            continue
        fecha = bruto.get("fecha")
        hora = bruto.get("hora")
        fecha = fecha if isinstance(fecha, str) and RE_FECHA.search(fecha) else None
        hora = hora if isinstance(hora, str) and RE_HORA.search(hora) else None
        entradas.append(
            {
                "evolucion_n": len(entradas) + 1,
                "fecha": fecha,
                "hora": hora,
                "notas_evolucion": notas,
                "ordenes_medicas": ordenes,
            }
        )
    return entradas


def _render_texto_plano(entradas: list[dict]) -> str:
    bloques: list[str] = []
    for e in entradas:
        cab = f"--- EVOLUCIÓN {e['evolucion_n']} ---"
        fh = f"FECHA: {e['fecha'] or '[ilegible]'}  HORA: {e['hora'] or '[ilegible]'}"
        ordenes = e["ordenes_medicas"] or ["(sin órdenes en esta nota)"]
        bloques.append(
            "\n".join(
                [
                    cab,
                    fh,
                    "NOTAS DE EVOLUCIÓN:",
                    e["notas_evolucion"] or "[ilegible]",
                    "",
                    "ORDENES MEDICAS GENERALES:",
                    *[f"- {o}" for o in ordenes],
                ]
            )
        )
    return "\n\n".join(bloques).strip()


# --------------------------------------------------------------------------- motores de respaldo

def _crudo_desde_ocr(doc, max_paginas: int) -> dict:
    """Tesseract sobre la página completa. No separa columnas: una sola evolución."""
    try:
        from anonimizador_ocr import ocr as _ocr  # noqa: F401  (valida disponibilidad)
        import pytesseract
        from PIL import Image
    except Exception as exc:  # noqa: BLE001
        raise PdfExtractError(
            "El PDF es una imagen escaneada y no hay motor para leerla: configure "
            "OPENAI_API_KEY (visión) o instale Tesseract + pytesseract.",
            422,
        ) from exc

    import io

    partes: list[str] = []
    for i, pagina in enumerate(doc, start=1):
        if i > max_paginas:
            break
        pix = pagina.get_pixmap(dpi=DPI_RASTER)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        partes.append(pytesseract.image_to_string(img, lang="spa"))
    texto = "\n".join(partes).strip()
    if not texto:
        raise PdfExtractError(
            "Tesseract no reconoció texto en el PDF escaneado.", 422
        )
    return {
        "entries": [
            {
                "evolucion_n": 1,
                "fecha": None,
                "hora": None,
                "notas_evolucion": texto,
                "ordenes_medicas": [],
            }
        ],
        "paginas_sin_contenido": [],
    }


def _crudo_desde_capa_texto(paginas: list[tuple[int, str]]) -> dict:
    """Reutiliza el filtro de pdf_extract y entrega una única evolución de texto plano."""
    resultado = extraer_de_paginas(paginas, origen="capa_texto")
    return {
        "entries": [
            {
                "evolucion_n": 1,
                "fecha": None,
                "hora": None,
                "notas_evolucion": resultado["texto"],
                "ordenes_medicas": [],
            }
        ],
        "paginas_sin_contenido": [],
    }


# --------------------------------------------------------------------------- fachada

def extraer_estructurado(
    data: bytes,
    origen: str,
    *,
    transcriptor: Transcriptor | None = None,
    tiene_identificador=None,
    max_paginas: int = MAX_PAGINAS,
) -> dict:
    if len(data) > MAX_BYTES:
        raise PdfExtractError("El archivo supera 20 MB.", 413)
    if tiene_identificador is None:
        tiene_identificador = _detector_por_defecto

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise PdfExtractError("El archivo no es un PDF válido.", 400) from exc

    aviso: str | None = None
    try:
        n_paginas = doc.page_count
        if transcriptor is not None:
            motor = "vision"
            crudo = transcriptor(rasterizar(doc, max_paginas))
        elif _tiene_capa_texto(doc):
            motor = "capa_texto"
            aviso = (
                "Sin modelo de visión: se usó la capa de texto del PDF. Las "
                "columnas NOTAS y ORDENES no se separan."
            )
            paginas = [(i, p.get_text("text")) for i, p in enumerate(doc, start=1)]
            crudo = _crudo_desde_capa_texto(paginas)
        else:
            motor = "ocr"
            aviso = (
                "Sin modelo de visión: se usó OCR local. Revise la transcripción; "
                "las columnas no se separan."
            )
            crudo = _crudo_desde_ocr(doc, max_paginas)
    finally:
        doc.close()

    if not isinstance(crudo, dict):
        raise PdfExtractError("El motor de extracción no devolvió un resultado válido.", 502)

    entradas = _normalizar_entradas(crudo, tiene_identificador)
    if not entradas:
        raise PdfExtractError(
            "No se encontró contenido en las columnas NOTAS DE EVOLUCIÓN ni "
            "ORDENES MEDICAS GENERALES.",
            422,
        )

    if n_paginas > max_paginas:
        extra = (
            f"Se procesaron las primeras {max_paginas} de {n_paginas} páginas."
        )
        aviso = f"{aviso} {extra}".strip() if aviso else extra

    if entradas and nota_parece_cortada(entradas[-1]["notas_evolucion"]):
        aviso = f"{aviso} {AVISO_NOTA_CORTADA}".strip() if aviso else AVISO_NOTA_CORTADA

    sin_contenido = [
        p for p in crudo.get("paginas_sin_contenido", []) or [] if isinstance(p, int)
    ]

    return {
        "origen": origen,
        "n_paginas": n_paginas,
        "motor": motor,
        "entries": entradas,
        "paginas_sin_contenido": sin_contenido,
        "texto_plano": _render_texto_plano(entradas),
        "aviso": aviso,
    }
