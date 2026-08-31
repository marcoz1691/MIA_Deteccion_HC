## 3.6 Anonimización OCR de historias reales

El corpus de trabajo de esta tesis proviene de historias clínicas de la clínica CITIMED
(Ecuador) que llegan como PDF escaneados: páginas rasterizadas, sin capa de texto
aprovechable, con formularios preimpresos rellenados a mano. Para poder usarlas en
investigación había que resolver antes un problema de de-identificación que no admite las
soluciones habituales: no existe texto sobre el que aplicar un reemplazo, y buena parte de
los identificadores del paciente están manuscritos. Se desarrolló para ello un anonimizador
propio (`s11/anonimizador_ocr/`) que reconoce el contenido de cada página, localiza los
identificadores y los tacha **a nivel de píxel**, ejecutándose íntegramente en local sin
enviar nada a servicios externos.

### 3.6.1 Arquitectura de detección en cuatro capas

El diseño parte de una constatación empírica: el OCR convencional lee bien lo impreso y mal
lo manuscrito. Apoyar toda la de-identificación en el texto reconocido dejaría sin proteger
precisamente los campos que el personal sanitario rellena a mano. La herramienta combina por
eso cuatro capas ordenadas de mayor a menor dependencia del OCR, de modo que el fallo de una
no implique el fallo del conjunto.

**Capa 1. Reglas adaptadas a Ecuador** (`deteccion.py`). Expresiones regulares para cédula de
identidad, RUC, celular y fijo, correo electrónico, número de historia clínica, fecha de
nacimiento, edad de 90 años o más (criterio HIPAA) y direcciones. La cédula no se acepta por
su forma, sino que se **valida con el dígito verificador**: diez dígitos, código de provincia
entre 01 y 24 (o 30 para extranjeros), tercer dígito menor que 6 y comprobación de módulo 10
con coeficientes alternos 2-1. El RUC de persona natural se valida como cédula seguida de
`001`. Esta validación cumple una doble función: confirma los aciertos y, cuando la forma
encaja pero el dígito verificador falla, el valor se tacha igualmente con confianza reducida
(0.5), porque un dígito verificador incorrecto sobre un escaneo es más probablemente un error
de OCR que un número que no sea una cédula. Las reglas operan además sobre una normalización
previa que revierte las confusiones típicas del OCR en tokens mayoritariamente numéricos
(`O`→`0`, `l`→`1`, `S`→`5`, `B`→`8`, y `@`→`0` en los correos), conservando la longitud del
texto para no perder las posiciones que después hay que traducir a coordenadas de píxel.

**Capa 2. Contexto más reconocimiento de entidades nombradas.** Los nombres no tienen forma
reconocible, así que se detectan por dos vías complementarias. La primera es el contexto
inmediato: patrones del tipo `Paciente:`, `Nombres y Apellidos:`, `Representante:`, `Madre:`,
`Dr.`/`Dra.`, `Médico Tratante:`, que capturan hasta cinco palabras capitalizadas a
continuación de la etiqueta. La segunda es el modelo de NER de spaCy `es_core_news_md`, que
recupera los nombres que aparecen sueltos en la prosa de las notas de evolución, donde no hay
etiqueta que sirva de ancla. Las entidades de tipo `PER` se filtran con una lista de parada
(`STOP_NER`) que descarta los falsos positivos característicos del dominio clínico:
instituciones, servicios, especialidades, topónimos, fármacos y verbos de reporte que el
modelo etiqueta ocasionalmente como persona. Los nombres del personal sanitario se tachan
también, por tratarse igualmente de datos personales.

**Capa 3. Tachado junto a etiquetas, guiado por máscara de tinta** (`zonas.py`). Es la capa
que resuelve el manuscrito y la que distingue a esta herramienta de un anonimizador de texto.
Se apoya en una asimetría del formulario: la *etiqueta* va impresa y el OCR sí la lee, aunque
el *valor* escrito al lado sea ilegible para él. Detectada la etiqueta, se tacha su entorno
sin necesidad de leer el valor, con un diccionario de unas 90 variantes
(`ETIQUETAS_FORMULARIO`) que tolera cabeceras mal reconocidas y etiquetas partidas en dos
renglones. La decisión de *dónde* tachar no es fija, sino que se toma observando los píxeles
escritos mediante una máscara de tinta que descarta previamente las rayas de la tabla: a la
**derecha** de la etiqueta en un campo en línea, **debajo** cuando la página es una tabla y
el dato está en la celda inferior a la cabecera, y **encima** en los bloques de firma, donde
el nombre se escribe sobre la raya y la etiqueta impresa queda debajo. El rectángulo se
extiende después en las cuatro direcciones siguiendo la tinta, de modo que cubra letra de
tamaño irregular, valores descolgados respecto del campo o que empiezan antes de la cabecera.

**Capa 4. Zonas fijas por plantilla.** Rectángulos definidos en coordenadas relativas en una
plantilla JSON, que se tachan siempre, en toda página del formulario correspondiente, con
independencia de lo que el OCR haya leído. Es el último recurso y el único con garantía
determinista: cubre la cabecera del Formulario 008 del MSP, la casilla del número de historia
clínica, los sellos, los códigos de barras y las firmas, elementos que ninguna de las capas
anteriores detecta. Las coordenadas se miden con una herramienta auxiliar
(`herramientas/medir_zonas.py`) sobre una página de revisión.

Las cajas producidas por las cuatro capas se fusionan cuando se solapan y se aplican sobre la
imagen. El PDF de salida se **reconstruye desde cero** a partir de las imágenes ya tachadas,
por lo que no arrastra la capa de texto original, ni anotaciones, ni adjuntos, ni metadatos de
autoría o de software. Si se solicita un PDF buscable, la capa de texto se genera haciendo OCR
sobre la imagen ya tachada, de manera que no puede contener lo que se ocultó. Por último, toda
página con confianza OCR media inferior al umbral configurado, o con menos palabras
reconocidas de las esperadas, o sin ningún identificador detectado, se deriva automáticamente
a revisión humana.

### 3.6.2 Resultados de la corrida sobre una historia real

Se procesó una historia clínica completa de 20 páginas, con autorización institucional. La
tabla resume los agregados de esa corrida, calculados a partir del informe de ejecución.

| Métrica | Valor |
|---|---|
| Documentos procesados | 1 |
| Páginas | 20 |
| Palabras reconocidas | 5 212 (media 260,6 por página) |
| Fuente de las palabras | Tesseract en 20/20 páginas (ninguna traía capa de texto utilizable) |
| Corrección de inclinación aplicada | 0,0° en las 20 páginas |
| Hallazgos totales | 127 |
| Rectángulos tachados tras fusión | 87 (media 4,35 por página; las 20 páginas con al menos uno) |
| Tiempo de procesamiento | 77,5 s (3,88 s por página) |
| Páginas derivadas a revisión manual | 1 (página 10) |

**Hallazgos por etiqueta.** Las etiquetas compuestas corresponden a hallazgos solapados que
el pipeline fusionó en un único rectángulo, por ejemplo un nombre y un número de historia
clínica contiguos en la misma celda.

| Etiqueta | Hallazgos |
|---|---|
| `NOMBRE` | 108 |
| `CEDULA` | 6 |
| `HC` | 4 |
| `DIRECCION` | 1 |
| `NOMBRE+HC` | 3 |
| `CEDULA+HC` | 1 |
| `HC+NOMBRE` | 1 |
| `NOMBRE+CEDULA` | 1 |
| `HC+CEDULA+NOMBRE` | 1 |
| `NOMBRE+HC+CEDULA+HC` | 1 |
| **Total** | **127** |

Contando la presencia de cada categoría también dentro de las etiquetas compuestas, el
reparto es: `NOMBRE` 115, `HC` 11, `CEDULA` 10 y `DIRECCION` 1. No se detectaron instancias de
`TELEFONO`, `EMAIL` ni `FECHA`; en el caso de las fechas, la corrida se ejecutó con la opción
`--fechas nacimiento`, que tacha únicamente la fecha de nacimiento y preserva las fechas de
atención, necesarias para el análisis clínico.

**Hallazgos por origen.** La distribución muestra el reparto real del trabajo entre las
capas.

| Origen | Hallazgos | Porcentaje | Capa |
|---|---|---|---|
| `contexto` | 52 | 40,9 % | Contexto (capa 2) |
| `ner` | 43 | 33,9 % | spaCy `es_core_news_md` (capa 2) |
| `celda` | 12 | 9,4 % | Tachado bajo cabecera de tabla (capa 3) |
| `etiqueta` | 12 | 9,4 % | Tachado junto a etiqueta en línea (capa 3) |
| `regex` | 8 | 6,3 % | Reglas Ecuador (capa 1) |
| **Total** | **127** | **100 %** | |

Dos lecturas merecen atención. La primera es que las capas 2 y 3 aportan conjuntamente el
93,7 % de los hallazgos, mientras que las reglas con validación de dígito verificador solo
explican el 6,3 %: en un documento manuscrito, los identificadores con estructura formal
reconocible son minoría frente a los nombres. La segunda es que la capa 3, que no necesita
leer el valor, aporta 24 hallazgos (18,9 %) que las capas dependientes del texto reconocido
no habrían producido. La capa 4 no intervino porque esta corrida se ejecutó sin plantilla de
zonas; su incorporación está prevista como respuesta a los escapes que detecte la
verificación humana.

**Confianza del OCR.** La confianza media por página se distribuyó así:

| Estadístico | Confianza OCR media por página |
|---|---|
| Mínimo | 40,2 |
| Máximo | 89,6 |
| Media | 74,57 |
| Mediana | 80,30 |

La única página derivada a revisión manual fue la **página 10**, con confianza media 40,2
frente al umbral configurado de 55, valor que el pipeline interpreta como página
predominantemente manuscrita. Contra una mediana de 80,30 en el resto del documento, esa
página concentra el riesgo de la corrida: si el OCR no reconoce el texto, las capas 1 y 2 no
tienen sobre qué operar y la protección recae íntegramente en la capa 3 y, en su caso, en la
capa 4.

### 3.6.3 Por qué 127 hallazgos no son una medida de recall

Conviene ser explícito sobre lo que las cifras anteriores acreditan y lo que no. Los 127
hallazgos son identificadores que el sistema **detectó**: constituyen el numerador de una
fracción cuyo denominador —cuántos identificadores **había** en el documento— no aparece en
ninguna salida automática y no puede aparecer. Un nombre manuscrito en una nota de evolución
que el OCR nunca convierte en texto no genera hallazgo, no consta en ningún registro y sigue
visible en el PDF resultante. El conteo de hallazgos mide la actividad del sistema, no su
cobertura, y una corrida con más hallazgos no es necesariamente más segura que otra con
menos.

Por la misma razón, el número de hallazgos tampoco informa sobre la precisión. El pipeline
prioriza deliberadamente el recall y produce sobre-tachado conocido: rectángulos que cubren
el identificador junto a la etiqueta impresa que lo precede, la palabra siguiente o una celda
completa de la tabla. Ese sesgo es el lado seguro del error desde el punto de vista de la
privacidad, pero tiene un coste sobre el corpus, porque destruye texto clínico que el análisis
posterior necesita. Cuantificarlo requiere igualmente una lectura humana.

El denominador solo se obtiene contando los identificadores presentes en las páginas
originales. Ese conteo es el objeto del protocolo de verificación humana documentado en
`s11/docs/protocolo_verificacion_humana.md`, que define el procedimiento en cuatro pasos
—conteo de referencia sobre las páginas originales, localización de identificadores todavía
visibles en las páginas tachadas, conteo de sobre-tachado y resolución de discrepancias por un
tercer integrante—, la definición operativa de las siete categorías para que dos revisores
cuenten igual, el cálculo del recall y del acuerdo entre revisores, y el criterio de bloqueo
aplicable: ninguna página entra al corpus sin recall del 100 % en `NOMBRE`, `CEDULA` y `HC`.
La plantilla de registro, con las 20 páginas cruzadas por las 7 categorías, está en
`s11/evidencias/verificacion_humana_plantilla.csv`. Cuando la verificación detecta un escape,
la corrección se aplica en la configuración —una etiqueta nueva en `ETIQUETAS_FORMULARIO` o
una zona fija en la plantilla JSON—, se re-ejecuta el pipeline y se vuelve a verificar, de
modo que el arreglo sea reproducible sobre el resto del lote y no un parche sobre una imagen.

### 3.6.4 Evidencias publicables y custodia del material original

Las salidas detalladas del anonimizador contienen PHI por diseño: el informe de ejecución
guarda, para cada hallazgo, el texto exacto que se detectó; el CSV de hallazgos reproduce esa
misma información en formato tabular; y las imágenes de revisión son las páginas
**originales** con los rectángulos dibujados encima, es decir, las páginas sin anonimizar. Ese
material permanece en el equipo local autorizado, está excluido del repositorio mediante
`.gitignore` y no se transfiere por ningún medio.

Lo que se incorpora al repositorio como evidencia del proceso de de-identificación es
exclusivamente la versión agregada, generada por el script `s11/sanitizar_evidencias.py` en
`s11/evidencias/anonimizacion_agregados.json`. Ese archivo contiene únicamente totales,
conteos por etiqueta y por origen, métricas de OCR por página y estadísticas de confianza,
todas ellas cifras. El script construye la salida campo a campo mediante una lista blanca y la
somete después a una comprobación defensiva que aborta la escritura si aparece cualquier campo
de texto libre, cualquier clave de las que transportan PHI en el informe crudo, cualquier
valor fuera de los vocabularios controlados de etiquetas, orígenes y fuentes de palabras, o
cualquier cadena con una racha de seis o más dígitos o con forma de dirección de correo. El
nombre del documento de entrada solo se conserva si es claramente un pseudónimo; en caso
contrario se sustituye por un identificador correlativo. La salida incluye además el digest
SHA-256 del informe de origen, que permite acreditar a qué corrida corresponden los agregados
sin necesidad de exponer su contenido, y una nota explícita de ausencia de PHI. Todo el
proceso es reproducible con una sola orden, de forma que la evidencia publicable pueda
regenerarse tras cada iteración de corrección.
