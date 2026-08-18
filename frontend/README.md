# Frontend React — MIA Detección HC

Cliente mínimo (`NotaInput` + `ResultadosPanel`) que llama a FastAPI `POST /generar`.

## Arranque

Necesitas **dos terminales** desde la raíz del repositorio.

**1. Backend**

```powershell
.venv\Scripts\Activate.ps1
uvicorn api.main:app --reload --port 8000
```

**2. Frontend**

```powershell
cd frontend
npm install
npm run dev
```

Abre [http://localhost:5173](http://localhost:5173). Vite hace proxy de `/generar` y `/health` hacia `http://127.0.0.1:8000`.

## Qué hace

1. Carga un ejemplo de nota (o texto propio).
2. Envía `{ nota_clinica, mock_llm, idioma }` a `POST /generar`.
3. Muestra `top1` (oración sospechosa) y la tabla de scores.

Por defecto usa **mock LLM** (sin API key), igual que la demo Streamlit.
