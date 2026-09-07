# Texto de reemplazo — Regularización del discurso MLOps, tecnologías y arquitectura

**Objetivo:** alinear el documento con lo que el repositorio realmente contiene, sin perder fuerza argumental.
**Principio aplicado:** no se elimina el argumento MLOps — se sustituye por lo que sí existe y se justifica técnicamente por qué DVC y MLflow no se adoptaron. Una decisión de diseño explicada vale más que una herramienta declarada y no usada.

---

## Lo que sí tienes en el repositorio (todo verificable)

| Práctica | Evidencia en el repo |
|---|---|
| Control de versiones de código | Git + GitHub, ramas por funcionalidad (`feature/*`) e integración por *pull request* (PR #5–#8 en el historial) |
| **CI/CD real** | `.github/workflows/tests.yml` — 2 *jobs* en cada push/PR a `main`: regresión con pytest + *golden set* de evaluación, y *smoke test* levantando la API con uvicorn |
| Reproducibilidad | `seed: 42` en `s7/config.yaml`; modelo serializado `salidas_ajuste/modelo_ajustado.joblib` |
| Fijación de dependencias | `requirements.txt` con versiones **exactas** en el núcleo analítico (`scikit-learn==1.8.0`, `pandas==3.0.2`, `numpy==2.4.4`, `joblib==1.5.3`, `matplotlib==3.10.8`, `scipy==1.17.1`); `requirements-dev.txt` separado |
| Configuración declarativa central | `s7/config.yaml` (rutas, modelo, tarifas, `top_k`, `bootstrap_n`, split) |
| **Registro de experimentos** | Artefactos JSON versionados con metadatos: `metricas_llm_real.json` incluye `comando`, `generado_utc`, `modelo`, `temperatura`, `n_oraciones`, tarifas e IC bootstrap. También `metricas_ajuste.json`, `metricas_tripartita.json`, `eval_citimed.json`, `interpretabilidad_meta.json` |
| **Caché determinista de inferencia** | `salidas_s7/cache/` indexada por SHA-256 del prompt → reejecución sin costo de API |
| Trazabilidad sin PHI | `salidas_s7/audit.log` registra cada inferencia con `nota_sha256`, nunca el texto |
| Gobernanza de datos | `.gitignore` excluye `s11/anonimizador_ocr/historias/`, `salidas*/`, `s11/corpus/*.csv`, `*.zip` |
| Sanitización de evidencias | `s11/sanitizar_evidencias.py` publica agregados con `entrada_sha256` del origen |
| Configuración unificada de pruebas | `pyproject.toml` → `[tool.pytest.ini_options]` |

**Lo que no existe y hay que dejar de afirmar:** DVC · MLflow (incompatible: exige `numpy<2`, el stack corre `numpy 2.4.4`) · LangChain · Dockerfile / Kubernetes · microservicios como procesos independientes.

---

## 1. §5.1 — Marco de referencia para la gestión del proyecto

### Reemplaza el párrafo introductorio

> Para la ejecución, control y seguimiento del proyecto se adoptó un marco de trabajo híbrido que combina la agilidad iterativa de Scrum con prácticas de ingeniería de aprendizaje automático (MLOps) y control de versiones mediante Git.

### Reemplaza el segundo viñetado («MLOps y DevOps»)

> **MLOps y DevOps:** El ciclo de vida del modelo se gestiona mediante prácticas implementadas directamente sobre el repositorio, sin plataformas externas de orquestación. La reproducibilidad se asegura con una semilla única (*seed* = 42) declarada en la configuración central del proyecto; el versionado del código se realiza con Git y GitHub bajo un esquema de ramas por funcionalidad e integración mediante *pull request*; las dependencias del núcleo analítico se fijan con versiones exactas en `requirements.txt`, y las de desarrollo se aíslan en `requirements-dev.txt`; y la integración continua se ejecuta en GitHub Actions, que ante cada *push* o *pull request* sobre la rama principal corre la suite de regresión, el conjunto dorado de evaluación y una prueba de humo contra la API en ejecución.

### Añade a continuación (nuevo apartado 5.1.1)

> **5.1.1. Registro de experimentos y versionado de datos**
>
> El seguimiento de experimentos se resuelve mediante artefactos JSON versionados en el repositorio, en lugar de un servidor de *tracking*. Cada corrida escribe un archivo con sus metadatos y métricas —comando ejecutado, marca temporal UTC, modelo, temperatura, tamaño de muestra, tarifas aplicadas e intervalos de confianza por *bootstrap*—, de modo que toda cifra reportada en este documento puede rastrearse hasta el archivo que la produjo. Complementariamente, las llamadas al modelo de lenguaje se almacenan en una caché indexada por el hash SHA-256 del *prompt*, lo que permite reejecutar una evaluación completa de forma determinista y sin costo adicional de API.
>
> Se evaluó el uso de MLflow para esta función y se descartó en la presente fase por una incompatibilidad de dependencias: MLflow 2.x requiere `numpy<2`, mientras que el resto del núcleo analítico opera sobre `numpy 2.4.4`. La restricción y la vía de instalación en entorno aislado quedan documentadas en el propio repositorio, y su adopción se plantea entre las recomendaciones de escalamiento.
>
> Respecto del versionado de datos, el proyecto no incorpora DVC. La decisión responde al modelo de gobernanza adoptado: las historias clínicas originales, las salidas del anonimizador, las imágenes de revisión y los archivos con texto clínico están excluidos del control de versiones y permanecen bajo custodia local, por lo que no existe un conjunto de datos versionable fuera del entorno del investigador. Lo que sí se versiona son los agregados desprovistos de información sensible, acompañados del hash SHA-256 del archivo de origen que los generó, lo que preserva la trazabilidad sin exponer material clínico. La incorporación de DVC se plantea para el escenario de despliegue institucional, en el que el corpus residiría dentro de la infraestructura de la clínica.

> **Por qué conviene:** este bloque convierte dos ausencias en dos decisiones de ingeniería fundamentadas, y la de DVC queda además alineada con el marco ético del capítulo 7 —no versionar datos es una consecuencia directa de la política de PHI, no una omisión.

---

## 2. §6.5.1 — Arquitectura técnica y despliegue

### Reemplaza el último viñetado («MLOps»)

> **MLOps:** La reproducibilidad del *pipeline* se sostiene en una semilla única, la fijación exacta de versiones de las librerías del núcleo analítico, el registro de cada corrida en artefactos JSON versionados con sus metadatos y métricas, y una caché de inferencia indexada por hash que permite reejecutar las evaluaciones de forma determinista. La automatización de pruebas se ejecuta en GitHub Actions sobre cada integración a la rama principal.

### Reemplaza la frase introductoria del apartado

> Se diseñó e implementó una arquitectura modular de componentes desacoplados por responsabilidad, ejecutada localmente para garantizar la privacidad de los datos. Los componentes principales incluyen:

*(elimina «de microservicios, orquestada localmente»)*

---

## 3. §7.1.3 — Actividades realizadas

### Reemplaza el viñetado «Diseño de la arquitectura del sistema»

> **Diseño de la arquitectura del sistema:** Modelado de los flujos de información y especificación de una arquitectura modular por responsabilidades —ingesta y anonimización, segmentación, generación de *embeddings*, recuperación semántica e inferencia—, desplegada como un único servicio en entorno local.

*(elimina «microservicios contenerizados»)*

---

## 4. §7.1.4 — Herramientas utilizadas

### Reemplaza el viñetado «Infraestructura, despliegue y MLOps»

> **Infraestructura, despliegue y MLOps:** Ejecución en entorno local con configuración declarativa centralizada y semilla fija; registro de experimentos mediante artefactos JSON versionados y caché de inferencia indexada por hash SHA-256; Git y GitHub para el versionado del código bajo un esquema de ramas por funcionalidad; y GitHub Actions para la automatización de la integración continua, que comprende pruebas de regresión, evaluación sobre conjunto dorado y prueba de humo sobre la API.

---

## 5. Tabla 4 — Estructura de costos

### Reemplaza la celda «Descripción y detalle» de la fila «Herramientas Open Source»

> Uso de frameworks libres (Python, FastAPI, scikit-learn, FAISS, Sentence Transformers, spaCy, PyMuPDF, React) sin costo de licencia.

*(elimina **LangChain**, **MLflow** y **DVC** de esa celda: ninguno se instala en el proyecto)*

---

## 6. §7.2.6 — Arquitectura del prototipo

### Reemplaza el párrafo introductorio

> El prototipo funcional se diseñó bajo una arquitectura modular de componentes desacoplados por responsabilidad, que operan dentro de un único servicio en un entorno local controlado, lo que garantiza que ningún dato salga del equipo. Esta separación preserva la ruta de evolución hacia un despliegue en microservicios independientes, planteada en las recomendaciones del capítulo 8. Los componentes de la infraestructura comprenden:

---

## 7. §7.5.1 — Privacidad y confidencialidad

### Reemplaza el viñetado «Mitigación técnica»

> **Mitigación técnica:** Para mitigar este riesgo, la arquitectura incorpora un módulo local de anonimización previa y la ejecución íntegra del procesamiento en el equipo del investigador, sin envío de datos sin procesar a servicios externos de inferencia y en cumplimiento de las normativas de confidencialidad médica. El aislamiento del despliegue mediante contenedores en entornos cerrados (*on-premise* o nube privada controlada) se plantea como vía de escalamiento institucional y se detalla en las recomendaciones.

---

## 8. §4.1 — Alcance: «Incluye»

### Reemplaza el bloque «Implementación de pipeline de MLOps»

> - Implementación de prácticas de MLOps:
>   - Registro de experimentos mediante artefactos versionados con metadatos y métricas
>   - Versionado de código con Git y del modelo entrenado como artefacto serializado
>   - Automatización de integración continua con GitHub Actions

---

## 9. Lo que NO debes tocar

Estas menciones son **correctas** y quedan coherentes una vez aplicados los cambios anteriores:

| Ubicación | Texto | Por qué se mantiene |
|---|---|---|
| §2.1.1 (Propuesta A) | «Arquitectura de software: microservicios (ingestión, inferencia, generación de alertas)» · «Gestión del ciclo de vida del modelo: pipeline de MLOps (registro de experimentos, versionado, validación y automatización CI/CD)» | Es la **arquitectura propuesta** en la fase de análisis de alternativas, no una afirmación de lo ejecutado. Legítimo en tiempo futuro/condicional |
| §2.1.1 (Tecnologías) | «Despliegue: Entorno local, no contenedores, GitHub Actions (CI/CD)» | **Es exacto.** De hecho es el pasaje que contradecía al resto del documento; ahora el resto se alinea con él |
| §8.2, recomendación 2 | «integración de orquestadores de contenedores (como Kubernetes)» | Recomendación a futuro ✓ |
| §8.2, recomendación 3 | «institucionalizar el uso de DVC y MLflow para el monitoreo permanente» | Recomendación a futuro ✓ — y ahora **gana coherencia**: se recomienda adoptar lo que se explicó por qué aún no se adoptó |
| §9, línea 4 | «Consolidar una infraestructura completa de MLOps utilizando GitHub Actions, DVC y MLflow» | Trabajo futuro ✓ |

---

## 10. Verificación final (búsqueda en Word)

Tras aplicar los cambios, busca cada término y confirma que **solo** aparezca en contextos de propuesta, recomendación o trabajo futuro:

- [ ] `DVC` → debe quedar solo en §5.1.1 (justificación de no adopción), §8.2 rec. 3 y §9
- [ ] `MLflow` → solo en §5.1.1 (justificación), §2.1.1 (propuesta), §8.2 rec. 3 y §9
- [ ] `LangChain` → **cero apariciones** (no se usa en el proyecto)
- [ ] `contenedor` / `contenerizad` → solo §7.5.1 (como vía futura), §8.2 rec. 2 y §9
- [ ] `microservicios` → solo §2.1.1 (propuesta), §7.2.6 (como ruta de evolución) y §8.2
- [ ] `Se incorporó` / `Se integró` junto a DVC o MLflow → **cero apariciones**
- [ ] `Docker` → verifica que no quede afirmado como usado

> **Nota adicional:** §5.1 menciona actualmente «control de versiones mediante Git, DVC y MLflow». El reemplazo del punto 1 ya lo corrige, pero conviene revisar también la Tabla 4 (punto 5) y §7.1.4 (punto 4), donde la tríada se repite.
