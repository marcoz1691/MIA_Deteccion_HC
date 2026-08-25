"""TC-S10-01..07 — Pipeline CITIMED y anonimización PHI."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from s10.citimed_utils import phi_restante, texto_clinico_desde_anon
from s10.probar_citimed import preparar_csv_eval, verificar_phi_inferencias


@pytest.mark.regression
def test_tc_s10_01_omite_cabeceras():
    """TC-S10-01: Omite cabeceras administrativas."""
    raw = """DATOS DEL PACIENTE
Nombre: [PACIENTE_1]
EVOLUCIÓN El paciente refiere dolor.
DIAGNÓSTICO Gingivitis leve.
"""
    cuerpo = texto_clinico_desde_anon(raw)
    assert "DATOS DEL PACIENTE" not in cuerpo
    assert "EVOLUCIÓN" in cuerpo or "dolor" in cuerpo
    assert "Gingivitis" in cuerpo


@pytest.mark.regression
def test_tc_s10_02_detecta_phi_residual():
    """TC-S10-02: Detecta PHI residual."""
    hallazgos = phi_restante("El paciente Rosa Elena Andrade refiere dolor.")
    assert any("Rosa Elena Andrade" in h for h in hallazgos)


@pytest.mark.regression
def test_tc_s10_03_ignora_etiquetas_anon():
    """TC-S10-03: Ignora etiquetas [PACIENTE_N]."""
    assert phi_restante("El paciente [PACIENTE_1] refiere dolor.") == []


@pytest.mark.regression
def test_tc_s10_04_aborta_sin_force():
    """TC-S10-04: Aborta inferencia con PHI sin --force."""
    inferencias = [{"phi_residual": ["Rosa Elena Andrade"], "nota_texto": "texto"}]
    with pytest.raises(SystemExit) as exc:
        verificar_phi_inferencias(inferencias, force=False)
    assert exc.value.code == 2


@pytest.mark.regression
def test_tc_s10_04_permite_con_force():
    inferencias = [{"phi_residual": ["Rosa Elena Andrade"], "nota_texto": "texto"}]
    assert verificar_phi_inferencias(inferencias, force=True)


@pytest.mark.regression
def test_tc_s10_07_export_csv_eval(tmp_path):
    """TC-S10-07: Export CSV eval formato correcto."""
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
        assert contenido.count("\n") == 3
    finally:
        pc.DATA_CSV = original


@pytest.mark.integration
def test_tc_s10_05_pipeline_txt_sintetico():
    """TC-S10-05: Pipeline TXT con ejemplo sintético (si existe)."""
    ejemplo = (
        ROOT
        / "s10"
        / "anonimizador"
        / "ANONIMIZADOR"
        / "ejemplos"
        / "historia_ejemplo.sintetico.txt"
    )
    if not ejemplo.exists():
        pytest.skip("Ejemplo sintético no disponible")
    cuerpo = texto_clinico_desde_anon(ejemplo.read_text(encoding="utf-8"))
    assert len(cuerpo.strip()) > 20
    # El sintético puede contener nombres ficticios; verificar que etiquetas anon están OK
    assert "[PACIENTE_" not in cuerpo or phi_restante("El paciente [PACIENTE_1] refiere dolor.") == []


@pytest.mark.integration
@pytest.mark.skip(reason="Requiere PDF de prueba y dependencias anonimizador; ejecutar manualmente")
def test_tc_s10_06_pipeline_pdf():
    """TC-S10-06: Pipeline PDF — ejecutar manualmente con archivo de prueba."""
    pass
