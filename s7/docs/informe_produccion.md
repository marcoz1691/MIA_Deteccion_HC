# Informe de riesgos de producción — S7

Detección de inconsistencias en historias clínicas (CITIMED).
Fecha: 2026-07-23 · Grupo: Patricio Bayas · José Puebla · Marco Zurita Rojas

---

## 1. Resumen ejecutivo

Este documento identifica riesgos operativos al desplegar el sistema en un entorno clínico real (CITIMED Odontología), con estimaciones basadas en la arquitectura híbrida acordada: **TF-IDF local + LLM vía API (MEDEC) / Ollama local (CITIMED)**.

---

## 2. Matriz de riesgos por brazo

| Dimensión | TF-IDF ajustado | LLM zero-shot (API) | LLM + RAG |
|---|---|---|---|
| **Latencia/oración** | ~1–5 ms (CPU, batch) | ~200–800 ms | ~500–1500 ms |
| **Latencia/nota (10 orac.)** | ~10–50 ms | ~2–8 s | ~5–15 s |
| **Costo / 1000 notas** | $0 | ~$0.50–2.00 | ~$1.00–3.00 |
| **Costo / 1000 oraciones** | $0 | ~$0.05–0.20 | ~$0.10–0.30 |
| **Privacidad PHI** | On-premise, sin egress | Datos salen del hospital | Igual + chunks clínicos en prompt |
| **Escalabilidad** | CPU horizontal | Rate limits API | FAISS + API |
| **Reproducibilidad** | Alta (SEED=42) | Media (modelos cambian) | Media-baja |
| **Mantenimiento** | Bajo | Medio (prompts, API) | Alto (índice + prompts) |

*Latencias LLM medidas en modo mock/heurístico durante desarrollo; con API real se registran en `salidas_s7/metricas_tripartita.json` → `llm_stats`.*

---

## 3. Privacidad de datos clínicos

### Riesgos
- **MEDEC (público):** apto para API cloud con cache local de respuestas.
- **CITIMED Odontología (PHI):** enviar notas a API externa viola confidencialidad clínica sin acuerdo de tratamiento (DPA) y desidentificación previa.

### Mitigaciones
1. **Desidentificación local** antes de cualquier llamada externa (nombres, RUT, fechas exactas).
2. **CITIMED → solo Ollama/Mistral-7B on-premise**; misma interfaz `LLMClient` con `OPENAI_BASE_URL=http://localhost:11434/v1`.
3. **Cache en disco** (`salidas_s7/cache/`) excluido de git; cifrar en producción.
4. **Acuerdo de tratamiento de datos** con proveedor API si se usa cloud en fase piloto anonimizada.
5. **Auditoría:** registrar qué oraciones se envían, cuándo y con qué hash (sin texto plano en logs).

---

## 4. Latencia

### Arquitectura recomendada: cascada (pre-screening)

```
Nota clínica → segmentar oraciones → TF-IDF (rápido)
                                      ↓ score > τ (ej. 0.3)
                              LLM + RAG (solo candidatas)
                                      ↓
                              Localización top-1 al médico
```

**Beneficio estimado:** si TF-IDF filtra el 80 % de oraciones como baja prioridad, la latencia por nota cae de ~8 s a ~2 s (LLM solo en ~2 oraciones).

### Benchmark de referencia (objetivo producción)

| Escenario | P50 | P95 |
|---|---|---|
| TF-IDF solo | 3 ms/oración | 8 ms |
| LLM API | 400 ms | 1200 ms |
| Cascada TF-IDF→LLM | 500 ms/nota | 2000 ms |

Medir en piloto con 100 notas reales de odontología antes de go-live.

---

## 5. Costos

### Estimación API (gpt-4o-mini, ~150 tokens/oración)

| Volumen | Zero-shot | + RAG (+100 tokens ctx) |
|---|---|---|
| 1.000 oraciones | ~$0.08 | ~$0.15 |
| 10.000 oraciones/mes | ~$0.80 | ~$1.50 |
| 100.000 oraciones/mes | ~$8.00 | ~$15.00 |

*Basado en tarifas config: $0.15/1M input, $0.60/1M output ([`s7/config.yaml`](../config.yaml)).*

### Mitigaciones de costo
- **Cache agresivo** por hash de prompt (implementado en `llm_client.py`).
- **Batch API** cuando el proveedor lo soporte.
- **Modelo pequeño** para clasificación binaria (YES/NO, max_tokens=10).
- **Cascada TF-IDF** reduce llamadas LLM en ~70–90 %.

---

## 6. Disponibilidad y escalabilidad

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Caída API LLM | Sin detección semántica | **Implementado:** fallback a TF-IDF solo + alerta (`LLMUnavailableError` → `ResultadoNota.modo_degradado` en `inferencia.py` / demo) |
| Rate limiting | Cola de revisión retrasada | **Implementado:** retry exponencial en `llm_client.py` (`max_retries`, `retry_base_delay_s`) |
| Drift del modelo API | Métricas degradan | Monitor AUPRC semanal; versionar prompts |
| Índice FAISS desactualizado | RAG obsoleto | Re-indexar guías trimestralmente |

Comportamiento del fallback:

1. Llamada API real falla → reintentos con backoff.
2. Si persiste el fallo → no se usa mock silencioso; se lanza `LLMUnavailableError`.
3. `analizar_nota(..., fallback_tfidf=True)` limpia scores LLM, asegura TF-IDF y marca `modo_degradado=True` con mensaje para el revisor.
4. La demo Streamlit muestra banner de alerta y métrica «Modo: Degradado (TF-IDF)».

---

## 7. Observabilidad (MLflow)

Registrar por experimento:
- ROC-AUC, **AUPRC**, localización top-1
- Latencia P50/P95 por brazo
- Tokens consumidos y costo USD
- Versión de prompt, modelo y commit git

Comando sugerido (requiere entorno separado; ver `requirements-optional.txt`):

```bash
# MLflow no está en requirements.txt principal (conflicto numpy<2 vs numpy 2.4.4)
pip install -r requirements-optional.txt  # solo en venv dedicado
mlflow run s7/ -P brazos=tfidf,llm_zero,llm_rag
```

Alternativa sin MLflow: métricas y latencia ya se registran en `salidas_s7/metricas_tripartita.json`.

---

## 8. Recomendación de despliegue por fase

| Fase | Entorno | Brazo activo | Datos |
|---|---|---|---|
| **Piloto S7** | Dev | TF-IDF + LLM mock/API | MEDEC |
| **Piloto CITIMED** | On-premise | TF-IDF + Ollama local | Odontología anonimizada |
| **Producción v1** | Hospital | Cascada TF-IDF → LLM local | PHI desidentificado |
| **Producción v2** | Hospital + RAG | Cascada + FAISS guías CITIMED | Índice interno |

---

## 9. Checklist pre-producción

- [ ] Corpus CITIMED anonimizado y aprobado por comité ético
- [ ] Ollama/Mistral-7B desplegado en servidor hospitalario
- [ ] Benchmark latencia en 100 notas odontológicas reales
- [ ] AUPRC ≥ referencia S7 (0.42) en test MEDEC
- [ ] Recall Medication/Diagnosis no degradado vs S7
- [ ] Política de retención de cache y logs definida
- [ ] Plan de respuesta ante falso negativo crítico documentado
