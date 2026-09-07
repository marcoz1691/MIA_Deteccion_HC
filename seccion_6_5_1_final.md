# 6.5.1. Arquitectura técnica y despliegue

> Texto completo y continuo. Reemplaza íntegramente la sección 6.5.1 actual.
> Formato Capstone: Arial 12 regular, justificado. Viñetas con rótulo en negrita, igual que el resto del documento.

---

Se diseñó e implementó una arquitectura modular de componentes desacoplados por responsabilidad, ejecutada íntegramente en local para garantizar la privacidad de los datos. Los componentes principales incluyen:

- **Módulo de ingesta y anonimización:** Componente encargado de la depuración local de los registros clínicos de CITIMED, que aplica el enmascaramiento de identificadores antes de que el texto alcance cualquier etapa analítica.

- **Servicio de recuperación semántica (RAG):** Utiliza Sentence Transformers para generar embeddings y un índice vectorial FAISS para recuperar guías de práctica clínica, códigos CIE-10 y protocolos institucionales relevantes.

- **Motor de detección y localización:** Opera bajo un esquema en cascada. Un clasificador léxico —TF-IDF combinado con rasgos numéricos por oración y regresión logística— puntúa la totalidad de las oraciones y constituye el componente de producción; únicamente aquellas que superan el umbral de decisión se elevan a un analizador generativo basado en un modelo de lenguaje de gran escala en modo zero-shot, que evalúa la oración en el contexto recuperado. Si el servicio generativo no responde, el sistema entrega el resultado del clasificador léxico y notifica de manera explícita la degradación al auditor.

- **Capa de exposición (API e interfaz):** API REST en FastAPI e interfaz institucional en React (espacio de trabajo de tres zonas, historial persistente en SQLite y tema claro por defecto). Streamlit se conserva únicamente como demostración analítica opcional, no como superficie de uso del prototipo.

- **MLOps:** La reproducibilidad del pipeline se sostiene en cuatro mecanismos implementados sobre el propio repositorio: una semilla única declarada en la configuración central, la fijación de versiones exactas para las librerías del núcleo analítico, el registro de cada corrida en artefactos JSON versionados que conservan comando, marca temporal, modelo, tamaño de muestra e intervalos de confianza, y una caché de inferencia indexada por el hash SHA-256 del prompt que permite reejecutar una evaluación completa de forma determinista. La automatización de pruebas se ejecuta en GitHub Actions sobre cada incorporación de código a la rama principal, y comprende la suite de regresión, la evaluación sobre el conjunto dorado y una prueba de humo contra la API en ejecución.

---

## Qué cambió y por qué

| Elemento | Antes | Ahora | Motivo |
|---|---|---|---|
| Frase inicial | «arquitectura de **microservicios**, orquestada localmente» | «arquitectura **modular de componentes desacoplados**, ejecutada íntegramente en local» | El backend es una **única aplicación FastAPI** (`api/main.py`); los componentes son módulos en el mismo proceso, no servicios independientes. Además, «microservicios» chocaba con §2.1.1, que ya decía «Entorno local, no contenedores» |
| Viñeta **MLOps** | «**Se incorporó** el control de versiones de datos (DVC) y de experimentos (MLflow)» | Semilla fija · versiones exactas · artefactos JSON versionados · caché por hash · CI en GitHub Actions | **No existe** `.dvc/`, `dvc.yaml` ni `mlruns/`; DVC no figura en ningún `requirements`. Y `requirements-optional.txt` declara que **MLflow es incompatible con el stack** (exige `numpy<2`, el proyecto corre `numpy 2.4.4`). Lo que sí tienes está verificado y es más específico |
| Viñeta **Motor de detección** | «Basado en un **modelo de lenguaje de gran escala (LLM)**, ajustado o en modo zero-shot» | Cascada: clasificador léxico en producción → LLM solo sobre las oraciones que superan el umbral | Esta era la corrección más importante. Tal como estaba, **contradecía la conclusión central del propio documento**: §7.2.4 y §8.1 establecen que el LLM no supera al modelo léxico y que la decisión final fue una arquitectura en cascada con TF-IDF como componente de producción. También contradecía la Figura 10, que ya dibuja la cascada con el umbral y el modo degradado |
| Módulo de ingesta | «Servicio encargado de…» | «Componente encargado de…» + mención al orden de ejecución | Coherencia con el cambio de «microservicios» a «componentes» |

---

## Ajustes de una línea en otros capítulos

La §6.5.1 ya queda coherente, pero el documento seguirá contradiciéndose si estas cuatro frases no se corrigen. Son sustituciones puntuales:

| Ubicación | Sustituir por |
|---|---|
| **§5.1**, viñeta «MLOps y DevOps» | **MLOps y DevOps:** El ciclo de vida del modelo se gestiona mediante prácticas implementadas sobre el repositorio, sin plataformas externas de orquestación: semilla única para la reproducibilidad, versionado del código con Git y GitHub bajo ramas por funcionalidad e integración por pull request, fijación de versiones exactas en el núcleo analítico, e integración continua automatizada en GitHub Actions. *(elimina «control de versiones mediante Git, DVC y MLflow» del párrafo introductorio: deja solo Git)* |
| **§7.1.3**, viñeta «Diseño de la arquitectura del sistema» | …especificación de una arquitectura modular por responsabilidades (ingesta y anonimización, segmentación, embeddings, recuperación semántica e inferencia), desplegada como un único servicio en entorno local. *(elimina «microservicios contenerizados»)* |
| **§7.1.4**, viñeta «Infraestructura, despliegue y MLOps» | **Infraestructura, despliegue y MLOps:** Ejecución en entorno local con configuración declarativa centralizada y semilla fija; registro de experimentos mediante artefactos JSON versionados y caché de inferencia indexada por hash SHA-256; Git y GitHub para el versionado del código; y GitHub Actions para la integración continua, que comprende pruebas de regresión, evaluación sobre conjunto dorado y prueba de humo sobre la API. |
| **Tabla 4**, fila «Herramientas Open Source» | Uso de frameworks libres (Python, FastAPI, scikit-learn, FAISS, Sentence Transformers, spaCy, PyMuPDF, React) sin costo de licencia. *(elimina LangChain, MLflow y DVC: ninguno se instala en el proyecto)* |

**No toques:** §2.1.1 (es la arquitectura *propuesta* en el análisis de alternativas, y su línea «Despliegue: Entorno local, no contenedores» ya era la correcta), §8.2 recomendaciones 2 y 3, ni el capítulo 9. Allí DVC, MLflow y Kubernetes figuran como trabajo futuro, y una vez hechos estos cambios dejan de contradecir al cuerpo del documento.

---

## Opcional pero recomendado

Si además quieres justificar por escrito la ausencia de DVC y MLflow —en vez de solo dejar de afirmarlos—, el archivo `seccion_5_1_final.md` contiene dos sub-apartados redactados para la §5.1 (**5.1.1 Registro de experimentos** y **5.1.2 Versionado de datos y gobernanza**) que convierten ambas ausencias en decisiones de ingeniería fundamentadas: MLflow por incompatibilidad de dependencias documentada, y DVC porque versionar datos contradiría la política de PHI del capítulo 7. Un tribunal valora más una restricción explicada que una herramienta declarada y ausente.
