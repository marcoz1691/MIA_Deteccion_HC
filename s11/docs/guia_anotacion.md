# Guía de anotación de inconsistencias clínicas — Corpus CITIMED Odontología

**Proyecto:** MIA_Deteccion_HC — Detección automática de inconsistencias en historias clínicas
**Programa:** Maestría en Inteligencia Artificial Aplicada — Universidad de las Américas (UDLA), Ecuador
**Anotadores:** Patricio Bayas Meza, José Puebla Paladines, Marco Zurita Rojas
**Versión:** S11
**Documento asociado obligatorio:** `s11/docs/anexo_etico.md`

---

## 1. Propósito y alcance

Esta guía fija los criterios con los que los tres integrantes del equipo etiquetan oraciones de
historias clínicas de CITIMED como consistentes o inconsistentes. Su objetivo no es capturar la
opinión clínica de cada anotador, sino producir un corpus **reproducible**: dos personas que sigan
esta guía deben asignar la misma etiqueta a la misma oración, y una tercera debe poder auditar por
qué. El acuerdo entre anotadores es, por tanto, un requisito del corpus y no un subproducto.

El corpus resultante se usa para evaluar la transferencia del detector desde el conjunto público
MEDEC (inglés, dominio hospitalario general) al dominio real de destino (español, odontología). Se
consume mediante `s7/eval_citimed.py`, en modo `cross_domain` —entrenar con MEDEC y evaluar en
CITIMED— y en modo `fine_tune` —partición interna de CITIMED al 80/20—.

### 1.1 Advertencia previa de privacidad

**Las oraciones que se anotan provienen de PDF ya anonimizados.** Antes de comenzar, cada anotador
debe haber leído `s11/docs/anexo_etico.md`.

> **Si durante la anotación aparece un identificador residual** —un nombre, una cédula, un número de
> historia clínica, un teléfono, una dirección, una fecha de nacimiento— **el anotador debe detener
> la anotación de inmediato**, no copiar el identificador a ningún archivo, mensaje ni nota
> personal, y reportar el hallazgo indicando únicamente el `nota_id`, el `oracion_id` y la
> categoría del identificador encontrado. El lote completo se retira, se corrige la causa en el
> pipeline y se reprocesa según el ciclo de corrección del §6 del anexo ético. **No se continúa
> anotando sobre un lote con fuga confirmada.**

El anonimizador prioriza el recall, de modo que es esperable encontrar sobre-tachado: palabras
inocuas redactadas junto al identificador. Eso no es una fuga y no interrumpe la anotación; se trata
como una oración truncada (§7.3).

---

## 2. Definición operativa de inconsistencia clínica

Se etiqueta como **inconsistente** (`label = 1`) una oración que cumpla **las tres condiciones**
siguientes de forma simultánea:

1. **Afirmación clínica.** La oración enuncia un diagnóstico, una conducta, un procedimiento, una
   prescripción o una atribución etiológica, en modo asertivo. No es una pregunta, una hipótesis
   declarada como tal, ni una transcripción de lo que refiere el paciente.
2. **Conflicto verificable en el registro.** La afirmación contradice otra información presente en
   la propia oración o en la nota (hallazgos, alergias, antecedentes, resultados, edad, peso,
   diagnóstico previo), o contradice un conocimiento clínico estándar y no controvertido del dominio
   odontológico. El conflicto debe poder señalarse: el anotador tiene que ser capaz de nombrar el
   elemento con el que la afirmación choca.
3. **Localización en esta oración.** La oración es el lugar donde el error se materializa. Si la
   oración solo aporta el dato que revela el error de otra, la etiqueta corresponde a la otra
   (§7.4).

### 2.1 Criterios de exclusión

**No** se etiqueta como inconsistente una oración que solo presente:

- **Incertidumbre declarada.** Diagnósticos diferenciales, sospechas, hipótesis a confirmar,
  formulaciones con «probable», «a descartar», «se plantea», «pendiente de confirmación».
- **Discurso referido.** Lo que el paciente refiere, niega o cree, aunque sea clínicamente
  incorrecto. La inconsistencia es del registro profesional, no del relato del paciente.
- **Deficiencias de redacción o de OCR.** Faltas de ortografía, gramática defectuosa, abreviaturas
  no estándar, texto cortado o caracteres corruptos, mientras el contenido clínico siga siendo
  identificable y correcto.
- **Omisiones.** La ausencia de un dato o de una conducta esperada no es una inconsistencia
  localizable en una oración. Solo se etiqueta lo que está escrito y es erróneo.
- **Discrepancia de estilo o de escuela.** Variaciones de práctica legítimas entre profesionales,
  protocolos institucionales alternativos, preferencias de material o de técnica que no contradicen
  el estándar.
- **Errores puramente administrativos.** Códigos de facturación, casillas mal marcadas, numeración
  de piezas en un campo de formulario sin contenido clínico asociado.
- **Contenido que exige juicio experto no disponible.** Si el anotador necesita un dato que la nota
  no contiene, o un criterio especializado que no domina, para decidir si hay conflicto, la oración
  **no** se etiqueta como positiva: se marca para dirimencia (§6.4). La duda no se resuelve
  etiquetando.

### 2.2 Regla de una sola oración positiva por nota

Cada nota tiene **como máximo una** oración con `label = 1`. Esta restricción no es arbitraria: la
métrica de localización del proyecto (`localizacion_top1` en `s7/metricas.py`) toma la primera
oración positiva de cada nota como referencia única y la compara con la oración de mayor puntuación
del modelo. Un corpus con dos positivos en la misma nota produciría métricas de localización mal
definidas y no comparables con las obtenidas sobre MEDEC.

En consecuencia:

- Nota sin inconsistencia: todas sus oraciones llevan `label = 0`.
- Nota con inconsistencia: exactamente una oración lleva `label = 1` y el resto `label = 0`.
- Si el anotador identifica dos inconsistencias independientes en una misma nota, aplica la regla de
  prioridad del §7.5.

---

## 3. Unidad de anotación: la oración

La unidad de anotación es la **oración**, en coherencia con la reformulación nota→oración que
sostiene el proyecto: una alerta útil para el profesional debe señalar el fragmento concreto que
debe revisar, no la nota entera.

### 3.1 Segmentación

Las oraciones llegan ya segmentadas y numeradas por el pipeline de preparación del corpus. **El
anotador no re-segmenta.** Si una unidad está manifiestamente mal cortada —dos oraciones fundidas en
una, o una oración partida en dos por un punto de abreviatura— lo registra como incidencia de
segmentación y continúa; el arreglo se hace en el pipeline y se reprocesa el lote, no se corrige a
mano en el CSV, porque eso desalinearía los identificadores `oracion_id`.

### 3.2 Oraciones que dependen del contexto de la nota

La etiqueta se asigna **a la oración**, pero se decide **leyendo la nota completa**. El
procedimiento es siempre el mismo:

1. Leer la nota íntegra antes de etiquetar cualquiera de sus oraciones.
2. Determinar si la nota contiene una inconsistencia y cuál es.
3. Localizar la oración donde esa inconsistencia se materializa y etiquetarla.
4. Etiquetar como `0` el resto de las oraciones de la nota, **incluidas las que aportaron la
   evidencia** del conflicto.

La consecuencia práctica es que una misma oración puede ser positiva en una nota y negativa en otra.
«Se prescribe amoxicilina 500 mg cada 8 horas» es correcta en una nota sin alergias registradas e
incorrecta en una nota que documenta alergia a penicilinas. Esto es deliberado y refleja la
naturaleza del problema: el modelo debe aprender señales de superficie que correlacionan con el
error, y la evaluación mide hasta dónde llega esa aproximación.

Cuando la evidencia del conflicto está en otra oración, el anotador **anota en el registro de
dirimencia el `oracion_id` de la oración que aporta la evidencia**. Ese dato no forma parte del CSV
del corpus, pero es indispensable para que el tercer integrante pueda auditar la decisión sin
releer la nota entera.

---

## 4. Tipos de error

El corpus reutiliza la taxonomía de MEDEC, para que las métricas por tipo sean comparables entre
ambos conjuntos. Los cinco valores admitidos son los que efectivamente circulan por el pipeline del
proyecto, tal como aparecen en `s10/evidencias/analisis_por_tipo.json`.

| Valor de `error_type` | Denominación | Naturaleza del error |
|---|---|---|
| `diagnosis` | Diagnóstico | El diagnóstico enunciado no corresponde a los hallazgos, pruebas o antecedentes documentados |
| `management` | Conducta | La conducta, el seguimiento, la derivación o la solicitud de pruebas es inadecuada para la situación descrita |
| `treatment` | Tratamiento | El procedimiento terapéutico indicado o realizado no corresponde al diagnóstico establecido |
| `pharmacotherapy` | Farmacoterapia | Fármaco, dosis, vía, frecuencia o duración incorrectos; contraindicación o interacción no considerada |
| `causalOrganism` | Agente causal | Se atribuye el cuadro a un agente etiológico que no le corresponde |

**Todos los ejemplos de esta sección son ficticios**, construidos por el equipo para ilustrar los
criterios. No proceden de ninguna historia clínica real.

### 4.1 `diagnosis` — Diagnóstico

El diagnóstico consignado contradice los hallazgos clínicos, radiográficos o de laboratorio que la
propia nota documenta, o es incompatible con la estadificación descrita.

**Positivo 1.** «La radiografía periapical muestra radiolucidez apical en la pieza 46 y la prueba de
vitalidad pulpar resulta negativa; se establece el diagnóstico de gingivitis marginal localizada.»
*Motivo:* los hallazgos describen una patología periapical de origen pulpar y el diagnóstico
enunciado corresponde a una afección gingival distinta.

**Positivo 2.** «Se registra movilidad grado III y pérdida ósea radiográfica del 60 % en el sector
anteroinferior; se diagnostica periodontitis estadio I.» *Motivo:* la estadificación declarada
contradice la magnitud de la pérdida ósea y la movilidad consignadas en la misma oración.

**Negativo (caso límite).** «Se plantea como diagnóstico diferencial pulpitis irreversible o
periodontitis apical aguda, pendiente de prueba térmica.» *Motivo:* la incertidumbre está declarada
de forma explícita; enumerar diferenciales no es afirmar un diagnóstico. Excluido por §2.1,
incertidumbre declarada.

### 4.2 `management` — Conducta

La conducta adoptada —seguimiento, derivación, solicitud de estudios, decisión de continuar o
suspender— no se corresponde con la situación clínica descrita.

**Positivo 1.** «Ante la sospecha de fractura radicular vertical en la pieza 21 se decide control
clínico en doce meses sin estudio de imagen complementario.» *Motivo:* la conducta de espera
prolongada sin imagen no corresponde a la sospecha planteada.

**Positivo 2.** «El paciente refiere dolor torácico opresivo irradiado al brazo izquierdo durante la
infiltración anestésica; se indica continuar el procedimiento y reevaluar al final de la jornada.»
*Motivo:* la conducta omite la interrupción y la derivación urgente que el cuadro descrito exige.
Nótese que lo que el paciente refiere no es lo etiquetado: lo etiquetado es la decisión profesional
consignada en la misma oración.

**Negativo (caso límite).** «Se solicita tomografía computarizada de haz cónico para planificar la
colocación del implante en la zona de la pieza 36.» *Motivo:* la conducta es adecuada al propósito
declarado. Que el estudio sea de alto costo o que otro profesional prefiriera una radiografía
panorámica es discrepancia de escuela, excluida por §2.1.

### 4.3 `treatment` — Tratamiento

El procedimiento terapéutico indicado o realizado no corresponde al diagnóstico establecido en la
misma nota, por exceso, por defecto o por naturaleza.

**Positivo 1.** «Diagnóstico: caries oclusal en dentina sin compromiso pulpar en la pieza 37; plan de
tratamiento: exodoncia de la pieza 37.» *Motivo:* el tratamiento es desproporcionado respecto del
diagnóstico consignado, que admite tratamiento restaurador conservador.

**Positivo 2.** «Se confirma pulpitis reversible en la pieza 14 y se realiza tratamiento de conducto
radicular en la misma sesión.» *Motivo:* el diagnóstico de reversibilidad pulpar es incompatible con
el tratamiento endodóntico ejecutado.

**Negativo (caso límite).** «Se realiza exodoncia de la pieza 48 por pericoronitis recurrente y
posición ectópica con imposibilidad de erupción.» *Motivo:* el tratamiento se corresponde con el
diagnóstico y la justificación consta en la misma oración.

### 4.4 `pharmacotherapy` — Farmacoterapia

Error en el fármaco, la dosis, la vía, la frecuencia o la duración; contraindicación documentada no
respetada; interacción relevante no considerada.

**Positivo 1.** «Antecedente de alergia documentada a penicilinas; se prescribe amoxicilina 500 mg
cada 8 horas durante 7 días.» *Motivo:* la prescripción contradice una contraindicación registrada
en la misma oración.

**Positivo 2.** «Paciente de 6 años, 20 kg de peso; se indica ibuprofeno 800 mg cada 8 horas por vía
oral.» *Motivo:* la dosis consignada excede en un orden de magnitud el rango pediátrico razonable
para el peso declarado.

**Negativo (caso límite).** «Se prescribe paracetamol 1 g cada 8 horas durante 3 días para el dolor
posoperatorio de la exodoncia.» *Motivo:* fármaco, dosis, frecuencia y duración son estándar para un
adulto y la indicación es coherente. La ausencia de mención del peso del paciente es una omisión, no
una inconsistencia (§2.1).

### 4.5 `causalOrganism` — Agente causal

Se atribuye el cuadro clínico a un microorganismo o agente etiológico que no le corresponde.

**Positivo 1.** «Se diagnostica candidiasis pseudomembranosa del paladar, causada por *Streptococcus
mutans*.» *Motivo:* la atribución etiológica contradice el diagnóstico enunciado en la misma
oración.

**Positivo 2.** «La gingivitis ulceronecrosante del paciente se atribuye a infección por virus del
papiloma humano.» *Motivo:* atribución viral de un cuadro de etiología bacteriana.

**Negativo (caso límite).** «Se toma muestra del absceso submandibular para cultivo; el informe
reporta flora mixta con predominio de anaerobios estrictos.» *Motivo:* la oración transcribe un
resultado de laboratorio coherente con el cuadro; no formula una atribución errónea.

### 4.6 Prioridad entre tipos

Cuando una oración positiva encaja en más de un tipo, se aplica el siguiente orden de prioridad,
que asigna el tipo al **elemento que hace falsa la afirmación**:

1. `pharmacotherapy`, si el error está en el fármaco, dosis, vía, frecuencia o duración.
2. `causalOrganism`, si el error está en la atribución etiológica.
3. `diagnosis`, si el error está en el diagnóstico enunciado.
4. `treatment`, si el error está en el procedimiento terapéutico.
5. `management`, como categoría residual para errores de conducta, seguimiento o derivación.

Ejemplo de aplicación: «Diagnóstico: gingivitis leve; se indica exodoncia de todas las piezas» es
`treatment`, no `diagnosis`, porque el diagnóstico es plausible y lo que falla es el procedimiento.

---

## 5. Esquema de datos

El corpus se entrega como un único CSV codificado en **UTF-8**, con la primera fila de cabecera y
comillas dobles en los campos de texto. El archivo se deposita en `data/citimed_odontologia.csv`,
ruta declarada en `s7/config.yaml` y excluida del control de versiones por `.gitignore`. La
plantilla de referencia es `data/citimed_odontologia.example.csv`.

| Columna | Tipo | Significado | Valores admitidos |
|---|---|---|---|
| `oracion` | Texto | Oración tal como quedó tras la anonimización y la segmentación, sin modificaciones del anotador | Cadena no vacía, mínimo 3 caracteres. Se preserva la puntuación y los marcadores de redacción |
| `label` | Entero | Etiqueta de inconsistencia | `0` (consistente) o `1` (inconsistente). Nunca vacío |
| `nota_id` | Entero | Identificador de la nota clínica a la que pertenece la oración | Entero ≥ 0, estable y único por nota. No debe derivarse del número de historia clínica ni de ningún identificador del paciente |
| `oracion_id` | Entero | Posición de la oración dentro de su nota | Entero consecutivo desde `0`, en orden de aparición, sin huecos ni repeticiones dentro de la misma nota |
| `error_type` | Texto | Tipo de error, solo cuando `label = 1` | `diagnosis`, `management`, `treatment`, `pharmacotherapy`, `causalOrganism`. **Vacío** cuando `label = 0` |

### 5.1 Correspondencia con el código

`s7/eval_citimed.py` exige de forma estricta únicamente las dos columnas declaradas en
`s7/config.yaml` bajo `citimed.col_texto` (`oracion`) y `citimed.col_label` (`label`); las renombra
internamente y falla con error explícito si faltan. Las columnas `nota_id` y `oracion_id` están
declaradas en la configuración (`col_nota_id`, `col_oracion_id`) y son **imprescindibles** para la
métrica de localización, porque `localizacion_top1` agrupa por nota y compara identificadores de
oración. La correspondencia de nombres es la siguiente:

| Columna del CSV de CITIMED | Nombre interno en `s7/metricas.py` |
|---|---|
| `nota_id` | `text_id` |
| `oracion_id` | `sid` |
| `oracion` | `oracion` |
| `label` | `label` |
| `error_type` | `error_type` |

**Pendiente técnico declarado.** En la versión actual, `cargar_citimed` renombra `col_texto` y
`col_label`, pero no `col_nota_id` ni `col_oracion_id`, y `eval_citimed.py` no invoca
`localizacion_top1`. Por tanto, calcular la localización top-1 sobre CITIMED exigirá renombrar
`nota_id`→`text_id` y `oracion_id`→`sid` en el script de evaluación. Esta guía documenta el esquema
de datos correcto; **el ajuste del script queda pendiente y no forma parte de este documento.**

### 5.2 Validaciones obligatorias antes de entregar el CSV

Cada lote se valida contra las reglas siguientes antes de considerarse cerrado:

1. Cabecera exactamente igual a la de `data/citimed_odontologia.example.csv`.
2. `label` toma solo los valores `0` y `1`; sin celdas vacías.
3. Cada `nota_id` tiene **como máximo una** fila con `label = 1` (§2.2).
4. `error_type` está vacío en todas las filas con `label = 0` y contiene uno de los cinco valores
   admitidos, escrito exactamente como en la tabla del §4, en todas las filas con `label = 1`.
5. El par (`nota_id`, `oracion_id`) es único en todo el archivo.
6. Los `oracion_id` de cada nota forman una secuencia consecutiva desde `0`.
7. Ninguna celda contiene identificadores del paciente (§1.1).
8. El archivo abre correctamente con `pandas.read_csv` en UTF-8, sin filas descartadas.

### 5.3 Sobre la denominación de los tipos de error

La plantilla `data/citimed_odontologia.example.csv` emplea, a modo ilustrativo, los valores
`Medication` y `Diagnosis`, con inicial mayúscula. Los valores que realmente circulan por el
pipeline son los cinco de minúscula camello listados en el §4, como acredita
`s10/evidencias/analisis_por_tipo.json`. La divergencia tiene una consecuencia observable: el filtro
de tipos críticos de `s7/analisis_por_tipo.py` busca `"Medication"` y `"Diagnosis"`, y por eso el
campo `criticos` del informe de la entrega S10 aparece vacío. **Esta guía adopta como canónicos los
valores en minúscula camello.** Unificar la plantilla de ejemplo y el filtro de tipos críticos es un
pendiente de código ajeno a este documento y se deja consignado para el grupo.

---

## 6. Procedimiento de doble anotación

### 6.1 Reparto del trabajo

El corpus se divide en lotes. Sobre el total de oraciones:

- El **30 % se anota por duplicado y en doble ciego**: dos integrantes lo etiquetan de forma
  independiente, sin acceso a las decisiones del otro, sin comentarlas y sin trabajar sobre el mismo
  archivo. Este subconjunto se selecciona **por notas completas**, con muestreo aleatorio y semilla
  fija (42, la del resto del proyecto), nunca por oraciones sueltas, porque el §3.2 exige leer la
  nota íntegra para decidir.
- El **70 % restante se anota una sola vez**, distribuido entre los tres integrantes.

Los archivos de la fase de doble ciego se nombran `lote_<n>_anotador_<inicial>.csv` y no se
comparten hasta que ambos anotadores declaran su lote cerrado.

### 6.2 Cálculo del acuerdo

Sobre el subconjunto duplicado se calcula el **kappa de Cohen** de la columna `label`:

```
kappa = (Po - Pe) / (1 - Pe)
```

donde `Po` es la proporción de oraciones en que ambos anotadores coinciden (acuerdo observado) y
`Pe` es la proporción de acuerdo esperada por azar, obtenida a partir de las distribuciones
marginales de cada anotador. Se calcula con `sklearn.metrics.cohen_kappa_score`.

Se reportan **tres cifras** y no solo una:

1. Kappa sobre `label` en todo el subconjunto duplicado, que es la medida principal.
2. Acuerdo simple (`Po`), como referencia, advirtiendo que con prevalencia baja el acuerdo simple
   es engañosamente alto: coincidir en que el 95 % de las oraciones es negativo no demuestra nada.
3. Kappa sobre `error_type`, restringido a las oraciones que **ambos** anotadores marcaron como
   positivas. Esta cifra mide la consistencia de la taxonomía, no la de la detección, y se informa
   por separado.

### 6.3 Interpretación de los rangos

Se adopta la escala convencional de Landis y Koch:

| Rango de κ | Interpretación | Consecuencia para el proyecto |
|---|---|---|
| < 0,00 | Peor que el azar | Error de procedimiento o de alineación de archivos; investigar antes que reanotar |
| 0,00 – 0,20 | Insignificante | La guía no es operativa; reescribir criterios y reanotar desde cero |
| 0,21 – 0,40 | Aceptable bajo | Insuficiente; sesión de calibración y reanotación del lote |
| 0,41 – 0,60 | Moderado | Insuficiente para el criterio del proyecto; calibrar y reanotar |
| 0,61 – 0,80 | Sustancial | **Umbral mínimo de aceptación del proyecto: κ ≥ 0,70** |
| 0,81 – 1,00 | Casi perfecto | Acuerdo satisfactorio |

**Criterio de bloqueo.** No se anota el 70 % restante hasta que el subconjunto duplicado alcance
**κ ≥ 0,70** sobre `label`. Si el valor obtenido es inferior, el procedimiento es: revisar en
conjunto todas las discrepancias, identificar el criterio ambiguo, **modificar esta guía** añadiendo
la regla que faltaba, y reanotar el subconjunto duplicado con la guía corregida. El kappa se
recalcula sobre la nueva anotación. Cada iteración se registra con su versión de guía y su kappa,
para que el informe final pueda documentar la evolución del acuerdo.

El kappa alcanzado, el tamaño del subconjunto duplicado y el número de iteraciones se reportan en el
informe final. **Un corpus sin kappa reportado no se considera entregable.**

### 6.4 Desempate

Toda discrepancia entre los dos anotadores del subconjunto duplicado, y toda oración que un anotador
haya marcado como dudosa en la fase de anotación simple, se resuelve así:

1. El **tercer integrante**, que no participó en la anotación de esa nota, emite un voto sin conocer
   la identidad de los anotadores discrepantes.
2. Su decisión es vinculante y se registra en el **registro de dirimencia** con: `nota_id`,
   `oracion_id`, etiqueta de cada anotador, etiqueta final, y **la regla de esta guía** que sustenta
   la decisión, citada por su número de sección.
3. Si el dirimente concluye que ninguna regla de la guía cubre el caso, **no decide por criterio
   propio**: la oración se deja fuera del corpus, se abre un punto en la guía y el caso se resuelve
   en la siguiente sesión de calibración de los tres integrantes.
4. Si la discrepancia se repite en tres o más casos con el mismo patrón, deja de tratarse como
   dirimencia individual: es un defecto de la guía y se corrige en el §7.

---

## 7. Casos límite y reglas de desempate frecuentes

Las reglas de esta sección son de aplicación obligatoria y prevalecen sobre la intuición del
anotador. Cada nueva regla incorporada tras una sesión de calibración se añade aquí con su fecha.

### 7.1 Abreviaturas

Las historias odontológicas abundan en abreviaturas. El pipeline normaliza algunas de forma
automática (`Rx`→radiografía, `Tx`→tratamiento, `Dx`→diagnóstico, `Hx`→historia, `O.D.`→odontología,
según `ABREV_ODONTO` en `s7/preprocesamiento.py`), pero el anotador trabaja sobre el texto sin
normalizar.

- **Abreviatura de significado inequívoco en el contexto:** se interpreta y se anota con normalidad.
  «Dx: pulpitis irreversible; Tx: obturación» se lee como diagnóstico y tratamiento.
- **Abreviatura ambigua que cambia la etiqueta:** si la etiqueta depende de cuál de dos lecturas
  posibles se adopte, la oración va a dirimencia. No se elige la lectura que hace el caso
  interesante.
- **Abreviatura de dosis o unidad:** `mg`, `ml`, `g`, `c/8h`, `qd`, `VO` se interpretan con su
  significado estándar. Si la unidad falta por completo y de ello depende la corrección de la dosis,
  la oración **no** se etiqueta como positiva: es una deficiencia de registro, no una prescripción
  errónea demostrable.
- **Nomenclatura dental:** se asume notación FDI de dos dígitos (pieza 36, pieza 21). Si una nota usa
  otro sistema de forma consistente, se registra como observación del lote y se aplica la misma
  interpretación en todas sus oraciones.

### 7.2 Negaciones

La negación invierte el sentido clínico y es la fuente más frecuente de discrepancia. El sistema
extrae explícitamente un rasgo de negación mediante la expresión `NEG_ES` (`no`, `sin`, `niega`,
`negativo`, `negativa`, `ausente`), lo que hace especialmente importante que la anotación sea
coherente con ella.

- **Se anota siempre el sentido resultante, no las palabras.** «No se evidencia compromiso pulpar; se
  realiza tratamiento de conducto» es positiva `treatment`: la negación es lo que hace inconsistente
  la conducta.
- **Negación como descarte correcto:** «Se descarta fractura radicular tras la tomografía» es
  negativa. Descartar es una conclusión legítima.
- **Doble negación:** se reduce a su sentido afirmativo antes de decidir.
- **Alcance dudoso de la negación:** cuando no se puede determinar si la negación afecta a un solo
  elemento o a la enumeración completa —«sin dolor ni movilidad ni sangrado a la exploración de las
  piezas 36 y 37»— y de ello depende la etiqueta, la oración va a dirimencia.
- **Negación aportada por el paciente:** «el paciente niega alergias» es discurso referido. Si el
  registro documenta una alergia en otra oración, la inconsistencia se materializa en la
  prescripción, no en esta oración.

### 7.3 Oraciones truncadas por el OCR o por la anonimización

- **Truncamiento que no afecta al contenido clínico decisivo:** se anota con normalidad. Un
  encabezado cortado o un marcador de redacción en un campo administrativo no impide decidir.
- **Truncamiento que afecta al elemento del que depende la etiqueta** —la dosis, el nombre del
  fármaco, la pieza dental, el diagnóstico—: la oración se etiqueta `label = 0` y se registra como
  **oración degradada** en el registro del lote. No se etiqueta como positiva por sospecha, y no se
  reconstruye el texto faltante por conjetura.
- **Oración ilegible en más de la mitad de su extensión:** se excluye del corpus. Se registra el
  motivo y **no se renumeran** los `oracion_id` restantes de la nota; el hueco resultante se resuelve
  en el pipeline, que regenera la numeración consecutiva antes de emitir el CSV final.
- **Sobre-tachado del anonimizador:** se trata igual que el truncamiento de OCR. No es una fuga y no
  interrumpe la anotación.
- **Nunca se consulta el PDF original** para reconstruir una oración degradada. Ese material está
  fuera del alcance de la anotación por el §5 del anexo ético.

### 7.4 Inconsistencia repartida entre dos oraciones

Es el caso más común: una oración documenta el hecho (alergia, diagnóstico, hallazgo) y otra comete
el error (prescripción, tratamiento, conducta). Dado el §2.2, solo una puede ser positiva.

**Regla:** se etiqueta la oración que contiene **la afirmación errónea**, no la que aporta la
evidencia que la delata. La justificación es funcional: la alerta debe llevar al profesional al lugar
que debe corregir. Si el sistema señalara la oración que documenta la alergia, el profesional leería
un dato correcto y no sabría qué hacer con él.

Aplicación práctica:

| Configuración | Oración positiva |
|---|---|
| Oración A documenta alergia a penicilinas; oración B prescribe amoxicilina | B, `pharmacotherapy` |
| Oración A establece el diagnóstico; oración B indica un tratamiento incompatible | B, `treatment` |
| Oración A reporta un hallazgo radiográfico; oración B enuncia un diagnóstico que lo contradice | B, `diagnosis` |
| Oración A enuncia un diagnóstico erróneo; oración B indica el tratamiento correcto para ese diagnóstico erróneo | A, `diagnosis` |

La última fila merece atención: cuando el tratamiento es coherente con un diagnóstico equivocado, el
error está en el diagnóstico y el tratamiento es una consecuencia correcta de una premisa falsa. Se
etiqueta la premisa.

En todos los casos, el `oracion_id` de la oración que aporta la evidencia se consigna en el registro
de dirimencia como sustento de la decisión (§3.2).

### 7.5 Dos inconsistencias independientes en la misma nota

Cuando la nota contiene dos errores sin relación causal entre sí, se etiqueta uno solo, aplicando en
orden:

1. **Gravedad clínica potencial.** Prevalece el error con mayor capacidad de daño (una
   contraindicación farmacológica sobre un intervalo de control mal fijado).
2. **Prioridad de tipo** del §4.6, si la gravedad es equiparable.
3. **Orden de aparición**, quedándose con la primera, si los dos criterios anteriores no dirimen.

El segundo error se consigna en el registro de dirimencia con su `oracion_id` y su tipo. Esa nota
queda marcada como **nota de error múltiple** y se excluye del cálculo del kappa, porque la
discrepancia entre anotadores en estos casos reflejaría la regla de prioridad y no el criterio de
detección. El equipo reporta cuántas notas de error múltiple contiene el corpus, porque es una
limitación conocida de la comparabilidad con MEDEC.

### 7.6 Otros casos resueltos

- **Oración correcta que contradice el estándar por indicación justificada en la nota:** si la nota
  explicita la razón de la desviación («se mantiene la profilaxis antibiótica por antecedente de
  endocarditis»), no hay inconsistencia.
- **Copia y pega evidente entre notas:** una oración claramente arrastrada de otra atención se anota
  por su contenido en la nota donde aparece. Si contradice el resto de esa nota, es positiva.
- **Contradicción entre dos fechas de atención:** es un error de registro administrativo, no una
  inconsistencia clínica localizable. Excluido por §2.1.
- **Oración positiva cuyo tipo no encaja en ninguna de las cinco categorías:** la oración se excluye
  del corpus y el caso se lleva a calibración. No se fuerza el encaje en `management` por descarte
  sin discutirlo.

---

## 8. Flujo de trabajo del anotador

1. Confirmar que el lote proviene de un PDF anonimizado **con doble revisión cerrada** según el §6
   del anexo ético. No se anota material sin esa confirmación.
2. Leer esta guía completa antes de la primera sesión, y releer los §2 y §7 al inicio de cada
   sesión posterior.
3. Trabajar por notas completas, nunca por oraciones sueltas.
4. Para cada nota: leerla íntegra, decidir si contiene inconsistencia, localizar la oración,
   etiquetar, poner `0` en el resto.
5. Marcar como dudosa toda oración en que se haya vacilado más de un minuto, en lugar de forzar una
   decisión.
6. Cerrar la sesión ejecutando las validaciones del §5.2 sobre el archivo parcial.
7. No comentar decisiones con el otro anotador mientras el lote de doble ciego esté abierto.

### 8.1 Registros que acompañan al corpus

Además del CSV, cada lote produce tres registros en texto plano, **sin contenido de las oraciones**
más allá de lo estrictamente necesario para auditar:

| Registro | Contenido |
|---|---|
| Registro de dirimencia | `nota_id`, `oracion_id`, etiquetas discrepantes, etiqueta final, sección de la guía aplicada, `oracion_id` de la oración que aporta la evidencia |
| Registro de oraciones degradadas y excluidas | `nota_id`, `oracion_id`, motivo (truncamiento, ilegibilidad, tipo no encajable), decisión |
| Registro de incidencias | Errores de segmentación, notas de error múltiple, sospechas de identificador residual (solo identificadores de posición y categoría, §1.1) |

---

## 9. Marcadores pendientes de completar

| Sección | Marcador | Responsable |
|---|---|---|
| §5 | Volumen del corpus: número de notas, número de oraciones y prevalencia observada de `label = 1` | Equipo |
| §5.1 | Ajuste de `eval_citimed.py` para renombrar `nota_id`→`text_id` y `oracion_id`→`sid` y calcular la localización top-1 sobre CITIMED | Equipo (fuera del alcance de esta guía) |
| §5.3 | Unificación de los valores de `error_type` en la plantilla de ejemplo y en el filtro de tipos críticos de `s7/analisis_por_tipo.py` | Equipo (fuera del alcance de esta guía) |
| §6.1 | Composición de los lotes y asignación nominal de anotadores | Equipo |
| §6.2 | Kappa de Cohen obtenido, tamaño del subconjunto duplicado y número de iteraciones de calibración | Equipo |
| §6.3 | Registro de versiones de esta guía con el kappa alcanzado en cada una | Equipo |
| §7 | Reglas nuevas surgidas de las sesiones de calibración, con su fecha | Equipo |
| §7.5 | Número de notas de error múltiple excluidas del cálculo del kappa | Equipo |
