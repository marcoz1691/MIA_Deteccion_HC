---
name: mia-pruebas
description: Ejecuta y diagnostica las pruebas de MIA_Deteccion_HC con pytest por fase y marcador (smoke, regression, integration, eval, perf, stress, security, e2e). Úsalo cuando el usuario pida correr pruebas, ver qué falla, cobertura, pruebas de seguridad, rendimiento o evaluación del modelo.
allowed-tools: Read, Grep, Glob, Bash
---

# Pruebas

Configuración en `pytest.ini` (un solo `python -m pytest` recoge `tests/`, `api/`, `s7/`, `s10/` y `s11/`). Guía: `tests/README.md`; scripts por fase: `tests/run_phase1.sh`.

```bash
pip install -r requirements-dev.txt
python -m pytest                      # todo
python -m pytest -m smoke             # post-deploy
python -m pytest -m regression        # regresión funcional
python -m pytest -m "eval"            # evaluación ML
python -m pytest -m security          # seguridad y cumplimiento
```

Marcadores: smoke, regression, integration, eval, perf, stress, security, e2e, requiere_ocr (se omite sin Tesseract).

Ante fallos: reproduce, lee el traceback, localiza la causa en el código y propón el arreglo. No saltes ni desactives pruebas para ponerlas en verde.
