# Suite SDET — MIA Detección HC

Plan de pruebas full-stack para detección de inconsistencias clínicas: API FastAPI, pipeline s7, UI React/Streamlit, anonimizador S10, evaluación ML, rendimiento y estrés.

**~95 casos de prueba** organizados en 8 categorías y 7 fases de ejecución.

---

## Instalación

```powershell
pip install -r requirements-dev.txt
```

Opcional (Fase 2 — UI React):

```powershell
cd frontend
npm install
cd ../tests/e2e/playwright
npx playwright install
```

---

## Fases de ejecución

| Fase | Cuándo | Comando | Duración |
|------|--------|---------|----------|
| **0 Smoke** | Cada deploy | `python tests/smoke/smoke.py` | ~5 min |
| **1 Regresión** | Cada PR merge | `.\tests\run_phase1.ps1` | ~30 min |
| **2 Full-stack** | Pre-release | `pytest tests/ -m integration` + Playwright | ~2 h |
| **3 Eval ML** | Semanal / pre-release | `python tests/eval/run_eval_suite.py --run-scripts` | 4–8 h |
| **4 Rendimiento** | Pre-release | `pytest tests/perf/benchmark_tfidf.py -m perf` | ~2 h |
| **5 Estrés** | Pre-go-live | `locust -f tests/perf/locustfile.py --host=...` | ~4 h |
| **6 Sign-off** | Go-live clínico | [signoff/CHECKLIST.md](signoff/CHECKLIST.md) | — |

### Fase 0 — Smoke

Verifica que el sistema responde tras un deploy:

1. `GET /health` → 200  
2. `POST /generar` nota medicación → alerta  
3. `POST /generar` nota limpia → sin alerta  
4. Frontend React carga (opcional)

```powershell
# API en :8000, frontend en :5173
python tests/smoke/smoke.py

# Solo API
python tests/smoke/smoke.py --skip-frontend
```

### Fase 1 — Regresión

```powershell
.\tests\run_phase1.ps1        # Windows
./tests/run_phase1.sh         # Linux/macOS
pytest -m regression -q       # Solo pytest, sin qa_e2e manual
```

Incluye: `tests/api/`, `tests/s7/`, `tests/s10/`, `tests/security/`, tests legacy en `api/test_settings.py`, `s7/test_fallback.py`, `s10/test_citimed_pipeline.py`.

Si uvicorn está activo en `:8000`, también ejecuta [`api/qa_e2e_manual.py`](../api/qa_e2e_manual.py) (TC-01..18).

### Fase 3 — Evaluación ML

```powershell
python tests/eval/run_eval_suite.py              # Golden set + umbrales (rápido)
python tests/eval/run_eval_suite.py --run-scripts  # + eval_tripartita, analisis_por_tipo, eval_idioma
```

**Umbrales de aceptación (referencia S7):**

| Métrica | Umbral mínimo |
|---------|---------------|
| ROC-AUC | ≥ 0.85 |
| AUPRC | ≥ 0.42 |
| Localización top-1 | > 0 (baseline S7) |

Requiere MEDEC + modelo entrenado para `--run-scripts`. Sin ellos, el golden set (TC-EVAL-10) y métricas en `s10/evidencias/metricas_tripartita.json` siguen ejecutándose.

### Fase 4 — Rendimiento

Objetivos SLA (desde `s7/docs/informe_produccion.md`):

| Escenario | P50 | P95 |
|-----------|-----|-----|
| TF-IDF solo | 3 ms/oración | 8 ms |
| LLM mock, 10 orac. | — | < 3 s |
| Tripartita mock | — | < 5 s |

```powershell
pytest tests/perf/benchmark_tfidf.py -m perf -v
```

TC-PERF-04 (Ollama real) se ejecuta manualmente con `MOCK_LLM=false` y Ollama en `:11434`.

### Fase 5 — Estrés (Locust)

```powershell
# Ramp-up gradual (TC-STR-01)
locust -f tests/perf/locustfile.py --host=http://127.0.0.1:8000 --headless -u 50 -r 10 -t 5m

# Payload grande (TC-STR-04) — usar clase NotaLargaUser en locustfile
locust -f tests/perf/locustfile.py --host=http://127.0.0.1:8000 NotaLargaUser

# Fault injection (TC-STR-06..09)
pytest tests/perf/test_stress.py -m stress -q
```

---

## Catálogo de casos de prueba

### API REST — `tests/api/`

| ID | Descripción |
|----|-------------|
| TC-API-01..02 | Health, OpenAPI docs |
| TC-API-03..08 | Happy path: limpia, medicación, plan, brazos, umbral |
| TC-API-09..14 | Validaciones 422 |
| TC-API-15..18 | 404, CORS, contrato JSON |
| TC-API-19..25 | MOCK_LLM override, 503, degradado, idioma, Content-Type |

### Pipeline ML — `tests/s7/test_inferencia.py`

| ID | Descripción |
|----|-------------|
| TC-ML-01..09 | Segmentación, fórmula combinada, RAG, cache, fallback |

### S10 PHI — `tests/s10/test_citimed.py`

| ID | Descripción |
|----|-------------|
| TC-S10-01..07 | Anonimización, detección PHI, CSV eval, pipeline TXT |

### Seguridad — `tests/security/`

| ID | Descripción |
|----|-------------|
| TC-SEC-01..07 | PHI en logs, gate S10, secrets, prompt injection |

### UI — `tests/e2e/`

| ID | Descripción |
|----|-------------|
| TC-UI-R01..08 | React (Playwright) |
| TC-UI-S01..08 | Streamlit (componentes) |

---

## Estructura de archivos

```
tests/
├── conftest.py              # TestClient + FakeModelo TF-IDF
├── fixtures/notas.py        # Notas clínicas de referencia
├── smoke/smoke.py           # Fase 0
├── api/                     # TC-API
├── s7/                      # TC-ML
├── s10/                     # TC-S10
├── perf/                    # TC-PERF, TC-STR, locustfile.py
├── eval/run_eval_suite.py   # TC-EVAL
├── security/                # TC-SEC
├── e2e/playwright/          # TC-UI-R
├── e2e/streamlit/           # TC-UI-S
├── signoff/CHECKLIST.md     # Fase 6
├── run_phase1.ps1
└── run_phase1.sh
```

---

## Marcadores pytest

```powershell
pytest -m smoke -q
pytest -m regression -q
pytest -m integration -q
pytest -m perf -q
pytest -m stress -q
pytest -m security -q
pytest -m e2e -q
pytest -m "not perf and not stress" -q   # CI rápido
```

Definidos en [`pytest.ini`](../pytest.ini).

---

## CI (GitHub Actions)

Workflow [`.github/workflows/tests.yml`](../.github/workflows/tests.yml):

1. **phase1-regression** — pytest `-m regression` + eval golden set  
2. **smoke** — levanta uvicorn y ejecuta `tests/smoke/smoke.py`

---

## Notas técnicas

- **Modelo TF-IDF en tests:** `tests/conftest.py` inyecta `FakeModeloTfidf`; no requiere entrenar `s6/modelo_ajustado.py` para regresión.
- **LLM en tests:** `MOCK_LLM=true` por defecto en fixtures; heurísticas deterministas en `s7/llm_client.py`.
- **Reportes locales:** `tests/eval/last_eval_report.json` y `tests/perf/last_benchmark.json` se generan al ejecutar suites y están en `.gitignore`.
- **Compatibilidad:** los tests legacy en `api/`, `s7/`, `s10/` siguen ejecutándose vía `pytest.ini`.

---

## Sign-off producción

Antes de go-live clínico (CITIMED), completar [signoff/CHECKLIST.md](signoff/CHECKLIST.md) alineado con `s7/docs/informe_produccion.md` §9.
