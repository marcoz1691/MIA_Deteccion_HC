# Anexo ético: protección de datos personales de salud en el proyecto MIA_Deteccion_HC

**Proyecto:** Detección automática de inconsistencias en historias clínicas
**Programa:** Maestría en Inteligencia Artificial Aplicada — Universidad de las Américas (UDLA), Ecuador
**Integrantes:** Patricio Bayas Meza, José Puebla Paladines, Marco Zurita Rojas
**Institución de datos clínicos:** CITIMED (dominio odontología, Ecuador)
**Entrega:** S11 — versión final

---

## 1. Propósito y alcance de este anexo

Este anexo documenta las salvaguardas éticas y de protección de datos que rigen el tratamiento de
historias clínicas reales en el proyecto. Cubre tres frentes: el marco normativo al que se alinea la
de-identificación, el protocolo técnico y humano con que se ejecuta, y los límites que el equipo
declara de manera explícita para que ningún lector atribuya al sistema garantías que no posee.

El alcance del anexo es el tratamiento de datos con destino **académico y de investigación**: el
corpus de trabajo se emplea para evaluar un prototipo de detección de inconsistencias, no para
soportar decisiones asistenciales ni administrativas sobre pacientes concretos. Dos documentos
complementan este anexo y deben leerse junto a él:

- `s11/docs/guia_anotacion.md`, que fija los criterios de etiquetado del corpus anotado.
- `s11/anonimizador_ocr/README.md`, que describe la implementación del pipeline de
  de-identificación, sus parámetros y su flujo de revisión.

El proyecto opera con dos fuentes de datos de naturaleza jurídica distinta, y esa distinción
gobierna todas las decisiones que siguen:

| Fuente | Naturaleza | Idioma | Uso permitido | Infraestructura de cómputo |
|---|---|---|---|---|
| MEDEC (Ben Abacha et al., 2025) | Conjunto público de investigación, sin datos personales identificables | Inglés | Entrenamiento, ajuste y publicación de métricas | Cómputo local o servicio externo compatible con OpenAI |
| Corpus CITIMED Odontología | Historias clínicas reales con datos personales de salud | Español | Evaluación *cross-domain* del prototipo, previa de-identificación y con autorización institucional | **Exclusivamente local**: modelo servido con Ollama en `http://localhost:11434/v1` |

Ninguna nota clínica de CITIMED, ni en su forma original ni de-identificada, se transmite a un
servicio de inferencia externo. La ruta de API externa está reservada para MEDEC, que es un
conjunto público.

---

## 2. Marco normativo de referencia

### 2.1 HIPAA como referencia internacional

Ecuador no dispone, a la fecha de esta entrega, de un catálogo reglamentario de identificadores de
salud con el nivel de detalle del estándar estadounidense. Por ello el equipo adopta como
**referencia técnica** el método *Safe Harbor* de la regla de privacidad de HIPAA (45 CFR
§164.514(b)(2)), que enumera dieciocho categorías de identificadores cuya supresión permite
considerar un registro como de-identificado. La adopción es metodológica, no jurisdiccional: HIPAA
no es derecho aplicable en Ecuador, pero ofrece una lista de verificación reconocida
internacionalmente y auditable.

La tabla siguiente contrasta las dieciocho categorías con la cobertura efectiva del pipeline
implementado en `s11/anonimizador_ocr/`.

| # | Identificador HIPAA | Cobertura en el proyecto | Mecanismo |
|---|---|---|---|
| 1 | Nombres | Automática + revisión humana | Reglas de contexto, NER (spaCy `es_core_news_md`), tachado junto a etiqueta y por tinta |
| 2 | Subdivisiones geográficas menores que el estado (dirección, ciudad, parroquia, código postal) | Automática (dirección, domicilio, barrio) | Regla de contexto `CONTEXTO_DIRECCION` |
| 3 | Fechas relativas al individuo (nacimiento, ingreso, alta, defunción) | Parcial y deliberada: se redacta la fecha de nacimiento; las fechas de atención se conservan por defecto (véase §3.3) | `--fechas nacimiento` (valor predeterminado) |
| 3b | Edad superior a 89 años | Automática | Regla `CONTEXTO_EDAD` sobre expresiones de 90 años o más |
| 4 | Números de teléfono | Automática | Regla de formato ecuatoriano (celular y fijo, con y sin prefijo +593) |
| 5 | Números de fax | No implementada como categoría propia | Cae bajo la regla de teléfono cuando comparte formato; en caso contrario requiere zona fija |
| 6 | Correo electrónico | Automática, con tolerancia a errores de OCR en el símbolo `@` | Reglas `EMAIL` |
| 7 | Número de seguridad social | Sustituido por el equivalente local: cédula de identidad y RUC (§2.2) | Validadores `cedula_valida`, `ruc_valido` |
| 8 | Número de historia clínica | Automática | Regla `HC` y etiquetas de formulario (`HCU`, `Historia Clínica Única`, `N° de Archivo`) |
| 9 | Número de beneficiario de plan de salud | Cobertura indirecta | Suele coincidir con la cédula; formularios propios de aseguradora requieren zona fija |
| 10 | Números de cuenta | No implementada | Requiere zona fija o revisión humana |
| 11 | Números de certificado o licencia | No implementada (incluye registro profesional del odontólogo) | Requiere zona fija o revisión humana |
| 12 | Identificadores de vehículo y placas | No aplicable al material analizado | — |
| 13 | Identificadores de dispositivo y números de serie | No implementada | Requiere revisión humana |
| 14 | URL | No implementada como categoría propia | — |
| 15 | Direcciones IP | No aplicable al material analizado | — |
| 16 | Identificadores biométricos (huellas, voz) | **No detectables por OCR**: firmas y huellas exigen zona fija | Plantilla JSON de zonas fijas |
| 17 | Fotografías de rostro completo e imágenes equiparables | **No detectables por OCR** | Plantilla JSON de zonas fijas |
| 18 | Cualquier otro número, característica o código único (códigos de barras, sellos institucionales) | **No detectables por OCR** | Plantilla JSON de zonas fijas + revisión humana |

Las filas marcadas como no implementadas o no detectables no son omisiones silenciosas: son el
motivo por el cual el protocolo exige revisión humana del 100 % de las páginas (§6) y por el cual
el sistema ofrece zonas fijas por plantilla para los elementos gráficos.

### 2.2 Adaptación al contexto ecuatoriano

El marco jurídico aplicable al tratamiento es la **Ley Orgánica de Protección de Datos Personales**
(LOPDP) del Ecuador, que clasifica los datos relativos a la salud como datos sensibles y sujeta su
tratamiento a base de licitud reforzada, principios de finalidad, minimización y
proporcionalidad, y medidas de seguridad acordes al riesgo. El proyecto invoca los siguientes
principios de forma operativa:

- **Finalidad y limitación de uso.** Los datos se emplean únicamente para evaluar el prototipo de
  detección de inconsistencias en el marco del trabajo de titulación. No se construyen perfiles,
  no se reidentifica y no se cede el corpus a terceros.
- **Minimización.** Se conserva la mínima porción de la historia clínica necesaria para la tarea:
  el texto clínico segmentado en oraciones, sin los campos administrativos ni de filiación.
- **Seguridad.** Procesamiento íntegramente local, sin egreso a internet, con exclusión del
  material identificable del control de versiones (§5).
- **Responsabilidad demostrable.** Cada corrida del anonimizador deja evidencia auditable
  (`hallazgos.csv`, `paginas_a_revisar.csv`, `informe.json`) que permite reconstruir qué se tachó,
  en qué página y por qué regla.

La sustitución de identificadores estadounidenses por sus equivalentes locales es la principal
adaptación técnica del pipeline:

| Elemento local | Especificidad implementada |
|---|---|
| **Cédula de identidad** | Diez dígitos, código de provincia válido (01–24, más 30 para personas extranjeras), tercer dígito menor que 6 y **validación del dígito verificador por módulo 10**. Una secuencia con forma de cédula pero dígito verificador incorrecto se tacha igualmente, con confianza reducida, porque el error suele provenir del OCR y no del documento. |
| **RUC** | Trece dígitos. Se valida como cédula de persona natural seguida de `001`; para sociedades y entidades públicas se acepta por forma (tercer dígito 6 o 9). |
| **Teléfonos** | Formato ecuatoriano: celular `09XXXXXXXX`, fijo `0[2-7]XXXXXXX`, con prefijo internacional `+593` opcional y separadores tolerados. |
| **Número de historia clínica** | Reconocimiento de las denominaciones usadas en el sistema de salud ecuatoriano: `HC`, `H.C.`, `HCU`, `Historia Clínica Única`, `N° de Archivo`, `Número de Hist. Clínica Única`. |
| **Ruido de OCR** | Normalización de confusiones frecuentes (`O`→`0`, `l`→`1`, `S`→`5`, `@`→`0`) restringida a tokens mayoritariamente numéricos, preservando desplazamientos de carácter para no desalinear las cajas de píxeles. |

---

## 3. Protocolo de de-identificación

### 3.1 Arquitectura por capas

El anonimizador rasteriza cada página del PDF escaneado, ejecuta reconocimiento óptico de
caracteres con Tesseract en español, localiza los identificadores y los **tacha a nivel de píxel**.
El PDF de salida se reconstruye desde cero a partir de las imágenes ya tachadas, de modo que no
arrastra la capa de texto original, ni anotaciones, ni adjuntos, ni metadatos de autor, fecha o
software. Cuando se solicita un PDF buscable, la capa de texto se genera con un segundo OCR
ejecutado **sobre la imagen ya tachada**, por lo que no puede contener lo redactado.

La detección se organiza en cuatro capas de dependencia decreciente respecto del OCR, precedidas
por una quinta capa que no depende de él en absoluto:

1. **Reglas** (`deteccion.py`): patrones y validadores de identificadores estructurados.
2. **Contexto y NER**: nombres en prosa, a partir de disparadores léxicos y de reconocimiento de
   entidades con spaCy.
3. **Junto a etiquetas** (`zonas.py`): la etiqueta impresa del formulario sí se lee aunque el valor
   sea manuscrito, de modo que se tacha a la derecha de la etiqueta o debajo cuando la página es
   una tabla.
4. **Tinta** (`mascara_tinta`): la posición del valor se decide observando los píxeles escritos,
   descontando las rayas de tabla, y la caja se extiende en las cuatro direcciones siguiendo la
   tinta. Cubre manuscrito ilegible, celdas y bloques de firma.
5. **Zonas fijas** (plantilla JSON): rectángulos en coordenadas relativas que se tachan siempre,
   independientemente de lo que el OCR haya leído.

### 3.2 Categorías redactadas

| Categoría | Qué protege | Capa que la cubre | Regla o modelo que la detecta |
|---|---|---|---|
| `NOMBRE` | Paciente, representante, familiares, acompañante y personal sanitario | Contexto + NER, etiquetas, tinta | Disparadores `Paciente:`, `Nombres y Apellidos:`, `Representante:`, `Dr.`/`Dra.`, `Médico tratante:`; NER de spaCy filtrado por lista de exclusión clínica (`STOP_NER`) |
| `CEDULA` | Cédula de identidad y pasaporte | Reglas, etiquetas | Patrón de diez dígitos + validación de provincia, tercer dígito y dígito verificador módulo 10 |
| `RUC` | Registro Único de Contribuyentes | Reglas, etiquetas | Patrón de trece dígitos + validación de persona natural (`cédula`+`001`) o de sociedad por forma |
| `TELEFONO` | Teléfono celular y fijo | Reglas, etiquetas | Patrón de numeración ecuatoriana con prefijo `+593` opcional |
| `EMAIL` | Correo electrónico | Reglas, etiquetas | Patrón estándar más variante tolerante al `@` mal reconocido |
| `FECHA` | Fecha de nacimiento (por defecto) | Reglas, etiquetas | Fecha numérica o textual validada, condicionada a contexto de nacimiento en los 40 caracteres previos |
| `HC` | Número de historia clínica única y número de archivo | Reglas, etiquetas, zonas fijas | Patrón de denominaciones ecuatorianas; se tacha solo el número y se conserva legible la etiqueta |
| `DIRECCION` | Domicilio, barrio, residencia | Contexto | Disparadores `Dirección:`, `Domicilio:`, `Barrio:`, `Residencia:` |
| `EDAD` | Edad de 90 años o más | Reglas | Expresiones de edad igual o superior a 90 años, siguiendo el criterio de HIPAA |
| `ZONA` / `ETIQUETA` | Cabeceras de formulario estandarizado, casillas de filiación, bloques de firma | Zonas fijas, tinta | Plantilla JSON en coordenadas relativas |

Además, cada página cuya confianza media de OCR quede por debajo del umbral configurado (55 por
defecto) o que contenga menos de quince palabras reconocidas se marca en `paginas_a_revisar.csv`
como probable manuscrito con destino a revisión manual.

### 3.3 Decisiones de criterio y su justificación

**Se redactan también los nombres del personal sanitario.** El nombre del odontólogo tratante, del
cirujano, del anestesiólogo, del instrumentista y de los ayudantes constituye un dato personal de
una persona física identificada, y su tratamiento no está amparado por la autorización que se
refiere al material clínico del paciente. Adicionalmente, en una clínica de tamaño acotado el
nombre del profesional actúa como cuasi-identificador: combinado con la fecha de atención y la
especialidad, reduce el conjunto de pacientes posibles a un número muy pequeño, lo que habilita la
reidentificación por inferencia. Por ello `ETIQUETAS_FORMULARIO` incluye los campos de personal y
`CONTEXTO_NOMBRE` incorpora los disparadores `Dr.`, `Dra.`, `Médico` y `Tratante`. El pipeline
permite revertir esta decisión, pero el proyecto no la revierte.

**Se redacta la fecha de nacimiento y se conservan las fechas de atención.** La fecha de nacimiento
es un identificador directo de alta capacidad de reidentificación cuando se cruza con registros
externos, y su valor analítico para la tarea es nulo: el modelo no razona sobre la edad exacta del
paciente para decidir si una oración es inconsistente. Las fechas de atención, en cambio, sostienen
la coherencia temporal de la nota, que es precisamente el material sobre el que se detectan
inconsistencias: una secuencia de evolución, un control posoperatorio o un intervalo entre
prescripciones pierden sentido clínico si se suprimen las fechas. La configuración predeterminada
es por tanto `--fechas nacimiento`. Se declara con transparencia que esta decisión constituye una
desviación consciente del método *Safe Harbor* estricto, que exige eliminar todos los elementos de
fecha salvo el año; la desviación se compensa con la exclusión del material identificable del
control de versiones, con el procesamiento local y con la conservación del corpus únicamente dentro
del equipo. Si el comité o la institución lo requieren, el pipeline admite `--fechas todas` sin
cambios de código.

**Se prioriza el sobre-tachado.** El sistema está calibrado para recall, no para precisión: es
esperable que tache la etiqueta contigua o la palabra siguiente al valor. Se asume ese coste porque
el error por exceso degrada la utilidad del corpus, mientras que el error por defecto expone a una
persona.

### 3.4 Evidencia de la corrida documentada

Sobre la historia clínica de veinte páginas autorizada por CITIMED, la corrida registrada en
`s11/anonimizador_ocr/salidas/` produjo **127 hallazgos distribuidos en las veinte páginas**. La
composición de la evidencia, extraída de los agregados sin texto en claro, es la siguiente:

| Categoría | Cajas en que aparece |
|---|---|
| `NOMBRE` | 115 |
| `HC` | 11 |
| `CEDULA` | 10 |
| `DIRECCION` | 1 |

Los totales por categoría suman más de 127 porque una misma caja puede fusionar dos o más
categorías contiguas (por ejemplo, nombre y número de historia clínica en la misma línea de
cabecera). Por capa de detección, el reparto fue: contexto 52, NER 43, celda de tabla 12, etiqueta
de formulario 12 y reglas 8. Una sola página, la número 10, quedó derivada a revisión manual por
confianza media de OCR de **40,2 frente al umbral de 55**, con el motivo registrado como probable
manuscrito.

Este reparto es coherente con el diseño: en un formulario clínico ecuatoriano los identificadores
estructurados (cédula, historia clínica) son pocos y aparecen en la cabecera, mientras que los
nombres se dispersan por la prosa, las firmas y los campos de personal, y son los que exigen las
capas de contexto, NER y tinta.

---

## 4. Constancia de autorización institucional

El equipo declara que el tratamiento de la historia clínica empleada en esta entrega cuenta con
**autorización institucional de CITIMED para uso académico**, otorgada en el marco del trabajo de
titulación de la Maestría en Inteligencia Artificial Aplicada de la Universidad de las Américas.
La autorización habilita el uso del material con fines de investigación y evaluación del prototipo,
bajo las condiciones de de-identificación, custodia local y no cesión a terceros descritas en este
anexo.

La formalización documental de esa autorización se encuentra **pendiente de adjuntar** a la fecha de
esta versión del anexo. El equipo se abstiene deliberadamente de consignar datos que no obran en su
poder en forma verificable, por lo que los campos correspondientes quedan como marcadores explícitos
que deben completarse a mano antes de la entrega final:

- Documento habilitante: **[adjuntar acta de autorización institucional de CITIMED]**
- Número de oficio o referencia interna: **[pendiente]**
- Fecha de emisión: **[pendiente]**
- Cargo y nombre del firmante autorizado por CITIMED: **[pendiente]**
- Vigencia y alcance declarados en el documento: **[pendiente]**
- Ubicación del documento firmado en el expediente de titulación: **[pendiente]**
- Dictamen del comité de ética o instancia equivalente de la UDLA, si corresponde: **[pendiente de gestión]**

Mientras estos marcadores no se completen, ninguna afirmación de este anexo debe leerse como
constancia formal de aprobación ética: la autorización institucional está declarada por el equipo y
su respaldo documental está en trámite de incorporación al expediente.

Se hace constar además que el material sintético incluido en el repositorio con fines de prueba
(`s11/anonimizador_ocr/pruebas/generar_ejemplo.py` y el ejemplo asociado) contiene **datos
íntegramente ficticios**, generados para verificar el funcionamiento de las reglas, y no proviene de
ninguna persona real.

---

## 5. Cadena de custodia

**Procesamiento local sin egreso.** Todo el pipeline de de-identificación se ejecuta en el equipo
del investigador: rasterizado, OCR con Tesseract, NER con un modelo spaCy descargado previamente,
tachado y reconstrucción del PDF. No hay llamadas de red en ninguna etapa. Para el entorno sin
conexión de CITIMED, el `README.md` del anonimizador documenta el procedimiento de instalación
desconectada, descargando el binario de Tesseract, el modelo de idioma `spa.traineddata` y las
ruedas de los paquetes en una máquina con internet y transfiriéndolos al equipo aislado. Cuando el
análisis de inconsistencias requiere un modelo de lenguaje sobre notas con datos de salud, se emplea
un modelo servido localmente con Ollama en `http://localhost:11434/v1`; la ruta hacia API externa
queda reservada para MEDEC.

**Exclusión del control de versiones.** El repositorio excluye por configuración el material
identificable. Las reglas relevantes de `.gitignore` son:

```
anonimizador/
s11/anonimizador_ocr/historias/
s11/anonimizador_ocr/salidas*/
s11/evidencias/crudo/
data/citimed_odontologia.csv
data/citimed_analisis.db
```

Esto abarca las historias clínicas originales, las imágenes de revisión (que muestran la página
**sin tachar** con las cajas superpuestas y son, por tanto, material plenamente identificable), los
informes con texto detectado en claro y el corpus anotado. El repositorio conserva únicamente el
código, la documentación y los ejemplos sintéticos.

**Qué sale del equipo local.** Solo dos clases de artefacto abandonan la máquina de procesamiento:
(a) **agregados sin texto**, es decir, recuentos, distribuciones por categoría y por capa de
detección, métricas de confianza y listados de páginas derivadas a revisión, sin ninguna cadena
extraída del documento; y (b) **páginas ya tachadas y verificadas** por doble revisor, cuando su
inclusión en el informe o la presentación resulta necesaria como evidencia visual. Las cifras
consignadas en §3.4 de este anexo pertenecen a la primera clase.

**Auditoría sin texto en claro.** La trazabilidad del proceso se sostiene sobre `hallazgos.csv` e
`informe.json`, que se conservan localmente como evidencia. Para permitir verificación externa sin
exponer contenido, el equipo publica únicamente **hashes** de los artefactos (PDF de entrada,
PDF anonimizado, informe de hallazgos) y agregados numéricos. Un hash acredita que el archivo
auditado es el mismo que se procesó, sin revelar nada de su contenido.

- Registro de hashes de la corrida documentada: **[completar con el listado de hashes generado localmente]**

---

## 6. Control de calidad de la de-identificación

La anonimización automática es la primera pasada, no el resultado final. El protocolo de control de
calidad que el equipo se impone es el siguiente.

**Revisión humana del 100 % de las páginas, con doble revisor.** Cada página del corpus se inspecciona
visualmente contra la imagen de revisión, que muestra la página original con las cajas detectadas y
su etiqueta, y contra la imagen anonimizada. Dos integrantes distintos revisan cada página de forma
independiente; el tercero actúa como dirimente. No se acepta muestreo: el corpus es de tamaño
reducido y el coste de una fuga no es proporcional al ahorro de tiempo. Las páginas listadas en
`paginas_a_revisar.csv` —como la página 10 de la corrida documentada— reciben además una inspección
reforzada palabra por palabra, porque su baja confianza de OCR indica que las capas dependientes del
reconocimiento de texto tuvieron poco material sobre el que operar.

**Criterio de bloqueo.** Una página no se incorpora al corpus de trabajo hasta que ambos revisores
confirmen **recall del 100 % en las categorías `NOMBRE`, `CEDULA` y `HC`**. Estas tres son las de
capacidad de reidentificación directa e inmediata en el contexto ecuatoriano y concentran, además,
la práctica totalidad de los hallazgos observados. La página se marca como apta solo con doble
confirmación; ante discrepancia entre revisores, prevalece la lectura más conservadora, es decir, la
que exige tachar.

**Ciclo de corrección ante un escape.** Si un revisor detecta un identificador no tachado, el
procedimiento es:

1. Detener el uso de la página y de todo artefacto derivado de ella.
2. Registrar el escape: página, categoría, tipo de soporte (impreso, manuscrito, sello, firma) y
   causa probable (OCR no leyó, etiqueta no reconocida, valor fuera de campo etiquetado).
3. Corregir la causa, no solo el síntoma. Según el caso: añadir la variante de etiqueta a
   `ETIQUETAS_FORMULARIO`, añadir la zona fija a la plantilla JSON, ajustar el modo de segmentación
   de Tesseract, ampliar el ancho de tachado junto a la etiqueta o subir el umbral de derivación a
   revisión manual.
4. **Reprocesar el lote completo**, no solo la página afectada, porque la misma causa puede haber
   producido escapes no detectados en otras páginas.
5. Repetir la doble revisión sobre el lote reprocesado y anotar el incidente en el registro de
   calidad.
6. Destruir de forma segura los artefactos derivados de la versión defectuosa.

- Registro de escapes detectados y corregidos: **[completar durante la fase de anotación]**

---

## 7. Límites y riesgos declarados

El equipo declara los siguientes límites de manera explícita, por considerar que una descripción
honesta de las carencias es parte del rigor exigible a un trabajo de titulación.

**Recall bajo del OCR frente al manuscrito real.** Tesseract lee correctamente el texto impreso y
mal la escritura a mano. Las capas de etiquetas, tinta y zonas fijas existen precisamente para no
depender del reconocimiento del valor manuscrito, pero su cobertura es posicional: funcionan cuando
el dato está donde el formulario dice que debe estar. **Un nombre escrito a mano en medio de una
nota de evolución, fuera de cualquier campo etiquetado, puede escaparse.** Solo la revisión humana
o la incorporación de un modelo específico de manuscrito —TrOCR o PaddleOCR, ambos ejecutables en
local— cubriría ese caso. Esta es la limitación más importante del pipeline y el motivo principal
del criterio de revisión total del §6.

**Sobre-tachado como error del lado seguro.** La calibración hacia recall produce redacción de
material no identificable: etiquetas, palabras contiguas, fragmentos de celda. Se acepta
conscientemente, porque degrada la utilidad del corpus en lugar de exponer a una persona.

**Elementos gráficos no detectables.** Firmas, huellas, sellos institucionales, códigos de barras y
fotografías no son texto y el OCR no los reconoce. Su tratamiento depende íntegramente de las zonas
fijas por plantilla y de la revisión humana. En formularios no estandarizados, donde no cabe
plantilla, la única salvaguarda es el revisor.

**Validación imperfecta de identificadores dañados por el OCR.** Una cédula cuyo dígito verificador
no cuadra puede deberse a un error de reconocimiento o a un dato erróneo en el documento. El
pipeline la tacha en ambos casos, con confianza reducida, lo que es correcto desde la privacidad
pero impide usar la validación como medida de calidad del OCR.

**La anonimización automática no sustituye la revisión humana.** Ninguna cifra de esta entrega debe
interpretarse como garantía de de-identificación completa. El pipeline reduce el volumen de trabajo
manual y concentra la atención del revisor donde el riesgo es mayor; la garantía, en la medida en
que existe, la aporta el procedimiento de doble revisión con criterio de bloqueo.

**Riesgo residual de reidentificación por inferencia.** Aun con todos los identificadores directos
suprimidos, una combinación suficientemente específica de diagnóstico, procedimiento, fecha de
atención y contexto institucional puede singularizar a un paciente dentro de una clínica pequeña.
El proyecto mitiga este riesgo por la vía de la custodia —corpus reducido, local, no cedido y no
publicado— y no por la vía de la supresión adicional de contenido clínico, que destruiría la
utilidad del material.

---

## 8. Uso responsable del sistema

El sistema de detección de inconsistencias es un **prototipo de investigación académica**. No es un
dispositivo médico, no ha sido sometido a validación clínica prospectiva, no está certificado por
ninguna autoridad sanitaria y no debe emplearse como soporte de decisiones asistenciales.

**No sustituye el criterio clínico.** El sistema no diagnostica, no prescribe y no evalúa la
idoneidad de una conducta terapéutica. Señala oraciones cuya formulación resulta estadísticamente
compatible con una inconsistencia documental, lo cual es una afirmación sobre el texto, no sobre el
paciente.

**La responsabilidad final es del profesional.** El odontólogo o el médico tratante conserva
íntegramente la responsabilidad clínica y legal de sus decisiones. Una alerta del sistema no
transfiere responsabilidad, y su ausencia no exime de la revisión profesional del registro.

**Las alertas son sugerencias verificables.** El diseño del sistema privilegia deliberadamente la
localización: la reformulación de la tarea de nivel de nota a nivel de oración obedece a que una
alerta útil debe señalar **la oración concreta sospechosa**, de modo que el profesional pueda
verificarla o descartarla en segundos leyendo el fragmento señalado. Con el conjunto público MEDEC,
el sistema localiza correctamente la oración errónea en el 84,6 % de las notas con error (263 de
311). Una tasa de localización que no es del 100 % significa que el profesional debe leer la nota,
no solo la oración señalada, cuando la alerta le resulte dudosa.

**Prevalencia baja y lectura de las métricas.** A nivel de oración, el sistema alcanza ROC-AUC de
0,949 y AUPRC de 0,419 sobre una prevalencia de 4,5 %. La brecha entre ambas métricas no es un
defecto oculto: es la consecuencia esperada de un problema de clase muy minoritaria, y se declara
para que ningún lector interprete el ROC-AUC como una promesa de precisión operativa. Estas cifras
provienen de MEDEC, en inglés y en dominio hospitalario general; **la transferencia al español
odontológico de CITIMED está por medir**, y medirla es precisamente la finalidad del corpus anotado
que este anexo habilita.

**Supervisión humana en el bucle.** Cualquier uso futuro del sistema en un entorno real debe
mantener al profesional en el bucle de decisión, registrar las alertas aceptadas y rechazadas para
auditoría, y someterse a una evaluación previa de impacto en protección de datos conforme a la
LOPDP.

---

## 9. Documentos relacionados

| Documento | Contenido |
|---|---|
| `s11/docs/guia_anotacion.md` | Criterios operativos de anotación de inconsistencias, esquema de datos y procedimiento de doble anotación con acuerdo entre anotadores |
| `s11/anonimizador_ocr/README.md` | Implementación del pipeline de de-identificación, parámetros, instalación desconectada y límites técnicos |
| `s11/fragmentos/track-f.md` | Síntesis de este anexo para la sección §6 del informe final |
| `s11/docs/protocolo_verificacion_humana.md` | Protocolo de verificación humana de las alertas del detector |

## 10. Marcadores pendientes de completar

| Sección | Marcador | Responsable |
|---|---|---|
| §4 | Acta de autorización institucional de CITIMED, número de oficio, fecha, firmante, vigencia y ubicación en el expediente | Equipo |
| §4 | Dictamen del comité de ética o instancia equivalente de la UDLA, si corresponde | Equipo |
| §5 | Registro de hashes de los artefactos de la corrida documentada | Equipo |
| §6 | Registro de escapes detectados y corregidos durante la anotación | Equipo |
