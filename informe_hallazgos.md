# Informe de hallazgos — Auditoría técnico-académica

**Documento auditado:** `Proyecto_Capstone_v12_formatoFinal.pdf` (90 pp., portada 31-ago-2026)
**Repositorio:** `MIA_Deteccion_HC` — rama `main`, HEAD `8bbe4b8`
**Rúbrica:** S12 — Informe, presentación y prototipo versión final (TTMZ0055-402)
**Fecha de auditoría:** 6 de septiembre de 2026
**Alcance:** solo lectura. No se modificó ningún archivo del documento ni del repositorio.

---

## Resumen ejecutivo

El documento corrigió con éxito los seis puntos de forma que hundieron la nota en S11 (Gantt, anexos, objetivos sin temporalidad, costos ≠ $0, registro académico sin "bitácora de entregas"). Sin embargo, la auditoría cruzada contra el repositorio detecta **tres problemas de integridad que pesan más que el formato**: (1) la sección §7.4 completa —anonimizador v2 sobre capa de texto nativa, Tablas 10 y 11, Figura 17, y las cifras "99 expedientes / 413 páginas / 2 137 redacciones"— **no tiene una sola línea de código ni un archivo de evidencia en el repositorio**; (2) el documento afirma en pasado haber incorporado **DVC, MLflow, LangChain y contenedores**, que no existen en el repo y que el propio `requirements-optional.txt` declara incompatibles con el stack; y (3) el **AUPRC de la Tabla 6 (0,419)** proviene de una corrida obsoleta (`s6/`) y no del modelo que el sistema realmente carga (`salidas_ajuste/` = 0,398). Además, el repositorio contiene trabajo sustantivo **no documentado**: la restricción del detector a cuatro ejes MVP, el pipeline de extracción de PDF por visión, y el set adversarial `s12/poison/`. Las referencias siguen en 13 (se pidieron 20+) y LOPDP/HL7 FHIR se citan en el texto pero no aparecen en la bibliografía.

---

## Hallazgos críticos (bloquean la nota)

### C-1. §7.4 «Actualización del anonimizador sobre capa de texto nativa» no existe en el repositorio

Es el hallazgo más grave. El documento dedica las páginas 69–74 a un componente v2 con cuatro vías de detección (tabular/geométrica, firma, título, campo etiquetado), consolidación por solapamiento >50 %, y resultados sobre 99 expedientes.

Búsquedas ejecutadas sobre todo el repo (excluyendo `.venv`, `.git`, `node_modules`):

| Término buscado | Resultado |
|---|---|
| `SENESCYT`, `capa de texto nativa`, `APELLIDOS Y NOMBRES`, `vía tabular`, `via_tabular` | **0 archivos** |
| `anonimizador_v2`, `anon_v2`, archivos con `v2` en el nombre | **0 archivos** |
| `413`, `2137`, `2 137` en `*.json/*.md/*.py/*.csv/*.txt` | solo `s11/tools/_dump_v3.txt`, que es un volcado de una **versión previa del Word (abril 2026)**, no evidencia de ejecución |

Lo que sí existe es exclusivamente **v1 (OCR)**: `s11/anonimizador_ocr/` y una copia comprimida en `anonimizador/anonimizador 1.5-.../`, más el anonimizador de texto plano de S10 en `s10/anonimizador/ANONIMIZADOR/`.

**Cifras no verificables** (§7.4.1, Tabla 10, Resumen p4, Abstract p5, Conclusión 2 p78): 99 documentos, 413 páginas, rango 2–7 págs (media 4,2), 2 137 cajas redactadas, desglose por método (tabla 1 625 / firma 320 / título 192), 25 s de procesamiento (0,06 s/pág), 413/413 páginas al 100 %, 0/2 137 falsos positivos, 2/2 137 errores de frontera.

> **Riesgo:** estas cifras aparecen en el Resumen, el Abstract y las Conclusiones como el logro más amplio del componente de privacidad. Si el tribunal pide reproducirlas, no hay script que ejecutar. Es exactamente el tipo de afirmación que el docente señaló como parte del "registro permanente" institucional.

**Acción:** o se sube el código y el JSON de agregados de la corrida v2, o se retira §7.4 (y sus menciones en Resumen, Abstract, Tablas 10–11, Figura 17 y Conclusión 2) y se reetiqueta como trabajo futuro.

---

### C-2. Stack MLOps declarado en pasado que no existe en el repositorio

| Afirmación del documento | Realidad del repo |
|---|---|
| §5.1: «control de versiones mediante Git, **DVC** y **MLflow**» | No existe `.dvc/`, `dvc.yaml`, `*.dvc` ni `mlruns/`. `dvc` no figura en ningún `requirements*.txt` |
| §6.5.1: «**Se incorporó** el control de versiones de datos (DVC) y de experimentos (MLflow) para garantizar la reproducibilidad» | `requirements-optional.txt` dice literalmente: *«MLflow 2.x exige numpy<2, **incompatible con el stack S7** (numpy 2.4.4)… **O espera a integrar tracking** manual vía JSON»* |
| §7.1.4: «MLflow para la gestión del ciclo de vida… DVC para el versionado de datos» | ídem |
| §4.1 «Incluye»: «Registro de experimentos (MLflow)» | no implementado |
| Tabla 4: «frameworks libres (Python, FastAPI, **LangChain**, FAISS, MLflow, DVC)» | **`langchain` no aparece en ningún requirements ni import del proyecto** |
| §7.1.3: «microservicios **contenerizados**»; §7.5.1: «despliegue de **contenedores** en entornos cerrados» | No hay `Dockerfile` ni `docker-compose.yml`. **Contradice al propio documento**, §2.1.1: «Despliegue: Entorno local, **no contenedores**, GitHub Actions (CI/CD)» |
| §7.2.6 / §6.5.1: «arquitectura de **microservicios** desacoplados» | El backend es una **única aplicación FastAPI** (`api/main.py`); los "servicios" son módulos en el mismo proceso |

Lo que sí es cierto y está verificado: **CI/CD con GitHub Actions** (`.github/workflows/tests.yml` ✓), semilla única 42 (`s7/config.yaml` ✓), spaCy (`requirements-anonimizador.txt` ✓), FAISS y Sentence Transformers (`requirements.txt` ✓).

**Acción:** reescribir en modo declarativo honesto — «se diseñó el pipeline para DVC/MLflow; el tracking se implementó mediante JSON versionado en `salidas_s7/` por incompatibilidad numpy≥2», eliminar LangChain de la Tabla 4, y unificar el discurso de contenedores con §2.1.1.

---

### C-3. El AUPRC de la Tabla 6 no corresponde al modelo que el sistema carga

El repositorio contiene **dos** `metricas_ajuste.json` con idénticos valores salvo el AUPRC:

| Clave | `s6/metricas_ajuste.json` (obsoleto) | `salidas_ajuste/metricas_ajuste.json` (**vigente**) |
|---|---|---|
| `prueba.auprc` | **0.4186** | **0.3977** |
| `prueba.auprc_ci95` | `[0.419, 0.392, 0.446]` | `[0.4031, 0.3529, 0.4574]` |
| `validacion.auprc` | 0.4512 | 0.5110 |

`s7/config.yaml` apunta a `modelo_tfidf: salidas_ajuste/modelo_ajustado.joblib` — es decir, **el modelo en producción es el de `salidas_ajuste/`**, cuyo AUPRC de prueba es **0,398 (IC 95 % 0,353–0,457)**.

La **Tabla 6 (p39)** reporta: `AUPRC (oración) — 0.419 — IC 95% 0.392-0.446`. Ese par proviene de la corrida S6 descartada.

Peor aún, **el propio documento se contradice**: §6.4.5 (p44) dice «Desbalance 4,5%: **AUPRC = 0,40** complementa al AUC» — que sí coincide con el modelo vigente (0,3977). Dos valores distintos para la misma métrica, en el mismo documento.

**Acción:** sustituir en Tabla 6 por `0,398 — IC 95 % 0,353–0,457`, o re-ejecutar y regenerar ambos artefactos para que coincidan.

---

### C-4. Trabajo sustantivo del repositorio ausente del documento

Tres bloques de ingeniería reales, versionados y con pruebas, que el documento no menciona:

**(a) Restricción del detector a cuatro ejes MVP.** `s7/prompts.py` define `EJES_MVP_ES/EN`: *«solo estos cuatro: lateralidad, sexo, alergias, edad… **No evalúes medicamentos**»*. Confirmado por el commit `0be92db` «Tighten MVP inconsistency rules: laterality vs exam, pause medications, ignore visit reason» y por la prueba `tests/s7/test_prompts_mvp.py`.

> Esto es una **decisión metodológica de alcance de primer orden** y el documento no la enuncia en ningún punto. Al contrario, §1.1.2 sigue listando «Prescripción de medicamentos no compatibles con alergias» entre las inconsistencias objetivo.
>
> **Y aparece en la propia Figura 16 del documento (Anexo 1, p86)**, donde se lee en pantalla: *«Contrasta lateralidad, sexo, alergias y edad. Medicamentos aún no se evalúan. El umbral 0,50 usa TF-IDF + LLM.»* — el lector ve en la captura una restricción que el texto nunca explica y que contradice el alcance declarado.

**(b) Pipeline de extracción estructurada de PDF.** `api/pdf_extract.py`, `api/pdf_estructura.py`, `api/vision_client.py` + endpoints `GET /muestras-pdf`, `POST /extraer-pdf`, `POST /extraer-pdf-estructurado`, con cascada de motores (visión multimodal → OCR local → capa de texto) y pruebas (`api/test_pdf_extract.py`, `api/test_vision_client.py`, `tests/api/test_extraer_pdf*.py`). La Figura 16 (Anexo 1) muestra el control «DOCUMENTO PDF — Opcional. Solo NOTAS DE EVOLUCIÓN y ORDENES MEDICAS GENERALES», funcionalidad no descrita en §7.2.

**(c) Set adversarial `s12/poison/`.** 21 PDFs anonimizados etiquetados por tipo de inconsistencia inducida (`GENERO`, `INESTABLE`, `LATERALIDAD`, `DIAGNOSTICO`, `EDAD`). No se referencia en ningún `.py`, `.md`, `.json` ni en el documento. Es un activo de validación valioso y desaprovechado en la narrativa.

**Acción:** documentar (a) obligatoriamente —afecta la interpretación de todas las métricas— y (b)/(c) como aportes de la fase final.

---

### C-5. Referencias: 13 (se pidieron 20+) y normativa citada pero no referenciada

- Total de entradas: **13** (pp. 83–84). El docente pidió explícitamente elevar a **20+**.
- **LOPDP** se invoca como marco jurídico central en §7.5.5 (p76) — *«tipificadas como datos sensibles de categoría especial bajo el marco de la Ley Orgánica de Protección de Datos Personales del Ecuador (LOPDP)»* — pero **no figura en la bibliografía**.
- **HL7 FHIR** se menciona en §9 (p81) como línea de trabajo futuro — **no figura en la bibliografía**.
- **HIPAA Safe Harbor** (los 18 identificadores) se usa como referencia metodológica en §7.5.5 — **no figura en la bibliografía**.
- **Error de año en cita APA:** el texto (p9) cita `(Bowman, 2022; Roman-Belmonte et al., 2023)`; la referencia n.º 3 (p83) dice **`Bowman, S. (2013)`**. Nueve años de discrepancia en una de las dos fuentes que sostienen la cifra 7 %–15 % del planteamiento del problema.
- **Inconsistencia de apellido:** §7.2.1 (p55) cita `(Abacha, A. B., et al., 2025)`; §6.1.2 (p36) cita `(Ben Abacha et al., 2025)`; la referencia es `Ben Abacha, A.`. La forma correcta es *Ben Abacha*.
- `Roman-Belmonte et al. (2023)` se cita en p9 pero **no está en la lista de referencias** (la lista salta de Johnson a Jurafsky a Russell; no hay entrada Roman-Belmonte).

**Acción:** añadir LOPDP (Registro Oficial), HL7 FHIR R4, HIPAA Safe Harbor 45 CFR §164.514, Roman-Belmonte et al. (2023), corregir Bowman a 2013 (o cambiar la cita en texto), y completar hasta 20+.

---

### C-6. Acta institucional aún pendiente

§7.5.5 (p77): *«la formalización mediante acta institucional **pendiente de integración**; dicha acta **debe incorporarse como anexo antes de la entrega definitiva**, dado el volumen de material sensible involucrado»*.

El documento se autodeclara incompleto en el punto ético más sensible, y se procesaron 99 expedientes reales (413 páginas) con PHI. El docente lo listó explícitamente en el cierre administrativo de S11. Los anexos (14.1–14.5) son solo capturas de interfaz; no hay anexo ético, ni acta, ni la guía de anotación como anexo.

---

## Hallazgos menores

### M-1. Numeración de figuras rota (varios errores)

| Ubicación | Problema |
|---|---|
| p59 | Caption literal **«Figura 101»** (debe ser 11) |
| p61 | Caption literal **«Figura 112»** (debe ser 12) |
| p69 y p86 | **«Figura 16» usada dos veces**: *Recall de identificación en la capa de texto* (p69) y *Interfaz principal y carga de expedientes* (Anexo 1, p86). El Anexo 1 debería ser Figura 18 |
| Anexos | Salta de «Figura 16» (p86) a «Figura 18» (p87) — **no existe Figura 17 en anexos**, pero sí en el cuerpo (p71) |
| p67 | Texto: *«Las **figuras 12 a 14** compilan la evidencia gráfica»* — las figuras reales son **14, 15 y 16** |
| Índice de figuras | «Figura 10 **Preparación de historias clínicas CITIMED** 59» vs. caption real en p59: *«La organización en componentes del asistente, agrupada en cinco capas»* |
| Índice de figuras | «Figura 13 Flujo de información **68**» — está en la **p62** |
| Índice de figuras | Números de página corruptos: **688**, **698**, **887**, **898**, **909** (Figuras 14, 15, 18, 19, 20) |
| Índice de figuras | Puntos de relleno manuales («……») en Figuras 12, 20 y 21 en vez de campo TOC |

### M-2. Numeración de secciones: salto de 10 a 14

El índice y el cuerpo pasan de **«10. Referencias bibliográficas»** a **«14. Anexos»** (14.1–14.5). Faltan los apartados 11, 12 y 13. Es el tipo de fallo formal que la rúbrica penaliza en «Cumplimiento de lineamientos».

### M-3. Estilo de captions inconsistente con APA

Las Figuras 1–9 usan título nominal («*Diagrama de Ishikawa – Factores que…*»). Las Figuras 10, 11(101), 12(112), 13 y 17 usan **oraciones descriptivas completas** en su lugar: «*Detalla la distribución física de los componentes y la frontera que delimita…*», «*Traza la secuencia de interacciones que se producen desde que…*», «*Describe la canalización de anonimización, incluidas sus dos rutas…*». En APA el título de figura es un sintagma nominal; la descripción va en nota al pie de figura.

### M-4. Objetivo específico 4 con sintaxis rota

p27: *«**Evaluar e integrar la fase de desarrollo, los componentes del sistema** mediante pruebas funcionales…»*. Al eliminar el inciso temporal de S11 («en un período de dos semanas posteriores a la fase de desarrollo») quedó una frase agramatical. Debería leerse: «Evaluar e integrar los componentes del sistema mediante pruebas funcionales…».

Nota positiva: los cinco objetivos ya **no contienen plazos** — corrección de S11 lograda ✓.

### M-5. Título de §7.5.5 invierte el significado

p76: **«Protocolo de identificación por capas»**. Debe ser **«de-identificación»**. El apartado describe justamente lo contrario de lo que su título anuncia. (En S11 el título era correcto: «Protocolo de de-identificación por capas».)

### M-6. Costos: mejorados pero aún poco defendibles

Tabla 4 pasó de $0,00 a **$300,00** en Recursos Humanos — atendió la observación. Pero $300 por «Equipo de 3 maestrantes durante 16 semanas» equivale a **$6,25 por persona por semana**, muy por debajo de cualquier valor de referencia de mercado para perfiles de ML/IA en Ecuador. El docente pidió «desglosar el **valor de referencia** de esa mano de obra… para que la estimación sea **defendible**». Recomendación: usar tarifa hora-hombre referencial (p. ej. 3 × 10 h/sem × 16 sem × tarifa) y declarar la diferencia como aporte académico en especie.

Además, la Tabla 4 sigue listando **LangChain** entre las herramientas utilizadas (ver C-2).

### M-7. Discrepancias menores de redacción

- p64: «**reducendo** la dispersión» → *reduciendo*.
- p5 (Abstract): «*administrative, and legal risks.To overcome*» — falta espacio tras el punto.
- p83/p86: «**10.Referencias**» y «**14.Anexos**» — falta espacio tras el punto.
- Portada: «Patricio Ponce Herrera» aparece sin etiqueta de rol (¿tutor? ¿profesor guía?), a diferencia de los tres autores.
- §6.5.5 (p49): guion largo mal cerrado — la oración *«Para abordar los requerimientos… - cuyo archivo comprende dos subconjuntos… el segundo motivó la segunda versión del componente que se describe más adelante—, se integró…»* abre con guion corto y cierra con raya; la sintaxis queda rota (sujeto sin predicado principal claro).
- §6.4.7 (p44) **repite literalmente** los tres bullets de §6.4.3 (p43): «Sesgo por tipo de error», «Automatización sin supervisión: 57 falsos negativos», «Falsa confianza: AUC 0,949 pero scores ≈ 0,50». Duplicación de contenido que la rúbrica penaliza como «repetición».

### M-8. Tabla 7 sub-reporta el estado actual del repositorio

La Tabla 7 (p52) reporta 21 casos unitarios + 14 de frontend = el snapshot de S11. El repo actual tiene una suite bastante mayor: `tests/api/` (contract, degraded, generar, health, extraer_pdf, extraer_pdf_estructurado), `tests/s7/`, `tests/security/`, `tests/perf/`, `tests/e2e/`, más `api/test_pdf_extract.py` y `api/test_vision_client.py`. Una ejecución de `tests/api/ + api/test_pdf_extract.py` da **57 pruebas en verde**.

El documento **sí declara** esta limitación («en el directorio tests/ se dispone de una suite SDET más amplia… la presente entrega prioriza y reporta la consolidación de la suite unitaria unificada»), por lo que es honesto — pero desaprovecha evidencia real que subiría la nota en «Resultados y evidencia».

---

## Inconsistencias numéricas / métricas

> Sección prioritaria. Cada fila cita la ubicación exacta en el documento y el archivo del repositorio que la contradice o confirma.

### A. Contradicciones reales

| # | Métrica | Cita exacta en el documento | Valor en el repositorio | Veredicto |
|---|---|---|---|---|
| **N-1** | **AUPRC (oración, test)** | Tabla 6, p39: `AUPRC (oración) \| - \| 0.419 \| IC 95% 0.392-0.446` | `salidas_ajuste/metricas_ajuste.json` → `prueba.auprc = 0.3977`, `auprc_ci95 = [0.4031, 0.3529, 0.4574]` | **CONTRADICE.** El 0,419/[0,392–0,446] es de `s6/metricas_ajuste.json` (corrida obsoleta). Ver C-3 |
| **N-2** | **AUPRC — contradicción interna** | §6.4.5, p44: «Desbalance 4,5%: **AUPRC = 0,40** complementa al AUC» vs. Tabla 6, p39: **0.419** | 0.3977 | **CONTRADICE al propio documento.** §6.4.5 es el correcto |
| **N-3** | **CV 5-fold (media)** | Tabla 6, p39: `CV 5 fold (AUC) \| 0.9654 ± 0.007` | `cv_auc_mean = 0.965`, `cv_auc_sd = 0.0072` | **INCONSISTENTE.** El repo no contiene 0,9654; los folds son [0.9509, 0.9684, 0.9664, 0.9713, 0.968]. Además el Resumen (p3) dice «0,965 ± 0,007» — dos cifras distintas en el mismo documento |
| **N-4** | **ROC-AUC baseline (nota)** | p37, p39 (Tabla 6), p38, p57, p78: `0,504` (≈6 apariciones) | `baseline_a_nivel_nota.roc_auc = 0.5051` en los tres JSON; `s6/BITACORA.md` L44 dice `0.504` pero L60 dice `0.505` | **AMBIGUO.** El repo se contradice a sí mismo (0.504 / 0.505 / 0.5051). Redondeo correcto de 0,5051 = **0,505** |
| **N-5** | **ROC-AUC ajustado (headline)** | Resumen p3, Tabla 6 p39, §6.3.2 p38, §7.2.4 p57, §7.3 p64, §8.1 p78, Tabla 5 p34: `0,949` | `salidas_ajuste` → `prueba.roc_auc = 0.9485`. Pero `s6/BITACORA.md` L103 y L110 reportan **`0.948`** e «AUC 0,504 → **0,948**» | **RIESGO.** 0,9485 admite 0,948 o 0,949 según convención. La bitácora del propio proyecto usa 0,948, y el documento usa 0,948 para la corrida de 400 oraciones. El docente pidió en S11 «**unifiquen el ROC-AUC en un solo valor**» y siguen conviviendo 0,948/0,949 separados por 0,001 |
| **N-6** | **Muestra piloto: 96 vs 100** | Resumen p4: «procesó una muestra piloto de **96 oraciones**» vs. Abstract p5: «from which **100 evaluation sentences** were derived» | `reporte_anotacion.json`: 96 extraídas CITIMED + 4 plantilla = 100 eval | **INCONSISTENTE entre Resumen y Abstract.** Ambos son ciertos pero describen cosas distintas sin decirlo |
| **N-7** | **Cifras del anonimizador v2** | §7.4.1 p71–72, Tabla 10, Resumen p4, Abstract p5, Conclusión 2 p78: 99 docs / 413 págs / 2 137 cajas / 25 s / 1 625-320-192 por método / 0 FP / 2 errores frontera / media 4,2 págs | **NINGÚN archivo del repositorio contiene estas cifras** | **NO VERIFICABLE.** Ver C-1 |
| **N-8** | **«Figuras 12 a 14»** | p67: «Las **figuras 12 a 14** compilan la evidencia gráfica derivada de la fase experimental» | Las figuras referidas son la **14, 15 y 16** | **REFERENCIA CRUZADA ERRÓNEA** |
| **N-9** | **Latencia TF-IDF** | Tabla 8 p66 y §6.5.4 p48: `0,381` / «0,38 milisegundos» | `metricas_llm_real.json` → 0.381 ✓; pero `salidas_s7/metricas_tripartita.json` → `latency_ms_per_oracion: 0.312` | **MENOR.** Dos artefactos del repo discrepan entre sí; el documento eligió el correcto (0,381) |

### B. Cifras verificadas y correctas (no requieren acción)

Se confirmó contra el repositorio, con coincidencia exacta:

- **Comparación tripartita LLM real** (Tabla 8, p66) — `s11/evidencias/metricas_llm_real.json`: TF-IDF ROC-AUC 0,948 (0.9475) ✓ · AUPRC 0,406 (0.4055) ✓ · latencia 0,381 ✓ · $0,000 ✓ | LLM zero 0,509 (0.5094) ✓ · 0,054 ✓ · 587,2 ✓ · $0,0128 ✓ | LLM+RAG 0,507 (0.5067) ✓ · 0,053 ✓ · 535,4 ✓ · $0,0300 ✓ | mock 0,954/0,498/0,498 (0.9537/0.4979/0.4979) ✓
- **Localización top-1**: 84,6 % y 263/311 notas — `localizacion_top1_test = 0.8457`, `notas_con_error_test = 311` (0.8457×311 = 263) ✓ · 85,7 % en la corrida de 400 (`0.8571`) ✓ · 9,5 % de ambos brazos LLM (`0.0952`) ✓
- **Distinción 0,948 vs 0,949 y 84,6 % vs 85,7 %** (p66): la explicación metodológica del documento (400 oraciones submuestreadas vs. partición oficial completa) es **correcta y bien argumentada** ✓
- **Baseline**: accuracy 0,523 (0.5226) ✓ · recall 0,945 (0.9453) ✓ · precision 0,523 (0.5231) ✓ · F1 0,674 (0.6735) ✓ · clasificador trivial 0,521 (`s6/BITACORA.md` L45) ✓
- **Modelo ajustado**: recall 0,817 (0.8167) ✓ · precisión 0,357 (0.3567) ✓ · IC ROC-AUC 0,940–0,958 (`[0.9398, 0.9576]`) ✓ · sd folds 0,0072 ✓
- **Matriz de confusión**: 458 falsos positivos (§6.4.2) y 57 falsos negativos (§6.4.3) — `prueba.matriz_confusion = [[6020, 458], [57, 254]]` ✓
- **Prevalencia** 4,5 % — `prevalencia_oracion_error_train = 0.0448` ✓
- **Diagnóstico del corpus**: solapamiento léxico 95,6 %, notas idénticas 96,6 %, oración errónea 8,9 % del texto — consistentes con `s6/BITACORA.md` ✓
- **Anonimización v1 (OCR)** (Tabla 9, p67) — `anonimizacion_agregados.json` + `verificacion_humana_resumen.json`: 1 doc/20 págs ✓ · 127 hallazgos / 87 cajas ✓ · 77,5 s ✓ · página 10 con OCR 40,2 ✓ · recall NOMBRE 0,898 (115/128) ✓ · CÉDULA 1,000 (10/10) ✓ · HC 1,000 (12/12) ✓ · criterio de bloqueo **no cumplido** ✓ · 96 extraídas / 13 omitidas ✓
- **Corpus piloto**: 100 oraciones, 2 positivas, solape 30 % = 29 oraciones — `reporte_anotacion.json` ✓
- **Cross-domain**: ROC-AUC 0,735 (0.7347) y AUPRC 0,269 (0.2689) — `salidas_s7/eval_citimed.json` ✓ · ensayo n=4 con AUC/AUPRC 1,000 — `salidas_s7/prueba_citimed.json` ✓
- **Pruebas**: 21 casos unitarios ✓ (5+3+6+6+1 = 21, coincide con `_run_unit.txt`) · 14 frontend ✓ (`_run_frontend.txt`) · 3,40 s ✓ · cobertura 21 % ✓ (`reporte_pytest.txt`: `TOTAL 2481 1964 21%`)
- **Kappa**: el documento decide **no reportar** el coeficiente y explica por qué (aplicación determinista, no doble ciego humano). El repo tiene `kappa_cohen: 1.0` con la misma advertencia. **Esta es una mejora de integridad respecto a S11** ✓
- **Proyección >50 % / <10 min**: correctamente marcada como proyección no medida en campo, en Resumen, Abstract, §5.3.2, §7.3 y §8.1 ✓ — corrige un riesgo mayor de S11

---

## Diagramas / artefactos: presentes en uno y ausentes en el otro

### En el documento pero NO en el repositorio

| Artefacto | Ubicación en el doc | Estado en repo |
|---|---|---|
| **Anonimizador v2 (capa de texto nativa)** — código, agregados, corrida | §7.4, Tablas 10–11 | **Ausente por completo** (C-1) |
| **Figura 17** — Canalización de anonimización (dos rutas) | p71 | No hay fuente ni PNG que la genere |
| **Figura 1** — Diagrama de Ishikawa | p8 | No hay fuente ni PNG en el repo |
| **Figura 11(101)** — Distribución física / diagrama de despliegue | p59 | No hay fuente; `s11/generar_flujo_prototipo.py` genera *flujo_prototipo.png*, que es otra figura |
| **Figura 12(112)** — Diagrama de secuencia | p61 | No hay fuente ni PNG |
| **Figura 10** — Diagrama de componentes (cinco capas) | p59 | No hay fuente ni PNG |
| **Figura 13** — Diagrama de flujo de información (nivel 1) | p62 | No hay fuente ni PNG |
| **Figura 2** — Diagrama de Gantt | p35 | No hay fuente ni PNG |
| **DVC / MLflow / LangChain / Dockerfile** | §5.1, §6.5.1, §7.1.4, Tabla 4 | **Ausentes** (C-2) |
| **Acta institucional CITIMED** | Declarada pendiente §7.5.5 | Ausente |

> **Nota:** los cinco diagramas UML/arquitectura (componentes, despliegue, secuencia, flujo de información, actividad) son un aporte técnico fuerte del documento, pero al no estar versionados no son reproducibles ni auditables. Recomendación: subir los `.puml`/`.drawio` fuente a `docs/diagramas/`.

### En el repositorio pero NO en el documento

| Artefacto | Ruta | Relevancia |
|---|---|---|
| **Restricción a 4 ejes MVP** | `s7/prompts.py` (`EJES_MVP_ES/EN`), `tests/s7/test_prompts_mvp.py`, commit `0be92db` | **Alta** — cambia el alcance del detector y la lectura de todas las métricas (C-4a) |
| **Extracción estructurada de PDF** | `api/pdf_extract.py`, `api/pdf_estructura.py`, `api/vision_client.py`, 3 endpoints, 4 archivos de prueba | **Alta** — es la funcionalidad visible en la Figura 16 (C-4b) |
| **Set adversarial de envenenamiento** | `s12/poison/` — 21 PDFs etiquetados (GENERO, INESTABLE, LATERALIDAD, DIAGNOSTICO, EDAD) | **Alta** — evidencia de validación robusta sin explotar (C-4c) |
| **Base de conocimiento GPC ampliada** | `s7/knowledge/` — 8 GPC del MSP Ecuador (caries, diabetes t2, dolor lumbar, ERC, HTA, neumonía pediátrica, odontología embarazo, protocolos odontológicos) + `mvp_consistencia.txt`; `s7/ingest_gpc.py`, `s7/knowledge_src/gpc_msp` | **Media-alta** — aparece en las capturas de los Anexos 3 y 4 («GPC: neumonía pediátrica», «GPC: mvp consistencia») pero el cuerpo solo habla genéricamente de «guías clínicas y CIE-10». Es contenido normativo **ecuatoriano**, justo lo que el docente pidió reforzar |
| **Trazabilidad RAG por oración** | commits `4a59a84`, `1127ddd` | Media — es lo que muestran los Anexos 4 y 5 |
| **Suite SDET completa** | `tests/` (contract, degraded, security/compliance, perf/stress, perf/locustfile, e2e/streamlit, eval/run_eval_suite) | Media — declarada pero no reportada (M-8) |
| **Historial SQLite + endpoints** | `api/db.py`, `GET/DELETE /historial` | Baja — el documento sí lo cubre en §6.5.7 ✓ |
| **Evidencias de idioma** | `salidas_s7/eval_idioma_en_es.json`, `sesgo_idioma_llm_real` en `metricas_llm_real.json` (ROC-AUC EN 0,458 vs ES 0,497) | Media — el documento afirma que el sesgo lingüístico es un riesgo (§6.4.3) pero **no reporta esta medición que ya existe**. Es evidencia que fortalecería el argumento |

---

## Calificación estimada por criterio de rúbrica

| Criterio | Puntos | Estimación | Justificación |
|---|---|---|---|
| **Estructura y claridad del informe** | /25 | **17–19** | Nivel «Bueno / Muy bueno». El registro académico está corregido: desaparecieron «entrega S11», «deuda», «el evaluador» y la tabla de trazabilidad-réplica. La narrativa problema→método→resultados→discusión es clara. **Restan:** salto de numeración 10→14 (M-2), captions «Figura 101/112» (M-1), duplicación literal de §6.4.3 en §6.4.7 (M-7), objetivo 4 agramatical (M-4), título de §7.5.5 con el sentido invertido (M-5), guion mal cerrado en §6.5.5. |
| **Metodología y coherencia del proyecto aplicado** | /30 | **17–20** | Nivel «Bueno». La metodología central es sólida y **el hallazgo negativo (LLM no supera a TF-IDF) está honestamente reportado y bien argumentado** — eso es de nivel excelente. **Pero la coherencia con lo ejecutado falla:** MLOps declarado en pasado que no existe (C-2), microservicios/contenedores que contradicen §2.1.1, y sobre todo la **restricción a 4 ejes MVP no declarada** (C-4a), que es un cambio de alcance que el lector solo descubre leyendo una captura de pantalla. Los supuestos y limitaciones sí están explícitos y bien hechos (proyección >50 %, cota inferior de recall, n=4 sin inferencia, cobertura 21 % declarada como limitación) — eso salva el criterio de caer más abajo. |
| **Resultados, evidencia y conclusiones** | /25 | **13–16** | Nivel «Bueno», con riesgo de «Regular». Las tablas y figuras están bien presentadas y la interpretación es sólida. **Pero:** §7.4 completa —con Tablas 10 y 11, Figura 17 y cifras en Resumen, Abstract y Conclusión 2— **no tiene evidencia reproducible** (C-1); el AUPRC de la Tabla 6 no corresponde al modelo vigente y se contradice con §6.4.5 (C-3, N-1, N-2); y el CV aparece como 0,9654 y 0,965 en dos lugares (N-3). Si el tribunal audita la trazabilidad de una sola cifra de §7.4, este criterio cae a 10. |
| **Calidad de la presentación (diapositivas)** | /10 | **n/e** | **No evaluable.** El único archivo hallado es `Formato presentación Capstone.v1.pptx` en la raíz, **sin versionar** (`git status`: untracked) y con nombre de plantilla, no de entregable. Debe confirmarse que existe la presentación final. |
| **Cumplimiento de lineamientos y citación** | /10 | **4–6** | Nivel «Regular / Bueno». **A favor:** Arial 12 uniforme, texto justificado, control de cambios aceptado, Gantt presente (Figura 2 ✓), anexos con contenido ✓, objetivos sin temporalidad ✓, costos ≠ $0 ✓ — los seis puntos de S11 atendidos. **En contra:** solo **13 referencias** de 20+ pedidas (C-5); **LOPDP, HL7 FHIR y HIPAA citados en texto pero ausentes de la bibliografía**; **Roman-Belmonte et al. (2023) citado y no referenciado**; **error de año Bowman 2022 vs 2013**; apellido «Abacha» vs «Ben Abacha»; numeración de figuras rota con «Figura 16» duplicada; índice con páginas corruptas (688, 698, 887…); salto de sección 10→14; **acta institucional pendiente** (C-6). |
| **TOTAL (sin presentación)** | **/90** | **51–61** | |
| **TOTAL proyectado (con presentación 7/10)** | **/100** | **58–68** | Banda **Insuficiente–Regular**. Con C-1, C-2, C-3 y C-5 corregidos, la proyección sube a **78–85 (Bueno–Muy bueno)**. |

### Ruta de mayor retorno por hora invertida

1. **Resolver C-1** (§7.4): subir el código v2 + JSON de agregados, o retirar la sección. — *impacto: +4 a +6 pts*
2. **Resolver C-5** (referencias 13→20+, añadir LOPDP/FHIR/HIPAA/Roman-Belmonte, corregir Bowman). — *impacto: +3 a +4 pts*
3. **Resolver C-2** (reescribir DVC/MLflow/LangChain/contenedores en modo honesto). — *impacto: +2 a +3 pts*
4. **Resolver C-3 y N-3** (AUPRC 0,398 e IC 0,353–0,457; unificar CV en 0,965 ± 0,007). — *impacto: +2 a +3 pts*
5. **Documentar C-4a** (alcance MVP de 4 ejes) en §4.1, §7.2.4 y §8.1. — *impacto: +2 a +3 pts*
6. **M-1/M-2** (numeración de figuras y secciones, regenerar índices con campos TOC). — *impacto: +1 a +2 pts*
7. **Adjuntar el acta institucional** (C-6). — *impacto: +1 a +2 pts y elimina un riesgo ético*

---

## Supuestos tomados durante el análisis

1. **Versión del documento.** Se auditó el PDF adjunto (`Proyecto_Capstone_v12_formatoFinal.pdf`, 90 pp.). El repositorio contiene `s11/docs/Proyecto_Capstone_S11.docx` (703 párrafos, 9 tablas, 8 anexos) que es una **versión anterior y distinta**; no se usó como fuente de verdad salvo para contrastar la evolución respecto a S11.
2. **Artefacto de métricas vigente.** Se asumió que `salidas_ajuste/metricas_ajuste.json` es la fuente autoritativa para el modelo ajustado, porque `s7/config.yaml` declara `modelo_tfidf: salidas_ajuste/modelo_ajustado.joblib`. `s6/metricas_ajuste.json` y `s10/evidencias/metricas_tfidf.json` se trataron como snapshots históricos.
3. **Redondeo.** Se aplicó redondeo estándar (half-up) a 3 decimales. Bajo esta convención 0,9485 → 0,949 y 0,5051 → 0,505. Una convención half-even daría 0,948 y 0,505. Los hallazgos N-4 y N-5 se marcaron como «ambiguo/riesgo» y no como error absoluto por esta razón.
4. **Estado del repositorio.** Se auditó `main` en `8bbe4b8`, incluyendo archivos sin versionar (`s12/`, `docs/images.png`, el `.pptx`). No se revisaron ramas remotas (`origin/Codigo2`, `origin/cursor/*`) — es posible, aunque improbable, que el anonimizador v2 de §7.4 viva en una rama no fusionada. **Esto debe verificarse antes de retirar la sección.**
5. **Particiones MEDEC.** Las cifras 2 189 / 574 / 597 (§6.2.1, §7.2.1) se dieron por válidas: corresponden a los CSV oficiales declarados en `s7/config.yaml`, cuyo conteo directo no se ejecutó por costo.
6. **Figuras sin fuente versionada.** Se asumió que las figuras de arquitectura (10, 11, 12, 13, 17) y el Gantt (2) e Ishikawa (1) se elaboraron en herramientas externas (draw.io/PlantUML/Excel) sin exportar la fuente al repo. Se reportan como «sin fuente versionada», no como inexistentes — la imagen sí está embebida en el PDF.
7. **Presentación.** No se localizó una presentación final identificable; `Formato presentación Capstone.v1.pptx` (raíz, sin versionar) parece una plantilla. El criterio de rúbrica correspondiente se dejó como «no evaluable» en lugar de puntuarlo a la baja.
8. **Cifras de §7.4.** Se buscó por valor numérico (`413`, `2137`, `2 137`), por terminología (`SENESCYT`, `capa de texto nativa`, `APELLIDOS Y NOMBRES`, `vía tabular`), y por nombre de archivo (`*v2*`). La ausencia se declara sobre esas tres estrategias combinadas.
