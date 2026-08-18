# API FastAPI — detección de inconsistencias

Backend HTTP que expone el mismo pipeline de la demo Streamlit (`s7/inferencia.analizar_nota`).

## Arranque

Desde la **raíz del repositorio**:

```bash
# Activar entorno virtual e instalar dependencias (si aún no lo hiciste)
pip install -r requirements.txt

# Servidor de desarrollo
uvicorn api.main:app --reload --port 8000
```

Documentación interactiva: [http://localhost:8000/docs](http://localhost:8000/docs)

Frontend React (opcional): [`frontend/README.md`](../frontend/README.md) — `npm run dev` en el puerto 5173, con proxy a esta API.

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servicio y disponibilidad del modelo TF-IDF |
| `POST` | `/generar` | Analiza una nota clínica y retorna scores por oración |

## Ejemplo — error de medicación (mock LLM)

```bash
curl -X POST http://localhost:8000/generar \
  -H "Content-Type: application/json" \
  -d "{\"nota_clinica\": \"Paciente refiere dolor en molar 36. Antecedentes: alergia documentada a penicilina. Se indica amoxicilina 500 mg cada 8 h.\", \"mock_llm\": true}"
```

La respuesta debe incluir `alerta: true` en la oración que menciona amoxicilina con alergia a penicilina (misma lógica mock que la demo Streamlit).

## Payload `POST /generar`

```json
{
  "nota_clinica": "Texto libre de la nota clínica.",
  "mock_llm": true,
  "idioma": "spanish",
  "brazos": ["tfidf", "llm_zero", "llm_rag"],
  "umbral": 0.5
}
```

- **nota_clinica** (obligatorio): texto de la historia clínica.
- **mock_llm** (default `true`): respuestas LLM simuladas, sin API key.
- **brazos**: `tfidf`, `llm_zero`, `llm_rag` (al menos uno).
- **umbral**: score mínimo para marcar alerta en una oración.

## Requisitos

- Modelo TF-IDF entrenado en `salidas_ajuste/modelo_ajustado.joblib` (necesario si usas brazo `tfidf`).
- Para `llm_rag`: primera petición puede tardar ~15 s mientras descarga embeddings y construye el índice FAISS.

## PowerShell (Windows)

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/generar" `
  -ContentType "application/json" `
  -Body '{"nota_clinica": "Paciente con alergia a penicilina. Se indica amoxicilina.", "mock_llm": true}'
```
