# 5.1. Marco de referencia para la gestión del proyecto

> Texto completo y continuo. Reemplaza íntegramente la sección 5.1 actual.
> Formato Capstone: Arial 12 regular, justificado, sangría de primera línea. Las viñetas conservan el rótulo en negrita, igual que el resto del documento.

---

Para la ejecución, control y seguimiento del proyecto se adoptó un marco de trabajo híbrido que combina la agilidad iterativa de Scrum con prácticas de ingeniería de aprendizaje automático (MLOps) y control de versiones mediante Git.

- **Scrum:** Aplicado a través de ciclos iterativos cortos (sprints) para el desarrollo incremental de los componentes del asistente inteligente, facilita la adaptación continua ante los requerimientos técnicos y analíticos del entorno clínico de CITIMED.

- **MLOps y DevOps:** El ciclo de vida del modelo se gestiona mediante prácticas implementadas directamente sobre el repositorio del proyecto, sin plataformas externas de orquestación. La reproducibilidad se asegura con una semilla única (seed = 42) declarada en la configuración central; el versionado del código se realiza con Git y GitHub bajo un esquema de ramas por funcionalidad e integración mediante pull request; las dependencias del núcleo analítico se fijan con versiones exactas y las de desarrollo se aíslan en un archivo independiente; y la integración continua se ejecuta en GitHub Actions, que ante cada incorporación de código a la rama principal corre la suite de regresión, la evaluación sobre el conjunto dorado y una prueba de humo contra la API en ejecución.

## 5.1.1. Registro de experimentos y trazabilidad de las corridas

El seguimiento de experimentos se resuelve mediante artefactos JSON versionados en el repositorio, en lugar de un servidor de tracking. Cada ejecución escribe un archivo con sus metadatos y métricas —comando ejecutado, marca temporal UTC, modelo empleado, temperatura, tamaño de muestra, tarifas aplicadas e intervalos de confianza calculados por bootstrap—, de modo que toda cifra reportada en este documento puede rastrearse hasta el archivo que la produjo. Complementariamente, las llamadas al modelo de lenguaje se almacenan en una caché indexada por el hash SHA-256 del prompt, lo que permite reejecutar una evaluación completa de forma determinista y sin costo adicional de interfaz de programación de aplicaciones. El registro de inferencias del prototipo se conserva en una bitácora de auditoría que almacena únicamente el hash de cada nota analizada, nunca su texto, lo que preserva la trazabilidad operativa sin retener información clínica.

Se evaluó el uso de MLflow para cubrir esta función y se descartó en la presente fase por una incompatibilidad de dependencias: MLflow 2.x requiere una versión de la librería NumPy anterior a la 2.0, mientras que el resto del núcleo analítico opera sobre NumPy 2.4.4. La restricción y la vía de instalación en un entorno virtual aislado quedan documentadas en el repositorio, y su adopción se plantea entre las recomendaciones de escalamiento del capítulo 8.

## 5.1.2. Versionado de datos y gobernanza de la información

El proyecto no incorpora una herramienta de versionado de datos como DVC. La decisión responde de manera directa al modelo de gobernanza adoptado: las historias clínicas originales, las salidas del módulo de anonimización, las imágenes de revisión y los archivos que contienen texto clínico están excluidos del control de versiones y permanecen bajo custodia local, por lo que no existe un conjunto de datos versionable fuera del entorno del investigador. Versionar ese material contradiría el propio marco de protección descrito en el capítulo 7.

Lo que sí se versiona son los agregados desprovistos de información sensible —conteos, métricas y distribuciones—, acompañados del hash SHA-256 del archivo de origen que los generó. Este mecanismo preserva la trazabilidad entre cada resultado publicado y la corrida que lo produjo, sin exponer material clínico. La incorporación de un versionado de datos formal se plantea para el escenario de despliegue institucional, en el que el corpus residiría dentro de la infraestructura de la Clínica CITIMED y quedaría sujeto a sus propias políticas de custodia.

---

## Ajustes puntuales fuera de la §5.1

La sección anterior queda coherente por sí sola, pero el documento seguirá contradiciéndose si no se corrigen estas cinco frases en otros capítulos. Son reemplazos de una línea:

| Ubicación | Sustituir por |
|---|---|
| **§6.5.1**, viñeta «MLOps» | **MLOps:** La reproducibilidad del pipeline se sostiene en una semilla única, la fijación exacta de versiones del núcleo analítico, el registro de cada corrida en artefactos JSON versionados y una caché de inferencia indexada por hash. La automatización de pruebas se ejecuta en GitHub Actions sobre cada integración a la rama principal. |
| **§6.5.1**, frase inicial | Se diseñó e implementó una arquitectura modular de componentes desacoplados por responsabilidad, ejecutada localmente para garantizar la privacidad de los datos. *(elimina «de microservicios, orquestada localmente»)* |
| **§7.1.3**, viñeta «Diseño de la arquitectura» | …especificación de una arquitectura modular por responsabilidades (ingesta y anonimización, segmentación, embeddings, recuperación semántica e inferencia), desplegada como un único servicio en entorno local. *(elimina «microservicios contenerizados»)* |
| **§7.1.4**, viñeta «Infraestructura, despliegue y MLOps» | **Infraestructura, despliegue y MLOps:** Ejecución en entorno local con configuración declarativa centralizada y semilla fija; registro de experimentos mediante artefactos JSON versionados y caché de inferencia indexada por hash SHA-256; Git y GitHub para el versionado del código; y GitHub Actions para la integración continua, que comprende pruebas de regresión, evaluación sobre conjunto dorado y prueba de humo sobre la API. |
| **Tabla 4**, fila «Herramientas Open Source» | Uso de frameworks libres (Python, FastAPI, scikit-learn, FAISS, Sentence Transformers, spaCy, PyMuPDF, React) sin costo de licencia. *(elimina LangChain, MLflow y DVC)* |

**No toques** §2.1.1 (es la arquitectura *propuesta*, y su línea «Despliegue: Entorno local, no contenedores» ya era correcta), ni §8.2 recomendaciones 2 y 3, ni el capítulo 9: allí DVC, MLflow y Kubernetes aparecen como trabajo futuro y ahora ganan coherencia con la §5.1.2.
