# API FastAPI — MIA Detección HC

Backend HTTP que expone el pipeline de detección de inconsistencias en historias clínicas (`s7/inferencia.analizar_nota`). El frontend React y la demo Streamlit consumen la misma lógica de inferencia.

- **OpenAPI (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Despliegue producción:** [`DEPLOY.md`](DEPLOY.md)

---

## Arranque

Desde la **raíz del repositorio**:

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

Alternativa directa:

```bash
python -m api.main
```

El servicio carga al iniciar:

- Configuración desde `s7/config.yaml`
- Modelo TF-IDF desde `salidas_ajuste/modelo_ajustado.joblib` (si existe)
- Índice RAG bajo demanda (primera petición con brazo `llm_rag`)

Frontend React (opcional): [`frontend/README.md`](../frontend/README.md) — `npm run dev` en el puerto 5173, con proxy a esta API.

---

## Resumen de endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servicio, modelo TF-IDF y configuración LLM |
| `POST` | `/generar` | Analiza una nota clínica y retorna scores por oración |

No hay autenticación en la API. CORS está abierto (`allow_origins=["*"]`) para desarrollo; en producción conviene restringirlo en el reverse proxy.

---

## Variables de entorno

Definidas en `.env` (ver [`.env.example`](../.env.example)):

| Variable | Descripción |
|----------|-------------|
| `MOCK_LLM` | Si está definida (`true`/`false`), **fuerza** el modo mock en el servidor e ignora `mock_llm` del cliente |
| `OPENAI_API_KEY` | Clave para LLM (OpenAI, Ollama con valor `ollama`, etc.) |
| `OPENAI_BASE_URL` | URL base alternativa (p. ej. `http://localhost:11434/v1` para Ollama) |
| `MISTRAL_API_KEY` | Clave alternativa; cualquiera de las dos activa `llm_api_configurada` |

---

## `GET /health`

Comprueba que el servicio responde y expone el estado de recursos internos. Útil para load balancers y verificación post-deploy.

### Respuesta `200 OK`

```json
{
  "status": "ok",
  "modelo_tfidf_disponible": true,
  "modelo_tfidf_path": "C:\\...\\salidas_ajuste\\modelo_ajustado.joblib",
  "mock_llm": true,
  "mock_llm_forzado": false,
  "llm_api_configurada": false
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `status` | string | Siempre `"ok"` si el proceso está vivo |
| `modelo_tfidf_disponible` | boolean | `true` si el joblib existe y se cargó al arranque |
| `modelo_tfidf_path` | string | Ruta absoluta del modelo configurado |
| `mock_llm` | boolean | Modo mock **efectivo** en el servidor |
| `mock_llm_forzado` | boolean | `true` si `MOCK_LLM` está definido en el entorno |
| `llm_api_configurada` | boolean | `true` si hay `OPENAI_API_KEY` o `MISTRAL_API_KEY` |

### Ejemplo

```bash
curl http://localhost:8000/health
```

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

---

## `POST /generar`

Recibe el texto de una nota clínica, la segmenta en oraciones y calcula scores de inconsistencia con uno o más **brazos** de inferencia.

### Request body

```json
{
  "nota_clinica": "Paciente refiere dolor en molar 36. Antecedentes: alergia documentada a penicilina. Se indica amoxicilina 500 mg cada 8 h.",
  "mock_llm": true,
  "idioma": "spanish",
  "brazos": ["tfidf", "llm_zero", "llm_rag"],
  "umbral": 0.5
}
```

| Campo | Tipo | Obligatorio | Default | Descripción |
|-------|------|-------------|---------|-------------|
| `nota_clinica` | string | **Sí** | — | Texto libre de la historia clínica (mín. 1 carácter) |
| `mock_llm` | boolean | No | `true` | Solicita respuestas LLM simuladas. Ignorado si `MOCK_LLM` está definido en el servidor |
| `idioma` | `"english"` \| `"spanish"` | No | `"spanish"` | Idioma de los prompts LLM |
| `brazos` | array | No | `["tfidf", "llm_zero", "llm_rag"]` | Métodos a ejecutar (mín. 1). Valores: `tfidf`, `llm_zero`, `llm_rag` |
| `umbral` | float | No | `0.5` | Score mínimo (0–1) para marcar `alerta: true` en una oración |

#### Brazos de inferencia

| Brazo | Requisito | Descripción |
|-------|-----------|-------------|
| `tfidf` | `salidas_ajuste/modelo_ajustado.joblib` | Modelo supervisado local (rápido, sin API externa) |
| `llm_zero` | API LLM o mock | Clasificación zero-shot por oración |
| `llm_rag` | API LLM o mock + índice FAISS | Clasificación con contexto RAG desde `s7/rag/` |

### Respuesta `200 OK`

```json
{
  "oraciones": [
    {
      "sid": 0,
      "oracion": "Paciente refiere dolor en molar 36.",
      "score_tfidf": 0.12,
      "score_llm_zero": 0.08,
      "score_llm_rag": 0.10,
      "score_localizacion": 0.09,
      "alerta": false,
      "respuesta_llm_zero": "no",
      "respuesta_llm_rag": "no",
      "latencia_llm_zero_ms": 45.2,
      "latencia_llm_rag_ms": 120.5
    },
    {
      "sid": 2,
      "oracion": "Se indica amoxicilina 500 mg cada 8 h.",
      "score_tfidf": 0.78,
      "score_llm_zero": 0.92,
      "score_llm_rag": 0.95,
      "score_localizacion": 0.89,
      "alerta": true,
      "respuesta_llm_zero": "yes",
      "respuesta_llm_rag": "yes",
      "latencia_llm_zero_ms": 38.1,
      "latencia_llm_rag_ms": 95.3
    }
  ],
  "top1": {
    "sid": 2,
    "oracion": "Se indica amoxicilina 500 mg cada 8 h.",
    "score_localizacion": 0.89,
    "alerta": true
  },
  "truncado": false,
  "n_total": 3,
  "modo_degradado": false,
  "brazos_efectivos": ["tfidf", "llm_zero", "llm_rag"],
  "mensaje_fallback": null
}
```

#### Campos de respuesta

**Nivel nota**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `oraciones` | array | Una entrada por oración analizada |
| `top1` | object \| null | Oración con mayor `score_localizacion` |
| `truncado` | boolean | `true` si la nota excedió el límite de oraciones del pipeline |
| `n_total` | integer | Número total de oraciones detectadas (antes de truncar) |
| `modo_degradado` | boolean | `true` si se pidieron brazos LLM pero el servidor degradó a solo TF-IDF |
| `brazos_efectivos` | string[] | Brazos que realmente se usaron en el análisis |
| `mensaje_fallback` | string \| null | Explicación cuando hubo degradación (p. ej. API LLM no disponible) |

**Por oración (`oraciones[]`)**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `sid` | integer | Índice de la oración en la nota |
| `oracion` | string | Texto de la oración |
| `score_tfidf` | float \| null | Score del brazo TF-IDF (null si no se ejecutó) |
| `score_llm_zero` | float \| null | Score zero-shot |
| `score_llm_rag` | float \| null | Score con RAG |
| `score_localizacion` | float | Score combinado usado para resaltar y alertas |
| `alerta` | boolean | `score_localizacion >= umbral` |
| `respuesta_llm_zero` | string \| null | Respuesta cruda del LLM zero-shot |
| `respuesta_llm_rag` | string \| null | Respuesta cruda del LLM con RAG |
| `latencia_llm_zero_ms` | float \| null | Latencia del brazo zero-shot |
| `latencia_llm_rag_ms` | float \| null | Latencia del brazo RAG |

#### Cálculo de `score_localizacion`

El score de localización combina los brazos activos:

- Si hay LLM y TF-IDF: `0.65 × LLM + 0.35 × TF-IDF`
- Si solo TF-IDF: usa `score_tfidf`
- Si solo LLM: prioriza `llm_rag` sobre `llm_zero`

La oración con mayor `score_localizacion` aparece en `top1`.

### Errores

| Código | Cuándo | Ejemplo de `detail` |
|--------|--------|---------------------|
| `422` | Validación Pydantic (body inválido) | `"String should have at least 1 character"` |
| `503` | Modelo TF-IDF ausente y se pidió brazo `tfidf` | `"Modelo TF-IDF no encontrado en ... Entrena con: python s6/modelo_ajustado.py"` |
| `503` | LLM real requerido pero sin API key ni TF-IDF de respaldo | `"API LLM no disponible y no hay modelo TF-IDF para fallback."` |

En algunos casos de fallo parcial del LLM (con TF-IDF disponible), la API responde `200` con `modo_degradado: true` en lugar de error.

### Ejemplos

**cURL — caso típico con mock (desarrollo)**

```bash
curl -X POST http://localhost:8000/generar \
  -H "Content-Type: application/json" \
  -d "{\"nota_clinica\": \"Paciente con alergia a penicilina. Se indica amoxicilina.\", \"mock_llm\": true}"
```

**Solo TF-IDF (sin LLM)**

```bash
curl -X POST http://localhost:8000/generar \
  -H "Content-Type: application/json" \
  -d "{\"nota_clinica\": \"Nota clínica de prueba.\", \"brazos\": [\"tfidf\"]}"
```

**PowerShell**

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/generar" `
  -ContentType "application/json" `
  -Body '{"nota_clinica": "Paciente con alergia a penicilina. Se indica amoxicilina.", "mock_llm": true}'
```

**JavaScript (frontend)**

Ver [`frontend/src/api/client.js`](../frontend/src/api/client.js):

```javascript
const res = await fetch("/generar", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    nota_clinica: nota,
    idioma: "spanish",
    brazos: ["tfidf", "llm_zero", "llm_rag"],
    umbral: 0.5,
    mock_llm: true, // omitir en prod si MOCK_LLM está en el servidor
  }),
});
const data = await res.json();
```

---

## Requisitos previos

| Recurso | Ruta / comando | Necesario para |
|---------|----------------|----------------|
| Modelo TF-IDF | `python s6/modelo_ajustado.py` → `salidas_ajuste/modelo_ajustado.joblib` | Brazo `tfidf` |
| Índice RAG | Primera petición con `llm_rag` (~15 s) o pre-calentar | Brazo `llm_rag` |
| API LLM | `.env` con claves + `MOCK_LLM=false` | LLM real en producción |

---

## Arquitectura interna

```
POST /generar
    └── InferenceService.generar()
            ├── resolve_mock_llm()      ← api/settings.py
            ├── _validate_resources()   ← joblib / API key
            ├── analizar_nota()         ← s7/inferencia.py
            └── serialize_resultado() ← api/service.py → GenerarResponse
```

Los esquemas Pydantic viven en [`schemas.py`](schemas.py). La app FastAPI está en [`main.py`](main.py).

---

## Flujo recomendado por entorno

| Entorno | `MOCK_LLM` | `mock_llm` en body | Brazos típicos |
|---------|------------|--------------------|----------------|
| Desarrollo local | omitir o `true` | `true` | los tres |
| Staging | `false` | omitir | `tfidf`, `llm_rag` |
| Producción CITIMED | **`false`** | omitir (servidor decide) | según política; anonimizar PHI antes (S10) |

Para checklist completo de despliegue, ver [`DEPLOY.md`](DEPLOY.md).
