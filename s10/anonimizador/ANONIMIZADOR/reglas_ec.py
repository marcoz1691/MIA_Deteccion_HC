"""
reglas_ec.py
------------
Reglas y expresiones regulares para detectar identificadores directos (PHI) en
historias clínicas del Ecuador. Se prioriza ALTA PRECISIÓN: las reglas se validan
con contexto o con dígito verificador cuando es posible, para no redactar texto
clínico legítimo por error.

Categorías cubiertas:
    CEDULA      cédula ecuatoriana (10 dígitos, con validación de dígito verificador)
    RUC         registro único de contribuyentes (13 dígitos)
    TELEFONO    fijo y celular (+593, 0XXXXXXXXX)
    EMAIL       correo electrónico
    FECHA       fechas en varios formatos (se desplazan, no se borran)
    NUM_HISTORIA número de historia clínica / afiliación IESS (con contexto)
    EDAD_90     edades de 90 años o más (identificador según norma de privacidad)
    URL, IP     direcciones web e IP
"""
from __future__ import annotations
import re
import datetime as dt

# --- Cédula ecuatoriana ---
# (a) por CONTEXTO: precedida de la palabra "cédula/CI/documento" -> se redacta
#     SIEMPRE, aunque el dígito verificador falle (p. ej. por error de tipeo/OCR).
_CEDULA_CTX = re.compile(
    r"(?P<ctx>\b(?:c[ée]dula|c\.?i\.?|documento(?:\s+de\s+identidad)?)\s*[:#°ºNo\.\-]*\s*)"
    r"(?P<num>\d{6,10})", re.IGNORECASE)
# (b) SUELTA: 10 dígitos con dígito verificador válido (alta precisión).
_CEDULA_CAND = re.compile(r"(?<!\d)(\d{10})(?!\d)")

def cedula_valida(num: str) -> bool:
    """Valida una cédula ecuatoriana por su algoritmo de dígito verificador.
       Reduce falsos positivos frente a cualquier secuencia de 10 dígitos."""
    if len(num) != 10 or not num.isdigit():
        return False
    prov = int(num[:2])
    if prov < 1 or prov > 24:
        return False
    if int(num[2]) >= 6:  # tercer dígito < 6 para personas naturales
        return False
    coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = 0
    for c, d in zip(coef, [int(x) for x in num[:9]]):
        p = c * d
        if p >= 10:
            p -= 9
        total += p
    verificador = (10 - (total % 10)) % 10
    return verificador == int(num[9])

# --- RUC: 13 dígitos (cédula/sociedad + 001) ---
_RUC = re.compile(r"(?<!\d)(\d{13})(?!\d)")

# --- Teléfono Ecuador: +593 o 0 seguido de 8-9 dígitos ---
_TELEFONO = re.compile(
    r"(?<![\d])(?:\+?593[\s\-]?|0)(?:[2-7]|9)\d(?:[\s\-]?\d){6,7}(?![\d])")

# --- Email ---
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# --- URL / IP ---
_URL = re.compile(r"\bhttps?://[^\s]+\b")
_IP = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")

# --- Edad >= 90 (identificador según Safe Harbor) ---
_EDAD90 = re.compile(r"\b(9\d|1\d{2})\s*a[ñn]os\b", re.IGNORECASE)

# --- Número de historia clínica / afiliación, detectado por CONTEXTO ---
_NUM_CTX = re.compile(
    r"(?P<ctx>(?:historia\s*(?:cl[ií]nica)?|HC|N[°ºo\.]*\s*de\s*historia|"
    r"afiliaci[oó]n|IESS|expediente|registro)\s*[:#°ºNo\.\-]*\s*)(?P<num>[A-Z]?\d{4,12})",
    re.IGNORECASE)

# --- Fechas: dd/mm/aaaa, dd-mm-aaaa, aaaa-mm-dd, "12 de marzo de 2025" ---
_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
          "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
          "noviembre": 11, "diciembre": 12}
_FECHA_NUM = re.compile(
    r"(?<!\d)(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})(?!\d)"
    r"|(?<!\d)(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})(?!\d)")
_FECHA_TXT = re.compile(
    r"\b(\d{1,2})\s+de\s+(" + "|".join(_MESES) + r")\s+de\s+(\d{4})\b",
    re.IGNORECASE)


def _parse_fecha(m: re.Match):
    """Devuelve (datetime, tipo) para una coincidencia de fecha, o (None, None)."""
    g = m.groups()
    try:
        if m.re is _FECHA_TXT:
            d, mes, a = int(g[0]), _MESES[g[1].lower()], int(g[2])
            return dt.date(a, mes, d), "txt"
        # numérica
        if g[0] is not None:  # dd/mm/aaaa
            d, mo, a = int(g[0]), int(g[1]), int(g[2])
            if a < 100:
                a += 2000 if a < 50 else 1900
            return dt.date(a, mo, d), "num_dmy"
        else:                 # aaaa/mm/dd
            a, mo, d = int(g[3]), int(g[4]), int(g[5])
            return dt.date(a, mo, d), "num_ymd"
    except (ValueError, TypeError, KeyError):
        return None, None


def buscar_identificadores(texto: str):
    """
    Devuelve una lista de dicts: {inicio, fin, texto, tipo}
    para todos los identificadores estructurados encontrados por reglas.
    Las fechas se devuelven con su objeto date para poder desplazarlas.
    """
    hallazgos = []

    def add(ini, fin, txt, tipo, extra=None):
        h = {"inicio": ini, "fin": fin, "texto": txt, "tipo": tipo}
        if extra:
            h.update(extra)
        hallazgos.append(h)

    for m in _EMAIL.finditer(texto):
        add(m.start(), m.end(), m.group(), "EMAIL")
    for m in _URL.finditer(texto):
        add(m.start(), m.end(), m.group(), "URL")
    for m in _NUM_CTX.finditer(texto):
        add(m.start("num"), m.end("num"), m.group("num"), "NUM_HISTORIA")
    for m in _CEDULA_CTX.finditer(texto):
        add(m.start("num"), m.end("num"), m.group("num"), "CEDULA")
    for m in _RUC.finditer(texto):
        add(m.start(), m.end(), m.group(), "RUC")
    for m in _CEDULA_CAND.finditer(texto):
        if cedula_valida(m.group(1)):
            add(m.start(), m.end(), m.group(), "CEDULA")
    for m in _TELEFONO.finditer(texto):
        add(m.start(), m.end(), m.group(), "TELEFONO")
    for m in _EDAD90.finditer(texto):
        add(m.start(), m.end(), m.group(), "EDAD_90")
    for m in _IP.finditer(texto):
        add(m.start(), m.end(), m.group(), "IP")
    for rx in (_FECHA_TXT, _FECHA_NUM):
        for m in rx.finditer(texto):
            fecha, _ = _parse_fecha(m)
            if fecha:
                add(m.start(), m.end(), m.group(), "FECHA", {"fecha": fecha})

    return hallazgos
