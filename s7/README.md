# S7 — Comparación tripartita y mejoras post-feedback profesor

Implementa las 5 mejoras solicitadas:

1. **Comparación tripartita** — `eval_tripartita.py`
2. **AUPRC** — `metricas.py` (usado por S6 y S7)
3. **Sesgo EN-ES** — `eval_idioma.py`, `eval_tfidf_idioma.py`, `eval_citimed.py`
4. **Análisis por ErrorType** — `analisis_por_tipo.py`
5. **Riesgos producción** — `docs/informe_produccion.md`

## Orden recomendado

```bash
python s6/modelo_ajustado.py
python s7/analisis_por_tipo.py
python s7/eval_tripartita.py --mock-llm --max-oraciones 500
python s7/eval_idioma.py --mock-llm --subset 200
python s7/eval_tfidf_idioma.py
python s7/eval_citimed.py
```

Salidas en `salidas_s7/` (gitignored).
