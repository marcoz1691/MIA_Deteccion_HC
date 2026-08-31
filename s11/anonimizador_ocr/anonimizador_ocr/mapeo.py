"""Puente entre el texto plano (donde corren regex y NER) y las cajas de píxeles (donde se tacha)."""
from __future__ import annotations

from dataclasses import dataclass

from .ocr import Palabra


@dataclass
class Caja:
    x0: int
    y0: int
    x1: int
    y1: int
    etiqueta: str
    texto: str = ""
    origen: str = ""     # "regex", "ner", "etiqueta", "zona"
    conf: float = 100.0

    def unir(self, otra: "Caja") -> "Caja":
        return Caja(min(self.x0, otra.x0), min(self.y0, otra.y0),
                    max(self.x1, otra.x1), max(self.y1, otra.y1),
                    self.etiqueta, (self.texto + " " + otra.texto).strip(), self.origen, min(self.conf, otra.conf))


def construir_texto(palabras: list[Palabra]) -> str:
    """Ordena por (bloque, párrafo, línea) y luego por x; une palabras con espacio y líneas con salto.
    Rellena `ini`/`fin` de cada palabra con su offset en el texto resultante."""
    palabras.sort(key=lambda p: (p.clave_linea, p.x0))
    trozos: list[str] = []
    pos = 0
    linea_prev = None
    for p in palabras:
        if linea_prev is not None:
            sep = "\n" if p.clave_linea != linea_prev else " "
            trozos.append(sep)
            pos += 1
        p.ini = pos
        p.fin = pos + len(p.texto)
        trozos.append(p.texto)
        pos = p.fin
        linea_prev = p.clave_linea
    return "".join(trozos)


def palabras_en_span(palabras: list[Palabra], ini: int, fin: int) -> list[Palabra]:
    return [p for p in palabras if p.fin > ini and p.ini < fin]


def cajas_desde_span(palabras: list[Palabra], ini: int, fin: int, etiqueta: str, origen: str, margen: int) -> list[Caja]:
    """Una caja por línea (un span puede saltar de línea)."""
    por_linea: dict[tuple, Caja] = {}
    for p in palabras_en_span(palabras, ini, fin):
        c = Caja(p.x0 - margen, p.y0 - margen, p.x1 + margen, p.y1 + margen, etiqueta, p.texto, origen, p.conf)
        k = p.clave_linea
        por_linea[k] = por_linea[k].unir(c) if k in por_linea else c
    return list(por_linea.values())


def fusionar_cajas(cajas: list[Caja], tolerancia: int = 6) -> list[Caja]:
    """Une cajas que se tocan o solapan (misma etiqueta o no) para no dejar rendijas."""
    cajas = sorted(cajas, key=lambda c: (c.y0, c.x0))
    resultado: list[Caja] = []
    for c in cajas:
        fusionada = False
        for i, r in enumerate(resultado):
            if (c.x0 <= r.x1 + tolerancia and c.x1 >= r.x0 - tolerancia and
                    c.y0 <= r.y1 + tolerancia and c.y1 >= r.y0 - tolerancia):
                resultado[i] = r.unir(c)
                if r.etiqueta != c.etiqueta:
                    resultado[i].etiqueta = f"{r.etiqueta}+{c.etiqueta}" if c.etiqueta not in r.etiqueta else r.etiqueta
                fusionada = True
                break
        if not fusionada:
            resultado.append(c)
    return resultado
