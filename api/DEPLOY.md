# Producción — checklist de despliegue

Guía para desplegar la API FastAPI + frontend React en CITIMED (on-premise).

## Checklist previo al go-live

| # | Artefacto / config | Comando o ruta | Obligatorio |
|---|-------------------|----------------|-------------|
| 1 | Modelo TF-IDF | `python s6/modelo_ajustado.py` → `salidas_ajuste/modelo_ajustado.joblib` | Sí (brazo `tfidf`) |
| 2 | Índice RAG (FAISS) | Primera petición con `llm_rag` o pre-calentar con curl | Si usas RAG |
| 3 | Variables LLM | `.env` o secrets del contenedor (ver abajo) | Sí en prod |
| 4 | `MOCK_LLM=false` | En el entorno del proceso uvicorn | **Sí en prod** |
| 5 | Build frontend | `cd frontend && npm run build` → `frontend/dist/` | Sí |
| 6 | nginx / reverse proxy | Sirve `dist/` + proxy `/generar` | Recomendado |
| 7 | Anonimización PHI | Servicio S10 antes de enviar notas reales | Sí (CITIMED) |

## Variables de entorno (servidor)

```env
# Producción — LLM real (Ollama on-premise, datos no salen del hospital)
MOCK_LLM=false
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1

# Alternativa cloud (solo datos anonimizados / MEDEC)
# MOCK_LLM=false
# OPENAI_API_KEY=sk-...
```

| Variable | Dev | Prod |
|----------|-----|------|
| `MOCK_LLM` | omitir o `true` | **`false`** (fuerza LLM real; ignora el cliente) |
| `OPENAI_API_KEY` | opcional | requerida si `MOCK_LLM=false` |
| `OPENAI_BASE_URL` | opcional | `http://localhost:11434/v1` para Ollama |

Si `MOCK_LLM=false` y no hay API key, `POST /generar` degrada a TF-IDF (`modo_degradado: true`) o responde 503 si tampoco hay joblib.

## Endpoints

| Método | Ruta | Uso |
|--------|------|-----|
| `GET` | `/health` | Load balancer / K8s (no exponer detalles al usuario final) |
| `POST` | `/generar` | Análisis de notas |

`GET /health` incluye:

- `modelo_tfidf_disponible`
- `mock_llm` — modo efectivo en el servidor
- `mock_llm_forzado` — `true` si `MOCK_LLM` está definido en el entorno
- `llm_api_configurada` — hay clave API en el servidor

## Arranque producción

```powershell
# Desde la raíz del repo, con .env cargado
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Sin `--reload`. El modelo TF-IDF se carga una vez al iniciar.

## Pre-calentar RAG (opcional)

La primera petición con brazo `llm_rag` puede tardar ~15 s (embeddings + FAISS):

```powershell
curl -X POST http://localhost:8000/generar `
  -H "Content-Type: application/json" `
  -d '{"nota_clinica": "Paciente con alergia a penicilina. Se indica amoxicilina.", "brazos": ["llm_rag"]}'
```

Con `MOCK_LLM=false` en prod, omitir `mock_llm` en el body (el servidor decide).

## Frontend

Ver [`frontend/README.md`](../frontend/README.md). En producción:

- No se muestra «Backend listo» ni el checkbox Mock LLM.
- El build no envía `mock_llm`; el servidor usa `MOCK_LLM` del entorno.

## Verificación post-deploy

```powershell
# Health interno (desde el servidor o red privada)
curl http://localhost:8000/health

# Esperado en prod:
# mock_llm: false, mock_llm_forzado: true, llm_api_configurada: true
# modelo_tfidf_disponible: true
```
