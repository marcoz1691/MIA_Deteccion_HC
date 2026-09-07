#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anonimizador_pdf.py  (v2)
Anonimizador de PDFs de historias clínicas en español (formulario SNS-MSP / HCU).

Detecta nombres de personas por cuatro vías complementarias:

  1. TABLA   Celda que está DEBAJO de una cabecera de columna
             ("PRIMER APELLIDO", "SEGUNDO NOMBRE", "APELLIDOS Y NOMBRES"...).
             Es puramente geométrico: no necesita dos puntos ni texto seguido.
  2. FIRMA   Línea de nombre en mayúsculas cuya línea siguiente es una
             especialidad o credencial ("MEDICINA GENERAL", "ANESTESIOLOGÍA",
             "CI:", "SENESCYT"...). Cubre las firmas al pie de cada evolución.
  3. TITULO  Nombre precedido de abreviatura: Dr. Dra. Lic. Lcda. Lcdo. Md.
             Ing. Sr. Sra. Psic. Odont. Tlgo. ...
  4. CAMPO   Nombre tras una etiqueta con dos puntos ("Paciente:",
             "Médico tratante:", "Acompañante:"...).
  + opcional NER con spaCy (--ner) y lista propia de nombres (--lista).

Un filtro de vocabulario clínico evita tachar diagnósticos: en
"PADRE: HIPERTENSIÓN ARTERIAL" no hay ningún nombre y no se toca.

Uso:
    python anonimizador_pdf.py HC002.pdf -o HC002_anon.pdf --reporte auditoria.csv
    python anonimizador_pdf.py historias/ -o historias_anon/ --identificadores
    python anonimizador_pdf.py HC002.pdf --simulacion

Requisitos:  pip install pymupdf      (opcional: spacy + es_core_news_lg)
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

try:
    import pymupdf
except ImportError:  # pragma: no cover
    try:
        import fitz as pymupdf
    except ImportError:
        sys.exit("Falta PyMuPDF. Instala con:  pip install pymupdf")


# ============================================================================
# VOCABULARIO
# ============================================================================

# --- 1. Cabeceras de columna cuyo valor (celda de abajo) es un nombre -------
CABECERAS_NOMBRE = [
    "PRIMER APELLIDO", "SEGUNDO APELLIDO", "PRIMER NOMBRE", "SEGUNDO NOMBRE",
    "APELLIDO PATERNO", "APELLIDO MATERNO",
    "APELLIDOS Y NOMBRES", "NOMBRES Y APELLIDOS", "NOMBRE COMPLETO",
    "NOMBRE DEL PACIENTE", "APELLIDOS", "NOMBRES",
    "NOMBRE DEL PROFESIONAL", "PROFESIONAL RESPONSABLE",
]

# --- 2. Cabeceras de identificadores (solo con --identificadores) -----------
CABECERAS_ID = [
    "NUMERO HIST. CLINICA UNICA", "NUMERO DE HISTORIA CLINICA",
    "HISTORIA CLINICA UNICA", "NUMERO DE ARCHIVO", "UNICODIGO",
    "CEDULA", "CEDULA DE IDENTIDAD", "No. CEDULA", "DOCUMENTO DE IDENTIDAD",
    "TELEFONO", "CELULAR", "DIRECCION", "FECHA DE NACIMIENTO",
]

# --- 3. Cabeceras vecinas: no se tachan, solo delimitan las columnas --------
CABECERAS_LIMITE = [
    "SEXO", "EDAD", "CONDICION EDAD", "NRO.HOJA", "NRO. HOJA",
    "INSTITUCION DEL SISTEMA", "ESTABLECIMIENTO DE SALUD",
    "ESTADO CIVIL", "NACIONALIDAD", "INSTRUCCION", "OCUPACION",
    "ETNIA", "GRUPO SANGUINEO", "TIPO DE SEGURO", "PARENTESCO",
]

# --- 4. Especialidades/credenciales que aparecen bajo una firma -------------
CREDENCIALES = [
    "medicina general", "medicina interna", "medico general", "medico tratante",
    "medico residente", "medico especialista", "medico", "cirugia",
    "cirugia general", "anestesiologia", "ginecologia", "obstetricia",
    "pediatria", "traumatologia", "cardiologia", "gastroenterologia",
    "dermatologia", "urologia", "neurologia", "neurocirugia", "psiquiatria",
    "psicologia", "psicologia clinica", "radiologia", "imagenologia",
    "patologia", "laboratorio clinico", "enfermeria", "nutricion",
    "terapia fisica", "rehabilitacion", "emergenciologia", "oncologia",
    "neumologia", "endocrinologia", "nefrologia", "otorrinolaringologia",
    "oftalmologia", "reumatologia", "infectologia", "hematologia",
    "odontologia", "fisiatria", "residente", "interno rotativo",
    "senescyt", "reg. senescyt", "codigo senescyt", "acess",
    "ci:", "cc:", "cedula:", "codigo:", "reg:",
]

# --- 5. Etiquetas "Campo: valor" -------------------------------------------
# OJO: aquí NO van "padre", "madre" ni "familiar". En la sección APF
# (antecedentes patológicos familiares) lo que sigue es un diagnóstico.
ETIQUETAS_CAMPO = [
    "paciente", "nombre", "nombres", "apellido", "apellidos",
    "nombres y apellidos", "apellidos y nombres", "nombre completo",
    "nombre del paciente", "primer nombre", "segundo nombre",
    "apellido paterno", "apellido materno",
    "medico", "medico tratante", "medico responsable", "medico solicitante",
    "profesional", "profesional responsable",
    "atendido por", "solicitado por", "elaborado por", "revisado por",
    "realizado por", "informado por", "referido por", "derivado por",
    "acompanante", "representante", "representante legal", "informante",
    "conyuge", "titular", "afiliado", "beneficiario", "tutor", "testigo",
    "firma", "recibido por", "entregado por",
]

# --- 6. Abreviaturas de título --------------------------------------------
TITULOS_SEGUROS = [
    "dr", "dra", "drs", "dctr",
    "lic", "licda", "licdo", "lcda", "lcdo", "ldo", "lda",
    "md", "mgs", "msc", "phd",
    "ing", "arq", "econ", "abg", "abog",
    "psic", "psiq", "odont", "obst", "obsta", "enf", "enfr",
    "tlgo", "tlga", "tnlgo", "tnlga", "bqf", "flgo",
    "sr", "sra", "srta", "sres", "prof",
]
TITULOS_CON_PUNTO = [
    "ab", "od", "ps", "psc", "int", "est", "res", "tec",
    "qf", "q.f", "m.d", "mg", "esp", "doc", "nut", "ft",
]

# --- 7. Palabras que NO son nombre aunque vayan en mayúsculas ---------------
NO_ES_NOMBRE = {
    # formulario
    "historia", "clinica", "hoja", "formulario", "form", "anexo", "pagina",
    "fecha", "hora", "inicio", "edad", "sexo", "genero", "estado", "civil",
    "ocupacion", "instruccion", "cedula", "ci", "identificacion", "documento",
    "pasaporte", "telefono", "celular", "direccion", "domicilio", "correo",
    "nacionalidad", "etnia", "mestiza", "mestizo", "indigena", "afroecuatoriano",
    "masculino", "femenino", "femenina", "soltero", "soltera", "casado",
    "casada", "divorciado", "viudo", "union", "libre", "no", "si", "ninguno",
    "ninguna", "sin", "datos", "nota", "notas", "registrar", "administracion",
    "unicodigo", "archivo", "numero", "nro", "red", "complementaria",
    "condicion", "marcar", "usuario", "paciente", "pacientes", "seguro",
    # institución / lugar
    "hospital", "centro", "consultorio", "laboratorio", "servicio", "area",
    "unidad", "sala", "piso", "cama", "consulta", "externa", "emergencia",
    "quirofano", "citimed", "consorciomedico", "cia", "ltda", "cym", "iess",
    "msp", "sns", "hcu", "ministerio", "salud", "publica", "social", "ecuador",
    # sección / documento clínico
    "evolucion", "evoluciones", "prescripciones", "prescripcion", "ordenes",
    "medicas", "generales", "farmacoterapia", "indicaciones", "hospitalaria",
    "ingreso", "egreso", "alta", "epicrisis", "interconsulta", "referencia",
    "contrarreferencia", "informe", "resultado", "resultados", "analisis",
    "subjetivo", "objetivo", "plan", "impresion", "app", "apf", "aqx", "ago",
    "antecedentes", "patologicos", "personales", "familiares", "quirurgicos",
    "ginecoobstetricos", "habitos", "alergias", "motivo", "enfermedad",
    "actual", "examen", "fisico", "diagnostico", "diagnosticos", "tratamiento",
    "procedimiento", "procedimientos", "hallazgos", "complicaciones",
    "observaciones", "biopsia", "medicacion", "medicamento", "dosis", "via",
    "oral", "intravenosa", "receta", "consentimiento", "informado",
    # valores frecuentes
    "positivo", "negativo", "normal", "anormal", "presente", "presentes",
    "ausente", "grupo", "factor", "rh", "total", "control", "general",
    "activo", "leve", "moderado", "severo", "derecho", "izquierdo",
    "superior", "inferior", "bilateral", "dias", "meses", "anos", "horas",
    "veces", "dia", "sangre", "sanguineo",
    # calendario
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "setiembre", "octubre", "noviembre", "diciembre",
    "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo",
}

# Vocabulario clínico: evita que un diagnóstico en mayúsculas pase por nombre.
TERMINOS_CLINICOS = {
    "hipertension", "hipertensivo", "arterial", "diabetes", "mellitus",
    "obesidad", "morbida", "sobrepeso", "asma", "epoc", "cancer", "neoplasia",
    "tumor", "artritis", "artrosis", "gastritis", "gastropatia", "hernia",
    "hiatal", "hiato", "reflujo", "ulcera", "colecistectomia", "colelitiasis",
    "apendicitis", "hipotiroidismo", "hipertiroidismo", "tiroides", "tiroideo",
    "insulina", "resistencia", "sindrome", "ovario", "poliquistico",
    "anemia", "leucemia", "linfoma", "insuficiencia", "renal", "cardiaca",
    "hepatica", "cirrosis", "hepatitis", "vih", "sida", "tuberculosis",
    "neumonia", "bronquitis", "migrana", "cefalea", "epilepsia", "convulsion",
    "depresion", "ansiedad", "dislipidemia", "colesterol", "trigliceridos",
    "infarto", "acv", "ictus", "trombosis", "embolia", "varices", "flebitis",
    "edema", "eritema", "dolor", "fiebre", "nausea", "vomito", "diarrea",
    "estrenimiento", "disnea", "tos", "endoscopia", "colonoscopia",
    "ecografia", "radiografia", "tomografia", "resonancia", "cirugia",
    "bariatrica", "anestesia", "sedacion", "esofago", "estomago", "duodeno",
    "antro", "piloro", "mucosa", "atrofica", "eritematosa", "mosaico",
    "pulmonar", "cardiaco", "abdomen", "torax", "cuello", "cabeza", "nariz",
    "boca", "extremidades", "pupilas", "conjuntivas", "signos", "vitales",
    "presion", "frecuencia", "cardiaca", "respiratoria", "temperatura",
    "saturacion", "peso", "talla", "imc", "glucosa", "hemoglobina",
}

NO_ES_NOMBRE |= TERMINOS_CLINICOS
NO_ES_NOMBRE.update(t.replace(".", "") for t in TITULOS_SEGUROS + TITULOS_CON_PUNTO)

PARTICULAS = {"de", "del", "la", "las", "los", "san", "santa", "van", "von", "di", "da", "y", "e"}

MAY = "A-ZÁÉÍÓÚÜÑ"
MIN = "a-záéíóúüñ"
TOKEN_NOMBRE = rf"(?:[{MAY}][{MIN}]+|[{MAY}]{{2,}}|{'|'.join(PARTICULAS)})"
SECUENCIA_NOMBRE = rf"{TOKEN_NOMBRE}(?:[ \t]+{TOKEN_NOMBRE}){{0,6}}"


def _alt(palabras):
    return "|".join(re.escape(p) for p in sorted(palabras, key=len, reverse=True))


_FLEX = {"a": "[aáà]", "e": "[eé]", "i": "[ií]", "o": "[oó]", "u": "[uúü]", "n": "[nñ]"}


def _flexible(frase: str) -> str:
    """'medico tratante' -> patrón que también acepta 'MÉDICO  TRATANTE'."""
    return "".join(r"\s+" if c == " " else _FLEX.get(c, re.escape(c)) for c in frase)


RE_TITULO = re.compile(
    rf"(?<![{MAY}{MIN}])"
    rf"(?:(?:{_alt(TITULOS_SEGUROS)})(?:\s*\.\s*|\s+)"
    rf"|(?:{_alt(TITULOS_CON_PUNTO)})\s*\.\s*)"
    rf"(?P<nombre>{SECUENCIA_NOMBRE})",
    re.IGNORECASE,
)

RE_CAMPO = re.compile(
    rf"(?:{'|'.join(_flexible(e) for e in sorted(ETIQUETAS_CAMPO, key=len, reverse=True))})"
    rf"\s*[:\-]\s*(?P<nombre>{SECUENCIA_NOMBRE})",
    re.IGNORECASE,
)

RE_CREDENCIAL = re.compile(rf"^(?:{_alt(CREDENCIALES)})\b")
RE_SOLO_LETRAS = re.compile(rf"^[{MAY}{MIN}'´`-]{{2,}}$")


def sin_tildes(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    ).lower()


def es_palabra_de_nombre(palabra: str) -> bool:
    """¿Esta palabra suelta puede formar parte de un nombre propio?"""
    limpia = palabra.strip(".,;:()[]")
    if not RE_SOLO_LETRAS.match(limpia):
        return False
    base = sin_tildes(limpia)
    if base in NO_ES_NOMBRE:
        return False
    return len(base) >= 2


def limpiar_nombre(bruto: str) -> str:
    tokens, limpio = bruto.split(), []
    for tok in tokens:
        base = sin_tildes(tok.strip(".,;:()"))
        if base in NO_ES_NOMBRE or (len(base) < 2 and base not in {"y", "e"}):
            break
        limpio.append(tok)
    while limpio and sin_tildes(limpio[-1]) in PARTICULAS:
        limpio.pop()
    while limpio and sin_tildes(limpio[0]) in PARTICULAS:
        limpio.pop(0)
    return " ".join(limpio)


# ============================================================================
# ESTRUCTURAS
# ============================================================================

@dataclass
class Hallazgo:
    pagina: int
    texto: str
    metodo: str
    rect: "pymupdf.Rect"


@dataclass
class Estadisticas:
    hallazgos: list[Hallazgo] = field(default_factory=list)
    paginas_sin_texto: list[int] = field(default_factory=list)


# ============================================================================
# GEOMETRÍA
# ============================================================================

def filas_de_pagina(pagina, tol: float = 2.5):
    """Agrupa TODAS las palabras de la página en filas visuales por su 'y',
    sin importar a qué bloque o celda pertenezcan. Imprescindible aquí: en el
    formulario HCU un mismo renglón (nombre + apellido de la firma) vive en
    bloques distintos."""
    palabras = sorted(pagina.get_text("words"), key=lambda w: (round(w[1], 1), w[0]))
    filas, actual, y_ref = [], [], None
    for w in palabras:
        if y_ref is None or abs(w[1] - y_ref) <= tol:
            actual.append(w)
            y_ref = w[1] if y_ref is None else y_ref
        else:
            filas.append(sorted(actual, key=lambda p: p[0]))
            actual, y_ref = [w], w[1]
    if actual:
        filas.append(sorted(actual, key=lambda p: p[0]))
    return filas


def lineas_con_palabras(pagina):
    """Líneas de texto (bloque, línea) con el mapa carácter -> rectángulo."""
    palabras = sorted(pagina.get_text("words"), key=lambda w: (w[5], w[6], w[7]))
    lineas, clave_actual, texto, mapa = [], None, "", []
    for x0, y0, x1, y1, palabra, bloque, linea, _n in palabras:
        clave = (bloque, linea)
        if clave != clave_actual:
            if mapa:
                lineas.append((texto, mapa))
            clave_actual, texto, mapa = clave, "", []
        if texto:
            texto += " "
        ini = len(texto)
        texto += palabra
        mapa.append((ini, len(texto), pymupdf.Rect(x0, y0, x1, y1)))
    if mapa:
        lineas.append((texto, mapa))
    return lineas


def rect_del_tramo(mapa, inicio, fin):
    caja = None
    for p_ini, p_fin, rect in mapa:
        if p_fin > inicio and p_ini < fin:
            caja = rect if caja is None else caja | rect
    return caja


# ============================================================================
# DETECTOR 1 — CELDA BAJO CABECERA DE TABLA
# ============================================================================

def detectar_tabla(pagina, num_pagina: int, con_identificadores: bool,
                   alto_celda: float = 26.0) -> list[Hallazgo]:
    """Busca cabeceras de columna y tacha lo que esté en la celda de abajo.

    El ancho de cada columna se limita con el punto medio hacia la cabecera
    vecina, así un apellido largo no invade la columna de al lado ni se corta.
    """
    objetivo = list(CABECERAS_NOMBRE) + (list(CABECERAS_ID) if con_identificadores else [])
    todas = objetivo + list(CABECERAS_LIMITE)

    encontradas = []  # (rect, es_objetivo)
    for frase in todas:
        for rect in pagina.search_for(frase):
            encontradas.append((rect, frase in objetivo, frase))
    if not encontradas:
        return []

    hallazgos = []
    # agrupar cabeceras por renglón: comparten la misma fila de la tabla
    encontradas.sort(key=lambda t: (round(t[0].y0, 0), t[0].x0))
    renglones: dict[int, list] = {}
    for rect, es_obj, frase in encontradas:
        renglones.setdefault(round(rect.y0 / 3), []).append((rect, es_obj, frase))

    palabras = pagina.get_text("words")

    for grupo in renglones.values():
        grupo.sort(key=lambda t: t[0].x0)
        for i, (rect, es_obj, frase) in enumerate(grupo):
            if not es_obj:
                continue
            izq = (grupo[i - 1][0].x1 + rect.x0) / 2 if i > 0 else rect.x0 - 6
            der = (grupo[i + 1][0].x0 + rect.x1) / 2 if i + 1 < len(grupo) else rect.x1 + 6
            arriba, abajo = rect.y1 + 0.5, rect.y1 + alto_celda

            celda = [w for w in palabras
                     if arriba < w[1] < abajo and izq <= (w[0] + w[2]) / 2 <= der]
            if not celda:
                continue
            # quedarse solo con el primer renglón de la celda
            y_min = min(w[1] for w in celda)
            celda = [w for w in celda if w[1] - y_min <= 3]

            utiles = [w for w in celda if es_palabra_de_nombre(w[4])] if frase in CABECERAS_NOMBRE \
                else [w for w in celda if len(w[4].strip()) >= 3]
            if not utiles:
                continue
            caja = pymupdf.Rect(utiles[0][:4])
            for w in utiles[1:]:
                caja |= pymupdf.Rect(w[:4])
            metodo = "tabla" if frase in CABECERAS_NOMBRE else "tabla-id"
            hallazgos.append(Hallazgo(num_pagina, " ".join(w[4] for w in utiles), metodo, caja))
    return hallazgos


# ============================================================================
# DETECTOR 2 — FIRMA AL PIE (nombre sobre la especialidad)
# ============================================================================

def detectar_firmas(pagina, num_pagina: int, salto_max: float = 30.0) -> list[Hallazgo]:
    """Una firma es una fila de puro nombre cuya fila siguiente contiene la
    especialidad o credencial ('MEDICINA GENERAL', 'ANESTESIOLOGÍA', 'CI:')."""
    filas = filas_de_pagina(pagina)
    hallazgos = []
    for i in range(1, len(filas)):
        fila_cred = filas[i]
        texto_cred = sin_tildes(" ".join(w[4] for w in fila_cred))
        if not RE_CREDENCIAL.search(texto_cred):
            continue

        fila_nombre = filas[i - 1]
        salto = fila_cred[0][1] - fila_nombre[0][1]
        if not (0 < salto <= salto_max):
            continue
        # una firma está visualmente separada del párrafo anterior; si el
        # renglón de arriba está pegado, es prosa clínica y no una firma
        if i >= 2:
            hueco_arriba = fila_nombre[0][1] - filas[i - 2][0][1]
            if hueco_arriba < 12.0:
                continue
        # la fila del nombre debe ser corta y estar hecha solo de nombres
        if not 1 < len(fila_nombre) <= 6:
            continue
        if not all(es_palabra_de_nombre(w[4]) for w in fila_nombre):
            continue

        caja = pymupdf.Rect(fila_nombre[0][:4])
        for w in fila_nombre[1:]:
            caja |= pymupdf.Rect(w[:4])
        hallazgos.append(
            Hallazgo(num_pagina, " ".join(w[4] for w in fila_nombre), "firma", caja))
    return hallazgos


# ============================================================================
# DETECTORES 3 y 4 — TÍTULO Y CAMPO (por texto)
# ============================================================================

def detectar_en_linea(texto, mapa, num_pagina, lista_extra) -> list[Hallazgo]:
    hallazgos, ocupado = [], []

    def registrar(ini, bruto, metodo):
        nombre = limpiar_nombre(bruto)
        if not nombre:
            return
        fin = ini + len(nombre)
        if any(ini < f and fin > i for i, f in ocupado):
            return
        caja = rect_del_tramo(mapa, ini, fin)
        if caja is None:
            return
        ocupado.append((ini, fin))
        hallazgos.append(Hallazgo(num_pagina, nombre, metodo, caja))

    for m in RE_TITULO.finditer(texto):
        registrar(m.start("nombre"), m.group("nombre"), "titulo")
    for m in RE_CAMPO.finditer(texto):
        registrar(m.start("nombre"), m.group("nombre"), "campo")
    for nombre in lista_extra:
        for m in re.finditer(rf"(?<![{MAY}{MIN}]){re.escape(nombre)}(?![{MAY}{MIN}])",
                             texto, re.IGNORECASE):
            registrar(m.start(), m.group(), "lista")
    return hallazgos


def detectar_con_ner(nlp, texto, mapa, num_pagina, ya_cubierto) -> list[Hallazgo]:
    hallazgos = []
    for ent in nlp(texto).ents:
        if ent.label_ != "PER":
            continue
        nombre = limpiar_nombre(ent.text)
        if not nombre or len(nombre) < 3:
            continue
        ini, fin = ent.start_char, ent.start_char + len(nombre)
        if any(ini < f and fin > i for i, f in ya_cubierto):
            continue
        caja = rect_del_tramo(mapa, ini, fin)
        if caja is None:
            continue
        ya_cubierto.append((ini, fin))
        hallazgos.append(Hallazgo(num_pagina, nombre, "ner", caja))
    return hallazgos


# ============================================================================
# SEUDÓNIMOS
# ============================================================================

class Seudonimos:
    def __init__(self, prefijo="PERSONA"):
        self.prefijo, self.mapa = prefijo, {}

    def codigo(self, nombre: str) -> str:
        clave = re.sub(r"\s+", " ", sin_tildes(nombre)).strip()
        if clave not in self.mapa:
            self.mapa[clave] = f"[{self.prefijo}_{len(self.mapa) + 1:03d}]"
        return self.mapa[clave]


# ============================================================================
# PROCESO
# ============================================================================

def anonimizar_pdf(entrada: Path, salida: Path | None, usar_ner=False, lista_extra=None,
                   seudonimos=None, etiqueta_fija="[NOMBRE]", simulacion=False,
                   con_identificadores=False, margen=1.0) -> Estadisticas:
    lista_extra = lista_extra or set()
    stats = Estadisticas()

    nlp = None
    if usar_ner:
        try:
            import spacy
            for modelo in ("es_core_news_lg", "es_core_news_md", "es_core_news_sm"):
                try:
                    nlp = spacy.load(modelo, disable=["lemmatizer"])
                    break
                except OSError:
                    continue
            if nlp is None:
                print("  aviso: no hay modelo de spaCy en español; sigo con reglas.", file=sys.stderr)
        except ImportError:
            print("  aviso: spaCy no instalado; sigo con reglas.", file=sys.stderr)

    doc = pymupdf.open(entrada)

    for num, pagina in enumerate(doc, start=1):
        lineas = lineas_con_palabras(pagina)
        if not lineas:
            stats.paginas_sin_texto.append(num)
            continue

        hallazgos = detectar_tabla(pagina, num, con_identificadores)
        hallazgos += detectar_firmas(pagina, num)

        for texto, mapa in lineas:
            propios = detectar_en_linea(texto, mapa, num, lista_extra)
            if nlp is not None:
                cubierto = []
                for h in propios:
                    idx = texto.find(h.texto)
                    if idx >= 0:
                        cubierto.append((idx, idx + len(h.texto)))
                propios += detectar_con_ner(nlp, texto, mapa, num, cubierto)
            hallazgos += propios

        # quitar duplicados: dos detectores pueden dar el mismo rectángulo
        unicos: list[Hallazgo] = []
        for h in hallazgos:
            if any((h.rect & u.rect).get_area() > 0.5 * min(h.rect.get_area(),
                                                            u.rect.get_area()) for u in unicos):
                continue
            unicos.append(h)

        for h in unicos:
            stats.hallazgos.append(h)
            if simulacion:
                continue
            if h.metodo == "tabla-id":
                etiqueta = "[ID]"
            else:
                etiqueta = seudonimos.codigo(h.texto) if seudonimos else etiqueta_fija
            caja = pymupdf.Rect(h.rect) + (-margen, -margen, margen, margen)
            pagina.add_redact_annot(
                caja, text=etiqueta, fontname="helv",
                fontsize=max(4.5, min(8.0, caja.height * 0.62)),
                align=pymupdf.TEXT_ALIGN_CENTER, fill=(0, 0, 0), text_color=(1, 1, 1),
            )

        if not simulacion:
            pagina.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)

    if not simulacion and salida is not None:
        doc.set_metadata({})
        doc.del_xml_metadata()
        salida.parent.mkdir(parents=True, exist_ok=True)
        doc.save(salida, garbage=4, deflate=True, clean=True)
    doc.close()
    return stats


# ============================================================================
# CLI
# ============================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Anonimiza nombres de personas en PDFs de historias clínicas.")
    ap.add_argument("entrada", type=Path, help="PDF o carpeta con PDFs")
    ap.add_argument("-o", "--salida", type=Path, help="PDF o carpeta de salida")
    ap.add_argument("--identificadores", action="store_true",
                    help="tachar también cédula, N° de historia clínica, archivo, teléfono")
    ap.add_argument("--ner", action="store_true", help="añadir spaCy NER (entidad PER)")
    ap.add_argument("--lista", type=Path, help=".txt con nombres conocidos, uno por línea")
    ap.add_argument("--seudonimos", type=Path, metavar="MAPA.CSV",
                    help="usar códigos estables (PERSONA_001) y guardar el mapa")
    ap.add_argument("--etiqueta", default="[NOMBRE]", help="texto de reemplazo")
    ap.add_argument("--reporte", type=Path, help="CSV de auditoría con lo detectado")
    ap.add_argument("--sin-texto-en-reporte", action="store_true",
                    help="el reporte guarda solo página y método, nunca el nombre real")
    ap.add_argument("--simulacion", action="store_true", help="no escribe; solo lista")
    args = ap.parse_args(argv)

    lista_extra = set()
    if args.lista:
        lista_extra = {l.strip() for l in args.lista.read_text(encoding="utf-8").splitlines() if l.strip()}
    seudonimos = Seudonimos() if args.seudonimos else None

    if args.entrada.is_dir():
        destino_dir = args.salida or args.entrada.with_name(args.entrada.name + "_anon")
        pares = [(f, destino_dir / f.name) for f in sorted(args.entrada.glob("*.pdf"))]
    else:
        destino = args.salida or args.entrada.with_name(args.entrada.stem + "_anon.pdf")
        pares = [(args.entrada, destino)]
    if not pares:
        sys.exit("No se encontraron PDFs.")

    todos = []
    for origen, destino in pares:
        print(f"→ {origen.name}")
        stats = anonimizar_pdf(
            origen, None if args.simulacion else destino, usar_ner=args.ner,
            lista_extra=lista_extra, seudonimos=seudonimos, etiqueta_fija=args.etiqueta,
            simulacion=args.simulacion, con_identificadores=args.identificadores)
        for h in stats.hallazgos:
            todos.append((origen.name, h))
            visible = "<oculto>" if args.sin_texto_en_reporte else h.texto
            print(f"   p.{h.pagina} [{h.metodo}] {visible}")
        if stats.paginas_sin_texto:
            print(f"   ATENCIÓN: páginas sin capa de texto (escaneadas): "
                  f"{stats.paginas_sin_texto} → requieren OCR, quedaron intactas.", file=sys.stderr)
        if not args.simulacion:
            print(f"   guardado: {destino}")

    if args.reporte:
        with args.reporte.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["archivo", "pagina", "metodo", "texto_detectado"])
            for arch, h in todos:
                w.writerow([arch, h.pagina, h.metodo,
                            "<oculto>" if args.sin_texto_en_reporte else h.texto])
        print(f"Reporte: {args.reporte}")

    if seudonimos and not args.simulacion:
        with args.seudonimos.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["nombre_original", "codigo"])
            for nombre, cod in seudonimos.mapa.items():
                w.writerow([nombre, cod])
        print(f"Mapa de seudónimos: {args.seudonimos}  "
              f"(reidentifica pacientes: guárdalo aparte y cifrado)")

    print(f"\nTotal detectado: {len(todos)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
