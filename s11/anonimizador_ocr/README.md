# Anonimizador de historias clínicas escaneadas (OCR + manuscrito) — CITIMED

Toma PDFs escaneados (o imágenes) de historias clínicas, reconoce el texto con OCR, detecta
identificadores del paciente (adaptado a Ecuador) y devuelve un PDF nuevo con esos datos
tachados **a nivel de píxel**, más material para revisión humana.

Funciona 100 % en local, sin enviar nada a internet.

## Cómo protege el dato manuscrito

El OCR convencional (Tesseract) lee bien lo impreso y mal lo escrito a mano. Por eso el
anonimizador combina cuatro capas, de más a menos dependiente del OCR:

| Capa | Qué hace | Sirve para |
|---|---|---|
| **Reglas** (`deteccion.py`) | Cédula (con dígito verificador), RUC, celular/fijo, correo, N° de historia clínica, fechas de nacimiento, edad ≥ 90, direcciones. Tolera confusiones de OCR (O/0, l/1, `@`→`0`). | Texto impreso y manuscrito legible |
| **Contexto + NER** | "Paciente: …", "Representante: …", "Dra. …" y nombres sueltos vía spaCy `es_core_news_md`. | Nombres dentro de prosa |
| **Junto a etiquetas** (`zonas.py`) | Las *etiquetas* van impresas y sí se leen; el *valor* no siempre. Se tacha a la **derecha** de cada etiqueta ("Cédula: ____") o **debajo** cuando la página es una tabla (cabeceras con el dato en la celda inferior). Tolera cabeceras mal leídas por el OCR y partidas en dos renglones. | **Manuscrito** y celdas de tabla |
| **Tinta** (`mascara_tinta`) | La posición del valor se decide mirando los píxeles escritos (sin las rayas de tabla): a la **derecha** de la etiqueta, **debajo** (celda de tabla) o **encima** (bloques de firma, donde el nombre va sobre la raya y la etiqueta impresa debajo). La caja se estira en las cuatro direcciones siguiendo la tinta, así cubre letra grande, valores descolgados o que empiezan antes de la cabecera. | **Manuscrito ilegible**, celdas y firmas |
| **Zonas fijas** (plantilla JSON) | Rectángulos en coordenadas relativas que se tachan siempre (cabecera del Form. 008, casilla de HC…). | Formularios estandarizados, aunque el OCR no lea nada |

Además, cada página cuya confianza OCR media sea baja o con pocas palabras se marca en
`paginas_a_revisar.csv` como **probable manuscrito → revisar a mano**. Esto es deliberado: con
letra de médico ningún OCR gratuito garantiza recall del 100 %, así que la herramienta hace
el trabajo pesado y deja al humano las páginas dudosas, con imágenes ya marcadas para que la
revisión sea rápida.

## Seguridad del PDF de salida

- El PDF final se construye **desde cero con las imágenes tachadas**: no arrastra la capa de
  texto original, anotaciones, adjuntos ni metadatos (autor, fechas, software).
- Con `--buscable` se añade una capa de texto haciendo OCR **sobre la imagen ya tachada**, así
  que no puede contener lo que se tachó.
- Las páginas que ya traían texto (PDF no escaneado) también se rasterizan y tachan en píxel.

## Instalación (Windows, Python 3.12)

```powershell
# 1. Tesseract (binario)
#    Descarga el instalador de https://github.com/UB-Mannheim/tesseract/wiki
#    Durante la instalación marca "Additional language data" -> Spanish,
#    o copia spa.traineddata en C:\Program Files\Tesseract-OCR\tessdata
#    Añade C:\Program Files\Tesseract-OCR al PATH (o define en cli.py pytesseract.pytesseract.tesseract_cmd).

# 2. Paquetes Python
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pip install https://github.com/explosion/spacy-models/releases/download/es_core_news_md-3.8.0/es_core_news_md-3.8.0-py3-none-any.whl

# 3. Comprobar
python -m anonimizador_ocr --entrada x --salida x --solo-comprobar
```

En Linux/Mac: `sudo apt install tesseract-ocr tesseract-ocr-spa` (o `brew install tesseract tesseract-lang`).

Para la máquina sin red de CITIMED: descarga el instalador de Tesseract, `spa.traineddata`,
las ruedas de `requirements.txt` (`pip download -r requirements.txt -d ruedas/`) y la rueda del
modelo spaCy en una máquina con internet, y luego `pip install --no-index --find-links ruedas/ ...`.

## Uso

```powershell
# Probar primero con el ejemplo sintético (datos ficticios)
python pruebas\generar_ejemplo.py
python -m anonimizador_ocr --entrada pruebas\ejemplo_escaneado.pdf --salida pruebas\salida

# Lote real (recorre subcarpetas)
python -m anonimizador_ocr --entrada historias\ --salida salidas\ --buscable

# Formulario estandarizado con plantilla de zonas
python -m anonimizador_ocr --entrada form008\ --salida salidas\ --zonas plantillas\form008.json
```

Salida en `salidas/`:

```
salidas/
  hc_001_anon.pdf              PDF anonimizado
  hallazgos.csv                qué se tachó, en qué página, por qué (regex / contexto / ner / etiqueta / zona)
  paginas_a_revisar.csv        páginas con OCR pobre (probable manuscrito) o sin ningún hallazgo
  informe.json                 todo lo anterior en detalle
  revision/hc_001/
     p001_revision.png         página ORIGINAL con las cajas en color y su etiqueta -> para validar
     p001_anonimizada.png      página tachada
```

### Opciones útiles

| Opción | Efecto |
|---|---|
| `--fechas todas\|nacimiento\|ninguna` | Por defecto solo se tacha la fecha de nacimiento (las fechas de atención suelen hacer falta para investigación). |
| `--psm 4` / `--psm 11` | Segmentación de Tesseract: 4 para formularios en columnas, 11 para texto disperso. Pruébalo si el OCR se salta campos. |
| `--ancho-etiqueta 0.4` | Fracción del ancho de página que se tacha a la derecha de una etiqueta (por defecto 0.55). |
| `--alto-celda 4` | En tablas: cuántas alturas de la cabecera se tachan por debajo de cada etiqueta (por defecto 3). Súbelo si el dato de la celda queda a medio tapar. |
| `--volcar-ocr` | Guarda `revision/<archivo>/pNNN_ocr.txt` con el texto crudo que leyó el OCR: útil para ver cómo leyó realmente cada cabecera y añadir variantes a `ETIQUETAS_FORMULARIO`. |
| `--sin-etiquetas` | Desactiva el tachado junto a etiquetas (para prosa sin formulario). |
| `--motor easyocr` | Motor alternativo, algo mejor con manuscrito legible. Pesado (torch). `pip install easyocr`; descarga sus pesos la primera vez. |
| `--etiquetar` | Escribe `[NOMBRE]`, `[CEDULA]`… dentro de cada rectángulo. |
| `--dpi 400` | Más resolución si los escaneos son de mala calidad (más lento). |
| `--umbral-manuscrito 65` | Sube el umbral para que más páginas vayan a revisión. |

## Flujo de trabajo recomendado

1. Corre 3-5 historias, abre `revision/*/p*_revision.png` y `hallazgos.csv`. Ajusta `--psm`,
   `--ancho-etiqueta` y, si el formulario es fijo, crea una plantilla de zonas (mide las
   coordenadas en un PNG de revisión y divídelas por el ancho/alto en píxeles).
2. Añade a `config.py → ETIQUETAS_FORMULARIO` las etiquetas propias de tus formularios
   ("Nombre del RN", "Cédula del representante"…) y a `deteccion.py → STOP_NER` las palabras que
   spaCy marque como persona sin serlo.
3. Corre el lote completo. Revisa **todas** las páginas de `paginas_a_revisar.csv` y una muestra
   aleatoria del resto (p. ej. 10 %) antes de entregar nada.
4. Guarda `hallazgos.csv` e `informe.json` como evidencia del proceso de de-identificación.

## Límites que conviene tener claros

- Tesseract con manuscrito real tiene recall bajo; por eso existen las capas de etiquetas,
  zonas y revisión. Un nombre escrito a mano en medio de la nota de evolución (fuera de un
  campo etiquetado) **puede escaparse**: solo la revisión humana o un modelo de manuscrito
  (TrOCR / PaddleOCR, ambos ejecutables en local) lo cubrirían.
- Se prioriza el recall: habrá sobre-tachado (p. ej. una etiqueta o la palabra siguiente).
  Es el lado seguro del error.
- Firmas, sellos, códigos de barras y fotos no se detectan: usa zonas fijas para ellos.
- Los nombres de médicos también se tachan (son datos personales); si el proyecto los necesita,
  quita `Dr.|Dra.|Médico|Tratante` de `CONTEXTO_NOMBRE` y filtra `origen == ner` con cuidado.

## Estructura

```
anonimizador_ocr/
  config.py      parámetros y diccionario de etiquetas de formulario
  ocr.py         deskew, preprocesado, motores tesseract / easyocr / capa de texto
  mapeo.py       texto plano <-> cajas de píxeles
  deteccion.py   reglas Ecuador + contexto + NER
  zonas.py       zonas fijas (JSON) y tachado junto a etiquetas
  redaccion.py   tachado en píxel, imagen de revisión, construcción del PDF
  pipeline.py    orquestación, informes CSV/JSON
  cli.py         línea de comandos
plantillas/ejemplo_zonas.json
pruebas/generar_ejemplo.py     genera un PDF escaneado sintético con datos FICTICIOS
herramientas/medir_zonas.py    dibuja zonas fijas con el ratón sobre una página y guarda la plantilla JSON
pruebas/test_deteccion.py      pruebas rápidas de las reglas
```
