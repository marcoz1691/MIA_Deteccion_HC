"""Extracción de PDF clínico filtrado (capa de texto, sin OCR)."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

fitz = pytest.importorskip("fitz")

from api import pdf_extract


def _pdf_bytes(paginas: list[str]) -> bytes:
    doc = fitz.open()
    for texto in paginas:
        page = doc.new_page()
        if texto:
            page.insert_text((72, 72), texto)
    data = doc.tobytes()
    doc.close()
    return data


def _pdf_vacio() -> bytes:
    doc = fitz.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


CLINICA_1 = (
    "Paciente refiere dolor persistente en molar treinta y seis desde hace tres dias."
)
CLINICA_2 = (
    "Se indica amoxicilina quinientos miligramos cada ocho horas pese a alergia documentada."
)
RUIDO = "----------\nHC:\nNombre:"
CON_CEDULA = (
    "El registro consigna la cedula 1712345678 del titular de la historia clinica."
)


def test_extrae_oraciones_utiles_y_omite_ruido_e_identificador():
    data = _pdf_bytes([RUIDO, CLINICA_1, CON_CEDULA, CLINICA_2])
    resultado = pdf_extract.extraer_de_bytes(
        data,
        origen="prueba_anon.pdf",
        tiene_identificador=lambda t: "1712345678" in t,
    )
    assert CLINICA_1 in resultado["texto"]
    assert CLINICA_2 in resultado["texto"]
    assert "1712345678" not in resultado["texto"]
    assert "----------" not in resultado["texto"]
    assert resultado["n_oraciones_utiles"] == 2
    assert resultado["n_omitidas_identificadores"] == 1
    assert resultado["n_omitidas_ruido"] >= 1
    assert resultado["origen"] == "prueba_anon.pdf"
    assert resultado["n_paginas"] == 4


def test_pdf_sin_capa_de_texto_lanza_400():
    with pytest.raises(pdf_extract.PdfExtractError) as exc:
        pdf_extract.extraer_de_bytes(_pdf_vacio(), origen="escaneado.pdf")
    assert exc.value.status == 400
    assert "texto extraíble" in str(exc.value).lower() or "buscable" in str(exc.value).lower()


def test_bytes_que_no_son_pdf_lanzan_400():
    with pytest.raises(pdf_extract.PdfExtractError) as exc:
        pdf_extract.extraer_de_bytes(b"esto no es un pdf", origen="nota.txt")
    assert exc.value.status == 400


def test_archivo_grande_lanza_413():
    with pytest.raises(pdf_extract.PdfExtractError) as exc:
        pdf_extract.extraer_de_bytes(
            b"%PDF" + b"x" * (pdf_extract.MAX_BYTES + 1),
            origen="grande.pdf",
        )
    assert exc.value.status == 413


def test_tope_de_oraciones():
    oraciones = [
        f"Paciente acude a control periodontal rutinario numero {i:02d} en consulta."
        for i in range(pdf_extract.MAX_ORACIONES_PDF + 5)
    ]
    data = _pdf_bytes(oraciones)
    resultado = pdf_extract.extraer_de_bytes(data, origen="largo.pdf")
    assert resultado["n_oraciones_utiles"] == pdf_extract.MAX_ORACIONES_PDF
    assert resultado["n_truncadas"] == 5


def test_resolver_muestra_bloquea_path_traversal(tmp_path, monkeypatch):
    salidas = tmp_path / "salidas_buscable"
    salidas.mkdir()
    (salidas / "hc0001_anon.pdf").write_bytes(_pdf_bytes([CLINICA_1]))
    historias = tmp_path / "historias"
    historias.mkdir()
    (historias / "hc0001.pdf").write_bytes(_pdf_bytes([CON_CEDULA]))
    monkeypatch.setattr(pdf_extract, "ANON_ROOT", tmp_path)

    with pytest.raises(pdf_extract.PdfExtractError) as exc:
        pdf_extract.resolver_muestra("../historias/hc0001.pdf")
    assert exc.value.status == 404

    with pytest.raises(pdf_extract.PdfExtractError) as exc2:
        pdf_extract.resolver_muestra("historias/hc0001.pdf")
    assert exc2.value.status == 404

    ruta = pdf_extract.resolver_muestra("salidas_buscable/hc0001_anon.pdf")
    assert ruta.name == "hc0001_anon.pdf"


def test_listar_muestras_solo_anon_pdf(tmp_path, monkeypatch):
    buscable = tmp_path / "salidas_buscable"
    buscable.mkdir()
    (buscable / "hc0001_anon.pdf").write_bytes(_pdf_bytes([CLINICA_1, CLINICA_2]))
    (buscable / "informe.json").write_text("{}")
    (tmp_path / "salidas").mkdir()
    monkeypatch.setattr(pdf_extract, "ANON_ROOT", tmp_path)

    muestras = pdf_extract.listar_muestras()
    assert len(muestras) == 1
    assert muestras[0]["id"] == "salidas_buscable/hc0001_anon.pdf"
    assert muestras[0]["nombre"] == "hc0001_anon.pdf"
    assert muestras[0]["n_paginas"] == 2


def test_listar_omite_pdf_sin_capa_de_texto(tmp_path, monkeypatch):
    salidas = tmp_path / "salidas"
    salidas.mkdir()
    (salidas / "hc0001_anon.pdf").write_bytes(_pdf_vacio())
    buscable = tmp_path / "salidas_buscable"
    buscable.mkdir()
    (buscable / "hc0001_anon.pdf").write_bytes(_pdf_bytes([CLINICA_1]))
    monkeypatch.setattr(pdf_extract, "ANON_ROOT", tmp_path)

    muestras = pdf_extract.listar_muestras()
    assert [m["id"] for m in muestras] == ["salidas_buscable/hc0001_anon.pdf"]
