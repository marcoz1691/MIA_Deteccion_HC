"""Detección de identificadores (PHI) sobre texto plano.

Reglas para Ecuador (cédula con dígito verificador, RUC, celular/fijo, HC) + contexto
("Paciente: ...", "Dirección: ...") + NER de spaCy para nombres sueltos.
Trabaja sobre texto que viene de OCR, así que tolera confusiones típicas (O/0, l/1, S/5...).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass
class Hallazgo:
    ini: int
    fin: int
    etiqueta: str
    texto: str
    origen: str          # "regex" | "contexto" | "ner"
    conf: float = 1.0


# --------------------------------------------------------------------------- normalización OCR

_CONFUSION_DIGITO = str.maketrans({
    "O": "0", "o": "0", "D": "0", "Q": "0",
    "I": "1", "l": "1", "|": "1", "!": "1", "í": "1",
    "Z": "2", "z": "2",
    "S": "5", "s": "5",
    "B": "8",
    "G": "6", "b": "6",
    "T": "7",
})


def _normalizar_digitos(texto: str) -> str:
    """Convierte letras que el OCR confunde con dígitos, SOLO dentro de tokens que ya son
    mayoritariamente numéricos. Conserva la longitud (mapeo 1:1) para no perder offsets."""
    salida = list(texto)
    for m in re.finditer(r"[0-9OoDQIl|!íZzSsBGbT.\-\s]{6,}", texto):
        trozo = m.group(0)
        # recortar al tramo entre el primer y el último dígito real (evita tragarse la "I" de "CI")
        digs = [i for i, ch in enumerate(trozo) if ch.isdigit()]
        if len(digs) < 5:
            continue
        a, b = digs[0], digs[-1] + 1
        # dejar entrar como mucho 1 letra pegada por cada lado (p. ej. "S" final leída por "5")
        while a > 0 and trozo[a - 1] not in " \t\n" and a > digs[0] - 1:
            a -= 1
        while b < len(trozo) and trozo[b] not in " \t\n" and b < digs[-1] + 2:
            b += 1
        nucleo = trozo[a:b]
        n_dig = len(digs)
        n_alfa = sum(ch.isalpha() or ch in "|!" for ch in nucleo)
        if n_alfa <= max(2, n_dig // 3):
            for i, ch in enumerate(nucleo):
                salida[m.start() + a + i] = ch.translate(_CONFUSION_DIGITO)
    return "".join(salida)


def sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


# --------------------------------------------------------------------------- validadores Ecuador

def cedula_valida(c: str) -> bool:
    """Cédula ecuatoriana: 10 dígitos, provincia 01-24 (30 = extranjeros), 3er dígito < 6, módulo 10."""
    c = re.sub(r"\D", "", c)
    if len(c) != 10 or not c.isdigit():
        return False
    prov = int(c[:2])
    if not (1 <= prov <= 24 or prov == 30):
        return False
    if int(c[2]) >= 6:
        return False
    coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    suma = 0
    for d, k in zip(c[:9], coef):
        v = int(d) * k
        suma += v - 9 if v > 9 else v
    verificador = (10 - suma % 10) % 10
    return verificador == int(c[9])


def ruc_valido(r: str) -> bool:
    r = re.sub(r"\D", "", r)
    if len(r) != 13:
        return False
    # RUC de persona natural = cédula + 001. Sociedades/públicas tienen otro algoritmo; se aceptan por forma.
    if r.endswith("001") and cedula_valida(r[:10]):
        return True
    return 1 <= int(r[:2]) <= 24 and r[2] in "6" "9"


# --------------------------------------------------------------------------- patrones

PATRONES: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.I)),
    # el OCR suele leer '@' como '0', 'a', '(a)' o 'Q': se acepta si el dominio parece de correo
    ("EMAIL", re.compile(r"[\w.+-]{3,}(?:@|\(a\)|[0oOQ])[\w-]{2,}\.(?:com|ec|org|net|edu|gob|gov|es)(?:\.[a-z]{2})?\b", re.I)),
    ("RUC", re.compile(r"(?<!\d)\d{13}(?!\d)")),
    ("CEDULA", re.compile(r"(?<!\d)\d{2}[\s.\-]?\d{4}[\s.\-]?\d{4}(?!\d)")),
    ("TELEFONO", re.compile(r"(?<!\d)(?:\+?593[\s\-]?)?(?:0?9\d[\s\-]?\d{3}[\s\-]?\d{4}|0[2-7][\s\-]?\d{3}[\s\-]?\d{4})(?!\d)")),
    ("HC", re.compile(
        r"(?:H\.?\s?C\.?U?|Historia\s+Cl[ií]nica|N[°ºo.]*\s*(?:de\s+)?(?:Archivo|Historia))\s*(?:N[°ºo.]*)?\s*[:#\-]?\s*"
        r"(\d[\d\-./]{3,})", re.I)),
]

FECHA_NUM = re.compile(r"(?<!\d)(\d{1,2})[\s/.\-]+(\d{1,2})[\s/.\-]+(\d{2,4})(?!\d)")
FECHA_TXT = re.compile(
    r"(?<!\w)\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)"
    r"(?:\s+de(?:l)?\s+\d{2,4})?", re.I)
CONTEXTO_NACIMIENTO = re.compile(r"(?:fecha\s+(?:de\s+)?nac(?:imiento|\.)?|f\.?\s?nac\.?|nacid[oa]\s+el|nacimiento)\s*[:\-]?\s*$", re.I)

# "Paciente: Juan Pérez"  -> captura hasta 5 palabras que empiecen por mayúscula o estén en mayúsculas
PALABRA_NOMBRE = r"(?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|[A-ZÁÉÍÓÚÑ]{3,})"   # 'HC', 'CI' (2 letras) no cuentan como nombre
CONTEXTO_NOMBRE = re.compile(
    r"(?i:Paciente|Nombres?(?:\s+y\s+Apellidos?)?|Apellidos?(?:\s+y\s+Nombres?)?|Nombre\s+del\s+paciente|"
    r"Madre|Padre|Representante|Responsable|C[oó]nyuge|Acompa[ñn]ante|Familiar|Informante|Dr\.?|Dra\.?|M[eé]dico|Tratante)"
    r"[ \t]*[:.\-]?[ \t]+(" + PALABRA_NOMBRE + r"(?:[ \t]+(?:de|del|la|los|y|" + PALABRA_NOMBRE + r")){0,5})", re.U)   # sin saltos de línea
CONTEXTO_DIRECCION = re.compile(r"(?:Direcci[oó]n|Domicilio|Barrio|Residencia)\s*[:\-]?\s*([^\n]{4,80})", re.I)
CONTEXTO_EDAD = re.compile(r"(?<!\d)(9\d|1[0-2]\d)\s*a[ñn]os", re.I)   # >= 90 años identifica (criterio HIPAA)

# Palabras que NER suele marcar como PER y NO son personas en un contexto clínico
STOP_NER = {
    "hospital", "centro", "salud", "ministerio", "msp", "iess", "ecuador", "quito", "guayaquil", "cuenca",
    "historia", "clínica", "clinica", "diagnóstico", "diagnostico", "paciente", "consulta", "emergencia",
    "medicina", "cirugía", "cirugia", "pediatría", "pediatria", "ginecología", "obstetricia", "enfermería",
    "fecha", "hora", "edad", "sexo", "peso", "talla", "temperatura", "presión", "presion", "alergias",
    "diabetes", "hipertensión", "hipertension", "covid", "ibuprofeno", "paracetamol", "metformina",
    "teléfono", "telefono", "celular", "correo", "direccion", "dirección", "cedula", "cédula",
    "acude", "refiere", "niega", "presenta", "ingresa", "egresa", "evoluciona", "recibe", "indica",
}


# --------------------------------------------------------------------------- NER

_nlp = None


def cargar_ner(modelo: str):
    global _nlp
    if _nlp is None:
        import spacy
        try:
            _nlp = spacy.load(modelo, disable=["parser", "lemmatizer", "attribute_ruler"])
        except OSError:
            _nlp = False
    return _nlp


def _ner(texto: str, modelo: str) -> list[Hallazgo]:
    nlp = cargar_ner(modelo)
    if not nlp:
        return []
    out = []
    for ent in nlp(texto).ents:
        if ent.label_ != "PER":
            continue
        t = ent.text.strip()
        if len(t) < 3 or any(ch.isdigit() for ch in t):
            continue
        tokens = [sin_tildes(w.lower()) for w in t.split()]
        if all(tok in STOP_NER for tok in tokens):
            continue
        if not any(w[:1].isupper() for w in t.split()):
            continue
        out.append(Hallazgo(ent.start_char, ent.end_char, "NOMBRE", t, "ner", 0.7))
    return out


# --------------------------------------------------------------------------- detector principal

def detectar(texto: str, usar_ner: bool = True, modelo_spacy: str = "es_core_news_md", fechas: str = "nacimiento") -> list[Hallazgo]:
    norm = _normalizar_digitos(texto)
    hallazgos: list[Hallazgo] = []

    for etiqueta, patron in PATRONES:
        for m in patron.finditer(norm):
            s, e = m.span()
            valor = m.group(0)
            if etiqueta == "CEDULA" and not cedula_valida(valor):
                # Forma de cédula pero dígito verificador incorrecto (OCR imperfecto): se tacha igual, con menos confianza
                hallazgos.append(Hallazgo(s, e, "CEDULA", texto[s:e], "regex", 0.5))
                continue
            if etiqueta == "RUC" and not ruc_valido(valor):
                hallazgos.append(Hallazgo(s, e, "RUC", texto[s:e], "regex", 0.5))
                continue
            if etiqueta == "HC":
                s, e = m.span(1)   # solo el número, dejar la etiqueta "HC" legible
                while e > s and texto[e - 1] in ".,;:-/":
                    e -= 1
            hallazgos.append(Hallazgo(s, e, etiqueta, texto[s:e], "regex", 0.95))

    # Fechas
    if fechas != "ninguna":
        for patron in (FECHA_NUM, FECHA_TXT):
            for m in patron.finditer(norm):
                s, e = m.span()
                if patron is FECHA_NUM:
                    d, mo = int(m.group(1)), int(m.group(2))
                    if not (1 <= d <= 31 and 1 <= mo <= 12) and not (1 <= mo <= 31 and 1 <= d <= 12):
                        continue
                if fechas == "todas" or CONTEXTO_NACIMIENTO.search(texto[max(0, s - 40):s]):
                    hallazgos.append(Hallazgo(s, e, "FECHA", texto[s:e], "regex", 0.9))

    # Nombres por contexto
    for m in CONTEXTO_NOMBRE.finditer(texto):
        s, e = m.span(1)
        hallazgos.append(Hallazgo(s, e, "NOMBRE", texto[s:e], "contexto", 0.9))

    for m in CONTEXTO_DIRECCION.finditer(texto):
        s, e = m.span(1)
        hallazgos.append(Hallazgo(s, e, "DIRECCION", texto[s:e], "contexto", 0.85))

    for m in CONTEXTO_EDAD.finditer(texto):
        s, e = m.span(1)
        hallazgos.append(Hallazgo(s, e, "EDAD", texto[s:e], "regex", 0.8))

    if usar_ner:
        hallazgos.extend(_ner(texto, modelo_spacy))

    return fusionar_hallazgos(hallazgos)


def fusionar_hallazgos(h: list[Hallazgo]) -> list[Hallazgo]:
    h = sorted(h, key=lambda x: (x.ini, -x.fin))
    out: list[Hallazgo] = []
    for x in h:
        if out and x.ini < out[-1].fin:
            prev = out[-1]
            prev.fin = max(prev.fin, x.fin)
            prev.conf = max(prev.conf, x.conf)
            if x.etiqueta != prev.etiqueta and x.etiqueta not in prev.etiqueta:
                prev.etiqueta = f"{prev.etiqueta}+{x.etiqueta}"
        else:
            out.append(Hallazgo(x.ini, x.fin, x.etiqueta, x.texto, x.origen, x.conf))
    return out
