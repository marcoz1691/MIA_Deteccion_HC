"""Configuración central. Todo lo que el usuario puede ajustar vive aquí."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    # --- Rasterizado / OCR -------------------------------------------------
    dpi: int = 300                     # 300 es el mínimo razonable para OCR
    motor: str = "tesseract"           # "tesseract" | "easyocr"
    idioma: str = "spa"                # código tesseract ("spa", "spa+eng")
    psm: int = 3                       # 3 = auto; 4 = columnas; 6 = bloque; 11 = disperso
    umbral_conf_palabra: float = 0.0   # descarta palabras OCR con confianza < umbral (0-100)
    usar_capa_texto: bool = True       # si la página ya trae texto, usarlo en vez de OCR
    deskew: bool = True                # corregir inclinación leve del escaneo

    # --- Detección ----------------------------------------------------------
    usar_ner: bool = True
    modelo_spacy: str = "es_core_news_md"
    fechas: str = "nacimiento"         # "todas" | "nacimiento" | "ninguna"
    redactar_junto_a_etiquetas: bool = True   # clave para formularios manuscritos
    ancho_max_etiqueta: float = 0.55   # fracción del ancho de página que se tacha a la derecha de una etiqueta
    alto_celda: float = 3.0            # en tablas: cuántas alturas de la cabecera se tachan POR DEBAJO de cada etiqueta

    # --- Zonas fijas (plantilla JSON) --------------------------------------
    zonas: Optional[Path] = None

    # --- Salida -------------------------------------------------------------
    buscable: bool = False             # re-OCR sobre la imagen ya tachada -> PDF con texto (seguro)
    calidad_jpeg: int = 80
    margen_px: int = 4                 # relleno alrededor de cada caja tachada
    etiquetar_cajas: bool = False      # escribir "[NOMBRE]" en blanco dentro del rectángulo

    # --- Revisión -----------------------------------------------------------
    revision: bool = True              # genera PNG con cajas + CSV de hallazgos
    volcar_ocr: bool = False           # escribe revision/<archivo>/pNNN_ocr.txt con el texto tal como lo leyó el OCR
    umbral_pagina_manuscrita: float = 55.0  # conf. media OCR por debajo => "posible manuscrito, revisar"
    min_palabras_pagina: int = 15      # menos palabras que esto => "revisar"

    etiquetas_a_redactar: set[str] = field(default_factory=lambda: {
        "NOMBRE", "CEDULA", "RUC", "TELEFONO", "EMAIL", "FECHA", "HC",
        "DIRECCION", "ZONA", "ETIQUETA", "EDAD",
    })


# Palabras que suelen ir impresas en formularios y a cuya derecha va el dato manuscrito.
# Se comparan sin tildes y en minúsculas contra el texto OCR.
ETIQUETAS_FORMULARIO: dict[str, str] = {
    # etiqueta (normalizada) -> tipo de dato que hay al lado
    "nombre": "NOMBRE",
    "nombres": "NOMBRE",
    "apellido": "NOMBRE",
    "apellidos": "NOMBRE",
    "paciente": "NOMBRE",
    "nombre del paciente": "NOMBRE",
    "apellidos y nombres": "NOMBRE",
    "nombres y apellidos": "NOMBRE",
    "representante": "NOMBRE",
    "responsable": "NOMBRE",
    "madre": "NOMBRE",
    "padre": "NOMBRE",
    "conyuge": "NOMBRE",
    "medico tratante": "NOMBRE",
    "medico responsable": "NOMBRE",
    "medico cirujano": "NOMBRE",
    "cirujano": "NOMBRE",
    "anestesiologo": "NOMBRE",
    "instrumentista": "NOMBRE",
    "ayudantes": "NOMBRE",
    "personal responsable": "NOMBRE",
    "profesional": "NOMBRE",
    "nombre profesional": "NOMBRE",
    "apellidos y nombres del paciente": "NOMBRE",
    "firma": "NOMBRE",
    "acompanante": "NOMBRE",
    "apellido paterno": "NOMBRE",
    "apellido materno": "NOMBRE",
    "primer apellido": "NOMBRE",
    "segundo apellido": "NOMBRE",
    "primer nombre": "NOMBRE",
    "segundo nombre": "NOMBRE",
    "nombres completos": "NOMBRE",
    "cedula": "CEDULA",
    "cedula de identidad": "CEDULA",
    "c.i.": "CEDULA",
    "ci": "CEDULA",
    "c.i": "CEDULA",
    "no. cedula": "CEDULA",
    "n° cedula": "CEDULA",
    "identificacion": "CEDULA",
    "ruc": "RUC",
    "telefono": "TELEFONO",
    "telefonos": "TELEFONO",
    "celular": "TELEFONO",
    "tel": "TELEFONO",
    "telf": "TELEFONO",
    "correo": "EMAIL",
    "email": "EMAIL",
    "e-mail": "EMAIL",
    "direccion": "DIRECCION",
    "domicilio": "DIRECCION",
    "barrio": "DIRECCION",
    "fecha de nacimiento": "FECHA",
    "fecha nacimiento": "FECHA",
    "f. nacimiento": "FECHA",
    "nacimiento": "FECHA",
    "historia clinica": "HC",
    "historia clinica n°": "HC",
    "hc": "HC",
    "h.c.": "HC",
    "hcu": "HC",
    "no. historia": "HC",
    "n° historia": "HC",
    "numero de historia": "HC",
    "numero de historia clinica": "HC",
    "no. de historia clinica": "HC",
    "nro. de historia clinica": "HC",
    "numero de cedula": "CEDULA",
    "no. de cedula": "CEDULA",
    "cedula de ciudadania": "CEDULA",
    "cedula o pasaporte": "CEDULA",
    "cedula de identidad o pasaporte": "CEDULA",
    "pasaporte": "CEDULA",
    "documento de identidad": "CEDULA",
    "numero de identificacion": "CEDULA",
    "numero unico de identificacion": "CEDULA",
    "numero de archivo": "HC",
    "numero hist. clinica unica": "HC",
    "numero hist clinica unica": "HC",
    "numero hist. clinica": "HC",
    "hist. clinica": "HC",
    "historia clinica unica": "HC",
    "numero de archivo": "HC",
    "numero hist. clinica unica": "HC",
    "numero hist clinica unica": "HC",
    "numero hist. clinica": "HC",
    "hist. clinica": "HC",
    "historia clinica unica": "HC",
    "n° archivo": "HC",
}

# Etiquetas de mayor longitud primero, para que "fecha de nacimiento" gane a "nacimiento".
ETIQUETAS_ORDENADAS = sorted(ETIQUETAS_FORMULARIO, key=len, reverse=True)
