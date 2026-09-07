# Tabla 6 — corrida de julio vs. corrida de agosto

Comparación completa de los dos artefactos que sostienen la Tabla 6 del documento, en el mismo formato de la tabla original.

| | Artefacto | Fecha | ¿Reproducible hoy? |
|---|---|---|---|
| **Julio** | `s6/metricas_ajuste.json` (idéntico a `s10/evidencias/metricas_tfidf.json`) | 2026-07-23 00:38 | **No** |
| **Agosto** | `salidas_ajuste/metricas_ajuste.json` | 2026-08-23 23:10 | **Sí** — reproducido celda por celda |

`s7/config.yaml` carga `salidas_ajuste/modelo_ajustado.joblib`, es decir, **el sistema opera con el modelo de agosto**.

---

## Tabla 6 — versión de JULIO (la que está hoy en el documento)

| Métrica (test MEDEC) | Baseline (nota) | Ajustado (oración) | Lectura |
|---|---|---|---|
| ROC-AUC | 0.505 | 0.949 | De azar a fuerte discriminación |
| ROC-AUC (IC 95 %) | - | 0.940 – 0.958 | Intervalo estrecho: resultado robusto |
| CV 5 fold (AUC) | - | 0.965 ± 0.007 | Muy estable entre pliegues |
| Recall (oración) | 0.945* | 0.817 | *El del baseline era espurio |
| Precisión (oración) | 0.523 | 0.357 | Baja por desbalance |
| Localización top-1 | n/d | 0.846 | Acierta la oración en 263/311 notas |
| **AUPRC (oración)** | - | **0.419** | **IC 95 % 0.392 – 0.446** |

## Tabla 6 — versión de AGOSTO (la correcta, corresponde al modelo desplegado)

| Métrica (test MEDEC) | Baseline (nota) | Ajustado (oración) | Lectura |
|---|---|---|---|
| ROC-AUC | 0.505 | 0.949 | De azar a fuerte discriminación |
| ROC-AUC (IC 95 %) | - | 0.940 – 0.958 | Intervalo estrecho: resultado robusto |
| CV 5 fold (AUC) | - | 0.965 ± 0.007 | Muy estable entre pliegues |
| Recall (oración) | 0.945* | 0.817 | *El del baseline era espurio |
| Precisión (oración) | 0.523 | 0.357 | Baja por desbalance |
| Localización top-1 | n/d | 0.846 | Acierta la oración en 263/311 notas |
| **AUPRC (oración)** | - | **0.398** | **IC 95 % 0.353 – 0.457; métrica clave con 4,6 % de positivos** |

> **Es la única fila que cambia.** Todo lo demás es idéntico entre ambas corridas, con valores en bruto coincidentes al cuarto decimal.

---

## Diferencias exactas, celda por celda

| Campo del JSON | Julio | Agosto | Δ |
|---|---|---|---|
| `prueba.auprc` | 0.4186 | **0.3977** | −0.0209 |
| `prueba.auprc_ci95` | [0.392, 0.446] | **[0.3529, 0.4574]** | IC más ancho |
| `validacion.auprc` | 0.4512 | **0.5110** | **+0.0598** |
| `validacion.auprc_ci95` | [0.428, 0.475] | **[0.458, 0.5708]** | IC más ancho |
| `ajustado_a_nivel_nota.auprc` | *(ausente)* | 0.4919 | clave nueva |
| `baseline_a_nivel_nota.auprc` | *(ausente)* | 0.5208 | clave nueva |

**Idénticos en ambos** (coincidencia exacta al cuarto decimal): `prueba.roc_auc` 0.9485 · `prueba.roc_auc_ci95` [0.9398, 0.9576] · `prueba.recall` 0.8167 · `prueba.precision` 0.3567 · `prueba.f1` 0.4966 · `prueba.accuracy` 0.9241 · `prueba.matriz_confusion` [[6020, 458], [57, 254]] · `validacion.roc_auc` 0.9678 · `cv_auc_mean` 0.965 · `cv_auc_sd` 0.0072 · `cv_auc_folds` [0.9509, 0.9684, 0.9664, 0.9713, 0.968] · `localizacion_top1_test` 0.8457 · `notas_con_error_test` 311 · `baseline_a_nivel_nota` completo (auc 0.5051, rec 0.9453, prec 0.5231, f1 0.6735, acc 0.5226) · `prevalencia_oracion_error_train` 0.0448

---

## Verificación empírica

Modelo cargado desde `salidas_ajuste/modelo_ajustado.joblib`, evaluado sobre las particiones oficiales de MEDEC:

```
PRUEBA      (n=6789, positivas=311)   ROC-AUC = 0.9485   AP = 0.3977
VALIDACION  (n=7054, positivas=319)   ROC-AUC = 0.9678   AP = 0.5110
```

**Agosto reproduce exacto en ambos splits.** Julio no reproduce por ninguna vía:

| Estimador probado | Prueba | ¿Da 0.4186? |
|---|---|---|
| `average_precision_score(y, score)` — el que usa `s7/metricas.py` | 0.3977 | No |
| `auc(recall, precision)` — trapecio sobre la curva PR | 0.3956 | No |
| `average_precision_score(y, pred)` — hipótesis de error con predicción binaria | 0.2998 | No |

Además, julio se desvía en **direcciones opuestas** según el split: por encima en prueba (+0.021) y por debajo en validación (−0.060). Con ROC-AUC y matriz de confusión idénticos, eso no puede provenir del mismo par (y, score) bajo ningún estimador. Los valores de julio corresponden a un artefacto intermedio que ya no está en el repositorio.

`s7/metricas.py` tiene un solo commit (`e4f4ef2`, 2026-07-23) y siempre usó `average_precision_score`, de modo que el cálculo no cambió entre ambas fechas.

---

## Qué hacer

1. **En la Tabla 6 del documento**, reemplazar la fila de AUPRC por la versión de agosto: `0.398`, IC 95 % `0.353 – 0.457`.
2. Con eso, **§6.4.5 deja de contradecir a la Tabla 6**: hoy dice «AUPRC = 0,40», que redondea 0.3977 y siempre fue el valor correcto.
3. **Retirar de circulación el artefacto de julio.** Renombrarlo `s6/metricas_ajuste_julio_2026.json` o moverlo a un directorio de histórico. Mientras conserve el nombre canónico, cualquier integrante del equipo puede volver a citarlo de buena fe. Nótese que `s10/evidencias/metricas_tfidf.json` es **el mismo archivo** y arrastra el mismo riesgo.
4. **Opcional, si quieres blindarlo ante el tribunal:** una nota al pie de la Tabla 6 —«Métricas recalculadas sobre el modelo vigente (`salidas_ajuste/modelo_ajustado.joblib`); los valores de AUPRC de iteraciones previas del ajuste no corresponden a este artefacto»— convierte una corrección silenciosa en trazabilidad explícita.

### Prevalencia: precisión menor

El documento justifica la precisión baja con «4,5 % positivos». Ese es el valor de **entrenamiento** (`prevalencia_oracion_error_train` = 0.0448). La prevalencia de la partición de **prueba**, que es donde se mide la precisión, es **4,6 %** (311/6789 = 0.0458). Dos opciones: cambiar a «4,6 %», o mantener «4,5 %» aclarando que es la prevalencia de entrenamiento.
