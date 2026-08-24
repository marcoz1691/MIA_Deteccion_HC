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

## Desarrollo vs producción

| | Desarrollo | Producción |
|---|---|---|
| Procesos | 2: `uvicorn` (8000) + `vite` (5173) | 1 URL pública (nginx o FastAPI sirviendo el build) |
| Indicador «Backend listo» | Visible (solo en `npm run dev`) | **Oculto** — el usuario no debe ver infraestructura |
| `/health` | Lo consulta el frontend para habilitar el botón | Lo usa el balanceador/K8s, no la UI |
| API | Proxy de Vite → `127.0.0.1:8000` | Mismo origen (`/generar`) o `VITE_API_URL` en el build |
| Mock LLM | Checkbox en «Opciones de análisis» | **Oculto** — servidor fija `MOCK_LLM=false` |
| Modelo LLM | Mock por defecto | Real (Ollama/OpenAI) vía env del servidor |

Checklist completo: [`api/DEPLOY.md`](../api/DEPLOY.md).

### Despliegue recomendado (mismo dominio)

1. **Build del frontend** (desde `frontend/`):

   ```powershell
   npm run build
   ```

   Genera `frontend/dist/` (HTML/JS/CSS estáticos).

2. **Reverse proxy** (nginx, Caddy, Traefik…) sirve todo bajo un solo host:

   - `/`, `/assets/*` → archivos estáticos de `frontend/dist`
   - `/generar`, `/health`, `/docs` → upstream `uvicorn` en el puerto interno 8000

   Ejemplo nginx:

   ```nginx
   server {
     listen 443 ssl;
     server_name app.ejemplo.local;

     root /var/www/mia/frontend/dist;
     index index.html;

     location /generar { proxy_pass http://127.0.0.1:8000; }
     location /health   { proxy_pass http://127.0.0.1:8000; }  # solo red interna / LB
     location /docs     { proxy_pass http://127.0.0.1:8000; }  # opcional, restringir en prod

     location / {
       try_files $uri $uri/ /index.html;
     }
   }
   ```

3. **Backend** (sin `--reload`), con variables de prod:

   ```powershell
   $env:MOCK_LLM="false"
   $env:OPENAI_API_KEY="ollama"
   $env:OPENAI_BASE_URL="http://localhost:11434/v1"
   uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
   ```

4. **Build sin URL externa**: no definas `VITE_API_URL`; las peticiones van a `/generar` en el mismo dominio que la UI.

### API en otro subdominio (opcional)

Si la API vive en `https://api.ejemplo.local`:

```powershell
$env:VITE_API_URL="https://api.ejemplo.local"
npm run build
```

Ajusta CORS en `api/main.py` (`allow_origins`) a los dominios permitidos, no `*`.
