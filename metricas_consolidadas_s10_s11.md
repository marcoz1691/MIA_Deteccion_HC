# Métricas consolidadas — S10, S11 y estado actual

Inventario de todos los artefactos de métricas del repositorio, con la versión de cada cifra por etapa y cuál es la autoritativa. Sirve como fuente única para revisar el documento.

---

## Resumen: dónde hay conflicto

| Métrica | S10 | S11 | Actual | Estado |
|---|---|---|---|---|
| **AUPRC test (TF-IDF ajustado)** | 0.4186 | — | **0.3977** | ⚠️ **Conflicto — el documento usa el valor viejo** |
| Tripartita (Tabla 8) | mock, n=500 | real, n=400 | = S11 | ✅ Contraste intencional, bien documentado |
| Sesgo de idioma EN/ES | mock (AUC 0.500) | real (AUC 0.4579) | = S11 | ⚠️ Conflicto, pero **no se reporta en el documento** |
| Recall por tipo (Figura 8) | idéntico | idéntico | idéntico | ✅ |
| Cross-domain CITIMED | — | 0.7347 | idéntico | ✅ |
| Anonimización v1 (Tabla 9) | — | 127/87, recall 0.898 | idéntico | ✅ |
| Corpus piloto | — | 96+4=100, κ determinista | idéntico | ✅ |
| Pruebas y cobertura | — | 21+14, 21 % | idéntico | ✅ |

---

## 1. Tabla 6 — TF-IDF ajustado sobre MEDEC test

### Las dos versiones

| Métrica (test MEDEC) | Baseline (nota) | **JULIO** | **AGOSTO** ✓ |
|---|---|---|---|
| ROC-AUC | 0.505 | 0.949 | 0.949 |
| ROC-AUC (IC 95 %) | - | 0.940 – 0.958 | 0.940 – 0.958 |
| CV 5 fold (AUC) | - | 0.965 ± 0.007 | 0.965 ± 0.007 |
| Recall (oración) | 0.945* | 0.817 | 0.817 |
| Precisión (oración) | 0.523 | 0.357 | 0.357 |
| Localización top-1 | n/d | 0.846 (263/311) | 0.846 (263/311) |
| **AUPRC (oración)** | - | **0.419** (IC 0.392–0.446) | **0.398** (IC 0.353–0.457) |

**Solo cambia el AUPRC.** Todo lo demás coincide al cuarto decimal.

### Por qué 0.398 es el correcto — tres fuentes independientes

| Fuente | Fecha | AUPRC test |
|---|---|---|
| `salidas_s7/eval_tfidf_idioma.json` = `s10/evidencias/eval_tfidf_idioma.json` (archivos idénticos) | **2026-08-17** | **0.3977** |
| `salidas_ajuste/metricas_ajuste.json` — el que `s7/config.yaml` carga | 2026-08-23 | **0.3977** |
| Recálculo directo sobre `modelo_ajustado.joblib` (n=6789, pos=311) | hoy | **0.3977** |

El artefacto del 17-ago es decisivo: ya traía 0.3977 **seis días antes** que `salidas_ajuste/`, con la misma matriz de confusión [[6020, 458], [57, 254]] y el mismo ROC-AUC 0.9485. Descarta la hipótesis de que el modelo se reentrenó y el AUPRC bajó: **0.3977 fue siempre el valor de este modelo**.

### Dónde vive todavía el 0.419 — cuatro lugares que hay que neutralizar

| Archivo | Fecha | Valor | Nota |
|---|---|---|---|
| `s6/metricas_ajuste.json` | 2026-07-23 00:38 | 0.4186 | origen |
| `s10/evidencias/metricas_tfidf.json` | 2026-07-23 00:38 | 0.4186 | **byte a byte idéntico al anterior** |
| `s10/evidencias/resumen_metricas.json` | 2026-08-23 22:29 | 0.4186 | **vector de propagación** al documento |
| `referencia_s7` dentro de ambos `metricas_tripartita.json` | 08-17 / 08-31 | 0.42 | redondeo del valor viejo |

> El `resumen_metricas.json` de S10 se escribió a las **22:29** del 23-ago y el artefacto vigente a las **23:10** — 41 minutos después. Ese resumen es, casi con certeza, la fuente de la que se tomó la cifra para la Tabla 6.

### No reproducible por ninguna vía

| Estimador | Resultado | ¿0.4186? |
|---|---|---|
| `average_precision_score(y, score)` — el que usa `s7/metricas.py` | 0.3977 | No |
| `auc(recall, precision)` — trapecio | 0.3956 | No |
| `average_precision_score(y, pred)` — hipótesis de error | 0.2998 | No |

Además julio se desvía en direcciones opuestas según el split: **+0.021 en prueba, −0.060 en validación** (0.4512 vs 0.5110). Con ROC-AUC idéntico en ambos, no puede provenir del mismo par (y, score).

---

## 2. Tabla 8 — Comparación tripartita

| Brazo | ROC-AUC **mock** (S10, n=500) | ROC-AUC **real** (S11, n=400) | AUPRC real | Latencia ms | USD/1 000 |
|---|---|---|---|---|---|
| TF-IDF ajustado | 0.9537 → **0,954** | 0.9475 → **0,948** | 0.4055 → **0,406** | 0.381 | 0,000 |
| LLM zero-shot | 0.4979 → **0,498** | 0.5094 → **0,509** | 0.0536 → **0,054** | 587,2 | 0,0128 |
| LLM + RAG | 0.4979 → **0,498** | 0.5067 → **0,507** | 0.0534 → **0,053** | 535,4 | 0,0300 |

**Todo verificado ✓.** Fuentes: `s10/evidencias/metricas_tripartita.json` (mock) y `s11/evidencias/metricas_llm_real.json` = `salidas_s7/metricas_tripartita.json` (real).

Localización top-1: TF-IDF **0.8571** (85,7 %) · ambos LLM **0.0952** (9,5 %) ✓

Los dos `metricas_tripartita.json` difieren **por diseño** (mock n=500 vs real n=400) y el documento contrasta ambos correctamente. No es un conflicto.

### Dato no reportado que conviene añadir

`metricas_llm_real.json` incluye **prueba de McNemar** que el documento no menciona:

| Comparación | p-valor | Lectura |
|---|---|---|
| TF-IDF vs LLM zero-shot | 0.0599 | diferencia no significativa al 5 % |
| TF-IDF vs LLM + RAG | 1.0000 | sin diferencia |
| LLM zero-shot vs LLM + RAG | **0.0059** | RAG **significativamente peor** que zero-shot |

Es evidencia estadística formal que refuerza la conclusión de la cascada. Vale una frase en §7.3.3.

---

## 3. Sesgo de idioma — conflicto no reportado

| Fuente | Fecha | ROC-AUC inglés | ROC-AUC español |
|---|---|---|---|
| `s10/evidencias/eval_idioma_en_es.json` | 2026-08-17 | **0.5000** (mock degenerado) | — |
| `salidas_s7/eval_idioma_en_es.json` | 2026-08-31 | **0.4579** | — |
| `metricas_llm_real.json → sesgo_idioma_llm_real` | 2026-08-31 | **0.4579** | **0.4974** |

El de S10 es la corrida mock (AUC exactamente 0.500 con predicciones todas negativas). El vigente es con LLM real. **El documento no reporta ninguno**, así que hoy no hay contradicción impresa — pero tampoco se aprovecha la evidencia.

§6.4.3 afirma cualitativamente que el sesgo lingüístico es un riesgo. Con Δ AUC = **−0,0395** (inglés por debajo de español, n=200) tienes la medición para sostenerlo.

---

## 4. TF-IDF por idioma — activo sin documentar

`salidas_s7/eval_tfidf_idioma.json` (idéntico en S10):

| Idioma | CV AUC | Test ROC-AUC | AUPRC | Recall | Precisión |
|---|---|---|---|---|---|
| Inglés (MEDEC original) | 0.9650 | 0.9485 | 0.3977 | 0.8167 | 0.3567 |
| **Español (MEDEC traducido)** | **0.9688** | **0.9587** | **0.4323** | **0.8392** | **0.3838** |

**El modelo rinde mejor en español que en inglés en las cinco métricas.** Es un resultado directamente relevante para la limitación «MEDEC ≠ CITIMED» que el documento reconoce en §6.4.5, y no se menciona en ninguna parte.

---

## 5. Figura 8 — recall por tipo de error

`analisis_por_tipo.json`, **idéntico** en `s10/evidencias/` y `salidas_s7/` ✓

| Tipo de error | n | Recall | Localización top-1 |
|---|---|---|---|
| diagnosis | 116 | 0.8966 | 0.9483 |
| treatment | 51 | 0.8627 | 0.8235 |
| pharmacotherapy | 36 | 0.8611 | 0.8611 |
| causalOrganism | 11 | 0.8182 | 0.8182 |
| **management** | 97 | **0.6804** | 0.7320 |

Coincide con el documento §6.4.2: «management 68 % vs diagnosis 90 %» ✓

---

## 6. Artefactos exclusivos de S11 — todos verificados ✓

| Métrica | Valor | Fuente |
|---|---|---|
| Anonimización v1: documentos / páginas | 1 / 20 | `anonimizacion_agregados.json` |
| Hallazgos / cajas tachadas | 127 / 87 | ídem |
| Tiempo de procesamiento | 77,5 s | ídem |
| Página a revisión (manuscrito) | 10 (OCR 40,2) | ídem |
| Recall capa texto NOMBRE | 0,898 (115/128) | `verificacion_humana_resumen.json` |
| Recall CÉDULA / HC / DIRECCIÓN | 1,000 (10/10) / 1,000 (12/12) / 1,000 (1/1) | ídem |
| Criterio de bloqueo NOMBRE+CÉDULA+HC | **No cumplido** | ídem |
| Oraciones extraídas / omitidas | 96 / 13 | `reporte_extraccion.json` |
| Corpus piloto de evaluación | 96 + 4 = 100, 2 positivas | `reporte_anotacion.json` |
| Solape doble ciego | 30 % = 29 oraciones | ídem |
| Cross-domain CITIMED | ROC-AUC 0.7347 · AUPRC 0.2689 | `eval_citimed.json` |
| Ensayo plantilla (n=4) | ROC-AUC / AUPRC 1.000 | `prueba_citimed.json` |
| Suite unitaria / frontend | 21 / 14 en verde | `_run_unit.txt`, `_run_frontend.txt` |
| Cobertura de código | 21 % · 3,40 s | `reporte_pytest.txt` |

Sin contraparte en S10: son las aportaciones nuevas de la etapa.

---

## Acciones

**Obligatoria**
1. Tabla 6 → AUPRC **0.398**, IC 95 % **0.353 – 0.457**. Con eso §6.4.5 («AUPRC = 0,40») deja de contradecirla.

**Higiene de artefactos** (evita que el error reaparezca)

2. Renombrar `s6/metricas_ajuste.json` → `s6/metricas_ajuste_2026-07-23.json`
3. Renombrar `s10/evidencias/metricas_tfidf.json` → añadir sufijo de fecha (es el mismo archivo)
4. Corregir `s10/evidencias/resumen_metricas.json`: `auprc` 0.4186 → 0.3977 — es el vector de propagación
5. `referencia_s7.auprc` en ambos `metricas_tripartita.json`: 0.42 → 0.40

**Oportunidades — evidencia que ya existe y no se reporta**

6. **McNemar** (§7.3.3): LLM+RAG es significativamente peor que zero-shot (p = 0,0059); TF-IDF vs LLM no alcanza significación (p = 0,0599). Sustenta estadísticamente la cascada.
7. **TF-IDF en español** (§6.4.5): rinde **mejor** que en inglés (AUC 0,959 vs 0,949). Rebate parcialmente la limitación de transferencia idiomática.
8. **Sesgo de idioma del LLM** (§6.4.3): Δ AUC = −0,0395 convierte una afirmación cualitativa en medición.

**Precisión menor**

9. El «4,5 % positivos» que justifica la precisión baja es la prevalencia de **entrenamiento** (0.0448). La de **prueba** —donde se mide la precisión— es **4,6 %** (311/6789 = 0.0458).
