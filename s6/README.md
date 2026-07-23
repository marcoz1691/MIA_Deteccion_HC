# Baseline — Detección de inconsistencias en historias clínicas (CITIMED)

**Modelo:** TF-IDF (n-gramas 1–2) → Regresión Logística (scikit-learn)
**Tarea:** clasificación binaria `hay inconsistencia (1) / no hay (0)`
**Rol:** punto de comparación **simple, determinista e interpretable** que la solución
final **LLM + RAG** debe superar. **No es la solución final: es el piso.**

> ### ⚠️ Resultado principal (leer antes de usar)
> Sobre el dataset público **MEDEC**, este baseline **no supera el azar**
> (**ROC-AUC = 0.504**) y su accuracy (0.523) empata con un clasificador trivial (0.521).
> No es un fallo de implementación: es la **prueba empírica** de que detectar
> inconsistencias clínicas **no es un problema léxico** y exige razonamiento semántico
> anclado en conocimiento externo (**LLM + RAG**). Ver `BITACORA.md`.

---

## 1. Contenido

```
baseline_citimed/
├── baseline.py             # baseline sobre CSV propio (o datos sintéticos)
├── baseline_medec.py       # baseline sobre MEDEC con particiones OFICIALES  <-- resultados del informe
├── datos_sinteticos.py     # generador de historias sintéticas (SOLO prueba de humo)
├── requirements.txt        # versiones fijadas
├── README.md
├── BITACORA.md             # registro fechado de cambios, resultados y decisiones
├── salidas/                # resultados con datos sintéticos
└── salidas_medec/          # resultados con MEDEC (evidencias del informe)
    ├── metricas_medec.json
    ├── ablacion.csv                # 5 variantes probadas
    ├── recall_por_tipo_error.csv
    ├── top_features_medec.csv
    ├── figura_informe.png
    ├── matriz_confusion_medec.png
    └── modelo_baseline_medec.joblib
```

## 2. Ejecución

```bash
pip install -r requirements.txt

# 1) Obtener MEDEC (dataset público)
git clone --depth 1 https://github.com/abachaa/MEDEC.git medec_try

# 2) Reproducir los resultados del informe
python baseline_medec.py

# 3) (opcional) Baseline con datos propios de CITIMED
python baseline.py --datos ruta/historias.csv --col-texto texto --col-label label
```

## 3. Resultados reproducibles (MEDEC, particiones oficiales, SEED = 42)

| Conjunto / referencia         | Accuracy | Precision | Recall | F1    | ROC-AUC |
|-------------------------------|----------|-----------|--------|-------|---------|
| Entrenamiento (CV 5-fold, F1) | —        | —         | —      | 0.261 ± 0.022 | — |
| Validación                    | 0.533    | 0.562     | 0.727  | 0.634 | 0.529   |
| **Prueba**                    | **0.523**| **0.523** | **0.945** | **0.674** | **0.504** |
| Clasificador trivial          | 0.521    | —         | —      | 0.685 | 0.500   |

⚠️ El F1 = 0.674 es **engañoso**: el modelo predice "hay error" en 562 de 597 notas
(marca casi todo como inconsistente). Por eso **siempre reportamos ROC-AUC** y la
línea trivial junto al F1.

### ¿Por qué falla? (diagnóstico medido sobre el corpus)
- Nota con error vs. nota corregida: **96,6 % de texto idéntico**.
- La oración errónea es solo el **8,9 %** del texto.
- Solapamiento de vocabulario entre clases: **95,6 %**.

→ Una *bolsa de palabras* carece de señal. El error es una **contradicción semántica**
frente al conocimiento médico, no un patrón de vocabulario.

### No es cuestión de hiperparámetros (ablación)
n-gramas 1-3, C=10, n-gramas de caracteres, LinearSVC y Naive Bayes: **ninguno supera
AUC ≈ 0.53**. El límite es **representacional**.

## 4. Advertencia sobre los datos sintéticos

Con el generador propio (`datos_sinteticos.py`) el mismo baseline obtuvo
**F1 = 0.798 / AUC = 0.845** — resultados que resultaron ser **falsa confianza**: el
generador introdujo atajos léxicos que el modelo memorizó. **Los datos sintéticos se
usan solo como prueba de humo del pipeline, nunca para validar desempeño.**

## 5. Criterio de éxito para la siguiente fase (LLM + RAG)

Superar **AUC = 0.504** y **F1 = 0.674** en la prueba de MEDEC, **sin degradar el recall
en errores críticos** (medicación / diagnóstico). El error más costoso es el **falso
negativo**: no detectar una inconsistencia real.

## 6. Reproducibilidad

`SEED = 42` (random, numpy) · particiones **oficiales** de MEDEC (no re-particionado) ·
CV 5-fold estratificada · versiones fijadas: scikit-learn 1.8.0, pandas 3.0.2,
numpy 2.4.4 (Python 3.12).
