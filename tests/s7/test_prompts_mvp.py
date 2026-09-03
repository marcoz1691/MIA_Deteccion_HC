"""El detector MVP usa el modelo (prompt + nota completa), no reglas que fuerzan el score."""
from __future__ import annotations

from s7.prompts import get_prompt


NOTA_SEXO = (
    "NOTA DE INGRESO. PACIENTE MASCULINO DE 39 AÑOS. "
    "ENFERMEDAD ACTUAL: PACIENTE FEMENINO CON ANTECEDENTE DE METAPLASIA GASTRICA."
)
ORACION = "PACIENTE FEMENINO CON ANTECEDENTE DE METAPLASIA GASTRICA."


def test_prompt_incluye_la_nota_completa():
    prompt = get_prompt("zero_shot", "spanish", ORACION, nota=NOTA_SEXO)
    assert "PACIENTE MASCULINO" in prompt
    assert ORACION in prompt


def test_prompt_mvp_pide_ejes_de_alto_nivel():
    prompt = get_prompt("zero_shot", "spanish", ORACION, nota=NOTA_SEXO)
    bajo = prompt.lower()
    for eje in ("lateralidad", "sexo", "alerg", "edad"):
        assert eje in bajo, eje
    assert "título" in bajo or "subtitulo" in bajo or "subtítulo" in bajo


def test_prompt_no_marca_medicamentos_ni_motivo_de_consulta():
    """Omeprazol suspendido para el procedimiento y el motivo de consulta no son SI."""
    prompt = get_prompt(
        "zero_shot",
        "spanish",
        "ACUDE PARA VALORACIÓN, CONTROL ENDOSCOPICO Y SEGUIMIENTO DE SU PATOLOGÍA GÁSTRICA.",
        nota="MANTIENE TRATAMIENTO HABITUAL CON OMEPRAZOL. ACUDE PARA CONTROL ENDOSCOPICO.",
    )
    bajo = prompt.lower()
    assert "omeprazol" in bajo or "medicament" in bajo
    assert "suspend" in bajo
    assert "seguimiento" in bajo or "control endosc" in bajo
    assert "motivo de consulta" in bajo or "no marques si por motivo" in bajo


def test_prompt_rag_tambien_lleva_nota_y_ejes():
    prompt = get_prompt(
        "rag",
        "spanish",
        ORACION,
        contexto="Alergia a penicilina contraindica aminopenicilinas.",
        nota=NOTA_SEXO,
    )
    assert "PACIENTE MASCULINO" in prompt
    assert "lateralidad" in prompt.lower()
    assert "penicilina" in prompt.lower()


def test_prompt_no_pide_juicio_clinico_fuera_de_ejes_mvp():
    """Alta vs tolerancia oral no es un eje MVP; el prompt debe excluirlo."""
    oracion = (
        "SIN TOLERANCIA ORAL A LÍQUIDOS, EN CONDICIONES DE ALTA TRAS VALORACIÓN MÉDICA."
    )
    prompt = get_prompt("zero_shot", "spanish", oracion, nota=oracion)
    bajo = prompt.lower()
    assert "tolerancia oral" in bajo
    assert "alta" in bajo
    assert "práctica estándar" not in bajo
    assert "practica estandar" not in bajo.replace("á", "a")


def test_prompt_lateralidad_contrasta_diagnostico_con_examen():
    """Pie derecho vs mano derecha o pie izquierdo es el caso a marcar."""
    prompt = get_prompt(
        "zero_shot",
        "spanish",
        "EXAMEN FISICO: MANO DERECHA SIN DEFORMIDAD.",
        nota="DIAGNOSTICO: FRACTURA DE PIE DERECHO. EXAMEN FISICO: MANO DERECHA SIN DEFORMIDAD.",
    )
    bajo = prompt.lower()
    assert "diagnóstico" in bajo or "diagnostico" in bajo
    assert "examen" in bajo
    assert "pie" in bajo
    assert "mano" in bajo
    assert "derecho/izquierdo" in bajo or "derecho / izquierdo" in bajo


def test_prompt_lateralidad_mismo_lado_hallazgos_opuestos():
    """Mismo izquierdo: nódulo vs sin lesiones focales también es SI."""
    prompt = get_prompt(
        "zero_shot",
        "spanish",
        "NO SE EVIDENCIAN LESIONES FOCALES EN EL LOBULO TIROIDEO IZQUIERDO.",
        nota=(
            "SE IDENTIFICA EN EL LOBULO TIROIDEO IZQUIERDO UN NODULO SOLIDO. "
            "NO SE EVIDENCIAN LESIONES FOCALES EN EL LOBULO TIROIDEO IZQUIERDO."
        ),
    )
    bajo = prompt.lower()
    assert "nódulo" in bajo or "nodulo" in bajo
    assert "lesiones" in bajo
    assert "mismo lado" in bajo or "misma later" in bajo or "mismo sitio" in bajo
