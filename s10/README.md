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
| [`generate_informe.py`](generate_informe.py) | Parte del Word S8, aplica correcciones del repo y exporta PDF |
| [`capture_demo.py`](capture_demo.py) | Genera capturas demo (análisis, métricas, fallback) |
| [`probar_citimed.py`](probar_citimed.py) | Anonimiza historias CITIMED → inferencia → CSV → eval |
| [`anonimizador/ANONIMIZADOR/`](anonimizador/ANONIMIZADOR/) | Servicio de anonimización (texto/PDF) |
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

## Pipeline CITIMED (anonimizador + inferencia)

Historias de ejemplo sintéticas en `s10/anonimizador/ANONIMIZADOR/ejemplos/` (p. ej.
`historia_ejemplo.sintetico.txt`). **No commitear** historias con PHI real; el archivo
`historia_ejemplo.txt` con datos ficticios realistas está en `.gitignore`.

```bash
# Requiere: python -m spacy download es_core_news_md (mejor anonimización)
python s10/probar_citimed.py
python s10/probar_citimed.py --entrada s10/anonimizador/ANONIMIZADOR/carpeta_historias/
```

Flujo:
1. **Anonimiza** → `s10/anonimizador/salidas/*_ANON.txt`
2. **Inferencia** TF-IDF + LLM mock sobre texto clínico en español
3. **CSV** → `data/citimed_odontologia.csv` (plantilla odontología + historias anonimizadas)
4. **Eval** cross-domain MEDEC→CITIMED → `salidas_s7/eval_citimed.json`

Reporte completo: `salidas_s7/prueba_citimed.json`. La demo Streamlit carga automáticamente historias anonimizadas de `s10/anonimizador/salidas/`.


- **S8:** [`s8/docs/S8_Informe_Final.docx`](../s8/docs/S8_Informe_Final.docx) — **plantilla de formato**; el informe S10 se genera copiando este Word y aplicando correcciones desde el repositorio (`generate_informe.py`).
- **Código:** `s6/`, `s7/`, `api/`, `frontend/`, `demo/` — fuente de verdad para métricas y arquitectura.
- **Bitácora:** [`s6/BITACORA.md`](../s6/BITACORA.md)

## Checklist de coherencia documental

- [x] API FastAPI + frontend React documentados en informe y README
- [x] Matriz §132–148: tripartita, FAISS, demo, EN-ES → **Implementado**
- [x] Anexo sin rutas obsoletas (`baseline_medec/`, `salidas_medec/`)
- [x] AUPRC 0.419 con prevalencia 4.5 % declarada
- [x] Ollama + fallback TF-IDF descritos
- [x] LangChain/Docker/DVC/MLflow en § trabajo futuro
- [x] Métricas citadas desde JSON locales

## Disclaimer

Prototipo de investigación académica. No sustituye criterio clínico ni decisiones terapéuticas.
