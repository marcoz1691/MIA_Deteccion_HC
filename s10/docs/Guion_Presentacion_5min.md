# Guion — Presentación 5 minutos (CITIMED)

**Archivo PPT:** `Presentacion_CITIMED_5min.pptx` (8 diapositivas)  
**Duración total:** ~5:00  
**Regenerar:** `python s10/generate_presentacion.py --duracion 5min`

---

## Diapositiva 1 — Portada · **15 s**

> Buenas tardes. Somos Patricio Bayas, José Puebla y Marco Zurita.  
> Presentamos **Detección de inconsistencias en historias clínicas**, proyecto CITIMED.

---

## Diapositiva 2 — El problema · **35 s**

> Las historias clínicas pueden tener errores — medicación contraindicada, plan incompatible con el diagnóstico — que afectan la seguridad del paciente.  
> Revisar cada nota a mano es lento y muchos errores pasan desapercibidos.  
> Nuestro objetivo **no es reemplazar al médico**: es **señalar la oración sospechosa** para que él decida.

---

## Diapositiva 3 — Insight clave · **50 s** ⭐

> Este es el hallazgo central.  
> En el dataset MEDEC, la nota con error y la corregida comparten el **96,6 % del texto**. La oración errónea es solo el **9 %**.  
> Si clasificamos **toda la nota** con TF-IDF, el ROC-AUC es **0,504** — azar.  
> Si pasamos a **nivel oración**, sube a **0,949** y localizamos la oración correcta en el **84,6 %** de los casos.  
> Conclusión: no es un problema de vocabulario; hace falta **razonamiento semántico**.

---

## Diapositiva 4 — Cómo funciona · **45 s**

> El pipeline es simple: segmentamos la nota en oraciones y puntúamos cada una con **tres brazos** — TF-IDF, rápido y local; LLM zero-shot; y LLM más RAG con guías clínicas.  
> Fusionamos scores y devolvemos la **oración top-1**.  
> Tenemos API FastAPI, frontend React y demo Streamlit. Si cae el LLM, degradamos a TF-IDF con alerta.

---

## Diapositiva 5 — Ejemplo · **40 s**

> Caso real de la demo: paciente con **alergia a penicilina**, y la nota prescribe **amoxicilina**.  
> El sistema resalta esa oración. RAG recupera guías de farmacoterapia que justifican la alerta.  
> El clínico revisa y corrige.

---

## Diapositiva 6 — Resultados · **50 s** ⭐

> En el test de MEDEC: ROC-AUC **0,949**, AUPRC **0,419** con solo 4,5 % de oraciones erróneas, y **84,6 %** de localización top-1 — 263 de 311 notas con error.  
> Comparen con el baseline a nivel nota: **0,504**. El salto viene de **reformular el problema**, no de tunear hiperparámetros.

---

## Diapositiva 7 — Prototipo y próximos pasos · **40 s**

> Prototipo end-to-end listo: API, React y Streamlit con mock LLM local.  
> Para CITIMED: anonimizador de PHI y Ollama on-premise.  
> Próximo paso: piloto odontológico con validación clínica. Todo en GitHub.

---

## Diapositiva 8 — Gracias · **15 s**

> Muchas gracias. ¿Preguntas?

---

## Control de tiempo

| Diap. | Tema              | Tiempo | Acumulado |
|-------|-------------------|--------|-----------|
| 1     | Portada           | 0:15   | 0:15      |
| 2     | Problema          | 0:35   | 0:50      |
| 3     | Insight clave     | 0:50   | 1:40      |
| 4     | Cómo funciona     | 0:45   | 2:25      |
| 5     | Ejemplo           | 0:40   | 3:05      |
| 6     | Resultados        | 0:50   | 3:55      |
| 7     | Prototipo         | 0:40   | 4:35      |
| 8     | Gracias           | 0:15   | **4:50**  |

Margen de ~10 s para respirar o una pregunta rápida antes del cierre.

## Si te pasas de tiempo

- Acorta diap. 4 y 7 (30 s cada una).
- **No recortes** diap. 3 ni 6: son el corazón de la presentación.
