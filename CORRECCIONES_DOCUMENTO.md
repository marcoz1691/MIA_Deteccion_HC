# Correcciones al documento final — consolidado

Todo lo derivado de la auditoría cruzada contra el repositorio, en orden de aparición en el documento. Cada bloque trae el texto listo para pegar.

**Estado del repositorio auditado:** `main` @ `ec1838e` (2026-09-06)

---

## Índice por prioridad

### CRÍTICO — integridad y reproducibilidad
| # | Sección | Qué |
|---|---|---|
| 9 | Tabla 6 | AUPRC 0,419 → **0,398** (cifra de otra corrida) |
| 12 | §7.2.7 (nuevo) | Declarar el alcance de cuatro ejes MVP |
| 13 | Tabla 8 | Nota al pie con la fecha del *prompt* |
| 15 | §7.4 | Falta la evidencia de la corrida v2 |
| 19 | §7.5.5 | Afirma que se anonimizan nombres del personal sanitario — no se cumple |
| 22 | Referencias | 13 → 20+; LOPDP y HL7 FHIR citados sin referencia; error de año en Bowman |

### IMPORTANTE — puntos de rúbrica
| # | Sección | Qué |
|---|---|---|
| 1–8 | §4.1, §5.1, §6.5.1, §7.1.3, §7.1.4, §7.2.6, §7.5.1, Tabla 4 | DVC / MLflow / LangChain / contenedores |
| 20 | §7.5.5 | Título invierte el significado |
| 23 | Varias | Numeración de figuras y secciones |
| 24 | Objetivo 4 | Sintaxis rota |

### MEJORA — evidencia ya calculada, sin reportar
| # | Sección | Qué |
|---|---|---|
| 10 | §6.4.3 | Sesgo de idioma medido (Δ AUC −0,0395) |
| 11 | §6.4.5 | TF-IDF rinde **mejor** en español |
| 14 | §7.3.3 | Prueba de McNemar |
| 16 | §9 | Ruta de ampliación de ejes |

---

# CAPÍTULO 3 — OBJETIVOS

## 24. Objetivo específico 4 — sintaxis [IMPORTANTE]

Al quitar el inciso temporal de S11 quedó agramatical. Sustituir el arranque:

> **Evaluar e integrar los componentes del sistema** mediante pruebas funcionales en escenarios clínicos simulados, con el fin de validar su interoperabilidad y desempeño…

*(el resto de la viñeta se mantiene sin cambios)*

---

# CAPÍTULO 4 — ALCANCE

## 8. §4.1 «Incluye» — pipeline de MLOps [IMPORTANTE]

Sustituir el bloque «Implementación de pipeline de MLOps»:

> - Implementación de prácticas de MLOps:
>   - Registro de experimentos mediante artefactos versionados con metadatos y métricas
>   - Versionado de código con Git y del modelo entrenado como artefacto serializado
>   - Automatización de integración continua con GitHub Actions

---

# CAPÍTULO 5 — PLANIFICACIÓN Y COSTOS

## 1. §5.1 — párrafo introductorio [IMPORTANTE]

> Para la ejecución, control y seguimiento del proyecto se adoptó un marco de trabajo híbrido que combina la agilidad iterativa de Scrum con prácticas de ingeniería de aprendizaje automático (MLOps) y control de versiones mediante Git.

*(elimina «DVC y MLflow» de esta frase)*

## 2. §5.1 — viñeta «MLOps y DevOps» [IMPORTANTE]

> **MLOps y DevOps:** El ciclo de vida del modelo se gestiona mediante prácticas implementadas directamente sobre el repositorio del proyecto, sin plataformas externas de orquestación. La reproducibilidad se asegura con una semilla única (*seed* = 42) declarada en la configuración central; el versionado del código se realiza con Git y GitHub bajo un esquema de ramas por funcionalidad e integración mediante *pull request*; las dependencias del núcleo analítico se fijan con versiones exactas en `requirements.txt`, y las de desarrollo se aíslan en un archivo independiente; y la integración continua se ejecuta en GitHub Actions, que ante cada incorporación de código a la rama principal corre la suite de regresión, el conjunto dorado de evaluación y una prueba de humo contra la API en ejecución.

## 3. §5.1.1 y §5.1.2 — apartados nuevos [IMPORTANTE]

> ### 5.1.1. Registro de experimentos y trazabilidad de las corridas
>
> El seguimiento de experimentos se resuelve mediante artefactos JSON versionados en el repositorio, en lugar de un servidor de *tracking*. Cada ejecución escribe un archivo con sus metadatos y métricas —comando ejecutado, marca temporal UTC, modelo empleado, temperatura, tamaño de muestra, tarifas aplicadas e intervalos de confianza calculados por *bootstrap*—, de modo que toda cifra reportada en este documento puede rastrearse hasta el archivo que la produjo. Complementariamente, las llamadas al modelo de lenguaje se almacenan en una caché indexada por el hash SHA-256 del *prompt*, lo que permite reejecutar una evaluación completa de forma determinista y sin costo adicional de interfaz de programación de aplicaciones. El registro de inferencias del prototipo se conserva en una bitácora de auditoría que almacena únicamente el hash de cada nota analizada, nunca su texto, lo que preserva la trazabilidad operativa sin retener información clínica.
>
> Se evaluó el uso de MLflow para cubrir esta función y se descartó en la presente fase por una incompatibilidad de dependencias: MLflow 2.x requiere una versión de la librería NumPy anterior a la 2.0, mientras que el resto del núcleo analítico opera sobre NumPy 2.4.4. La restricción y la vía de instalación en un entorno virtual aislado quedan documentadas en el repositorio, y su adopción se plantea entre las recomendaciones de escalamiento del capítulo 8.
>
> ### 5.1.2. Versionado de datos y gobernanza de la información
>
> El proyecto no incorpora una herramienta de versionado de datos como DVC. La decisión responde de manera directa al modelo de gobernanza adoptado: las historias clínicas originales, las salidas del módulo de anonimización, las imágenes de revisión y los archivos que contienen texto clínico están excluidos del control de versiones y permanecen bajo custodia local, por lo que no existe un conjunto de datos versionable fuera del entorno del investigador. Versionar ese material contradiría el propio marco de protección descrito en el capítulo 7.
>
> Lo que sí se versiona son los agregados desprovistos de información sensible —conteos, métricas y distribuciones—, acompañados del hash SHA-256 del archivo de origen que los generó. Este mecanismo preserva la trazabilidad entre cada resultado publicado y la corrida que lo produjo, sin exponer material clínico. La incorporación de un versionado de datos formal se plantea para el escenario de despliegue institucional, en el que el corpus residiría dentro de la infraestructura de la Clínica CITIMED y quedaría sujeto a sus propias políticas de custodia.

## 4. Tabla 4 — fila «Herramientas Open Source» [IMPORTANTE]

> Uso de frameworks libres (Python, FastAPI, scikit-learn, FAISS, Sentence Transformers, spaCy, PyMuPDF, React) sin costo de licencia.

*(elimina **LangChain**, **MLflow** y **DVC**: ninguno se instala en el proyecto)*

## 25. Tabla 4 — Recursos Humanos [OPCIONAL]

Los $300,00 por «3 maestrantes durante 16 semanas» equivalen a $6,25 por persona y semana. El docente pidió un **valor de referencia defendible**. Sugerencia de descripción:

> Equipo de 3 maestrantes, 16 semanas. Estimado a tarifa referencial de mercado para perfiles de ingeniería de datos e IA (3 personas × 10 h/semana × 16 semanas). El valor se declara como aporte académico en especie y no representa desembolso.

Ajusta el monto a la tarifa hora que decidas sostener.

---

# CAPÍTULO 6 — ESTUDIOS REALIZADOS

## 9. Tabla 6 — AUPRC [CRÍTICO]

Sustituir la última fila:

| Métrica (test MEDEC) | Baseline (nota) | Ajustado (oración) | Lectura |
|---|---|---|---|
| AUPRC (oración) | - | **0.398** | IC 95 % 0.353 – 0.457; métrica clave con 4,6 % de positivos |

**Tres cambios:** `0.419 → 0.398` · `IC 0.392-0.446 → 0.353-0.457` · `4.5% → 4,6%`.

**Justificación.** El valor 0,419 proviene de `s6/metricas_ajuste.json` (23-jul), que no corresponde al modelo que el sistema carga. El 0,398 está confirmado por tres fuentes independientes: `eval_tfidf_idioma.json` del 17-ago, `salidas_ajuste/metricas_ajuste.json` del 23-ago —el que declara `s7/config.yaml`— y el recálculo directo sobre `modelo_ajustado.joblib` (n = 6789, positivas = 311). El 0,419 no se reproduce por ninguna vía: ni con *average precision* (0,3977), ni con trapecio (0,3956), ni con predicción binaria (0,2998).

Con este cambio, **§6.4.5 deja de contradecir a la Tabla 6**: ya dice «AUPRC = 0,40», que siempre fue el valor correcto.

> **Higiene, para que no reaparezca.** El 0,419 vive además en `s10/evidencias/metricas_tfidf.json` (archivo idéntico al de `s6/`), en `s10/evidencias/resumen_metricas.json` —el vector por el que llegó al documento— y como `0.42` en el bloque `referencia_s7` de ambos `metricas_tripartita.json`. Renombra los dos primeros con sufijo de fecha y corrige los otros dos.

## 10. §6.4.3 — sesgo de idioma [MEJORA]

La viñeta afirma el riesgo de forma cualitativa teniendo la medición. Sustituir:

> **Sesgo lingüístico:** el corpus MEDEC está en inglés y los expedientes de CITIMED en español. La medición sobre un subconjunto de 200 oraciones con el modelo real arroja un ROC-AUC de 0,458 en inglés frente a 0,497 en español (Δ = −0,040), diferencia que en ambos casos resulta indistinguible del azar y confirma que el brazo generativo no discrimina en ninguno de los dos idiomas bajo este esquema de *prompting*.

*Fuente: `metricas_llm_real.json → sesgo_idioma_llm_real`*

## 11. §6.4.5 «Limitaciones» — transferencia idiomática [MEJORA]

Añadir viñeta:

> - La transferencia idiomática del componente léxico se midió de forma directa: reentrenado y evaluado sobre la traducción al español del mismo corpus, el modelo alcanza un ROC-AUC de 0,959 y un AUPRC de 0,432, frente a 0,949 y 0,398 en inglés. El desempeño no se degrada al cambiar de idioma, lo que acota la limitación de transferencia a la diferencia de dominio clínico y de convenciones de registro, y no al idioma en sí.

*Fuente: `salidas_s7/eval_tfidf_idioma.json`*

---

# CAPÍTULO 7 — DESARROLLO DEL PROYECTO

## 5. §7.1.3 — viñeta «Diseño de la arquitectura del sistema» [IMPORTANTE]

> **Diseño de la arquitectura del sistema:** Modelado de los flujos de información y especificación de una arquitectura modular por responsabilidades —ingesta y anonimización, segmentación, generación de *embeddings*, recuperación semántica e inferencia—, desplegada como un único servicio en entorno local.

*(elimina «microservicios contenerizados»)*

## 6. §7.1.4 — viñeta «Infraestructura, despliegue y MLOps» [IMPORTANTE]

> **Infraestructura, despliegue y MLOps:** Ejecución en entorno local con configuración declarativa centralizada y semilla fija; registro de experimentos mediante artefactos JSON versionados y caché de inferencia indexada por hash SHA-256; Git y GitHub para el versionado del código bajo un esquema de ramas por funcionalidad; y GitHub Actions para la automatización de la integración continua, que comprende pruebas de regresión, evaluación sobre conjunto dorado y prueba de humo sobre la API.

## 7. §7.2.6 — párrafo introductorio [IMPORTANTE]

> El prototipo funcional se diseñó bajo una arquitectura modular de componentes desacoplados por responsabilidad, que operan dentro de un único servicio en un entorno local controlado, lo que garantiza que ningún dato salga del equipo. Esta separación preserva la ruta de evolución hacia un despliegue en microservicios independientes, planteada en las recomendaciones del capítulo 8. Los componentes de la infraestructura comprenden:

## 12. §7.2.7 — apartado NUEVO [CRÍTICO]

> Insertar antes de «Funcionamiento del prototipo» y renumerar los siguientes.

> ### 7.2.7. Alcance del detector y ejes de inconsistencia evaluados
>
> El motor de detección no opera sobre el universo completo de inconsistencias documentales, sino sobre un conjunto acotado de cuatro ejes verificables a partir del propio expediente, sin recurrir a conocimiento clínico externo:
>
> 1. **Lateralidad:** contraste entre el diagnóstico o el procedimiento y el examen físico, tanto en la parte anatómica como en el lado.
> 2. **Sexo del paciente:** contradicción entre el sexo declarado y una mención posterior, o entre el sexo y un procedimiento incompatible con él.
> 3. **Alergias frente a prescripciones:** indicación de un fármaco de la misma clase que una alergia documentada en la nota.
> 4. **Edad:** procedimientos o hallazgos incompatibles con la edad registrada, o edades discordantes entre dos evoluciones.
>
> Los cuatro comparten una propiedad que sostiene la decisión: son **contradicciones internas del expediente**. Su verificación no exige un vademécum, una base de interacciones farmacológicas ni un modelo de razonamiento clínico; basta contrastar dos afirmaciones de la misma historia. Esa autocontención es lo que permite auditar cada alerta contra el texto y hace viable la supervisión humana.
>
> Quedan **fuera del alcance de esta fase** los errores de medicación entendidos como dosis, duplicidad o suspensión temporal de un tratamiento habitual para un procedimiento, así como las discordancias de signos vitales, tolerancia oral, hemodinamia o indicaciones de egreso. La exclusión responde a una limitación de evidencia y no de arquitectura: detectar una dosis incorrecta exige una fuente posológica normalizada de la que el proyecto no dispone, y emitir alertas sin esa base produciría falsos positivos en un dominio donde la carga de revisión ya es el principal costo operativo. La contradicción entre una alergia documentada y una prescripción —el caso de medicación de mayor gravedad clínica— sí permanece en alcance, porque se resuelve dentro de la nota.
>
> Esta delimitación es posterior a la evaluación comparativa sobre el corpus MEDEC reportada en el apartado 7.3 y no la afecta: las métricas de ese apartado corresponden a la tarea general de detección de errores definida por el propio corpus. La restricción a cuatro ejes gobierna el comportamiento del prototipo sobre expedientes de la Clínica CITIMED, y su verificación empírica se plantea entre las líneas de trabajo inmediato.

> **Por qué es crítico:** la restricción se lee hoy en la **Figura 16** del propio documento («Medicamentos aún no se evalúan») sin que el texto la explique. Un lector atento ve que la captura contradice al cuerpo.

## 13. Tabla 8 — nota al pie [CRÍTICO]

> Añadir como nota al pie de la tabla o como último párrafo de §7.3.3.

> Las métricas del brazo generativo corresponden a la formulación de *prompt* vigente al 31 de agosto de 2026, de propósito general sobre los tipos de error definidos por MEDEC. Con posterioridad a esta evaluación, el *prompt* del prototipo se acotó a los cuatro ejes descritos en el apartado 7.2.7 para su operación sobre expedientes de CITIMED. Dado que la caché de inferencia se indexa por el hash del *prompt*, una reejecución con la formulación vigente no reproduce estas cifras: mediría una tarea distinta y más restringida. La conclusión arquitectónica —el esquema en cascada con el clasificador léxico como componente de producción— no se altera, puesto que se sustenta en la comparación bajo condiciones idénticas para los tres brazos.

## 14. §7.3.3 — prueba de McNemar [MEJORA]

Añadir tras el párrafo que introduce la Tabla 8:

> Para contrastar si las diferencias observadas entre brazos son estadísticamente significativas se aplicó la prueba de McNemar sobre las predicciones pareadas. La comparación entre el modelo léxico y el brazo *zero-shot* arroja p = 0,060, valor que no alcanza significación al 5 % pese a la amplia distancia en ROC-AUC, lo que se explica por el reducido número de positivos del subconjunto evaluado. La comparación entre el modelo léxico y el brazo con recuperación aumentada resulta indistinguible (p = 1,000). En cambio, la diferencia entre ambos brazos generativos sí es significativa (p = 0,006), y su signo indica que **la incorporación de recuperación aumentada degrada el desempeño respecto del *zero-shot*** bajo este esquema de *prompting*, resultado coherente con la hipótesis de que el contexto recuperado —conocimiento clínico general— no aporta la información necesaria para resolver contradicciones internas del expediente.

*Fuente: `metricas_llm_real.json → mcnemar`*

## 15. §7.4 — evidencia de la corrida v2 [CRÍTICO]

**Estado actual del repositorio:** el código del anonimizador v2 existe y está versionado (`s12/anonimizador.py`, commit `ec1838e` del 2026-09-06, 657 líneas). Implementa las cuatro vías que describe el apartado: tabular, firma, título y campo etiquetado, más NER opcional. **La sección ya no describe código inexistente.**

**Lo que sigue faltando:** el archivo de agregados que sustente las cifras de la Tabla 10 —99 expedientes, 413 páginas, 2 137 cajas redactadas, desglose por método (1 625 / 320 / 192), 25 segundos, 0 falsos positivos, 2 errores de frontera—. Ninguna de esas cifras aparece en ningún `.json` o `.csv` del repositorio.

**Acción, en orden de preferencia:**

1. **Reejecutar y publicar los agregados.** El script ya tiene la bandera `--reporte` para emitir un CSV de auditoría y `--sin-texto-en-reporte` para omitir el texto detectado. Con eso generas un artefacto publicable sin PHI que respalda la Tabla 10 y cierra el punto.
2. Si el lote de 99 expedientes ya no está disponible, **reformular la Tabla 10** con lo que sí puedas reproducir hoy, y declarar el resto como corrida previa no versionada.

**Añadir en cualquiera de los dos casos**, al final de §7.4.1:

> El componente descrito se encuentra versionado en el repositorio del proyecto, junto con el reporte de auditoría de la corrida que sustenta las cifras de esta sección.

## 19. §7.5.5 — anonimización del personal sanitario [CRÍTICO]

El apartado afirma: *«el protocolo contempla la anonimización de los nombres del personal sanitario»*.

**Esa afirmación no se cumple en la salida del anonimizador v1.** Sobre expedientes procesados por v1 se verificó que el nombre del paciente y la cabecera quedan correctamente tachados, y que los médicos citados por campo etiquetado (`DR.`, `MÉDICO`) también. Pero **los bloques de firma al pie de cada evolución —nombre completo sobre la línea `MEDICINA GENERAL`— quedan legibles**.

La regla que resuelve esto (`detectar_firmas`, con las credenciales `MEDICINA GENERAL`, `ANESTESIOLOGÍA`, `CI:`, `SENESCYT`) existe en el v2, pero el v2 opera sobre la capa de texto nativa y no puede procesar expedientes escaneados como imagen, que es donde se observó la falla.

**Redacción sugerida para sustituir la frase:**

> El protocolo contempla la anonimización de los nombres del personal sanitario. Su cobertura difiere entre las dos versiones del componente: la versión sobre capa de texto nativa incorpora una regla específica de bloque de firma, que identifica el nombre del profesional por su posición sobre una línea de credencial reconocida. La versión basada en reconocimiento óptico cubre los nombres del personal citados en campos etiquetados, pero no alcanza de manera fiable los bloques de firma manuscritos o de baja confianza de reconocimiento, limitación que se declara de forma expresa y que refuerza la exigencia de revisión visual dual sobre los folios originales antes de liberar cualquier lote al corpus analítico.

> **Es un hallazgo a favor si se declara.** Reconocer una limitación medida en el componente de privacidad, y explicar qué versión la resuelve, es más sólido que una afirmación general que la evidencia contradice.

## 20. §7.5.5 — título [IMPORTANTE]

Actualmente: «Protocolo de **identificación** por capas». Debe ser:

> **Protocolo de de-identificación por capas**

El título anuncia lo contrario de lo que describe el apartado. En S11 estaba correcto.

## 16. §7.5.1 — viñeta «Mitigación técnica» [IMPORTANTE]

> **Mitigación técnica:** Para mitigar este riesgo, la arquitectura incorpora un módulo local de anonimización previa y la ejecución íntegra del procesamiento en el equipo del investigador, sin envío de datos sin procesar a servicios externos de inferencia y en cumplimiento de las normativas de confidencialidad médica. El aislamiento del despliegue mediante contenedores en entornos cerrados (*on-premise* o nube privada controlada) se plantea como vía de escalamiento institucional y se detalla en las recomendaciones.

---

# CAPÍTULO 8 — CONCLUSIONES

## 17. §8.1, conclusión 1 — añadir al final [CRÍTICO]

> A esa decisión se suma una segunda delimitación, de alcance: el detector desplegado sobre expedientes institucionales opera sobre cuatro ejes de contradicción interna —lateralidad, sexo, alergias y edad—, verificables sin conocimiento clínico externo. Acotar el dominio antes que ampliarlo fue una elección deliberada frente al perfil de precisión observado, y define con claridad la superficie sobre la que el sistema puede responder.

---

# CAPÍTULO 9 — TRABAJO FUTURO

## 18. Punto 5 nuevo [MEJORA]

> **5. Ampliación progresiva de los ejes de inconsistencia**
>
> El detector opera hoy sobre cuatro ejes de contradicción interna. Su ampliación admite dos rutas de distinto costo. La primera, de incorporación inmediata, es la **contradicción entre diagnósticos** dentro de un mismo episodio —dos diagnósticos primarios incompatibles entre evoluciones—, que conserva la propiedad de autocontención de los ejes actuales y cuya regla ya está formulada en la base de conocimiento del sistema. La segunda, de mayor alcance, son los **errores de medicación por dosis, duplicidad o interacción**, que exigen incorporar al índice vectorial una fuente posológica normalizada —vademécum institucional o cuadro nacional de medicamentos básicos— antes de poder emitir alertas con precisión aceptable.

---

# CAPÍTULO 10 — REFERENCIAS

## 22. Ampliar y corregir [CRÍTICO]

**Errores a corregir en lo existente:**

| Problema | Corrección |
|---|---|
| Texto cita «(Bowman, **2022**)» (p. 9); la referencia dice «Bowman, S. (**2013**)» | Unificar en **2013** (año real de la publicación en *Perspectives in Health Information Management*) |
| §7.2.1 cita «(Abacha, A. B., et al., 2025)»; §6.1.2 cita «(Ben Abacha et al., 2025)» | Unificar en **Ben Abacha et al. (2025)** — el apellido es *Ben Abacha* |
| «Roman-Belmonte et al., 2023» se cita en p. 9 pero **no está en la lista** | Añadir la entrada |

**Referencias a añadir** — cubren normativa citada en el texto sin respaldo bibliográfico y elevan el total hacia las 20+ solicitadas:

> Asamblea Nacional del Ecuador. (2021). *Ley Orgánica de Protección de Datos Personales*. Registro Oficial Suplemento 459, 26 de mayo de 2021.
>
> Health Level Seven International. (2019). *HL7 FHIR Release 4 (v4.0.1)*. https://hl7.org/fhir/R4/
>
> U.S. Department of Health and Human Services. (2012). *Guidance regarding methods for de-identification of protected health information in accordance with the HIPAA Privacy Rule*. https://www.hhs.gov/hipaa/for-professionals/privacy/special-topics/de-identification/
>
> Roman-Belmonte, J. M., Rodríguez-Merchán, E. C., & De la Corte-Rodríguez, H. (2023). *[completar con los datos de la fuente que se usó para la cifra 7 %–15 %]*
>
> Ministerio de Salud Pública del Ecuador. (2019). *Hipertensión arterial: Guía de Práctica Clínica*. Dirección Nacional de Normatización. https://www.salud.gob.ec/wp-content/uploads/2019/06/gpc_hta192019.pdf
>
> Ministerio de Salud Pública del Ecuador. (2017). *Neumonía adquirida en la comunidad en pacientes de 3 meses a 15 años: Guía de Práctica Clínica*. Dirección Nacional de Normatización. https://www.salud.gob.ec/wp-content/uploads/2017/05/Neumonía-GPC-24-05-2017.pdf

> **Las GPC del MSP son la vía más rápida para llegar a 20+ referencias con normativa ecuatoriana**, que es exactamente lo que pidió el docente. El repositorio contiene **ocho** guías del Ministerio en `s7/knowledge/` —caries, diabetes tipo 2, dolor lumbar, enfermedad renal crónica, hipertensión, neumonía pediátrica, odontología en el embarazo y protocolos odontológicos—, todas con su URL y licencia en la primera línea del archivo. Citarlas es legítimo: forman parte del corpus de recuperación del sistema y ya aparecen en las capturas de los Anexos 3 y 4.

## 21. Base de conocimiento GPC — mención en §7.2.1 o §6.5.1 [MEJORA]

El documento habla genéricamente de «guías clínicas y códigos CIE-10». Conviene nombrar la fuente:

> La base de conocimiento del componente de recuperación incorpora ocho guías de práctica clínica publicadas por el Ministerio de Salud Pública del Ecuador, junto con protocolos odontológicos y un conjunto de reglas de consistencia de alto nivel. El uso de normativa nacional, en lugar de referencias clínicas genéricas, alinea las recomendaciones recuperadas con el marco regulatorio bajo el que opera la institución.

---

# ANEXOS Y FORMATO

## 23. Numeración de figuras y secciones [IMPORTANTE]

| Ubicación | Problema | Corrección |
|---|---|---|
| p. 59 | Caption «Figura **101**» | Figura 11 |
| p. 61 | Caption «Figura **112**» | Figura 12 |
| p. 69 y p. 86 | **«Figura 16» usada dos veces** | La del Anexo 1 debe ser Figura 18 |
| Anexos | Salta de Figura 16 a Figura 18 | Renumerar en cadena |
| p. 67 | «Las **figuras 12 a 14**…» | Son las figuras **14 a 16** |
| Índice de figuras | «Figura 10 Preparación de historias clínicas» ≠ caption real | Unificar con el caption del cuerpo |
| Índice de figuras | Páginas corruptas: 688, 698, 887, 898, 909 | Regenerar el índice como campo automático |
| Índice y cuerpo | Salta de **«10. Referencias»** a **«14. Anexos»** | Renumerar Anexos como capítulo 11 |
| Figuras 10–13, 17 | Captions son oraciones descriptivas completas | En APA el título de figura es un sintagma nominal; la descripción va en nota al pie |

## 26. Acta institucional [CRÍTICO]

§7.5.5 declara: *«la formalización mediante acta institucional pendiente de integración; dicha acta debe incorporarse como anexo antes de la entrega definitiva»*.

El documento se autodeclara incompleto en el punto ético más sensible, habiéndose procesado 99 expedientes reales con PHI. **Adjuntarla como anexo, o reformular el compromiso si no va a estar a tiempo.**

---

## Verificación final — búsquedas en Word

- [ ] `0,419` / `0.419` → cero apariciones
- [ ] `LangChain` → cero apariciones
- [ ] `DVC` y `MLflow` → solo en §5.1.1/5.1.2 (justificación), §2.1.1 (propuesta), §8.2 rec. 3 y capítulo 9
- [ ] `Se incorporó` junto a DVC o MLflow → cero apariciones
- [ ] `contenerizad` / `contenedor` → solo §7.5.1, §8.2 rec. 2 y capítulo 9, siempre en futuro
- [ ] `microservicios` → solo §2.1.1 (propuesta), §7.2.6 (ruta de evolución) y capítulo 8
- [ ] `Bowman, 2022` → cero apariciones
- [ ] `Abacha, A. B.` → cero apariciones (debe ser *Ben Abacha*)
- [ ] `Figura 101` y `Figura 112` → cero apariciones
- [ ] Contar entradas de la bibliografía → 20 o más
- [ ] Buscar `medicamento` y `medicación` → cada aparición coherente con §7.2.7

---

## Qué NO tocar

| Ubicación | Por qué |
|---|---|
| §2.1.1 completo | Es la arquitectura **propuesta** en el análisis de alternativas. Su línea «Despliegue: Entorno local, no contenedores» ya era la correcta |
| §1.1.2, viñeta de alergias | «Prescripción de medicamentos no compatibles con alergias» **sí está en alcance** |
| §8.2 recomendaciones 2 y 3 | Trabajo futuro. Ganan coherencia con §5.1.2 |
| Capítulo 9 completo | Trabajo futuro |
| Explicación de 0,948 vs 0,949 (p. 66) | Está bien argumentada y es correcta |
| Decisión de no reportar el kappa | Mejora de integridad respecto a S11 |
| Toda la Tabla 8, Tabla 9, Figura 8 | Verificadas contra el repositorio, coinciden |
