## 4.4 Evaluación con LLM real: cierre de la limitación del modo simulado

Todas las métricas de los brazos LLM reportadas hasta S10 se obtuvieron con un cliente
simulado (`mock`), una heurística determinista de palabras clave que no realiza llamadas a
ninguna API. Esa simulación producía ROC-AUC ≈ 0,498 en ambos brazos LLM, es decir,
ausencia total de discriminación, por lo que la superioridad observada de TF-IDF no era
atribuible a una comparación válida. Esta sección reemplaza esas cifras por una medición
con un LLM real.

La corrida se ejecutó contra la API de OpenAI con el modelo `gpt-4o-mini`
(`temperature = 0`, `max_tokens = 10`), sobre las primeras 400 oraciones del split de test
de MEDEC-MS. MEDEC es un corpus público de notas clínicas sintéticas o desidentificadas,
por lo que el envío de texto a un proveedor externo no compromete datos de pacientes; para
el corpus CITIMED de odontología esta vía no sería admisible y se mantiene la recomendación
de modelo local (véase §6, privacidad). La corrida completó 442 llamadas nuevas a la API con
cero errores y cero reintentos; las 358 restantes se sirvieron desde el cache de prompts de
corridas reales previas.

### Comparación mock vs. LLM real

| Brazo | ROC-AUC mock | ROC-AUC real | AUPRC real | Latencia (ms/oración) | Costo USD / 1000 oraciones |
|---|---|---|---|---|---|
| TF-IDF ajustado | 0,9537 | 0,9475 | 0,4055 | 0,381 | 0,0000 |
| LLM zero-shot | 0,4979 | 0,5094 | 0,0536 | 587,25 | 0,0128 |
| LLM + RAG | 0,4979 | 0,5067 | 0,0534 | 535,35 | 0,0300 |

Intervalos de confianza al 95 % (bootstrap, n = 1000): TF-IDF ROC-AUC [0,9162; 0,9732] y
AUPRC [0,2509; 0,6274]; LLM zero-shot ROC-AUC [0,4565; 0,5811] y AUPRC [0,0325; 0,0822];
LLM + RAG ROC-AUC [0,4764; 0,5593] y AUPRC [0,0325; 0,0876]. La AUPRC de referencia por azar
en este subconjunto es 0,0525 (21 oraciones positivas sobre 400). Percentiles de latencia
medidos sobre la llamada a la API: zero-shot P50 = 534,68 ms y P95 = 982,58 ms;
RAG P50 = 523,06 ms y P95 = 674,93 ms, sin incluir el tiempo de recuperación FAISS.

La columna mock proviene de `s10/evidencias/metricas_tripartita.json`, calculada sobre 500
oraciones del mismo split; la corrida real usa las primeras 400. La diferencia de tamaño
explica el leve descenso de TF-IDF (−0,0062 en ROC-AUC, −0,0700 en AUPRC), que no obedece a
ningún cambio de modelo: TF-IDF es determinista y no interviene la API.

### Costo medido frente a la estimación previa

La sección 5 de [`s7/docs/informe_produccion.md`](../../s7/docs/informe_produccion.md)
estimaba, suponiendo unos 150 tokens por oración, un costo de 0,08 USD por 1000 oraciones en
zero-shot y 0,15 USD por 1000 oraciones con RAG. El consumo medido resultó
sustancialmente menor: 0,0128 USD por 1000 oraciones en zero-shot (6,3 veces por debajo de
lo estimado) y 0,0300 USD por 1000 oraciones con RAG (5,0 veces por debajo). El costo total
atribuido a las 800 evaluaciones de esta corrida fue de 0,0171 USD.

La discrepancia se explica por el tamaño real de los prompts: 82,14 tokens por oración en
zero-shot frente a los 150 supuestos, y 196,91 tokens en RAG, junto con una salida de un
solo token por respuesta gracias al formato YES/NO con `max_tokens = 10`. La estimación
previa era, por tanto, conservadora en el sentido correcto, y la conclusión de la sección de
costos se refuerza: el gasto de API no es el factor limitante para adoptar el brazo LLM. La
latencia sí se confirma como barrera operativa: el LLM es aproximadamente 1500 veces más
lento por oración que TF-IDF (587 ms frente a 0,38 ms), consistente con el rango de
200–800 ms anticipado en el informe de producción.

### Interpretación

El LLM real no supera al TF-IDF ajustado. La brecha es amplia y no marginal: 0,9475 frente a
0,5094 en ROC-AUC y 0,4055 frente a 0,0536 en AUPRC para el brazo zero-shot. Los intervalos
de confianza de ambos brazos LLM incluyen el valor 0,5 en ROC-AUC y su AUPRC es
indistinguible de la línea base por azar (0,0525), de modo que `gpt-4o-mini` en configuración
zero-shot sobre oraciones aisladas no discrimina oraciones inconsistentes en MEDEC. Los
intervalos de TF-IDF y de los brazos LLM no se solapan en ninguna de las dos métricas. La
localización top-1 confirma el mismo patrón: 0,8571 en TF-IDF frente a 0,0952 en ambos brazos
LLM.

Este resultado es importante porque cambia la naturaleza de la conclusión, no su dirección.
En S10 la ventaja de TF-IDF era un artefacto no interpretable, dado que el competidor era una
heurística de palabras clave. Con la API real, la ventaja se sostiene sobre una comparación
metodológicamente válida y queda cerrada la limitación señalada por el jurado. La causa
probable del bajo desempeño del LLM es de diseño experimental más que de capacidad del
modelo: el prompt entrega una oración descontextualizada, mientras que buena parte de los
errores de MEDEC son contradicciones respecto de otras partes de la nota, que resultan
indetectables sin ese contexto. La versión con RAG no corrige el problema, porque el
conocimiento recuperado es clínico general y no la propia nota del paciente. De hecho, RAG
vuelve al modelo más conservador: su recall cae de 0,0952 a 0,0476 y solo emite 14
predicciones positivas frente a 31 del zero-shot, una diferencia estadísticamente
significativa entre ambos brazos LLM (McNemar, p = 0,005925).

Las pruebas de McNemar sobre decisiones binarias en el umbral 0,5 deben leerse con cautela.
TF-IDF frente a LLM zero-shot arroja p = 0,059941 y TF-IDF frente a LLM + RAG arroja
p = 1,0000, valores que no reflejan la magnitud real de la diferencia: con un 94,75 % de
oraciones negativas, un clasificador que casi nunca predice positivo alcanza una exactitud
comparable a la de TF-IDF (0,9175 frente a 0,9200) sin detectar prácticamente ningún error.
La comparación informativa en este escenario de fuerte desbalance es la AUPRC, donde la
diferencia es inequívoca. En consecuencia, la recomendación del trabajo se mantiene: TF-IDF
ajustado como componente de producción y el brazo LLM reservado para exploración futura con
prompts que incorporen la nota completa.

El diagnóstico de sesgo idiomático con LLM real (200 oraciones del split de validación) no
aporta evidencia utilizable: ROC-AUC de 0,4579 con prompt en inglés y 0,4974 con prompt en
español, con AUPRC de 0,0500 en ambos casos. El delta EN−ES de −0,0395 tiene signo contrario
al esperado, pero ambos valores están en el entorno del azar, por lo que la diferencia no es
interpretable como sesgo de idioma. La hipótesis de ventaja del inglés sobre el corpus MEDEC
nativo no queda confirmada ni refutada con este diseño.

### Reproducibilidad

Las métricas de esta sección se regeneran con:

```bash
python s11/eval_llm_real.py --max-oraciones 400
```

El script ejecuta `s7/eval_tripartita.py` sin la bandera `--mock-llm`, reconstruye el consumo
de tokens y la latencia por brazo desde el cache de prompts, incorpora la comparación contra
la línea base mock de S10 y escribe
[`s11/evidencias/metricas_llm_real.json`](../evidencias/metricas_llm_real.json). Requiere
`OPENAI_API_KEY` en `.env`; el script aborta si detecta que la corrida cargada está en modo
mock, para evitar publicar métricas simuladas por error. Con el cache poblado la
consolidación puede repetirse sin costo mediante `--solo-consolidar`. El diagnóstico de
idioma se obtiene por separado con `python s7/eval_idioma.py --subset 200`.
