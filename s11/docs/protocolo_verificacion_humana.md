# Protocolo de verificación humana de la de-identificación

Instrucciones operativas para los dos revisores que validan el tachado de las historias
clínicas reales procesadas con el anonimizador OCR (`s11/anonimizador_ocr/`).

## 1. Objetivo

Medir el **recall real** de la de-identificación, es decir, qué fracción de los
identificadores que **había** en el documento quedó efectivamente tachada.

Esta medición no puede sustituirse por las salidas automáticas. El informe de la corrida
reporta 127 hallazgos en 20 páginas, pero un hallazgo es un identificador que el pipeline
**detectó**: es el numerador de una fracción cuyo denominador nadie ha contado todavía. Si
un nombre manuscrito en una nota de evolución nunca llega al texto que produce el OCR, no
genera hallazgo, no aparece en ningún CSV y sin embargo sigue visible en el PDF. Contar
hallazgos mide la actividad del sistema, no su cobertura.

El denominador solo se obtiene con una lectura humana de las páginas originales. Ese es el
trabajo que define este protocolo. Un objetivo secundario es cuantificar el
**sobre-tachado**: el pipeline prioriza deliberadamente el recall, así que tacha de más
(la etiqueta impresa junto al valor, la palabra siguiente, una celda entera). Conviene
saber cuánto, porque el sobre-tachado destruye texto clínico que el corpus necesita.

## 2. Materiales

| Material | Ruta | Contenido |
|---|---|---|
| Páginas originales con las cajas dibujadas encima | `s11/anonimizador_ocr/salidas/revision/<doc>/pNNN_revision.png` | **PHI** |
| Páginas ya tachadas | `s11/anonimizador_ocr/salidas/revision/<doc>/pNNN_anonimizada.png` | Sin PHI si el tachado es correcto |
| PDF anonimizado completo | `s11/anonimizador_ocr/salidas/<doc>_anon.pdf` | Sin PHI si el tachado es correcto |
| Plantilla de registro | `s11/evidencias/verificacion_humana_plantilla.csv` | Vacía, sin PHI |
| Agregados publicables de la corrida | `s11/evidencias/anonimizacion_agregados.json` | Sin PHI |

### Advertencia de manejo

Las imágenes `pNNN_revision.png` son las páginas **originales** con rectángulos de color
superpuestos: contienen nombres, cédulas y números de historia clínica reales y legibles.
Lo mismo ocurre con `informe.json` y `hallazgos.csv`, que guardan el texto detectado.

En consecuencia:

- Toda esa carpeta está excluida por `.gitignore` y **no sale del equipo local**. No se
  sube al repositorio, no se envía por correo ni por mensajería, no se copia a
  almacenamiento en la nube ni a memorias USB.
- La revisión se hace en el equipo autorizado, con la pantalla fuera de la vista de
  terceros y sin capturas de pantalla.
- Lo único publicable es la plantilla CSV rellena con conteos y las métricas derivadas de
  ella.

## 3. Procedimiento

Cada revisor trabaja de forma **independiente** sobre su propia copia de la plantilla,
nombrada `verificacion_humana_<iniciales>.csv` y guardada junto a los materiales locales
(fuera del repositorio hasta que se consolide). No se comparan resultados hasta terminar el
paso 3.

### Paso 1. Conteo de referencia sobre las páginas originales (el denominador)

Abrir `pNNN_revision.png` e **ignorar los rectángulos de color**: se leen las páginas como
si el anonimizador no hubiera intervenido. Para cada una de las 7 categorías de la sección
4, contar cuántas **instancias** de esa categoría aparecen en la página y anotarlo en
`presentes`.

Se cuenta por instancia (aparición física en la página), no por persona distinta. Si el
mismo nombre aparece en la cabecera, en la firma del consentimiento y en el pie de página,
son tres instancias. Si una página no tiene ninguna instancia de una categoría, se escribe
`0`, nunca se deja en blanco: la celda vacía significa "no revisado" y bloquea el cálculo.

### Paso 2. Revisión de las páginas tachadas (identificadores escapados)

Abrir `pNNN_anonimizada.png` y buscar identificadores **todavía legibles**. Para cada
categoría anotar en `escapados` cuántas instancias siguen visibles, total o parcialmente.

Cuenta como escapado todo lo que permita identificar: un nombre con la primera letra
cubierta pero el resto legible, una cédula a la que solo se le tachó un dígito, un valor que
se salió de la caja por la derecha. Ante la duda se cuenta como escapado. `tachados` se
obtiene como `presentes - escapados` y se anota en la misma fila para poder cuadrar los
números.

Es útil hacer este paso "en frío", sin la imagen de revisión al lado, para no dar por
tachado lo que se recuerda que tenía una caja encima.

### Paso 3. Conteo de sobre-tachado sobre las imágenes de revisión

Volver a `pNNN_revision.png` y examinar ahora sí cada rectángulo. Anotar en
`sobre_tachado` cuántos rectángulos de esa categoría cubren contenido que **no** es un
identificador de esa categoría: texto clínico, una etiqueta impresa del formulario, un
valor de otra columna, una celda entera de la tabla, o espacio en blanco relevante.

Un rectángulo que cubre el identificador más la etiqueta impresa que lo precede cuenta como
sobre-tachado. Un rectángulo que cubre solo el identificador con un margen de unos pocos
píxeles, no.

### Paso 4. Resolución de discrepancias

Al terminar los tres pasos, los dos revisores entregan sus CSV al tercer integrante del
equipo, que los cruza fila a fila. Para cada celda en que los conteos difieran:

1. El tercer integrante abre la página en discusión y aplica las definiciones de la
   sección 4 sin conocer qué revisor dijo qué.
2. Su valor es el definitivo y se registra en el CSV consolidado
   `verificacion_humana_consolidada.csv`.
3. Si la discrepancia proviene de una definición ambigua y no de un descuido, se corrige la
   definición en la sección 4 de este documento y **ambos revisores repiten** las páginas
   afectadas. Las definiciones se arreglan antes de seguir contando; no se resuelven caso a
   caso.

Las discrepancias en `escapados` se resuelven siempre por el valor **mayor**: si un revisor
vio un identificador legible y el otro no, el identificador está legible.

## 4. Definición operativa de las categorías

Las siete categorías son las de `ETIQUETAS_FORMULARIO` en
`s11/anonimizador_ocr/anonimizador_ocr/config.py` que aplican a estos formularios. Las
definiciones son operativas: existen para que dos revisores cuenten lo mismo, no para ser
exhaustivas.

| Categoría | Se cuenta | No se cuenta |
|---|---|---|
| `NOMBRE` | Nombre o apellido de una persona física, completo o parcial, impreso o manuscrito: paciente, representante, madre, padre, acompañante, informante y también el personal sanitario (médico tratante, cirujano, anestesiólogo, instrumentista, enfermería). Una firma manuscrita legible como nombre. Las iniciales cuando aparecen como sustituto del nombre en un campo de identificación. | Nombres de la institución, del servicio o de la especialidad. Nombres de fármacos, de procedimientos o de patologías con epónimo. Una firma que es solo un trazo, sin letras legibles (esa se registra como observación, no como instancia). |
| `CEDULA` | Cédula de identidad ecuatoriana (10 dígitos), RUC (13 dígitos), pasaporte o cualquier documento de identidad del paciente o de su representante, en el campo etiquetado o dentro de la prosa. | Códigos de afiliación al seguro, códigos de factura, códigos de cama o de servicio, números de lote de medicación. |
| `HC` | Número de historia clínica, número único de historia clínica, número de archivo, y el mismo número cuando reaparece en pies de página, sellos o etiquetas adhesivas. | Números de formulario del MSP (`Form. 008`, `Form. 053`), números de página, códigos CIE-10. |
| `TELEFONO` | Celular o fijo del paciente, del representante o de un contacto de emergencia, con o sin prefijo `+593`. | Teléfonos de la institución impresos en la cabecera o el pie del formulario (son de la clínica, no del paciente). |
| `EMAIL` | Cualquier dirección de correo del paciente o de su representante. | Correos institucionales impresos en el formulario. |
| `FECHA` | **Solo fecha de nacimiento** del paciente o del representante, en cualquier formato, y la edad cuando es de 90 años o más (criterio HIPAA). La corrida se ejecutó con `--fechas nacimiento`. | Fechas de atención, de ingreso, de egreso, de cirugía, de firma del consentimiento y de los signos vitales: son necesarias para la investigación y no se tachan por diseño. La edad por debajo de 90 años. |
| `DIRECCION` | Dirección de domicilio, calle y número, barrio, sector, referencia de ubicación, cantón o parroquia cuando acompañan al domicilio del paciente. | Provincia o ciudad aisladas. La dirección de la clínica impresa en el formulario. Lugar de nacimiento sin más detalle. |

Regla transversal: si un mismo rectángulo o un mismo valor encaja en dos categorías (por
ejemplo, una celda que contiene el nombre y debajo el número de historia clínica), se cuenta
**una instancia en cada categoría**. El informe automático refleja esto mismo con etiquetas
compuestas del tipo `NOMBRE+HC`.

## 5. Cálculo del recall y del acuerdo entre revisores

Sobre el CSV consolidado, por categoría *c*:

```
presentes(c)     = suma de la columna `presentes` en las filas de categoría c
escapados(c)     = suma de la columna `escapados` en las filas de categoría c
recall(c)        = (presentes(c) - escapados(c)) / presentes(c)
```

Si `presentes(c) = 0` el recall de esa categoría es indefinido y se reporta como `n/a`, no
como 100 %: no se puede acreditar cobertura sobre una categoría que no aparecía en el
documento. Este será previsiblemente el caso de `EMAIL` y podría serlo de `TELEFONO`.

La tasa de sobre-tachado se reporta como magnitud descriptiva, no como error:

```
sobre_tachado(c) = suma de la columna `sobre_tachado` / número de rectángulos de categoría c
```

El acuerdo entre revisores se calcula **antes** de la consolidación, comparando los dos CSV
independientes:

- **Acuerdo exacto por celda**: porcentaje de celdas numéricas con el mismo valor en los dos
  CSV, desglosado por columna (`presentes`, `escapados`, `sobre_tachado`). Es la métrica
  principal, por ser la más exigente y la más fácil de auditar.
- **Kappa de Cohen sobre la decisión binaria por fila**: para cada una de las 140 filas se
  reduce el juicio a "¿hay al menos una instancia de esta categoría en esta página?"
  (`presentes > 0`). Kappa corrige el acuerdo esperado por azar, que es alto porque la
  mayoría de las celdas valen 0.
- **Diferencia absoluta media** en `presentes`, para dimensionar el desacuerdo cuando no es
  exacto.

Un acuerdo exacto por debajo del 90 % en `presentes` indica que las definiciones de la
sección 4 no son suficientemente operativas: se revisan y se repite el conteo antes de
publicar cualquier cifra de recall.

## 6. Criterio de bloqueo

**Ninguna página entra al corpus de investigación sin recall del 100 % en `NOMBRE`,
`CEDULA` y `HC`.** Son las tres categorías que identifican directamente al paciente y no
admiten tolerancia: un único escape invalida la página.

Para `TELEFONO`, `EMAIL`, `FECHA` y `DIRECCION` el objetivo es también el 100 %, pero un
escape se documenta y se corrige sin bloquear el resto del lote.

Cuando se detecta un escape, el ciclo de corrección es:

1. **Identificar por qué se escapó** mirando el rectángulo ausente en la imagen de revisión:
   el OCR no leyó el valor, la etiqueta del formulario no está en `ETIQUETAS_FORMULARIO`, la
   etiqueta se leyó mal, o el valor estaba fuera de toda etiqueta (nombre manuscrito en medio
   de la prosa).
2. **Corregir la configuración**, según el caso:
   - Si el valor va junto a una etiqueta impresa que el pipeline no conoce, añadir esa
     etiqueta a `ETIQUETAS_FORMULARIO` en
     `s11/anonimizador_ocr/anonimizador_ocr/config.py`, incluida la variante tal como la
     leyó el OCR (`--volcar-ocr` muestra el texto crudo de cada cabecera).
   - Si el valor está siempre en la misma posición del formulario, definir una **zona fija**
     en la plantilla JSON de zonas (`plantillas/*.json`), medida con
     `herramientas/medir_zonas.py`, y pasarla con `--zonas`. Las zonas fijas se tachan
     aunque el OCR no lea nada, así que son la respuesta correcta para el manuscrito
     ilegible, las firmas y los sellos.
   - Si el valor cae fuera de cualquier estructura, ajustar los parámetros de tachado
     (`--ancho-etiqueta`, `--alto-celda`, `--psm`, `--dpi`) o aceptar que esa página se
     resuelve con tachado manual.
3. **Re-ejecutar el pipeline completo** sobre el documento. No se parchea la imagen a mano:
   la corrección tiene que quedar en la configuración para que sea reproducible en el resto
   del lote y en las historias que se procesen después.
4. **Volver a verificar** la página desde el paso 1, con el mismo procedimiento y los dos
   revisores. Se anota en el CSV consolidado la iteración a la que corresponde cada conteo.
5. **Regenerar los agregados publicables** con `python s11/sanitizar_evidencias.py`, para que
   el JSON de evidencia corresponda a la corrida definitiva.

Una corrección que resuelve un escape en una página suele resolverlo en varias, porque las
etiquetas y las zonas son propiedades del formulario, no de la página. Por eso conviene
completar el conteo de las 20 páginas antes de empezar a corregir, y no alternar.

## 7. Página de riesgo concentrado

**La página 10 concentra el riesgo de esta corrida y se revisa primero, por los dos
revisores, con atención reforzada.**

Es la única página que el pipeline derivó automáticamente a revisión manual: su confianza
OCR media es de 40.2, muy por debajo del umbral de 55 configurado en
`umbral_pagina_manuscrita`. Frente a una media de 74.6 y una mediana de 80.3 en el resto del
documento, ese valor apunta a una página predominantemente manuscrita.

La consecuencia es directa: si el OCR no lee el texto, las capas de reglas, contexto y NER no
tienen sobre qué operar, y la protección depende únicamente del tachado junto a etiquetas
guiado por la máscara de tinta y de las zonas fijas. La página produjo 3 hallazgos y 2
rectángulos, cifras bajas para una página con 329 palabras reconocidas, lo que es compatible
con que haya identificadores manuscritos sin detectar. Es la candidata más probable a
necesitar una zona fija o tachado manual.

El resto del documento se procesó íntegramente con Tesseract (las 20 páginas tienen
`fuente_palabras = tesseract`, ninguna traía capa de texto aprovechable) y no requirió
corrección de inclinación (ángulo corregido 0.0 en todas). Aun así, todas las páginas se
verifican: el umbral de 55 es un filtro de cribado, no una garantía sobre las páginas que lo
superan.

## 8. Entregables

Al cerrar la verificación se produce:

- `verificacion_humana_<iniciales>.csv`, uno por revisor, con los conteos independientes.
  Permanecen locales mientras contengan observaciones no revisadas.
- `verificacion_humana_consolidada.csv`, con los valores resueltos por el tercer integrante.
- Una tabla de recall por categoría, con su denominador explícito, y las métricas de acuerdo
  entre revisores.
- La declaración de qué páginas superan el criterio de bloqueo y pueden entrar al corpus.

Ninguno de estos entregables contiene texto identificatorio. La columna
`observacion_sin_texto` de la plantilla existe precisamente para eso: **no se escribe en ella
ningún dato identificatorio** (ni nombres, ni cédulas, ni teléfonos, ni direcciones, ni
correos, ni números de historia clínica, ni fragmentos de los mismos). Se escriben
descripciones de la situación, del tipo:

- `valor manuscrito parcialmente visible en esquina superior`
- `rectangulo desplazado a la derecha, deja ver el final del campo`
- `firma ilegible, no se cuenta como instancia`
- `celda de tabla tachada completa, se pierde el dato clinico de la columna`
- `dos instancias de la misma categoria en la misma linea, difícil de separar`

Un revisor que necesite señalar *cuál* valor concreto tiene el problema lo hace por su
posición en la página (cuadrante, número de fila de la tabla, campo del formulario), nunca
por su contenido.
