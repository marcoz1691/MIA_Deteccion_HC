# MIA_Deteccion_HC

Detección de inconsistencias en historias clínicas (proyecto CITIMED).

**Grupo:** Patricio Bayas Meza · José Puebla Paladines · Marco Zurita Rojas

## Resultado principal (S7)

Reformular la tarea de **nivel nota** a **nivel oración** sobre MEDEC eleva el ROC-AUC de **0.504 → 0.949** y localiza la oración errónea en **84.6 %** de las notas con error (263/311). AUPRC test = **0.419** (prevalencia 4.5 %).

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
python s10/generate_informe.py      # Word + PDF desde métricas del repo
python s10/run_verificacion.py      # batería completa (opcional, ~10 min)
```

---

## Inicio rápido (clonar y tener todo corriendo)

Sigue estos pasos **desde la raíz del repositorio** (`MIA_Deteccion_HC/`). Todos los comandos asumen que ya estás en esa carpeta.

### Requisitos previos

| Requisito | Versión mínima | Notas |
|-----------|----------------|-------|
| **Python** | 3.12 | Comprobar con `python --version` |
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

Genera `salidas_ajuste/modelo_ajustado.joblib` (~1 min en CPU). La demo lo necesita para el brazo TF-IDF.

### 5. Lanzar la demo interactiva

```bash
streamlit run demo/app.py
```

Abre **http://localhost:8501** en el navegador.

- **Mock LLM activo por defecto** — no requiere API key ni enviar datos a internet.
- Carga un ejemplo de odontología CITIMED o pega una nota clínica y pulsa **Analizar nota**.
- La primera vez que uses el brazo **LLM+RAG**, se descargará el modelo de embeddings (~15 s adicionales).

### Checklist de verificación

| Paso | Comando / archivo esperado |
|------|----------------------------|
| Entorno activo | El prompt muestra `(.venv)` |
| Dependencias OK | `python -c "import streamlit, sklearn, faiss"` sin error |
| MEDEC presente | Existe `medec_try/MEDEC-MS/` |
| Modelo entrenado | Existe `salidas_ajuste/modelo_ajustado.joblib` |
| Demo en marcha | `streamlit run demo/app.py` → http://localhost:8501 |

---

## Configuración opcional

### API real (OpenAI, Mistral, Ollama)

Por defecto la demo usa **mock LLM** (respuestas simuladas, todo local). Para usar un LLM real:

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

3. En la demo → **Configuración** → desmarca **Mock LLM** y acepta el consentimiento PHI.

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
| Demo lenta la primera vez | Descarga de embeddings RAG | Normal; las siguientes cargas usan caché en `salidas_s7/` |
| Error de permisos en PowerShell | Política de ejecución | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Puerto 8501 ocupado | Otra instancia de Streamlit | `streamlit run demo/app.py --server.port 8502` |

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
│   ├── inferencia.py            # Inferencia reutilizable (demo + scripts)
│   ├── config.yaml
│   └── docs/informe_produccion.md
├── demo/                        # Demo interactiva Streamlit
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

## Demo interactiva

Interfaz web para mostrar el flujo del prototipo al profesor o en clase.

**Modo por defecto:** mock LLM local, sin API key, banner verde indicando que ningún dato sale del equipo.

Ver [`demo/README.md`](demo/README.md) para un guion de presentación de 2 minutos.

Ver [`s6/BITACORA.md`](s6/BITACORA.md) para el historial completo, [`s7/docs/informe_produccion.md`](s7/docs/informe_produccion.md) para riesgos de producción, [`s8/README.md`](s8/README.md) para el borrador histórico S8 y [`s10/README.md`](s10/README.md) para la entrega consolidada S10.
