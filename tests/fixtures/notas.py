"""Notas clínicas de referencia para suites de prueba (TC-API, TC-UI, TC-EVAL)."""
from __future__ import annotations

NOTA_LIMPIA = (
    "Paciente de 45 años acude por control periodontal rutinario. "
    "Examen: encías rosadas, sin sangrado al sondaje. "
    "Plan: profilaxis y control en 6 meses."
)

NOTA_MEDICACION = (
    "Paciente refiere dolor en molar 36 desde hace 3 días. "
    "Antecedentes: alergia documentada a penicilina. "
    "Se indica amoxicilina 500 mg cada 8 h pese a alergia documentada a penicilina."
)

NOTA_PLAN = (
    "Paciente con gingivitis leve confirmada en examen clínico. "
    "Encías levemente inflamadas, sin movilidad dental. "
    "Diagnóstico: gingivitis leve; plan: extracción de todas las piezas."
)

NOTA_LARGA = ". ".join(
    [f"Oracion numero {i} sin inconsistencia aparente" for i in range(1, 23)]
) + "."

NOTAS_IDIOMA = {
    "es_medicacion": (
        "Paciente refiere dolor en molar 36. "
        "Antecedentes: alergia documentada a penicilina. "
        "Se indica amoxicilina 500 mg cada 8 h."
    ),
    "en_medicacion": (
        "Patient reports pain in tooth 36 for 3 days. "
        "History: documented allergy to penicillin. "
        "Amoxicillin 500 mg every 8 hours is prescribed."
    ),
    "es_limpia": NOTA_LIMPIA,
    "en_limpia": (
        "45-year-old patient presents for routine periodontal checkup. "
        "Exam: pink gums, no bleeding on probing. "
        "Plan: prophylaxis and follow-up in 6 months."
    ),
}
