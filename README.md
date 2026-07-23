# MIA_Deteccion_HC

Detección de inconsistencias en historias clínicas (proyecto CITIMED).

**Grupo:** Patricio Bayas Meza · José Puebla Paladines · Marco Zurita Rojas

## Estructura

```
MIA_Deteccion_HC/
├── requirements.txt          # dependencias del proyecto
├── s6/                       # entrega S6 — ajustes al prototipo
│   ├── modelo_ajustado.py    # clasificación a nivel de oración (MEDEC)
│   ├── metricas_ajuste.json  # resultados reproducibles
│   ├── figura_ajuste.png     # gráficos de desempeño
│   ├── BITACORA.md           # registro de decisiones y resultados
│   ├── README.md             # documentación del baseline (S5/S6)
│   └── docs/                 # informes y entregables (docx/pdf)
└── README.md
```

## Resultado principal (S6/S7)

Reformular la tarea de **nivel nota** a **nivel oración** sobre MEDEC eleva el ROC-AUC de **0.504 → 0.949** y localiza la oración errónea en **84.6 %** de las notas con error (263/311).

Ver [`s6/BITACORA.md`](s6/BITACORA.md) para el historial completo y [`s6/metricas_ajuste.json`](s6/metricas_ajuste.json) para las métricas detalladas.

## Ejecución rápida

```bash
pip install -r requirements.txt

# Clonar MEDEC (dataset público)
git clone --depth 1 https://github.com/abachaa/MEDEC.git medec_try

# Ejecutar modelo ajustado
python s6/modelo_ajustado.py
```

Las salidas se generan en `./salidas_ajuste/`.
