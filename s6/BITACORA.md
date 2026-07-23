# BITÁCORA DEL PROYECTO — CITIMED

Detección de inconsistencias en historias clínicas mediante LLM con RAG.
Grupo: Patricio Bayas Meza · José Puebla Paladines · Marco Zurita Rojas.

Registro fechado de decisiones, cambios y resultados. Cada entrada debe ser
reproducible con el código y la semilla indicados.

---

## S5 — Implementación del baseline (TF-IDF + Regresión Logística)

**Cambios**
- Se implementa `baseline.py`: pipeline TF-IDF (1-2 n-gramas) + Regresión Logística,
  partición estratificada 70/15/15, CV 5-fold, interpretabilidad y guardado del modelo.
- Se implementa `datos_sinteticos.py` para probar el flujo mientras se gestiona la
  anonimización del corpus real de CITIMED.
- Reproducibilidad: `SEED = 42`, versiones fijadas en `requirements.txt`.

**Resultados (datos sintéticos, semilla 42)**
| Conjunto   | Accuracy | Precision | Recall | F1    | ROC-AUC |
|------------|----------|-----------|--------|-------|---------|
| Validación | 0.827    | 0.909     | 0.730  | 0.810 | 0.836   |
| Prueba     | 0.822    | 0.941     | 0.693  | 0.798 | 0.845   |

**Observación**: resultados aparentemente buenos. Pendiente de validar con datos reales.

---

## S6 — Evaluación del baseline sobre el dataset público MEDEC

**Cambios**
- Se incorpora `baseline_medec.py`: ejecuta el baseline sobre **MEDEC**
  (Ben Abacha et al., 2025) usando sus **particiones oficiales** (train 2.189 /
  val 574 / test 597 con verdad de referencia).
- Se añade línea de referencia trivial (clase mayoritaria), ablación de 5 variantes
  y análisis de recall por tipo de error.

**Resultados (MEDEC, particiones oficiales, semilla 42)**
| Conjunto / referencia          | Accuracy | Precision | Recall | F1    | ROC-AUC |
|--------------------------------|----------|-----------|--------|-------|---------|
| Entrenamiento (CV 5-fold, F1)  | —        | —         | —      | 0.261 ± 0.022 | — |
| Validación                     | 0.533    | 0.562     | 0.727  | 0.634 | 0.529   |
| **Prueba**                     | **0.523**| **0.523** | **0.945** | **0.674** | **0.504** |
| Clasificador trivial           | 0.521    | —         | —      | 0.685 | 0.500   |

**HALLAZGO CRÍTICO — el baseline no supera el azar (AUC = 0.504).**

Diagnóstico de la causa raíz (medido sobre el corpus):
- La nota con error y su versión corregida son **96,6 % idénticas**.
- La oración errónea representa solo el **8,9 %** del texto de la nota.
- El solapamiento de vocabulario entre clases es del **95,6 %**.
→ Una bolsa de palabras **no tiene señal**: el error es una contradicción
  *semántica* contra el conocimiento médico, no un patrón léxico.

Ablación (evidencia de techo representacional, no de ajuste):

| Configuración              | Accuracy | F1    | ROC-AUC |
|----------------------------|----------|-------|---------|
| TF-IDF(1-2) + LR (baseline)| 0.523    | 0.674 | 0.505   |
| TF-IDF(1-3) + LR, C=10     | 0.531    | 0.654 | 0.527   |
| TF-IDF char(3-5) + LR      | 0.524    | 0.656 | 0.522   |
| TF-IDF + LinearSVC         | 0.531    | 0.663 | 0.511   |
| TF-IDF + MultinomialNB     | 0.521    | 0.685 | 0.492   |

Ninguna variante supera AUC ≈ 0.53.

**Lección metodológica registrada**
El mismo baseline dio F1 = 0.798 / AUC = 0.845 sobre nuestros datos sintéticos y
AUC = 0.504 sobre MEDEC. El generador sintético introdujo **atajos léxicos**
involuntarios que el modelo memorizó. **Decisión: los datos sintéticos se usarán solo
como prueba de humo del pipeline, nunca para validar desempeño.**

**Decisiones derivadas**
1. Migrar la detección de nivel documento a **nivel de oración** (MEDEC provee
   `Error Sentence ID`).
2. Reportar **siempre ROC-AUC junto al F1** y contra el clasificador trivial: el F1
   aislado (0.674) ocultaba el fracaso.
3. Priorizar el prototipo **LLM + RAG**; el baseline queda fijado como piso a superar.

**Criterio de éxito para la siguiente fase**
Superar **AUC = 0.504** y **F1 = 0.674** en la partición de prueba de MEDEC, sin
degradar el recall en errores críticos (medicación / diagnóstico).

---

## S7 — Ajuste del prototipo: de nivel-nota a nivel-oración

**Cambios**
- Nuevo `modelo_ajustado.py`: reformula la tarea a **nivel de oración** usando
  `Error Sentence ID` de MEDEC. Explota cada nota en sus oraciones (27.216 en train,
  prevalencia positiva 4,5 %).
- Ingeniería de features: TF-IDF + `FeatureUnion` con 4 rasgos numéricos por oración
  (longitud, nº palabras, nº dígitos, negación).
- Hiperparámetros: `GridSearchCV` (ngram, C) con CV 5-fold estratificada → mejor:
  unigrama, C=1,0.
- Análisis estadístico: IC95 % por bootstrap (1000 remuestreos), variabilidad por
  folds, prueba de McNemar (baseline vs. ajustado a nivel nota).

**Resultados (MEDEC, particiones oficiales, SEED=42)**
| Métrica (test)        | Baseline (nota) | Ajustado (oración) |
|-----------------------|-----------------|--------------------|
| ROC-AUC               | 0.504           | **0.948** (IC95 0.940–0.958) |
| CV 5-fold AUC (media) | 0.261 (F1)      | **0.965 ± 0.007** |
| Localización top-1    | n/d             | **0.846** (263/311 notas) |
| F1 (oración)          | —               | 0.497 |
| Precision (oración)   | —               | 0.357 (desbalance 4,5 %) |

**Hallazgos**
1. Reformular a nivel de oración **rescata la señal**: AUC 0,504 → 0,948, con IC
   estrecho y baja varianza entre folds (estable, no sobreajuste).
2. **Localiza** la oración errónea en el 84,6 % de las notas — la capacidad útil para
   CITIMED (médico revisor).
3. A **nivel de nota**, el ajustado NO mejora al baseline (McNemar p=0,53): MEDEC hace
   que casi toda nota tenga una oración candidata → la clasificación binaria por nota
   es intrínsecamente poco separable. El valor está en la localización, no en el flag.

**Riesgos mitigados**: partición por nota (evita leakage), CV+bootstrap (controla
sobreajuste), evaluación solo sobre MEDEC real (evita la falsa confianza de S6).

**Criterio de éxito para la fase LLM+RAG**: superar localización top-1 = 0,846 y
ROC-AUC = 0,948 del modelo ajustado, sin degradar recall en errores críticos.

**Próximo (S7)**: MLflow desde el día 1; LLM zero-shot (Mistral-7B) sobre la
validación de MEDEC; indexar guías/CIE-10/vademécum en FAISS → comparación tripartita
TF-IDF vs. LLM zero-shot vs. LLM+RAG con estas mismas métricas.

---

## S7 (ext.) — Comparación tripartita, AUPRC, sesgo EN-ES y riesgos de producción

**Cambios**
- Módulo compartido `s7/metricas.py`: ROC-AUC + **AUPRC** + bootstrap IC95 + McNemar + localización top-1.
- `s7/preprocesamiento.py`: propagación de `ErrorType`, negación bilingüe, stop_words configurables.
- `s7/eval_tripartita.py`: comparación **TF-IDF vs LLM zero-shot vs LLM+RAG** (enfoque híbrido API+cache).
- `s7/analisis_por_tipo.py`: recall/AUPRC/localización por tipo de inconsistencia clínica.
- `s7/eval_idioma.py` + `s7/eval_tfidf_idioma.py`: diagnóstico sesgo inglés-español.
- `s7/eval_citimed.py`: pipeline preparado para Odontología CITIMED (cross-domain y fine-tune).
- `s7/docs/informe_produccion.md`: latencia, costos y privacidad PHI.

**Arquitectura LLM (decisión)**
- MEDEC (público): API cloud (`gpt-4o-mini`) con cache JSON → reproducibilidad y bajo costo (~$2–5 val+test).
- CITIMED (PHI): migrar a Ollama + Mistral-7B local; misma interfaz `LLMClient`.

**Métricas ampliadas (test, referencia S7)**
| Métrica | TF-IDF ajustado (S7) | Notas |
|---------|----------------------|-------|
| ROC-AUC | 0.949 | IC95 0.940–0.958 |
| **AUPRC** | **0.419** | Complementaria; prevalencia 4.5 % |
| Localización top-1 | 0.846 | 263/311 notas |
| CV 5-fold AUC | 0.965 ± 0.007 | Estable |

**Análisis por ErrorType**
- Script `analisis_por_tipo.py` genera `salidas_s7/recall_por_tipo_error.csv`.
- Prioridad en errores críticos: **Medication** y **Diagnosis**.

**Sesgo EN-ES (plan 3 fases)**
- Fase A: LLM zero-shot EN vs ES sobre subset validación (`eval_idioma.py`).
- Fase B: TF-IDF con stop_words english/spanish/bilingüe (`eval_tfidf_idioma.py`).
- Fase C: evaluación CITIMED Odontología cuando corpus anonimizado esté listo (`eval_citimed.py`).

**Criterio de éxito LLM+RAG**
Superar localización top-1 = 0.846 y ROC-AUC = 0.948 del TF-IDF ajustado, sin degradar recall en Medication/Diagnosis.

**Ejecución S7**
```bash
pip install -r requirements.txt
python s6/modelo_ajustado.py                    # regenera modelo + AUPRC
python s7/analisis_por_tipo.py
python s7/eval_tripartita.py --mock-llm --max-oraciones 500
python s7/eval_idioma.py --mock-llm --subset 200
python s7/eval_tfidf_idioma.py                  # requiere MEDEC
python s7/eval_citimed.py                       # pendiente corpus CITIMED
```

**Próximo (S8)**
- [ ] Ejecutar comparación tripartita con API real (OPENAI_API_KEY en .env).
- [ ] Corpus CITIMED Odontología anonimizado → Fase C sesgo EN-ES.
- [ ] Cascada producción TF-IDF → LLM local.
- [ ] MLflow tracking en CI.

