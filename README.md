# MIA_Deteccion_HC

Detección de inconsistencias en historias clínicas (proyecto CITIMED).

**Grupo:** Patricio Bayas Meza · José Puebla Paladines · Marco Zurita Rojas

## Resultado principal (S7)

Reformular la tarea de **nivel nota** a **nivel oración** sobre MEDEC eleva el ROC-AUC de **0.504 → 0.949** y localiza la oración errónea en **84.6 %** de las notas con error (263/311). AUPRC test = **0.419** (prevalencia 4.5 %).

---

## Entrega S11

Borrador avanzado del documento final: cierra las tres deudas de la retroalimentación S10 (pytest declarado, LLM real, corpus CITIMED).

| Recurso | Descripción |
|---------|-------------|
| [`s11/docs/S11_Borrador_Avanzado.pdf`](s11/docs/S11_Borrador_Avanzado.pdf) | PDF para Moodle y Teams |
| [`s11/README.md`](s11/README.md) | Índice, evidencias y comandos |
| [`s11/docs/anexo_etico.md`](s11/docs/anexo_etico.md) | Protocolo de de-identificación |
| [`requirements-dev.txt`](requirements-dev.txt) | pytest y herramientas de prueba |

```bash
pip install -r requirements-dev.txt
python -m pytest
python s11/generate_informe.py
```

---

## Entrega S10

Informe consolidado y evidencias cuantitativas alineadas con el repositorio (no el borrador S8).

| Recurso | Descripción |
|---------|-------------|
| [`s10/docs/S10_Avance_Consolidado.pdf`](s10/docs/S10_Avance_Consolidado.pdf) | PDF para Moodle (plazo 23-ago-2026) |
| [`s10/docs/S10_Avance_Consolidado.docx`](s10/docs/S10_Avance_Consolidado.docx) | Fuente editable |
| [`s10/evidencias/`](s10/evidencias/) | JSON, CSV y figuras desde `salidas_s7/` y `s6/` |
| [`s10/README.md`](s10/README.md) | Índice y comandos de regeneración |

Regenerar informe y evidencias:

```bash
python s10/organize_evidencias.py   # copia JSON/figuras a s10/evidencias/
python s11/capture_prototipo.py     # capturas del frontend React (API + Vite en marcha)
python s10/generate_informe.py      # Word S8 corregido + PDF (requiere MS Word en Windows)
python s10/run_verificacion.py      # batería completa (opcional, ~10 min)
```

---

## Inicio rápido (clonar y tener todo corriendo)

Sigue estos pasos **desde la raíz del repositorio** (`MIA_Deteccion_HC/`). Todos los comandos asumen que ya estás en esa carpeta.

### Requisitos previos

| Requisito | Versión mínima | Notas |
|-----------|----------------|-------|
| **Python** | 3.12 | Comprobar con `python --version` |
| **Node.js** | 18+ | Solo para el frontend React (`frontend/`) |
| **Git** | cualquiera reciente | Para clonar este repo y el dataset MEDEC |
| **Conexión a internet** | — | Solo la primera vez (pip, MEDEC, embeddings RAG) |

> **Windows:** si `python` no funciona, prueba `py -3.12`. Para activar el entorno virtual puede hacer falta `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` en PowerShell.

### 1. Clonar el repositorio

```bash
git clone https://github.com/marcoz1691/MIA_Deteccion_HC.git
cd MIA_Deteccion_HC
```

### 2. Crear entorno virtual e instalar dependencias

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

La instalación puede tardar varios minutos la primera vez (PyTorch, sentence-transformers, etc.).

### 3. Descargar el dataset MEDEC

MEDEC es un dataset **público** externo; no viene incluido en este repo.

```bash
git clone --depth 1 https://github.com/abachaa/MEDEC.git medec_try
```

Debe quedar la ruta `medec_try/MEDEC-MS/` con los CSV de entrenamiento, validación y prueba.

### 4. Entrenar el modelo TF-IDF (obligatorio para la demo)

```bash
python s6/modelo_ajustado.py
```

Genera `salidas_ajuste/modelo_ajustado.joblib` (~1 min en CPU). Obligatorio para TF-IDF en la demo y la API.

### 5. Lanzar el prototipo (elige una interfaz)

#### Opción A — API FastAPI + frontend React (recomendado para integración)

**Terminal 1 — backend:**

```powershell
uvicorn api.main:app --reload --port 8000
```

Documentación OpenAPI: **http://localhost:8000/docs**

**Terminal 2 — frontend:**

```powershell
cd frontend
npm install
npm run dev
```

Abre **http://localhost:5173**. Vite hace proxy de `/generar` y `/health` hacia el puerto 8000.

- **Mock LLM activo por defecto** — no requiere API key.
- Carga el ejemplo de medicación o pega una nota y pulsa **Analizar**.
- La respuesta JSON incluye `top1` (oración sospechosa) y scores por brazo.

Ver [`api/README.md`](api/README.md) y [`frontend/README.md`](frontend/README.md).

#### Opción B — Demo Streamlit (presentación en clase)

```bash
streamlit run demo/app.py
```

Abre **http://localhost:8501**. Incluye páginas de Métricas, Configuración y consentimiento PHI.

Ver [`demo/README.md`](demo/README.md) para un guion de 2 minutos.

### Checklist de verificación

| Paso | Comando / archivo esperado |
|------|----------------------------|
| Entorno activo | El prompt muestra `(.venv)` |
| Dependencias OK | `python -c "import fastapi, uvicorn, sklearn, faiss"` sin error |
| MEDEC presente | Existe `medec_try/MEDEC-MS/` |
| Modelo entrenado | Existe `salidas_ajuste/modelo_ajustado.joblib` |
| API en marcha | `GET http://localhost:8000/health` → `modelo_tfidf_disponible: true` |
| Frontend (opción A) | `npm run dev` en `frontend/` → http://localhost:5173 |
| Streamlit (opción B) | `streamlit run demo/app.py` → http://localhost:8501 |

---

## Configuración opcional

### API real (OpenAI, Mistral, Ollama)

Por defecto la API y la demo usan **mock LLM** (respuestas simuladas, todo local). Para usar un LLM real:

1. Copia la plantilla de secrets:

   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # Linux/macOS
   copy .streamlit\secrets.toml.example .streamlit\secrets.toml   # Windows
   ```

2. Edita `.streamlit/secrets.toml`:

   ```toml
   OPENAI_API_KEY = "sk-..."
   # OPENAI_BASE_URL = "http://localhost:11434/v1"  # Ollama on-premise
   ```

   También puedes usar un archivo `.env` en la raíz (copia `.env.example`).

3. En la demo Streamlit → **Configuración** → desmarca **Mock LLM** y acepta el consentimiento PHI.

   En la API FastAPI, envía `"mock_llm": false` en el body de `POST /generar` (requiere key configurada).

### Autenticación (piloto)

En `.streamlit/secrets.toml`:

```toml
ENABLE_AUTH = true
AUTH_USERS = { medico = "tu_contraseña" }
```

### Dependencias opcionales

`requirements-optional.txt` incluye MLflow y herramientas de interpretabilidad (SHAP, LIME). **No instalar junto con `requirements.txt`** — MLflow exige `numpy<2`, incompatible con el stack S7. Usa un entorno virtual separado si lo necesitas.

---

## Solución de problemas

| Problema | Causa probable | Solución |
|----------|----------------|----------|
| `Modelo TF-IDF no encontrado` | No se entrenó el modelo | Ejecuta `python s6/modelo_ajustado.py` |
| `FileNotFoundError` al entrenar | MEDEC no clonado | `git clone --depth 1 https://github.com/abachaa/MEDEC.git medec_try` |
| `ModuleNotFoundError: streamlit` | Entorno virtual no activado o pip incompleto | Activa `.venv` y `pip install -r requirements.txt` |
| `503` en POST /generar | Modelo TF-IDF no entrenado | `python s6/modelo_ajustado.py` |
| Frontend no conecta a la API | Backend apagado o puerto distinto | Arranca `uvicorn api.main:app --port 8000` |
| Demo lenta la primera vez | Descarga de embeddings RAG | Normal; las siguientes cargas usan caché en `salidas_s7/` |
| Error de permisos en PowerShell | Política de ejecución | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Puerto 8501 ocupado | Otra instancia de Streamlit | `streamlit run demo/app.py --server.port 8502` |
| Puerto 8000 ocupado | Otra instancia de uvicorn | `uvicorn api.main:app --port 8001` |

---

## Estructura del proyecto

```
MIA_Deteccion_HC/
├── requirements.txt             # Dependencias principales (Python 3.12+)
├── requirements-optional.txt    # MLflow, SHAP, LIME (entorno separado)
├── .env.example                 # Plantilla API keys
├── .streamlit/
│   ├── config.toml              # Tema y opciones Streamlit
│   └── secrets.toml.example     # Plantilla secrets (copiar → secrets.toml)
├── s6/                          # Entrega S6 — ajuste TF-IDF (base de S7)
│   ├── modelo_ajustado.py       # Entrena y guarda el modelo
│   ├── metricas_ajuste.json
│   └── BITACORA.md
├── s7/                          # Entrega S7 — comparación tripartita + AUPRC
│   ├── eval_tripartita.py       # TF-IDF vs LLM zero-shot vs LLM+RAG
│   ├── analisis_por_tipo.py     # Recall por ErrorType
│   ├── eval_idioma.py           # Sesgo EN vs ES (LLM)
│   ├── inferencia.py            # Inferencia reutilizable (API + demo + scripts)
│   ├── config.yaml
│   └── docs/informe_produccion.md
├── api/                         # API REST FastAPI
│   ├── main.py                  # GET /health, POST /generar
│   ├── service.py               # InferenceService → analizar_nota()
│   └── schemas.py               # Pydantic request/response
├── frontend/                    # Cliente React + Vite
│   ├── src/App.jsx
│   └── vite.config.js           # Proxy → localhost:8000
├── demo/                        # Demo Streamlit (alternativa)
│   ├── app.py                   # Página principal — Análisis
│   ├── pages/                   # Métricas, Acerca, Configuración
│   ├── components/              # UI, auth, paneles
│   └── README.md                # Guion de presentación (2 min)
├── s8/                          # Entrega S8 — informes históricos
│   ├── docs/                    # Word borrador S8 (.docx)
│   └── README.md
├── s10/                         # Entrega S10 — informe consolidado + evidencias
│   ├── docs/                    # S10_Avance_Consolidado.pdf / .docx
│   ├── evidencias/              # JSON, CSV, figuras (committeable)
│   └── README.md
├── s11/                         # Entrega S11 — borrador avanzado
│   ├── docs/                    # PDF, anexo ético, guía de anotación
│   ├── evidencias/              # LLM real, agregados OCR, capturas
│   ├── anonimizador_ocr/        # OCR + tachado en píxel (sin PHI)
│   └── README.md
├── tests/                       # Suite SDET (funcional, perf, eval, E2E)
│   ├── README.md
│   ├── smoke/smoke.py           # Fase 0
│   ├── api/ s7/ s10/ perf/ eval/ security/ e2e/
│   └── signoff/CHECKLIST.md
├── pytest.ini
├── requirements-dev.txt         # pytest, httpx, locust, playwright
├── .github/workflows/tests.yml  # CI regresión + smoke
└── data/
    └── citimed_odontologia.example.csv
```

**Carpetas generadas localmente (no están en git):**

- `medec_try/` — dataset MEDEC clonado
- `salidas_ajuste/` — modelo TF-IDF entrenado
- `salidas_s7/` — caché LLM, índice FAISS, audit.log

---

## Scripts de experimentos (S7)

Con el entorno activo y MEDEC clonado:

```bash
# Comparación tripartita (mock LLM, sin API key)
python s7/eval_tripartita.py --mock-llm --max-oraciones 500

# Análisis por tipo de error
python s7/analisis_por_tipo.py

# Con API real (opcional)
# cp .env.example .env   → editar OPENAI_API_KEY
python s7/eval_tripartita.py --max-oraciones 200
```

Orden recomendado y más scripts en [`s7/README.md`](s7/README.md).

---

## Interfaces del prototipo

| Interfaz | Puerto | Uso |
|----------|--------|-----|
| **FastAPI + React** | 8000 + 5173 | Integración HTTP, OpenAPI `/docs`, UI moderna |
| **Streamlit** | 8501 | Demo en clase, métricas embebidas, consentimiento PHI |

**Modo por defecto:** mock LLM local, sin API key.

Ver [`api/README.md`](api/README.md), [`frontend/README.md`](frontend/README.md) y [`demo/README.md`](demo/README.md).

---

## Pruebas (suite SDET)

Suite de pruebas full-stack: funcional, ML/evaluación, rendimiento, estrés, seguridad PHI y E2E UI (~95 casos).

| Recurso | Descripción |
|---------|-------------|
| [`tests/README.md`](tests/README.md) | Guía completa: fases, comandos, marcadores pytest |
| [`tests/signoff/CHECKLIST.md`](tests/signoff/CHECKLIST.md) | Checklist sign-off producción (Fase 6) |
| [`.github/workflows/tests.yml`](.github/workflows/tests.yml) | CI: regresión + smoke en cada PR |

### Instalación

```powershell
pip install -r requirements-dev.txt
```

### Comandos rápidos

```powershell
# Fase 0 — Smoke post-deploy (requiere uvicorn en :8000)
python tests/smoke/smoke.py

# Fase 1 — Regresión funcional (pytest + qa_e2e si API activa)
.\tests\run_phase1.ps1

# Regresión solo pytest (sin servidor)
pytest -m regression -q

# Fase 3 — Evaluación ML (golden set + umbrales ROC-AUC/AUPRC)
python tests/eval/run_eval_suite.py

# Fase 4 — Rendimiento
pytest tests/perf/benchmark_tfidf.py -m perf -q

# Fase 5 — Estrés (Locust, servidor activo)
locust -f tests/perf/locustfile.py --host=http://127.0.0.1:8000 --headless -u 20 -r 5 -t 2m
```

### Cobertura por capa

| Capa | Casos | Ubicación |
|------|-------|-----------|
| API REST (`/health`, `/generar`) | TC-API-01..25 | `tests/api/` |
| Pipeline ML (s7) | TC-ML-01..09 | `tests/s7/` |
| Anonimización CITIMED (s10) | TC-S10-01..07 | `tests/s10/` |
| Evaluación ML | TC-EVAL-01..10 | `tests/eval/` |
| Rendimiento / estrés | TC-PERF, TC-STR | `tests/perf/` |
| Seguridad PHI | TC-SEC-01..07 | `tests/security/` |
| UI React / Streamlit | TC-UI-R/S | `tests/e2e/` |

Los 18 casos E2E originales de [`api/qa_e2e_manual.py`](api/qa_e2e_manual.py) están formalizados en pytest (`tests/api/`). El modelo TF-IDF en tests usa un **fake model** en memoria, por lo que la regresión no depende de `salidas_ajuste/modelo_ajustado.joblib`.

---

Ver [`s6/BITACORA.md`](s6/BITACORA.md) para el historial completo, [`s7/docs/informe_produccion.md`](s7/docs/informe_produccion.md) para riesgos de producción, [`s8/README.md`](s8/README.md) para el borrador histórico S8 y [`s10/README.md`](s10/README.md) para la entrega consolidada S10.
