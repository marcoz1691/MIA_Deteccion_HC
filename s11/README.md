# S11 — Borrador avanzado del documento final

Cierra las tres deudas de la retroalimentación S10 (96/100): pytest declarado,
evaluación con LLM real y avance del corpus CITIMED anonimizado con aval ético.

**Documento Moodle / Teams:** [`docs/S11_Borrador_Avanzado.pdf`](docs/S11_Borrador_Avanzado.pdf)

## Grupo

Patricio Bayas Meza · José Puebla Paladines · Marco Zurita Rojas

## Contenido

| Ruta | Descripción |
|------|-------------|
| [`docs/S11_Borrador_Avanzado.pdf`](docs/S11_Borrador_Avanzado.pdf) | Informe para Moodle y Teams |
| [`docs/anexo_etico.md`](docs/anexo_etico.md) | Protocolo de de-identificación y cadena de custodia |
| [`docs/guia_anotacion.md`](docs/guia_anotacion.md) | Criterios de etiquetado del corpus |
| [`docs/protocolo_verificacion_humana.md`](docs/protocolo_verificacion_humana.md) | Revisión dual de las 20 páginas |
| [`anonimizador_ocr/`](anonimizador_ocr/) | Anonimizador OCR 1.5 (sin historias ni salidas con PHI) |
| [`evidencias/`](evidencias/) | JSON/CSV/figuras publicables (sin texto clínico) |
| [`generate_informe.py`](generate_informe.py) | Regenera Word + PDF desde el S10 |

## Evidencias publicables

| Archivo | Contenido |
|---------|-----------|
| `metricas_llm_real.json` | TF-IDF vs LLM real vs RAG (n=400, gpt-4o-mini) |
| `anonimizacion_agregados.json` | 20 páginas, 127 hallazgos, sin texto |
| `verificacion_humana.csv` | Conteos por página y categoría |
| `verificacion_humana_resumen.json` | Recall de capa de texto |
| `reporte_anotacion.json` | n, prevalencia, kappa |
| `reporte_pytest.txt` | Salida de la suite unificada |
| `capturas/` | Figuras y prototipo React |

No se versionan: `anonimizador_ocr/historias/`, `anonimizador_ocr/salidas*/`, `corpus/*.csv`, `evidencias/crudo/`.

## Regenerar

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
cd frontend; npm test
python s11/eval_llm_real.py --max-oraciones 400   # requiere OPENAI_API_KEY; usa cache
python s11/extraer_corpus.py --sin-ner --omitir-residuos
python s11/anotar_piloto.py
python s7/eval_citimed.py --modo cross_domain
python s11/consolidar_verificacion.py
python s11/generar_figuras.py
python s11/generate_informe.py
```

## Relación con S10

S10 queda como snapshot. S11 parte de `s10/docs/S10_Avance_Consolidado.docx` y añade
§3.5–3.8, §4.4, §5, §6 ampliada, §7.2, pitch y reflexión.
