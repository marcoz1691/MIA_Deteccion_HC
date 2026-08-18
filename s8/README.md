# S8 — Entrega (histórico)

Documentación de la entrega S8. El borrador Word está **desactualizado** respecto al código actual; usar S10 como informe canónico.

## Documento S8 (referencia histórica)

| Archivo | Descripción |
|---------|-------------|
| [`docs/S8_Informe_Final.docx`](docs/S8_Informe_Final.docx) | Borrador informe S8 (9-ago-2026) — **no usar como fuente de verdad** |

Origen local: `Downloads/S8-BORRADOR INFORME FINAL (1).docx`

## Informe canónico (S10)

| Archivo | Descripción |
|---------|-------------|
| [`../s10/docs/S10_Avance_Consolidado.pdf`](../s10/docs/S10_Avance_Consolidado.pdf) | Informe consolidado alineado con el repositorio |
| [`../s10/README.md`](../s10/README.md) | Índice S10 + evidencias |

El informe S10 corrige el borrador S8: capacidades marcadas como pendientes en §132–148 (tripartita, FAISS, demo, EN-ES, fallback) están **implementadas** en `s6/`, `s7/` y `demo/`.

## Relación con el código

S8/S10 extienden el trabajo de S7 (`s7/`). La bitácora del proyecto está en [`s6/BITACORA.md`](../s6/BITACORA.md) — entrada **S10** documenta la consolidación final.

## Referencias cruzadas

- Código y evaluaciones: [`s7/README.md`](../s7/README.md)
- Demo interactiva: [`demo/README.md`](../demo/README.md)
- Riesgos de producción: [`s7/docs/informe_produccion.md`](../s7/docs/informe_produccion.md)
- Evidencias cuantitativas: [`../s10/evidencias/`](../s10/evidencias/)

## Pendientes (trabajo futuro, no S10)

- [ ] Ejecutar comparación tripartita con API real
- [ ] Corpus CITIMED Odontología anonimizado
- [ ] Cascada producción TF-IDF → LLM local (Ollama) en inferencia
- [ ] MLflow tracking en CI
- [ ] LangChain / Docker / DVC (plan futuro)

Ver [`s6/BITACORA.md`](../s6/BITACORA.md) entrada S10 y sección Limitaciones del informe PDF.
