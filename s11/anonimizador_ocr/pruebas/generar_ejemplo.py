"""Genera `pruebas/ejemplo_escaneado.pdf` con datos FICTICIOS para probar el anonimizador:
  pág. 1: formulario con etiquetas impresas y valores "manuscritos" (imagen, sin texto)
  pág. 2: nota de evolución impresa con identificadores dentro de la prosa (imagen, sin texto)
  pág. 3: formulario con valores manuscritos ilegibles (garabatos)
  pág. 4: página con capa de texto real (PDF no escaneado)
"""
from __future__ import annotations

import random
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # PyMuPDF < 1.24
    import fitz
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = Path(__file__).parent
random.seed(7)

W, H = 2480, 3508   # A4 a 300 dpi


def fuente(tam: int, cursiva=False):
    for nombre in (["DejaVuSerif-Italic.ttf", "FreeSerifItalic.ttf"] if cursiva else ["DejaVuSans.ttf", "FreeSans.ttf"]):
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def escribir_manuscrito(d: ImageDraw.ImageDraw, xy, texto, tam=54):
    """Simula escritura a mano: letra cursiva con desplazamientos y tamaño aleatorios por carácter."""
    x, y = xy
    for ch in texto:
        f = fuente(tam + random.randint(-6, 8), cursiva=True)
        dx, dy = random.randint(-2, 2), random.randint(-6, 6)
        d.text((x + dx, y + dy), ch, fill=(20, 30, 110), font=f)
        x += f.getlength(ch) * random.uniform(0.85, 1.05)


def escanear(img: Image.Image) -> Image.Image:
    """Ruido + ligera rotación + desenfoque: parecido a un escaneo real."""
    img = img.rotate(random.uniform(-1.2, 1.2), resample=Image.BICUBIC, expand=False, fillcolor="white")
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    ruido = Image.effect_noise((W, H), 18).convert("L")
    return Image.blend(img.convert("L"), ruido, 0.08).convert("RGB")


def pagina_formulario() -> Image.Image:
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fT, fL = fuente(64), fuente(44)
    d.text((300, 150), "MINISTERIO DE SALUD PÚBLICA — FORMULARIO 001", fill="black", font=fT)
    d.text((300, 240), "ADMISIÓN — DATOS DEL PACIENTE", fill="black", font=fL)
    d.rectangle([200, 330, 2280, 1500], outline="black", width=3)

    filas = [
        ("Apellidos y Nombres:", "Quishpe Morales Rosa Elena", 420),
        ("Cédula:", "1712345675", 560),
        ("Fecha de nacimiento:", "14/03/1968", 700),
        ("Teléfono:", "0998765432", 840),
        ("Dirección:", "Av. Amazonas N32-45 y Colón, Quito", 980),
        ("Representante:", "Carlos Quishpe", 1120),
    ]
    for etiqueta, valor, y in filas:
        d.text((240, y), etiqueta, fill="black", font=fL)
        escribir_manuscrito(d, (240 + fL.getlength(etiqueta) + 40, y - 10), valor)
        d.line([240, y + 70, 2240, y + 70], fill="black", width=2)

    d.text((240, 1260), "Historia Clínica N°:", fill="black", font=fL)
    escribir_manuscrito(d, (700, 1250), "0045871")
    d.text((1300, 1260), "Edad:", fill="black", font=fL)
    escribir_manuscrito(d, (1450, 1250), "56 años")

    d.text((240, 1600), "MOTIVO DE CONSULTA:", fill="black", font=fL)
    escribir_manuscrito(d, (240, 1680), "Dolor abdominal de 3 dias de evolucion,", 50)
    escribir_manuscrito(d, (240, 1760), "fiebre y vomito. Niega alergias.", 50)
    d.text((240, 1950), "Médico tratante:", fill="black", font=fL)
    escribir_manuscrito(d, (640, 1940), "Dr. Andres Villacis")
    return escanear(img)


def garabato(d: ImageDraw.ImageDraw, x, y, ancho, alto=60):
    """Trazo ilegible tipo letra de médico: el OCR no debe poder leerlo."""
    pts = []
    cx = x
    while cx < x + ancho:
        pts.append((cx, y + random.randint(0, alto)))
        cx += random.randint(8, 22)
    d.line(pts, fill=(25, 25, 90), width=4, joint="curve")


def pagina_manuscrita_ilegible() -> Image.Image:
    """Formulario con valores manuscritos ILEGIBLES: solo puede protegerse tachando junto a las etiquetas."""
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fL = fuente(44)
    d.text((300, 150), "HOJA DE EMERGENCIA — FORM. 008", fill="black", font=fuente(60))
    for etiqueta, y in (("Nombre:", 400), ("Cédula:", 540), ("Teléfono:", 680), ("Dirección:", 820)):
        d.text((240, y), etiqueta, fill="black", font=fL)
        garabato(d, 240 + fL.getlength(etiqueta) + 40, y - 5, random.randint(500, 1100))
        d.line([240, y + 70, 2240, y + 70], fill="black", width=2)
    d.text((240, 1000), "Evolución:", fill="black", font=fL)
    for i in range(6):
        garabato(d, 240, 1100 + i * 90, 1900, 50)
    return escanear(img)


def pagina_tabla() -> Image.Image:
    """Cabeceras de tabla (estilo Form. 008 MSP) con el dato DEBAJO de cada etiqueta."""
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fC, fV = fuente(38), fuente(44)
    d.text((300, 150), "ESTABLECIMIENTO DE SALUD — ADMISIÓN", fill="black", font=fuente(60))

    # fila 1: nombres (valores impresos, como los llena el sistema de admisión)
    cab1 = [("APELLIDO PATERNO", "QUISHPE", 240), ("APELLIDO MATERNO", "MORALES", 800),
            ("PRIMER NOMBRE", "ROSA", 1360), ("SEGUNDO NOMBRE", "ELENA", 1880)]
    d.rectangle([220, 380, 2380, 560], outline="black", width=3)
    for etiqueta, valor, x in cab1:
        d.text((x, 400), etiqueta, fill="black", font=fC)
        d.text((x, 470), valor, fill="black", font=fV)
        d.line([x - 20, 380, x - 20, 560], fill="black", width=2)

    # fila 2: cédula e historia clínica, valores MANUSCRITOS bajo la cabecera
    cab2 = [("CÉDULA", "1712345675", 240), ("HISTORIA CLÍNICA", "0045871", 1100), ("SEXO", "F", 1900)]
    d.rectangle([220, 640, 2380, 830], outline="black", width=3)
    for etiqueta, valor, x in cab2:
        d.text((x, 660), etiqueta, fill="black", font=fC)
        escribir_manuscrito(d, (x, 730), valor)
        d.line([x - 20, 640, x - 20, 830], fill="black", width=2)
    return escanear(img)


def pagina_tabla_apilada() -> Image.Image:
    """Cabeceras partidas en dos renglones y una cabecera 'mal impresa' (simula OCR con errores)."""
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fC, fV = fuente(36), fuente(46)
    d.text((300, 150), "FORMULARIO DE ADMISIÓN — HOSPITAL", fill="black", font=fuente(58))
    d.rectangle([220, 380, 2380, 700], outline="black", width=3)
    celdas = [("APELLIDO", "PATERNO", "QUISHPE", 260), ("APELLIDO", "MATERNO", "MORALES", 800),
              ("PRIMER", "NOMBRE", "ROSA", 1340), ("SEGUNDO", "NOMBRE", "ELENA", 1880)]
    for arriba, abajo, valor, x in celdas:
        d.text((x, 400), arriba, fill="black", font=fC)
        d.text((x, 450), abajo, fill="black", font=fC)
        d.text((x, 540), valor, fill="black", font=fV)
        d.line([x - 30, 380, x - 30, 700], fill="black", width=2)
    # cabecera con "error de imprenta" para probar la coincidencia aproximada + valor manuscrito grande
    d.rectangle([220, 780, 2380, 1080], outline="black", width=3)
    d.text((260, 800), "CEDLILA DE CIUDADANIA", fill="black", font=fC)   # ~ 'cedula de ciudadania'
    escribir_manuscrito(d, (300, 880), "1712345675", 78)
    d.text((1340, 800), "HISTORIA CLINICA", fill="black", font=fC)
    escribir_manuscrito(d, (1400, 880), "0045871", 78)
    return escanear(img)


def pagina_tabla_manuscrita() -> Image.Image:
    """La prueba dura: mismas cabeceras de tabla pero TODO el dato escrito a mano, con letra
    grande que baja mucho y garabatos que ensucian la zona (caso real de historia clínica)."""
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fC = fuente(36)
    d.text((300, 150), "REFERENCIA — DATOS DEL PACIENTE", fill="black", font=fuente(58))

    # fila de cabeceras apiladas, valores manuscritos grandes y descolgados
    d.rectangle([220, 380, 2380, 900], outline="black", width=3)
    celdas = [("APELLIDO", "PATERNO", "Quishpe", 260), ("APELLIDO", "MATERNO", "Morales", 800),
              ("PRIMER", "NOMBRE", "Rosa", 1340), ("SEGUNDO", "NOMBRE", "Elena", 1880)]
    for arriba, abajo, valor, x in celdas:
        d.text((x, 400), arriba, fill="black", font=fC)
        d.text((x, 450), abajo, fill="black", font=fC)
        escribir_manuscrito(d, (x, 620), valor, 92)          # bien por debajo de la cabecera
        garabato(d, x, 540, 380, 40)                          # tachones/ruido sobre la celda
    # segunda fila: cédula manuscrita en una sola cabecera
    d.rectangle([220, 980, 2380, 1420], outline="black", width=3)
    d.text((260, 1000), "CEDULA", fill="black", font=fC)
    escribir_manuscrito(d, (300, 1150), "1712345675", 100)
    d.text((1340, 1000), "HISTORIA CLINICA", fill="black", font=fC)
    escribir_manuscrito(d, (1400, 1180), "0045871", 100)
    garabato(d, 260, 1080, 900, 45)
    return escanear(img)


def pagina_evolucion() -> Image.Image:
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fT, fB = fuente(60), fuente(42)
    d.text((300, 200), "NOTA DE EVOLUCIÓN — HOSPITAL GENERAL DEL SUR", fill="black", font=fT)
    lineas = [
        "Paciente: Rosa Elena Quishpe Morales      HC: 0045871      Fecha: 22/08/2026",
        "CI 1712345675. Femenina de 56 años, nacida el 14 de marzo de 1968.",
        "Acude acompañada de su hijo Carlos Quishpe (cel. 099 876 5432).",
        "Refiere dolor abdominal difuso. Niega alergias a medicamentos.",
        "Se indica paracetamol 500 mg cada 8 horas y control en 48 horas.",
        "Antecedentes: hipertensión arterial en tratamiento con losartán.",
        "Correo de contacto: rosa.quishpe68@gmail.com. Dirección: Av. Amazonas N32-45, Quito.",
        "Evaluado por Dra. María Fernanda Torres, Medicina Interna.",
    ]
    y = 400
    for l in lineas:
        d.text((240, y), l, fill="black", font=fB)
        y += 110
    return escanear(img)


def main():
    doc = fitz.open()
    for img in (pagina_formulario(), pagina_tabla(), pagina_tabla_apilada(), pagina_tabla_manuscrita(), pagina_evolucion(), pagina_manuscrita_ilegible()):
        p = doc.new_page(width=595, height=842)
        ruta_tmp = AQUI / "_tmp.jpg"
        img.save(ruta_tmp, quality=75)
        p.insert_image(p.rect, filename=str(ruta_tmp))
        ruta_tmp.unlink()
    # página 3: texto real
    p = doc.new_page(width=595, height=842)
    p.insert_text((60, 80), "EPICRISIS", fontsize=16)
    texto = ("Paciente Rosa Elena Quishpe Morales, cédula 1712345675, HC 0045871.\n"
             "Ingresa el 20/08/2026 por dolor abdominal. Evoluciona favorablemente.\n"
             "Alta el 22/08/2026. Contacto: 0998765432. Responsable: Carlos Quishpe.")
    p.insert_text((60, 120), texto, fontsize=11)
    salida = AQUI / "ejemplo_escaneado.pdf"
    doc.save(salida)
    print("Generado:", salida)


if __name__ == "__main__":
    main()
