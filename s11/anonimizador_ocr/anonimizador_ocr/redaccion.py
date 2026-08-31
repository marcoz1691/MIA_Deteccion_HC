"""Tachado a nivel de píxel y reconstrucción del PDF.

La salida es SIEMPRE un PDF nuevo hecho de imágenes: no arrastra la capa de texto original,
ni anotaciones, ni adjuntos, ni metadatos. Si se pide `buscable`, la capa de texto se genera
haciendo OCR sobre la imagen YA tachada, así que no puede contener lo que se tachó.
"""
from __future__ import annotations

import io

try:
    import pymupdf as fitz
except ImportError:  # PyMuPDF < 1.24
    import fitz
from PIL import Image, ImageDraw, ImageFont

from .mapeo import Caja


def tachar(img: Image.Image, cajas: list[Caja], etiquetar: bool = False) -> Image.Image:
    out = img.convert("RGB")
    d = ImageDraw.Draw(out)
    w, h = out.size
    fuente = None
    if etiquetar:
        try:
            fuente = ImageFont.truetype("DejaVuSans.ttf", 18)
        except OSError:
            fuente = ImageFont.load_default()
    for c in cajas:
        x0, y0 = max(0, c.x0), max(0, c.y0)
        x1, y1 = min(w, c.x1), min(h, c.y1)
        if x1 <= x0 or y1 <= y0:
            continue
        d.rectangle([x0, y0, x1, y1], fill="black")
        if etiquetar and fuente and (x1 - x0) > 60:
            d.text((x0 + 3, y0 + 2), f"[{c.etiqueta}]", fill="white", font=fuente)
    return out


def dibujar_revision(img: Image.Image, cajas: list[Caja]) -> Image.Image:
    """Versión para revisión humana: el contenido sigue visible, las cajas van en rojo con su etiqueta."""
    out = img.convert("RGB")
    d = ImageDraw.Draw(out)
    try:
        fuente = ImageFont.truetype("DejaVuSans.ttf", 16)
    except OSError:
        fuente = ImageFont.load_default()
    colores = {"NOMBRE": "red", "CEDULA": "blue", "TELEFONO": "purple", "FECHA": "orange",
               "HC": "green", "DIRECCION": "brown", "EMAIL": "magenta", "ZONA": "gray", "EDAD": "teal", "RUC": "navy"}
    for c in cajas:
        col = colores.get(c.etiqueta.split("+")[0], "red")
        d.rectangle([c.x0, c.y0, c.x1, c.y1], outline=col, width=3)
        d.text((c.x0, max(0, c.y0 - 18)), f"{c.etiqueta} ({c.origen})", fill=col, font=fuente)
    return out


def _jpeg(img: Image.Image, calidad: int) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=calidad, optimize=True)
    return buf.getvalue()


class ConstructorPDF:
    """Acumula páginas-imagen y escribe el PDF final."""

    def __init__(self, buscable: bool = False, idioma: str = "spa", calidad_jpeg: int = 80):
        self.doc = fitz.open()
        self.buscable = buscable
        self.idioma = idioma
        self.calidad = calidad_jpeg

    def agregar_pagina(self, img: Image.Image, ancho_pt: float, alto_pt: float) -> None:
        if self.buscable:
            import pytesseract
            pdf_bytes = pytesseract.image_to_pdf_or_hocr(img, lang=self.idioma, extension="pdf")
            tmp = fitz.open("pdf", pdf_bytes)
            self.doc.insert_pdf(tmp)
            tmp.close()
        else:
            pagina = self.doc.new_page(width=ancho_pt, height=alto_pt)
            pagina.insert_image(pagina.rect, stream=_jpeg(img, self.calidad))

    def guardar(self, ruta) -> None:
        self.doc.set_metadata({})          # sin autor, título, fechas, productor
        self.doc.del_xml_metadata()
        self.doc.save(str(ruta), garbage=4, deflate=True, clean=True)
        self.doc.close()
