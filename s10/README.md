# S10 — Entrega consolidada

Documentación y evidencias de la entrega S10 (avance consolidado post-S7/S8).

**Plazo Moodle:** 23 de agosto de 2026, 23:59  
**Documento principal:** [`docs/S10_Avance_Consolidado.pdf`](docs/S10_Avance_Consolidado.pdf)

## Grupo

Patricio Bayas Meza · José Puebla Paladines · Marco Zurita Rojas

Repositorio: [github.com/marcoz1691/MIA_Deteccion_HC](https://github.com/marcoz1691/MIA_Deteccion_HC)

## Contenido

| Ruta | Descripción |
|------|-------------|
| [`docs/S10_Avance_Consolidado.pdf`](docs/S10_Avance_Consolidado.pdf) | Informe final S10 (entrega Moodle) |
| [`docs/S10_Avance_Consolidado.docx`](docs/S10_Avance_Consolidado.docx) | Fuente editable Word |
| [`evidencias/`](evidencias/) | JSON, CSV y figuras reproducibles |
| [`generate_informe.py`](generate_informe.py) | Regenera PDF/DOCX desde métricas del repo |
| [`organize_evidencias.py`](organize_evidencias.py) | Copia JSON/figuras a `evidencias/` |

## Evidencias (`evidencias/`)

| Archivo | Origen | Uso en informe |
|---------|--------|----------------|
| `metricas_tfidf.json` | `s6/metricas_ajuste.json` | ROC-AUC 0.949, **AUPRC 0.419**, localización 84.6 % |
| `metricas_tripartita.json` | `salidas_s7/` | Comparativa TF-IDF / LLM / LLM+RAG |
| `analisis_por_tipo.json` | `salidas_s7/` | Recall por ErrorType |
| `eval_idioma_en_es.json` | `salidas_s7/` | Sesgo EN vs ES (LLM mock) |
| `eval_tfidf_idioma.json` | `salidas_s7/` | TF-IDF stop_words EN/ES/bilingüe |
| `recall_por_tipo_error.csv` | `salidas_s7/` | Tabla anexo |
| `figura_ajuste.png` | `s6/` | Curvas ROC/PR |
| `capturas/` | Figuras S6/S7 | Métricas, interpretabilidad, comparación tripartita |
| `verificacion_s10.txt` | Generado | Checksum y métricas clave |

## Regenerar informe y evidencias

Desde la raíz del repositorio, con venv activo y evaluaciones ya ejecutadas:

```bash
python s6/modelo_ajustado.py
python s7/analisis_por_tipo.py
python s7/eval_tripartita.py --mock-llm --max-oraciones 500
python s7/eval_idioma.py --mock-llm --subset 200
python s7/eval_tfidf_idioma.py
python s7/test_fallback.py
python s10/organize_evidencias.py
python s10/generate_informe.py
```

## Relación con entregas anteriores

- **S8:** [`s8/docs/S8_Informe_Final.docx`](../s8/docs/S8_Informe_Final.docx) — borrador **histórico** (9-ago-2026); el informe S10 se redactó desde el repositorio actual.
- **Código:** `s6/`, `s7/`, `demo/` — fuente de verdad para métricas y arquitectura.
- **Bitácora:** [`s6/BITACORA.md`](../s6/BITACORA.md)

## Checklist de coherencia documental

- [x] Matriz §132–148: tripartita, FAISS, demo, EN-ES → **Implementado**
- [x] Anexo sin rutas obsoletas (`baseline_medec/`, `salidas_medec/`)
- [x] AUPRC 0.419 con prevalencia 4.5 % declarada
- [x] Ollama + fallback TF-IDF descritos
- [x] LangChain/Docker/DVC/MLflow en § trabajo futuro
- [x] Métricas citadas desde JSON locales

## Disclaimer

Prototipo de investigación académica. No sustituye criterio clínico ni decisiones terapéuticas.
