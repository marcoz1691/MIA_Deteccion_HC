---
name: mia-informe-evidencias
description: Regenera el informe, las evidencias y las capturas de las entregas S10 y S11 de MIA_Deteccion_HC. Úsalo cuando el usuario hable de informe, borrador, entrega, Moodle, PDF, evidencias, figuras, capturas del prototipo o actualizar el capstone.
allowed-tools: Read, Grep, Glob, Edit, Bash
---

# Informe y evidencias (S10 / S11)

Lee primero `s11/README.md` (índice y comandos) y `s10/README.md`.

## S11 (vigente)

```bash
pip install -r requirements-dev.txt
python -m pytest
python s11/generate_informe.py
```

Salida: `s11/docs/S11_Borrador_Avanzado.pdf`. Otros scripts en `s11/`: `generar_figuras.py`, `consolidar_verificacion.py`, `sanitizar_evidencias.py`, `actualizar_capstone.py`.

## S10

```bash
python s10/organize_evidencias.py   # copia JSON/figuras a s10/evidencias/
python s11/capture_prototipo.py     # requiere API + Vite en marcha
python s10/generate_informe.py      # requiere MS Word en Windows
python s10/run_verificacion.py      # batería completa, ~10 min, opcional
```

## Cuidados

- Corre `s11/sanitizar_evidencias.py` antes de publicar evidencias: no deben contener datos reales de pacientes.
- Si una cifra cambia, actualízala en el README y en el informe a la vez.
- Los pasos con Word o Tesseract pueden no estar disponibles aquí: dilo en vez de simular el resultado.
