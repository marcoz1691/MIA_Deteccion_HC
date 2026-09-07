"""Pruebas rápidas de las reglas: python -m pytest pruebas/ -q   (o python pruebas/test_deteccion.py)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from anonimizador_ocr.deteccion import cedula_valida, detectar  # noqa: E402


def etiquetas(texto, **kw):
    return {(h.etiqueta, h.texto) for h in detectar(texto, usar_ner=False, **kw)}


def test_cedula():
    assert cedula_valida("1712345675")
    assert not cedula_valida("1712345678")
    assert not cedula_valida("2512345675")   # provincia 25 no existe


def test_cedula_con_confusion_ocr():
    assert ("CEDULA", "17l234567S") in etiquetas("CI 17l234567S del paciente")


def test_telefono_y_email_ocr():
    e = etiquetas("cel. 099 876 5432, correo rosa.q680gmail.com")
    assert any(x[0].startswith("TELEFONO") or "TELEFONO" in x[0] for x in e)
    assert ("EMAIL", "rosa.q680gmail.com") in e


def test_hc_solo_numero():
    assert ("HC", "0045871") in etiquetas("Historia Clínica N°: 0045871.")


def test_fechas():
    t = "Fecha de nacimiento: 14/03/1968. Consulta: 22/08/2026"
    assert etiquetas(t) == {("FECHA", "14/03/1968")}
    assert ("FECHA", "22/08/2026") in etiquetas(t, fechas="todas")
    assert not any(x[0] == "FECHA" for x in etiquetas(t, fechas="ninguna"))


def test_nombre_contexto_no_cruza_linea():
    e = etiquetas("Paciente: Rosa Elena Quishpe\nCédula: 1712345675")
    assert ("NOMBRE", "Rosa Elena Quishpe") in e


def test_paciente_masculino_no_es_nombre():
    texto = (
        "PACIENTE MASCULINO CON ANTECEDENTE DE METAPLASIA GÁSTRICA. "
        "PACIENTE ACUDE PARA PROCEDIMIENTO PROGRAMADO. "
        "PACIENTE CONSCIENTE ORIENTADO EN TIEMPO Y ESPACIO."
    )
    assert not any(et == "NOMBRE" for et, _ in etiquetas(texto))


def test_apf_familiar_no_es_nombre():
    texto = (
        "APF:(ANTECEDENTES PATOLÓGICOS FAMILIARES):\n"
        "ABUELO MATERNO: CÁNCER PRÓSTATA\n"
        "ABUELA MATERNA: CANCER ESTOMAGO"
    )
    assert not any(et == "NOMBRE" for et, _ in etiquetas(texto))


def test_nombre_no_se_traga_el_resto_clinico():
    e = etiquetas("PACIENTE: ROSA ELENA QUISHPE REFIERE DOLOR EN PIE IZQUIERDO")
    nombres = {txt for et, txt in e if et == "NOMBRE"}
    assert "ROSA ELENA QUISHPE" in nombres
    assert not any("REFIERE" in n or "DOLOR" in n for n in nombres)


def test_nombre_tras_doctor_se_detecta():
    e = etiquetas("CONTROL POR CONSULTA EXTERNA DR. JUAN PEREZ")
    assert ("NOMBRE", "JUAN PEREZ") in e


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("ok", n)
