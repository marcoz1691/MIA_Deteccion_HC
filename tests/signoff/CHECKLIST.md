# Fase 6 — Sign-off producción (alineado con s7/docs/informe_produccion.md §9)

Checklist para go-live en entorno clínico (CITIMED Odontología).

## Pre-requisitos de entorno

- [ ] Corpus CITIMED anonimizado y aprobado por comité ético
- [ ] Ollama/Mistral-7B desplegado en servidor hospitalario (si LLM on-premise)
- [ ] `MOCK_LLM=false` en producción
- [ ] Política de retención de cache y logs definida
- [ ] Plan de respuesta ante falso negativo crítico documentado

## Fase 0 — Smoke (cada deploy)

```powershell
python tests/smoke/smoke.py --api http://127.0.0.1:8000 --frontend http://127.0.0.1:5173
```

- [ ] SMOKE-01 GET /health → 200
- [ ] SMOKE-02 POST medicación → alerta=true
- [ ] SMOKE-03 POST limpia → alerta=false
- [ ] SMOKE-04 Frontend carga → 200

## Fase 1 — Regresión funcional

```powershell
.\tests\run_phase1.ps1
```

- [ ] pytest api/s7/s10 — 100% PASS
- [ ] TC-API-04/05 detección medicación y plan
- [ ] TC-API-22 modo degradado TF-IDF

## Fase 2 — Integración full-stack

- [ ] TC-API-19..25 gaps API
- [ ] TC-UI-R01..08 React (Playwright)
- [ ] TC-UI-S01..08 Streamlit (manual o script)
- [ ] TC-S10-05..07 pipeline CITIMED

## Fase 3 — Evaluación ML

```powershell
python tests/eval/run_eval_suite.py --run-scripts
```

- [ ] TC-EVAL-01 ROC-AUC ≥ 0.85
- [ ] TC-EVAL-02 AUPRC ≥ 0.42
- [ ] TC-EVAL-03 localización top-1 ≥ baseline S7
- [ ] TC-EVAL-04/05 Recall Medication/Diagnosis no degradado
- [ ] TC-EVAL-06 Δ AUPRC ES/EN < 0.05
- [ ] TC-EVAL-10 golden set estable

## Fase 4 — Rendimiento

```powershell
pytest tests/perf/benchmark_tfidf.py -m perf -q
```

- [ ] TC-PERF-04 latencia piloto 100 notas reales (Ollama/API)
- [ ] TC-PERF-01..03 P95 dentro de objetivo
- [ ] TC-PERF-07 /health P95 < 10 ms

## Fase 5 — Estrés y resiliencia

```powershell
locust -f tests/perf/locustfile.py --host=http://127.0.0.1:8000 --headless -u 50 -r 10 -t 5m
pytest tests/perf/test_stress.py -m stress -q
```

- [ ] TC-STR-01 ramp-up 0% errores 5xx
- [ ] TC-STR-06 modo degradado bajo fallo LLM
- [ ] Break point documentado (P95 > 10s o error rate > 5%)

## Seguridad (TC-SEC)

```powershell
pytest tests/security/test_compliance.py -m security -q
```

- [ ] TC-SEC-01..03 PHI protegido
- [ ] TC-SEC-04 secrets fuera del repo
- [ ] TC-SEC-06 inyección prompt mitigada

## Sign-off final

| Campo | Valor |
|-------|-------|
| Build/Commit | |
| Entorno | STAGING / PROD |
| Fecha | |
| Responsable QA | |
| Blockers P0 | Ninguno / listar |
| Aprobación clínica | |

**Criterio GO:** Todas las fases 0–5 PASS + checklist §9 completo + 0 blockers P0.
