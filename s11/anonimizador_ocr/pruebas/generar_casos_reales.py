"""Reproduce con datos FICTICIOS los patrones que fallaron en formularios reales:
  pág. 1: "PACIENTE ___" y "MEDICO TRATANTE ___" manuscritos a la derecha, sin dos puntos;
          firma de personal con nombre encima de la etiqueta "Firma"
  pág. 2: fila de cabeceras numerada "7. APELLIDO PATERNO | APELLIDO MATERNO | NOMBRES | EDAD"
          con valores manuscritos debajo; "NÚMERO DE HISTORIA CLÍNICA:" con número manuscrito
          que se extiende muy a la derecha
  pág. 3: bloques de firma: nombre manuscrito ENCIMA de la etiqueta "Apellidos y nombres"
  pág. 4: "CEDULA O PASAPORTE: ___" manuscrito; "CIRUJANO"/"ANESTESIOLOGO" con nombre
          manuscrito debajo; "HISTORIA CLINICA" con número manuscrito al lado
  pág. 5: tabla impresa con "NUMERO HIST. CLINICA UNICA" / "NUMERO DE ARCHIVO" y valores
          impresos debajo, algo a la izquierda de la cabecera
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    import fitz
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent))
from pruebas.generar_ejemplo import W, H, fuente, escribir_manuscrito, garabato, escanear  # noqa: E402

random.seed(11)


def p1_checkout() -> Image.Image:
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fL = fuente(46)
    d.text((300, 150), "HOJA DE CHECKOUT", fill="black", font=fuente(64))
    d.text((240, 420), "PACIENTE", fill="black", font=fL)
    escribir_manuscrito(d, (560, 400), "Caza Barcia Luis Ramos", 62)
    d.line([540, 490, 1700, 490], fill="black", width=2)
    d.text((1800, 420), "Habitación", fill="black", font=fL)
    escribir_manuscrito(d, (2100, 400), "S/P", 60)
    d.text((240, 580), "MEDICO TRATANTE", fill="black", font=fL)
    escribir_manuscrito(d, (780, 560), "Dr. Santiago Davila", 62)
    d.line([760, 650, 1700, 650], fill="black", width=2)
    d.text((240, 800), "Personal responsable Checkin Admisiones", fill="black", font=fuente(38))
    d.text((1300, 790), "GISSETH AYALA", fill="black", font=fuente(40))
    escribir_manuscrito(d, (1900, 780), "GA", 60)
    # firma con nombre encima de la etiqueta
    escribir_manuscrito(d, (1500, 1080), "Johanna Jimenez", 56)
    d.line([1450, 1170, 2100, 1170], fill="black", width=2)
    d.text((1700, 1185), "Firma", fill="black", font=fuente(36))
    return escanear(img)


def p2_consentimiento() -> Image.Image:
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fC, fL = fuente(36), fuente(40)
    d.text((300, 150), "CONSENTIMIENTO INFORMADO", fill="black", font=fuente(58))
    d.text((240, 300), "4. NÚMERO DE HISTORIA CLÍNICA:", fill="black", font=fL)
    escribir_manuscrito(d, (1650, 285), "0 0 4 5 8 7 1 6", 60)   # llega muy a la derecha
    d.rectangle([220, 460, 2380, 640], outline="black", width=3)
    cab = [("7. APELLIDO PATERNO", "QUISHPE", 250), ("APELLIDO MATERNO", "MORALES", 850),
           ("NOMBRES", "ROSA ELENA", 1430), ("EDAD", "56", 2050)]
    for etiqueta, valor, x in cab:
        d.text((x, 480), etiqueta, fill="black", font=fC)
        escribir_manuscrito(d, (x - 30, 550), valor, 58)         # empieza ANTES de la cabecera
        d.line([x - 45, 460, x - 45, 640], fill="black", width=2)
    return escanear(img)


def p3_firmas() -> Image.Image:
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fC = fuente(36)
    d.text((300, 150), "DECLARACIÓN DE CONSENTIMIENTO", fill="black", font=fuente(56))
    y = 500
    for nombre in ("Quishpe Morales Rosa", "Santiago Davila V", "Melendez Ona Sergio"):
        escribir_manuscrito(d, (420, y), nombre, 64)
        d.line([380, y + 100, 1500, y + 100], fill="black", width=2)
        d.text((620, y + 115), "Apellidos y nombres", fill="black", font=fC)
        y += 320
    return escanear(img)


def p4_anestesia() -> Image.Image:
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fC = fuente(34)
    d.text((300, 130), "REGISTRO DE ANESTESIA", fill="black", font=fuente(56))
    d.text((240, 320), "CEDULA O PASAPORTE:", fill="black", font=fC)
    escribir_manuscrito(d, (900, 300), "1712345675", 60)
    d.text((1800, 320), "HISTORIA CLINICA", fill="black", font=fC)
    escribir_manuscrito(d, (1820, 380), "12232", 62)
    d.text((240, 480), "APELLIDOS", fill="black", font=fC)
    escribir_manuscrito(d, (300, 560), "Caza  Barcia  Luis  Ramiro", 62)
    d.rectangle([220, 700, 2380, 1000], outline="black", width=3)
    d.text((240, 720), "CIRUJANO", fill="black", font=fC)
    escribir_manuscrito(d, (280, 790), "Dr. Davila S.", 60)
    d.text((1300, 720), "AYUDANTES", fill="black", font=fC)
    d.text((240, 880), "ANESTESIOLOGO", fill="black", font=fC)
    escribir_manuscrito(d, (300, 940), "Dr. Melendez D.", 58)
    return escanear(img)


def p5_evolucion() -> Image.Image:
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fC, fV = fuente(32), fuente(38)
    d.text((300, 150), "EVOLUCION - HOSPITALARIA", fill="black", font=fuente(56))
    d.rectangle([220, 380, 2380, 560], outline="black", width=3)
    cab1 = [("INSTITUCION DEL SISTEMA", "RED COMPLEMENTARIA", 240),
            ("NUMERO HIST. CLINICA UNICA", "1312466566", 1150),
            ("NUMERO DE ARCHIVO", "12232", 1900)]
    for etiqueta, valor, x in cab1:
        d.text((x, 400), etiqueta, fill="black", font=fC)
        d.text((x - 25, 480), valor, fill="black", font=fV)      # valor impreso, algo a la izquierda
        d.line([x - 40, 380, x - 40, 560], fill="black", width=2)
    d.rectangle([220, 640, 2380, 820], outline="black", width=3)
    cab2 = [("PRIMER APELLIDO", "QUISHPE", 240), ("SEGUNDO APELLIDO", "MORALES", 800),
            ("PRIMER NOMBRE", "ROSA", 1360), ("SEGUNDO NOMBRE", "ELENA", 1820), ("EDAD", "56", 2260)]
    for etiqueta, valor, x in cab2:
        d.text((x, 660), etiqueta, fill="black", font=fC)
        d.text((x - 20, 740), valor, fill="black", font=fV)
        d.line([x - 35, 640, x - 35, 820], fill="black", width=2)
    d.text((240, 950), "PACIENTE MASCULINO DE 56 AÑOS, MESTIZO, NACIDO Y RESIDENTE EN QUITO.", fill="black", font=fuente(36))
    d.text((240, 1030), "MOTIVO DE CONSULTA: CONTROL ENDOSCOPICO.", fill="black", font=fuente(36))
    return escanear(img)


def main():
    doc = fitz.open()
    for img in (p1_checkout(), p2_consentimiento(), p3_firmas(), p4_anestesia(), p5_evolucion()):
        p = doc.new_page(width=595, height=842)
        tmp = AQUI / "_tmp2.jpg"
        img.save(tmp, quality=75)
        p.insert_image(p.rect, filename=str(tmp))
        tmp.unlink()
    salida = AQUI / "casos_reales.pdf"
    doc.save(salida)
    print("Generado:", salida)


if __name__ == "__main__":
    main()
