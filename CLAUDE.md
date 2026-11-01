# MIA_Deteccion_HC

Detección de inconsistencias en historias clínicas (proyecto CITIMED, maestría UDLA). Python 3.12+, FastAPI, scikit-learn, RAG; frontend React en `frontend/`. Documentos académicos en español.

## Reglas permanentes

- **Datos clínicos reales nunca al repo.** `data/citimed_*`, `data/*.db`, `s11/corpus/*.csv` y `s11/tessdata/` están en `.gitignore`; no los fuerces con `git add -f`. Sigue `s11/docs/anexo_etico.md`.
- No pegues contenido de historias clínicas reales en commits, issues ni salidas.
- Versiones de dependencias fijadas en `requirements.txt`; pytest va en `requirements-dev.txt`.
- No cambies cifras de resultados (ROC-AUC 0.949, AUPRC 0.419, etc.) sin regenerar las evidencias que las respaldan.
- Antes de entregar: `python -m pytest`.
- Claves de API solo en `.env` (ver `.env.example`).

## Skills del proyecto

En `.claude/skills/`: `mia-informe-evidencias` (regenerar informe y evidencias S10/S11) y `mia-pruebas` (pruebas por fase y marcadores).
