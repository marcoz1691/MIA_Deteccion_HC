"""Tests del pipeline CITIMED (utilidades y seguridad PHI)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from s10.citimed_utils import phi_restante, texto_clinico_desde_anon
from s10.probar_citimed import preparar_csv_eval, verificar_phi_inferencias


def test_texto_clinico_omite_cabeceras_administrativas():
    raw = """DATOS DEL PACIENTE
Nombre: [PACIENTE_1]
EVOLUCIÓN El paciente refiere dolor.
DIAGNÓSTICO Gingivitis leve.
"""
    cuerpo = texto_clinico_desde_anon(raw)
    assert "DATOS DEL PACIENTE" not in cuerpo
    assert "EVOLUCIÓN" in cuerpo or "dolor" in cuerpo
    assert "Gingivitis" in cuerpo


def test_phi_restante_detecta_nombre_no_anonimizado():
    hallazgos = phi_restante("El paciente Rosa Elena Andrade refiere dolor.")
    assert any("Rosa Elena Andrade" in h for h in hallazgos)


def test_phi_restante_ignora_etiquetas_anon():
    assert phi_restante("El paciente [PACIENTE_1] refiere dolor.") == []


def test_verificar_phi_aborta_sin_force():
    inferencias = [{"phi_residual": ["Rosa Elena Andrade"], "nota_texto": "texto"}]
    with pytest.raises(SystemExit) as exc:
        verificar_phi_inferencias(inferencias, force=False)
    assert exc.value.code == 2


def test_verificar_phi_permite_con_force():
    inferencias = [{"phi_residual": ["Rosa Elena Andrade"], "nota_texto": "texto"}]
    assert verificar_phi_inferencias(inferencias, force=True)


def test_preparar_csv_solo_plantilla_etiquetada(tmp_path):
    ejemplo = tmp_path / "ejemplo.csv"
    ejemplo.write_text(
        "oracion,label,nota_id,oracion_id,error_type\n"
        '"Oración A",0,1,0,\n'
        '"Oración B",1,1,1,Medication\n',
        encoding="utf-8",
    )
    dest = tmp_path / "citimed.csv"
    import s10.probar_citimed as pc

    original = pc.DATA_CSV
    pc.DATA_CSV = dest
    try:
        out = preparar_csv_eval(ejemplo)
        assert out == dest
        contenido = dest.read_text(encoding="utf-8")
        assert "Oración B" in contenido
        assert contenido.count("\n") == 3  # header + 2 filas
    finally:
        pc.DATA_CSV = original
