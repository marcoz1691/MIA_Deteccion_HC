"""Estrategias que no dependen de leer el dato:

1. Zonas fijas (plantilla JSON, coordenadas relativas 0-1) para formularios estandarizados.

2. Zonas junto a etiquetas: las ETIQUETAS del formulario van impresas y el OCR sí las lee;
   el VALOR muchas veces va a mano y no. La posición del valor se decide mirando la TINTA
   (píxeles escritos, sin las rayas de la tabla):
     * a la DERECHA   ("PACIENTE ______", "Cédula: ______")
     * DEBAJO         (celda de tabla: "APELLIDO PATERNO | NOMBRES" con el dato debajo)
     * ENCIMA         (bloques de firma: el nombre se escribe sobre la raya y la etiqueta
                       "Apellidos y nombres" / "Firma" va impresa debajo)
   Las cajas se estiran siguiendo la tinta en vertical y horizontal, para cubrir letra
   grande, valores descolgados o que empiezan antes de la cabecera.
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

import numpy as np

from .config import ETIQUETAS_FORMULARIO, ETIQUETAS_ORDENADAS
from .deteccion import sin_tildes
from .mapeo import Caja
from .ocr import Palabra

# Etiquetas que también son palabra corriente ("...DATOS DEL PACIENTE", "el padre refiere"):
# solo cuentan si llevan ':' o si ABREN la línea sin texto legible a su derecha (campo de formulario).
REQUIEREN_DOS_PUNTOS = {"paciente", "madre", "padre", "ci", "tel", "hc", "nacimiento", "barrio",
                        "responsable", "representante", "correo", "email", "identificacion", "ruc",
                        "nombre", "apellido", "firma", "pasaporte", "profesional", "ayudantes"}

# El valor se escribe ENCIMA de estas etiquetas (bloques de firma).
VALOR_ARRIBA = {"apellidos y nombres", "nombres y apellidos", "firma", "apellidos y nombres del paciente"}


# --------------------------------------------------------------------------- tinta

def mascara_tinta(img) -> "np.ndarray":
    """Píxeles con tinta (impresa o manuscrita), quitando las rayas largas de tablas y renglones."""
    import cv2

    g = np.array(img.convert("L"))
    binaria = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 15)
    horiz = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1)))
    vert = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40)))
    sin_lineas = cv2.subtract(binaria, cv2.max(horiz, vert))
    return cv2.morphologyEx(sin_lineas, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))


def _recorte(mascara, x0, y0, x1, y1):
    H, W = mascara.shape
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0:
        return None
    return mascara[y0:y1, x0:x1]

def hay_tinta(mascara, x0, y0, x1, y1) -> bool:
    if mascara is None:
        return False
    r = _recorte(mascara, x0, y0, x1, y1)
    if r is None:
        return False
    return int((r > 0).sum()) >= max(30, int(r.size * 0.002))


def extender_abajo(mascara, x0, x1, y0, y1_min, alto) -> int:
    """Baja el fondo hasta la última fila con tinta (huecos de hasta 3 alturas)."""
    if mascara is None:
        return y1_min
    r = _recorte(mascara, x0, y0, x1, min(mascara.shape[0], y0 + alto * 14))
    if r is None:
        return y1_min
    filas = (r > 0).sum(axis=1)
    umbral = max(3, (x1 - x0) // 200)
    ultima, hueco = -1, 0
    for i, v in enumerate(filas):
        if v >= umbral:
            ultima, hueco = i, 0
        else:
            hueco += 1
            if ultima >= 0 and hueco > alto * 3:
                break
    return y1_min if ultima < 0 else max(y1_min, y0 + ultima + 6)


def extender_arriba(mascara, x0, x1, y0_min, y0, alto) -> int:
    """Sube el techo hasta la primera fila con tinta hacia arriba, sin pasar de y0_min
    (para valores escritos sobre la raya de firma)."""
    if mascara is None:
        return y0
    base = max(0, y0 - alto * 8, y0_min)
    r = _recorte(mascara, x0, base, x1, y0)
    if r is None:
        return y0
    filas = (r > 0).sum(axis=1)
    umbral = max(3, (x1 - x0) // 200)
    primera, hueco = -1, 0
    for i in range(len(filas) - 1, -1, -1):        # de abajo hacia arriba
        if filas[i] >= umbral:
            primera, hueco = i, 0
        else:
            hueco += 1
            if primera >= 0 and hueco > alto * 2:
                break
    if primera < 0:
        return y0
    return min(y0, max(y0_min, base + primera - 4))


def extender_lados(mascara, x0, x1, y0, y1, alto, tope=6) -> tuple[int, int]:
    """Ensancha la caja mientras haya tinta contigua a izquierda/derecha (valores que empiezan
    antes de la cabecera o terminan más allá del ancho fijo)."""
    if mascara is None:
        return x0, x1
    H, W = mascara.shape
    y0c, y1c = max(0, y0), min(H, y1)
    if y1c <= y0c:
        return x0, x1
    umbral = max(2, (y1c - y0c) // 150)

    def _cols(a, b):
        r = _recorte(mascara, a, y0c, b, y1c)
        return (r > 0).sum(axis=0) if r is not None else np.zeros(0)

    # derecha
    cols = _cols(x1, min(W, x1 + alto * tope))
    hueco, avance = 0, 0
    for i, v in enumerate(cols):
        if v >= umbral:
            avance, hueco = i + 1, 0
        else:
            hueco += 1
            if hueco > alto:
                break
    x1 += avance + (4 if avance else 0)
    # izquierda
    cols = _cols(max(0, x0 - alto * tope), x0)
    hueco, retro = 0, 0
    for i in range(len(cols) - 1, -1, -1):
        if cols[i] >= umbral:
            retro, hueco = len(cols) - i, 0
        else:
            hueco += 1
            if hueco > alto:
                break
    x0 -= retro + (4 if retro else 0)
    return x0, x1


# --------------------------------------------------------------------------- 1. plantilla JSON

def cargar_zonas(ruta: Path) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    zonas = datos.get("zonas", datos if isinstance(datos, list) else [])
    for z in zonas:
        for k in ("x0", "y0", "x1", "y1"):
            if not (0.0 <= float(z[k]) <= 1.0):
                raise ValueError(f"Zona {z}: las coordenadas deben ser relativas (0-1).")
    return zonas


def cajas_desde_zonas(zonas: list[dict], num_pagina: int, ancho_px: int, alto_px: int) -> list[Caja]:
    cajas = []
    for z in zonas:
        pag = z.get("pagina", "todas")
        if pag != "todas" and int(pag) != num_pagina:
            continue
        cajas.append(Caja(
            int(z["x0"] * ancho_px), int(z["y0"] * alto_px), int(z["x1"] * ancho_px), int(z["y1"] * alto_px),
            z.get("etiqueta", "ZONA"), z.get("nombre", ""), "zona", 1.0,
        ))
    return cajas


# --------------------------------------------------------------------------- 2. junto a etiquetas

def _normalizar(t: str) -> str:
    return re.sub(r"[^a-z0-9.° ]", "", sin_tildes(t.lower())).strip(" .:")


def _coincide_etiqueta(candidato: str, et: str) -> bool:
    """Exacta o, para etiquetas multipalabra, aproximada (tolera errores y cortes del OCR)."""
    if candidato == et or candidato.replace(" ", "") == et.replace(" ", ""):
        return True
    if " " in et and len(et) >= 6:
        a, b = candidato.replace(" ", ""), et.replace(" ", "")
        if abs(len(a) - len(b)) <= 4:
            return difflib.SequenceMatcher(None, a, b).ratio() >= 0.85
    return False


def _lineas_por_geometria(palabras: list[Palabra], tol: float) -> list[list[Palabra]]:
    orden = sorted(palabras, key=lambda p: (p.y0 + p.y1) / 2)
    grupos: list[list[Palabra]] = []
    for p in orden:
        cy = (p.y0 + p.y1) / 2
        for g in grupos:
            gy = sum((q.y0 + q.y1) / 2 for q in g) / len(g)
            gh = sum(q.alto for q in g) / len(g)
            if abs(cy - gy) <= tol * max(gh, p.alto):
                g.append(p)
                break
        else:
            grupos.append([p])
    for g in grupos:
        g.sort(key=lambda p: p.x0)
    return grupos


def _etiquetas_en_linea(linea: list[Palabra]) -> list[tuple[int, int, str, str, bool]]:
    """(idx_ini, idx_fin, tipo, etiqueta_normalizada, con_colon) por cada etiqueta hallada."""
    textos = [_normalizar(p.texto) for p in linea]
    out = []
    i = 0
    while i < len(linea):
        encontrada = None
        for et in ETIQUETAS_ORDENADAS:
            n0 = len(et.split())
            for n in (n0, n0 + 1, max(1, n0 - 1)):     # el OCR parte o pega palabras
                if i + n > len(linea):
                    continue
                candidato = " ".join(t for t in textos[i:i + n] if t)
                if candidato and _coincide_etiqueta(candidato, et):
                    ultimo = linea[i + n - 1].texto.rstrip()
                    siguiente = linea[i + n].texto if i + n < len(linea) else ""
                    colon = ultimo.endswith(":") or siguiente.startswith(":")
                    encontrada = (i, i + n, ETIQUETAS_FORMULARIO[et], et, colon)
                    break
            if encontrada:
                break
        if encontrada:
            out.append(encontrada)
            i = encontrada[1]
        else:
            i += 1
    return out


def _ajustar_tinta(mascara, x0, y0, x1, y1, alto, sube_max=0):
    """Dos vueltas de extensión (abajo, arriba acotada, lados): la tinta que entra al ensanchar
    puede a su vez subir o bajar el borde."""
    techo = max(0, y0 - sube_max)
    for _ in range(2):
        y1 = extender_abajo(mascara, x0, x1, y0, y1, alto)
        if sube_max > 0:
            y0 = extender_arriba(mascara, x0, x1, techo, y0, alto)
        x0, x1 = extender_lados(mascara, x0, x1, y0, y1, alto)
    return x0, y0, x1, y1


def _caja_celda(x0, x1, fondo, alto, alto_celda, margen, tipo, texto, todas, mascara) -> Caja:
    """Caja bajo una cabecera; crece con lo que el OCR leyó y con la tinta (vertical y lateral)."""
    y0 = fondo + 2
    y1 = int(fondo + alto * alto_celda) + margen
    for q in todas:
        if q.x0 < x1 and q.x1 > x0 and q.y0 < fondo + alto * (alto_celda + 2) and q.y1 > y0:
            y1 = max(y1, q.y1 + margen)
    x0, y0, x1, y1 = _ajustar_tinta(mascara, x0, y0, x1, y1, alto)
    return Caja(x0, y0, x1, y1, tipo, texto, "celda", 0.9)


def cajas_junto_a_etiquetas(palabras: list[Palabra], ancho_px: int, ancho_max_frac: float, margen: int,
                            alto_celda: float = 3.0, mascara=None) -> list[Caja]:
    cajas: list[Caja] = []
    ancho_max = int(ancho_px * ancho_max_frac)
    todas = palabras
    # Para DETECTAR etiquetas se ignora el ruido del manuscrito (confianza baja / sin alfanuméricos);
    # para TACHAR y crecer se usan todas las palabras.
    detectables = [p for p in palabras if p.conf >= 40 and any(ch.isalnum() for ch in p.texto)]

    vistos: set[tuple] = set()
    # varias pasadas: dos tolerancias de agrupación (los bordes de tabla cambian la altura
    # aparente de las palabras) y una con umbral de confianza más bajo (impresiones degradadas)
    flojas = [p for p in palabras if p.conf >= 22 and any(ch.isalnum() for ch in p.texto)]
    for grupo, tol in ((detectables, 0.5), (detectables, 0.9), (flojas, 0.5)):
        lineas = _lineas_por_geometria(grupo, tol)
        cajas.extend(_procesar_lineas(lineas, ancho_px, ancho_max, margen, alto_celda, todas, mascara, vistos))
        cajas.extend(_cabeceras_apiladas(lineas, ancho_px, margen, alto_celda, todas, mascara, vistos))
    return cajas


def _procesar_lineas(lineas, ancho_px, ancho_max, margen, alto_celda, todas, mascara, vistos) -> list[Caja]:
    cajas: list[Caja] = []
    for linea in lineas:
        encontradas = _etiquetas_en_linea(linea)
        if not encontradas:
            continue

        # ¿fila de cabeceras de tabla? 2+ etiquetas y (sin ':' o sin nada legible entre ellas)
        indices = {i for a, b, *_ in encontradas for i in range(a, b)}
        huecos_vacios = all(i in indices for i in range(encontradas[0][0], encontradas[-1][1]))
        fila_cabeceras = len(encontradas) >= 2 and (not any(c for *_, c in encontradas) or huecos_vacios)

        if fila_cabeceras:
            xs = [linea[a].x0 for a, *_ in encontradas]
            col_media = (xs[-1] - xs[0]) / (len(xs) - 1) if len(xs) > 1 else ancho_max
            fondo = max(p.y1 for a, b, *_ in encontradas for p in linea[a:b])
            for k, (a, b, tipo, et, colon) in enumerate(encontradas):
                if (id(linea[a]), "celda") in vistos:
                    continue
                vistos.add((id(linea[a]), "celda"))
                alto = max(p.alto for p in linea[a:b])
                x0 = linea[a].x0 - margen - alto // 2
                if k + 1 < len(encontradas):
                    x1 = linea[encontradas[k + 1][0]].x0 - margen
                else:
                    x1 = min(ancho_px - margen, int(linea[a].x0 + max(col_media * 1.2, alto * 8)))
                cajas.append(_caja_celda(x0, x1, fondo, alto, alto_celda, margen, tipo,
                                         " ".join(p.texto for p in linea[a:b]), todas, mascara))
            continue

        for k, (a, b, tipo, et, colon) in enumerate(encontradas):
            if (id(linea[a]), et) in vistos:
                continue
            vistos.add((id(linea[a]), et))
            ini, fin = linea[a], linea[b - 1]
            alto = max(p.alto for p in linea[a:b])
            fondo = max(p.y1 for p in linea[a:b])
            techo = min(p.y0 for p in linea[a:b])

            # palabras legibles a la derecha, cerca (para distinguir campo de formulario de prosa)
            limite_der = min(ancho_px - margen, fin.x1 + ancho_max)
            palabras_der = [q for q in linea[b:] if fin.x1 < q.x0 < limite_der]
            derecha_texto = any(q.x0 < fin.x1 + alto * 8 for q in palabras_der)
            # prosa impresa: muchas palabras con confianza alta; manuscrito medio legible: pocas y flojas
            manuscrito_der = bool(palabras_der) and len(palabras_der) <= 6 and min(q.conf for q in palabras_der) < 80

            if et in VALOR_ARRIBA:
                # bloque de firma: el nombre va escrito ENCIMA de la etiqueta
                x0, x1 = ini.x0 - margen, min(ancho_px - margen, ini.x0 + ancho_max)
                y1 = techo - 2
                y0 = extender_arriba(mascara, x0, x1, 0, int(techo - alto * 1.2), alto)
                if y1 - y0 > 4:
                    for _ in range(2):
                        x0, x1 = extender_lados(mascara, x0, x1, y0, y1, alto)
                        y0 = extender_arriba(mascara, x0, x1, max(0, y0 - alto * 4), y0, alto)
                    cajas.append(Caja(x0, y0, x1, y1, tipo, f"^{fin.texto}", "celda", 0.85))
                continue

            if et in REQUIEREN_DOS_PUNTOS and not colon and not (a == 0 and (not derecha_texto or manuscrito_der)):
                continue   # palabra corriente, no etiqueta de campo

            # límites del tramo a la derecha
            x_ini = fin.x1 + margen
            x_fin = min(ancho_px - margen, x_ini + ancho_max)
            if k + 1 < len(encontradas):
                x_fin = min(x_fin, linea[encontradas[k + 1][0]].x0 - margen)
            for q in linea[b:]:
                if q.texto.rstrip().endswith(":") and q.x0 > fin.x1 + alto:
                    x_fin = min(x_fin, q.x0 - margen)
                    break

            cy = (fin.y0 + fin.y1) / 2
            y0d = int(cy - alto * 0.9) - margen
            y1d = int(cy + alto * 0.9) + margen

            if manuscrito_der:
                # valor manuscrito medio legible: cubrir esas palabras y seguir la tinta
                x1m = max(x_fin, max(q.x1 for q in palabras_der) + margen)
                y0m = min(y0d, min(q.y0 for q in palabras_der) - margen)
                y1m = max(y1d, max(q.y1 for q in palabras_der) + margen)
                x0m, y0m, x1m, y1m = _ajustar_tinta(mascara, x_ini, y0m, x1m, y1m, alto, sube_max=int(alto * 1.5))
                cajas.append(Caja(max(x0m, fin.x1 + 2), y0m, x1m, y1m, tipo,
                                  " ".join(p.texto for p in linea[a:b]), "etiqueta", 0.9))
                continue
            if derecha_texto:
                # prosa o valor impreso legible: tramo clásico a la altura de la línea
                if x_fin - x_ini >= alto:
                    cajas.append(Caja(x_ini, y0d, x_fin, y1d, tipo,
                                      " ".join(p.texto for p in linea[a:b]), "etiqueta", 0.9))
                continue

            # nada legible a la derecha: decidir por TINTA dónde está el valor manuscrito
            tinta_derecha = hay_tinta(mascara, x_ini, y0d - alto, x_fin, y1d + alto)
            tinta_abajo = hay_tinta(mascara, ini.x0 - alto, fondo + 2, fin.x1 + alto * 3, int(fondo + alto * 2.5))

            if tinta_derecha and x_fin - x_ini >= alto:
                x0e, y0e, x1e, y1e = _ajustar_tinta(mascara, x_ini, y0d, x_fin, y1d, alto, sube_max=int(alto * 1.5))
                x0e = max(x0e, fin.x1 + 2)          # no comerse la etiqueta
                cajas.append(Caja(x0e, y0e, x1e, y1e, tipo,
                                  " ".join(p.texto for p in linea[a:b]), "etiqueta", 0.9))
            if tinta_abajo:
                x1c = min(ancho_px - margen, fin.x1 + int(ancho_max * 0.6))
                cajas.append(_caja_celda(ini.x0 - margen - alto // 2, x1c, fondo, alto, alto_celda,
                                         margen, tipo, " ".join(p.texto for p in linea[a:b]), todas, mascara))
            if not tinta_derecha and not tinta_abajo and x_fin - x_ini >= alto:
                # campo en blanco: tramo clásico por si acaso (barato)
                cajas.append(Caja(x_ini, y0d, x_fin, y1d, tipo,
                                  " ".join(p.texto for p in linea[a:b]), "etiqueta", 0.7))
    return cajas


def _cabeceras_apiladas(lineas, ancho_px, margen, alto_celda, todas, mascara, vistos) -> list[Caja]:
    """Cabeceras partidas en dos renglones dentro de la celda (APELLIDO / PATERNO)."""
    cajas: list[Caja] = []
    for j in range(len(lineas) - 1):
        l1 = lineas[j]
        alto1 = max(p.alto for p in l1)
        l2 = None
        for l in lineas[j + 1:j + 3]:
            if min(p.y0 for p in l) - max(p.y1 for p in l1) <= alto1 * 1.2:
                l2 = l
                break
        if l2 is None:
            continue
        celdas: list[tuple[Palabra, Palabra, str]] = []
        for w1 in l1:
            for w2 in l2:
                if w2.x0 < w1.x1 and w2.x1 > w1.x0:
                    candidato = (_normalizar(w1.texto) + " " + _normalizar(w2.texto)).strip()
                    for et in ETIQUETAS_ORDENADAS:
                        if " " in et and _coincide_etiqueta(candidato, et):
                            celdas.append((w1, w2, ETIQUETAS_FORMULARIO[et]))
                            break
                    break
        if len(celdas) < 2:
            continue
        celdas.sort(key=lambda c: c[0].x0)
        xs = [c[0].x0 for c in celdas]
        col_media = (xs[-1] - xs[0]) / (len(xs) - 1)
        fondo = max(c[1].y1 for c in celdas)
        for k, (w1, w2, tipo) in enumerate(celdas):
            if (id(w1), "apilada") in vistos:
                continue
            vistos.add((id(w1), "apilada"))
            alto = max(w1.alto, w2.alto)
            x0 = min(w1.x0, w2.x0) - margen - alto // 2
            x1 = celdas[k + 1][0].x0 - margen if k + 1 < len(celdas) else min(ancho_px - margen, int(x0 + max(col_media * 1.2, alto * 8)))
            cajas.append(_caja_celda(x0, x1, fondo, alto, alto_celda, margen, tipo,
                                     f"{w1.texto} {w2.texto}", todas, mascara))
    return cajas
