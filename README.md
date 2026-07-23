# MIA_Deteccion_HC

Detección de inconsistencias en historias clínicas (proyecto CITIMED).

**Grupo:** Patricio Bayas Meza · José Puebla Paladines · Marco Zurita Rojas

## Estructura

```
MIA_Deteccion_HC/
├── requirements.txt
├── s6/                          # entrega S6 — ajuste TF-IDF (base de S7)
│   ├── modelo_ajustado.py
│   ├── metricas_ajuste.json
│   ├── figura_ajuste.png
│   ├── BITACORA.md
│   └── docs/
├── s7/                          # entrega S7 — comparación tripartita + AUPRC
│   ├── eval_tripartita.py       # TF-IDF vs LLM zero-shot vs LLM+RAG
│   ├── analisis_por_tipo.py     # recall por ErrorType
│   ├── eval_idioma.py           # sesgo EN vs ES (LLM)
│   ├── eval_tfidf_idioma.py     # sesgo EN vs ES (TF-IDF)
│   ├── eval_citimed.py          # Odontología CITIMED (preparado)
│   ├── metricas.py              # AUC + AUPRC + McNemar
│   ├── llm_client.py            # API + cache
│   ├── rag_index.py             # FAISS
│   ├── config.yaml
│   └── docs/informe_produccion.md
└── data/
    └── citimed_odontologia.example.csv
```

## Resultado principal (S7)

Reformular la tarea de **nivel nota** a **nivel oración** sobre MEDEC eleva el ROC-AUC de **0.504 → 0.949** y localiza la oración errónea en **84.6 %** de las notas con error (263/311). AUPRC test = **0.419** (prevalencia 4.5 %).

## Ejecución rápida

```bash
pip install -r requirements.txt

# Clonar MEDEC (dataset público)
git clone --depth 1 https://github.com/abachaa/MEDEC.git medec_try

# S7 — modelo TF-IDF ajustado
python s6/modelo_ajustado.py

# S7 — comparación tripartita (mock LLM sin API key)
python s7/eval_tripartita.py --mock-llm --max-oraciones 500

# S7 — análisis por tipo de error
python s7/analisis_por_tipo.py

# S7 — con API real (opcional)
# echo OPENAI_API_KEY=sk-... > .env
python s7/eval_tripartita.py --max-oraciones 200
```

Ver [`s6/BITACORA.md`](s6/BITACORA.md) para el historial completo y [`s7/docs/informe_produccion.md`](s7/docs/informe_produccion.md) para riesgos de producción.
