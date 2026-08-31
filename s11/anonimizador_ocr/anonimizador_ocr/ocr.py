"""Motores de OCR. Todos devuelven la misma estructura: lista de `Palabra` con caja en píxeles.

Motores:
  * tesseract  (por defecto; texto impreso; necesita el binario `tesseract` + `spa.traineddata`)
  * easyocr    (opcional; algo mejor con manuscrito legible; necesita torch, pesos descargados una vez)
  * capa_texto (no es OCR: lee las palabras que el PDF ya trae y las proyecta a píxeles)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
from PIL import Image


@dataclass
class Palabra:
    texto: str
    x0: int
    y0: int
    x1: int
    y1: int
    conf: float = 100.0          # 0-100
    bloque: int = 0
    parrafo: int = 0
    linea: int = 0
    # rellenados por mapeo.construir_texto
    ini: int = -1
    fin: int = -1

    @property
    def alto(self) -> int:
        return self.y1 - self.y0

    @property
    def clave_linea(self) -> tuple[int, int, int]:
        return (self.bloque, self.parrafo, self.linea)


@dataclass
class ResultadoOCR:
    palabras: list[Palabra]
    motor: str
    conf_media: float = 0.0
    angulo_corregido: float = 0.0
    imagen: Image.Image | None = field(default=None, repr=False)   # imagen (posiblemente deskew) sobre la que valen las cajas


# --------------------------------------------------------------------------- preprocesado

def a_gris(img: Image.Image) -> np.ndarray:
    return np.array(img.convert("L"))


def estimar_inclinacion(gris: np.ndarray) -> float:
    """Ángulo (grados) de las líneas de texto. Positivo = gira en sentido antihorario para corregir."""
    import cv2

    inv = cv2.bitwise_not(gris)
    _, binaria = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    # dilatar horizontalmente para fundir letras en líneas
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))
    lineas = cv2.dilate(binaria, kernel, iterations=1)
    coords = cv2.findNonZero(lineas)
    if coords is None or len(coords) < 500:
        return 0.0
    angulo = cv2.minAreaRect(coords)[-1]
    if angulo < -45:
        angulo += 90
    elif angulo > 45:
        angulo -= 90
    return float(angulo)


def corregir_inclinacion(img: Image.Image, max_grados: float = 5.0) -> tuple[Image.Image, float]:
    """Solo corrige inclinaciones pequeñas (escaneos torcidos); ignora ángulos grandes por seguridad."""
    gris = a_gris(img)
    ang = estimar_inclinacion(gris)
    if abs(ang) < 0.2 or abs(ang) > max_grados:
        return img, 0.0
    return img.rotate(ang, resample=Image.BICUBIC, expand=False, fillcolor="white"), ang


def preparar_para_ocr(img: Image.Image) -> Image.Image:
    """Escala de grises + suavizado ligero. Tesseract binariza internamente; no conviene binarizar aquí."""
    import cv2

    gris = a_gris(img)
    gris = cv2.fastNlMeansDenoising(gris, None, h=7, templateWindowSize=7, searchWindowSize=21)
    return Image.fromarray(gris)


# --------------------------------------------------------------------------- tesseract

def ocr_tesseract(img: Image.Image, idioma: str = "spa", psm: int = 3, umbral_conf: float = 0.0) -> list[Palabra]:
    import pytesseract

    datos = pytesseract.image_to_data(
        img, lang=idioma, config=f"--psm {psm}", output_type=pytesseract.Output.DICT
    )
    palabras: list[Palabra] = []
    n = len(datos["text"])
    for i in range(n):
        texto = (datos["text"][i] or "").strip()
        if not texto:
            continue
        try:
            conf = float(datos["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf < 0:          # -1 = no es una palabra reconocida (nivel bloque/línea)
            continue
        if conf < umbral_conf:
            continue
        x, y, w, h = datos["left"][i], datos["top"][i], datos["width"][i], datos["height"][i]
        palabras.append(Palabra(
            texto=texto, x0=x, y0=y, x1=x + w, y1=y + h, conf=conf,
            bloque=datos["block_num"][i], parrafo=datos["par_num"][i], linea=datos["line_num"][i],
        ))
    return palabras


# --------------------------------------------------------------------------- easyocr (opcional)

_lector_easyocr = None


def ocr_easyocr(img: Image.Image, idioma: str = "spa", umbral_conf: float = 0.0) -> list[Palabra]:
    """EasyOCR devuelve fragmentos (línea o parte de línea). Se reparten en palabras proporcionalmente."""
    global _lector_easyocr
    import easyocr  # type: ignore

    if _lector_easyocr is None:
        langs = ["es"] + (["en"] if "eng" in idioma else [])
        _lector_easyocr = easyocr.Reader(langs, gpu=False, verbose=False)

    resultados = _lector_easyocr.readtext(np.array(img.convert("RGB")), detail=1, paragraph=False)
    palabras: list[Palabra] = []
    # ordenar fragmentos de arriba a abajo, izquierda a derecha y asignar "líneas" por cercanía vertical
    frags = []
    for caja, texto, conf in resultados:
        xs = [p[0] for p in caja]; ys = [p[1] for p in caja]
        frags.append((min(ys), min(xs), max(xs), max(ys), texto, float(conf) * 100))
    frags.sort()
    linea = 0
    y_prev = None
    for (y0, x0, x1, y1, texto, conf) in frags:
        if conf < umbral_conf:
            continue
        alto = y1 - y0
        if y_prev is not None and abs(y0 - y_prev) > alto * 0.6:
            linea += 1
        y_prev = y0
        tokens = texto.split()
        if not tokens:
            continue
        total = sum(len(t) for t in tokens) + (len(tokens) - 1)
        cursor = x0
        ancho = x1 - x0
        for t in tokens:
            w = ancho * len(t) / max(total, 1)
            palabras.append(Palabra(t, int(cursor), int(y0), int(cursor + w), int(y1), conf, 0, 0, linea))
            cursor += w + ancho / max(total, 1)
    return palabras


# --------------------------------------------------------------------------- capa de texto del PDF

def palabras_desde_capa_texto(pagina, escala: float) -> list[Palabra]:
    """Usa el texto que ya trae el PDF (páginas no escaneadas). `escala` = px por punto."""
    palabras = []
    for (x0, y0, x1, y1, texto, b, l, w) in pagina.get_text("words"):
        texto = texto.strip()
        if not texto:
            continue
        palabras.append(Palabra(
            texto=texto, x0=int(x0 * escala), y0=int(y0 * escala),
            x1=int(math.ceil(x1 * escala)), y1=int(math.ceil(y1 * escala)),
            conf=100.0, bloque=b, parrafo=0, linea=l,
        ))
    return palabras


# --------------------------------------------------------------------------- fachada

def reconocer(img: Image.Image, motor: str, idioma: str, psm: int, umbral_conf: float, deskew: bool) -> ResultadoOCR:
    angulo = 0.0
    if deskew:
        img, angulo = corregir_inclinacion(img)
    entrada = preparar_para_ocr(img)
    if motor == "tesseract":
        palabras = ocr_tesseract(entrada, idioma, psm, umbral_conf)
    elif motor == "easyocr":
        palabras = ocr_easyocr(entrada, idioma, umbral_conf)
    else:
        raise ValueError(f"Motor OCR desconocido: {motor}")
    conf = float(np.mean([p.conf for p in palabras])) if palabras else 0.0
    return ResultadoOCR(palabras=palabras, motor=motor, conf_media=conf, angulo_corregido=angulo, imagen=img)


def confianza_media(palabras: Iterable[Palabra]) -> float:
    vals = [p.conf for p in palabras]
    return float(np.mean(vals)) if vals else 0.0
