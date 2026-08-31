# Prototipo funcional: persistencia y rediseño de la interfaz

*Fragmento destinado a la sección §5 del informe final S11.*

Entre las entregas S10 y S11 el prototipo pasó de ser una demostración efímera a una
aplicación con estado. Dos cambios lo explican: la incorporación de una capa de
persistencia en el backend y el rediseño completo de la interfaz alrededor del flujo
de trabajo clínico real. Ninguno de los dos altera el modelo de detección, y esto
conviene decirlo de entrada: las métricas de la sección §4 no cambian por este
trabajo. Lo que cambia es la posibilidad de que un profesional use el sistema más de
una vez y pueda volver sobre lo que ya revisó.

## 5.1 Persistencia del historial de análisis

Hasta S10 cada análisis se perdía al recargar la página. El prototipo ahora guarda
cada consulta en una base SQLite del lado del servidor, implementada en
`api/db.py` mediante la clase `HistorialDB`. El esquema es deliberadamente simple:

| Columna | Tipo | Contenido |
| --- | --- | --- |
| `id` | TEXT (clave primaria) | UUID4 generado por el servidor |
| `created_at` | TEXT | marca de tiempo UTC en formato ISO 8601 |
| `nota` | TEXT | texto de la nota analizada |
| `resultado_json` | TEXT | respuesta completa del análisis, serializada |
| `ejemplo_id` | TEXT | caso de demostración empleado, o `propia` |
| `idioma` | TEXT | idioma de la nota |
| `mock_llm` | INTEGER | si el análisis usó LLM simulado o real |
| `alerta` | INTEGER | si el análisis derivó en alerta |

Hay un índice descendente sobre `created_at`, porque la única consulta de lectura
frecuente es «dame los últimos N análisis». La tabla se autolimita: cada inserción
ejecuta un `DELETE` que conserva solo las `max_items` filas más recientes, con un
valor por defecto de 50 configurable con la variable de entorno
`HISTORIAL_MAX_ITEMS`. La decisión de acotar la tabla es intencional y no una
limitación técnica: se trata de datos clínicos, y una base que crece sin límite en el
equipo de un consultorio es una superficie de riesgo innecesaria.

El acceso a la conexión está encapsulado en un gestor de contexto que confirma la
transacción al salir sin error y la revierte ante cualquier excepción, de modo que un
fallo a mitad de una inserción no deja la tabla en estado inconsistente. La conexión
se abre con `check_same_thread=False` porque FastAPI atiende peticiones desde un pool
de hilos.

Sobre esta capa se exponen cuatro rutas nuevas en `api/main.py`:

| Ruta | Método | Función |
| --- | --- | --- |
| `/historial?limit=N` | GET | lista los N análisis más recientes |
| `/historial/{id}` | DELETE | elimina una entrada concreta |
| `/historial` | DELETE | vacía el historial completo |
| `/health` | GET | informa la ruta de la base y el número de entradas almacenadas |

La ampliación de `/health` merece una nota. El endpoint ahora declara si el modelo
TF-IDF está disponible y en qué ruta, si el LLM opera en modo simulado, si ese modo
viene forzado por el servidor, si hay credencial de API configurada, y el estado del
historial. Es un diagnóstico de una sola llamada: cuando la interfaz muestra
«Backend listo · TF-IDF · OpenAI», está reflejando esa respuesta. Para un evaluador
que reproduce el prototipo en otra máquina, esto reduce el diagnóstico de un
problema de configuración a leer un JSON.

## 5.2 Rediseño de la interfaz

La interfaz se reconstruyó como un espacio de trabajo de tres zonas, visible en la
figura del análisis. De izquierda a derecha: el historial persistente, la nota bajo
análisis y el hallazgo. El orden no es arbitrario; sigue la secuencia de lectura de
quien revisa una historia clínica, que primero se ubica en el contexto de lo ya
visto, luego lee el texto y por último atiende la alerta.

La zona de hallazgo es donde se concentra el argumento del proyecto. En lugar de
emitir un veredicto global sobre la nota, la interfaz señala la frase concreta que
debe revisarse, muestra su score de localización contra el umbral en una barra con
marca visible, y despliega el detalle por frase con las cuatro columnas de score
(TF-IDF, LLM, RAG y localización combinada). Un revisor puede así discrepar del
sistema con la evidencia a la vista, que es exactamente el comportamiento que se
busca en una herramienta de apoyo. La captura de la sección de evidencias muestra
el caso de la amoxicilina prescrita a un paciente con alergia documentada a
penicilina: el sistema marca la frase 3 con score de localización 0,66 sobre un
umbral de 0,50, y deja las dos frases anteriores por debajo de 0,10.

El disclaimer «Prototipo de investigación. No sustituye el criterio médico» quedó
fijo en la barra superior, no en un pie de página que se pierde al desplazarse. Es
una decisión de diseño con contenido ético, coherente con lo que se argumenta en la
sección §6.

Se atendieron además tres aspectos de accesibilidad: contraste verificado en ambos
temas, respeto de la preferencia `prefers-reduced-motion` para desactivar las
animaciones, y etiquetado ARIA de las regiones y los estados de carga. La suite del
frontend, ejecutada con el runner nativo de Node, cubre estos puntos en
`accessibility.test.js` y `panel-polish.test.js`; sus resultados se reportan junto
con el resto de las pruebas en la sección §3.5.

Existe también un tema oscuro accesible mediante un atajo no anunciado en la
interfaz: cinco pulsaciones sobre el logotipo en menos de dos segundos. La
preferencia queda registrada en `localStorage` y persiste entre sesiones. Se
documenta aquí por completitud y porque forma parte del código entregado, no como
una funcionalidad clínica.

## 5.3 Reproducción

```bash
# Terminal 1: backend
uvicorn api.main:app --reload --port 8000

# Terminal 2: frontend
cd frontend && npm install && npm run dev

# Capturas de evidencia (requiere ambos servicios arriba)
python s11/capture_prototipo.py
```

El script `s11/capture_prototipo.py` reemplaza al antiguo `s10/capture_demo.py`,
que quedó obsoleto tras la migración de Streamlit a React y el rediseño. Detecta
automáticamente el puerto en el que Vite haya arrancado, verifica que la API
responda, y genera las cuatro capturas de la carpeta `s11/evidencias/capturas/`:
vista inicial, hallazgo localizado, tema oscuro y panel de historial.
