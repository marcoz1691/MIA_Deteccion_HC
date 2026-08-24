# Anonimizador de historias clínicas — Proyecto CITIMED

Herramienta para **anonimizar (de-identificar) historias clínicas** en **texto** y
**PDF**, en español y adaptada a los identificadores del **Ecuador**. Implementa el
**Servicio de Anonimización (②)** de la arquitectura MLOps del proyecto: prepara los
datos de CITIMED para poder usarlos en el entrenamiento y la evaluación sin exponer
información del paciente.

> ⚠️ **Seguridad y ética.** La de-identificación automática **reduce** el riesgo, no lo
> elimina por completo. Ejecute esta herramienta **localmente** en CITIMED; **no suba
> historias clínicas reales a servicios externos**. Antes de liberar los datos, haga
> **revisión humana por muestreo**. Por defecto la anonimización es **irreversible**
> (no se guarda ningún mapa de re-identificación).

---

## 1. Enfoque (modelo híbrido)

La detección de datos personales (PHI) combina dos motores, como recomienda la
literatura de de-identificación clínica:

1. **Reglas** (`reglas_ec.py`) — identificadores estructurados del Ecuador, con **alta
   precisión**:
   - **Cédula** (10 dígitos con **validación de dígito verificador**, y además por
     contexto —`Cédula: …`— aunque el dígito falle por error de tipeo/OCR),
   - **RUC**, **teléfono** (+593 / 0X…), **email**, **URL/IP**,
   - **fechas** (varios formatos), **nº de historia clínica / afiliación IESS**,
   - **edad ≥ 90 años**.
2. **NER** (spaCy `es_core_news_md`) — entidades que las reglas no capturan:
   **nombres de personas (PER)**, **lugares (LOC)** y **organizaciones (ORG)**.

### Tratamiento del PHI
- **Pseudonimización consistente:** cada persona recibe una etiqueta estable
  (`[PACIENTE_1]`, `[MEDICO_1]`, `[PERSONA_1]`, `[LUGAR_1]`…). El **subtipo**
  (paciente/médico) se decide por el honorífico del contexto (`Dr.`, `Dra.`,
  `paciente`), y las **menciones sueltas del apellido** heredan la misma etiqueta.
- **Fechas:** se **desplazan** un offset constante por documento (no se borran), de
  modo que se **preservan los intervalos entre eventos** —clave para detectar
  inconsistencias temporales— sin revelar las fechas reales. (Opción `--no-desplazar-fechas`
  para reemplazarlas por `[FECHA]`.)
- **PDF:** redacción **real** con PyMuPDF (`apply_redactions`): el texto se **elimina**
  del PDF —no queda extraíble—, con recuadros negros sobre el PHI.
- **Auditoría:** se genera `auditoria_anonimizacion.json` con **conteos por tipo** y un
  **hash salado** de cada valor (nunca el valor en claro), útil para el comité de ética.

## 2. Instalación

```bash
pip install -r requirements.txt
python -m spacy download es_core_news_md
```

## 3. Uso

```bash
# Un archivo de texto
python anonimizador.py --entrada historia.txt --salida salidas/

# Un PDF (redacción real)
python anonimizador.py --entrada historia.pdf --salida salidas/

# Una carpeta completa (lote: .txt, .pdf, .csv)
python anonimizador.py --entrada carpeta_historias/ --salida salidas/

# Opciones
python anonimizador.py --entrada h.txt --no-desplazar-fechas   # fechas -> [FECHA]
python anonimizador.py --entrada h.txt --sin-ner               # solo reglas (sin spaCy)
python anonimizador.py --entrada h.txt --salt "clave-secreta"  # sal propia
```

## 4. Demostración incluida

`ejemplos/historia_ejemplo.sintetico.txt` es una historia **sintética** (sin datos reales).
Al ejecutarla se obtiene, sin fugas: cédula, teléfono, correo, nº de historia, IESS y
nombres redactados; fechas desplazadas; y el contenido clínico (diagnóstico,
tratamiento, síntomas) **intacto**. No commitear historias con PHI aparente; use
`historia_ejemplo.txt` solo de forma local (está en `.gitignore` del repo principal).

## 5. Categorías detectadas

| Categoría | Motor | Reemplazo |
|---|---|---|
| Cédula | regla (checksum + contexto) | `[CEDULA]` |
| RUC | regla | `[RUC]` |
| Teléfono | regla | `[TELEFONO]` |
| Email | regla | `[EMAIL]` |
| Nº historia / IESS | regla (contexto) | `[NUM_HISTORIA]` |
| Fecha | regla | fecha desplazada |
| Edad ≥ 90 | regla | `[EDAD_90]` |
| URL / IP | regla | `[URL]` / `[IP]` |
| Persona | NER + contexto | `[PACIENTE_n]` / `[MEDICO_n]` / `[PERSONA_n]` |
| Lugar / Organización | NER | `[LUGAR_n]` / `[ORG_n]` |

## 6. Limitaciones y recomendaciones

- **No es 100 % automático.** Puede fallar en nombres poco frecuentes, con errores
  ortográficos o partidos por saltos de línea; y puede sobre-redactar (marcar de más).
  Se recomienda **revisión humana por muestreo** y ajustar las reglas/gazetteers al
  vocabulario real de CITIMED.
- **PDF escaneado (imagen).** Requiere **OCR previo** (p. ej. `tesseract-ocr` +
  `pytesseract`, o `ocrmypdf`) para convertirlo en texto con coordenadas; sin OCR, las
  páginas-imagen no se redactan. (Integración de OCR: trabajo pendiente.)
- **Fechas.** El desplazamiento preserva intervalos entre fechas; las **edades** en
  texto se conservan tal cual, por lo que una edad podría no cuadrar con una fecha de
  nacimiento desplazada (no es una fuga, pero conviene tenerlo presente).
- **Alternativa.** Para producción a gran escala puede evaluarse
  **Microsoft Presidio** con estas mismas reglas como *recognizers* personalizados.

## 7. Reproducibilidad
`--salt` fija tanto los hashes de auditoría como el desplazamiento de fechas; con la
misma sal, el resultado es reproducible. Versiones fijadas en `requirements.txt`
(spaCy 3.8.15, es_core_news_md 3.8.0, PyMuPDF 1.28.2).
