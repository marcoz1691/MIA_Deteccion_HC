"""HTTP: GET /muestras-pdf y POST /extraer-pdf."""
from __future__ import annotations

import pytest

fitz = pytest.importorskip("fitz")

from api import pdf_extract


def _pdf_bytes(textos: list[str]) -> bytes:
    doc = fitz.open()
    for texto in textos:
        page = doc.new_page()
        if texto:
            page.insert_text((72, 72), texto)
    data = doc.tobytes()
    doc.close()
    return data


CLINICA = (
    "Paciente refiere dolor persistente en molar treinta y seis desde hace tres dias."
)


@pytest.mark.regression
def test_muestras_pdf_lista_anon(client, tmp_path, monkeypatch):
    buscable = tmp_path / "salidas_buscable"
    buscable.mkdir()
    (buscable / "hc0001_anon.pdf").write_bytes(_pdf_bytes([CLINICA]))
    (tmp_path / "salidas").mkdir()
    monkeypatch.setattr(pdf_extract, "ANON_ROOT", tmp_path)

    resp = client.get("/muestras-pdf")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["muestras"]) == 1
    assert data["muestras"][0]["id"] == "salidas_buscable/hc0001_anon.pdf"


@pytest.mark.regression
def test_extraer_pdf_path_traversal_404(client):
    resp = client.post(
        "/extraer-pdf",
        json={"muestra_id": "../historias/hc0001.pdf"},
    )
    assert resp.status_code == 404


@pytest.mark.regression
def test_extraer_pdf_sin_texto_400(client):
    doc = fitz.open()
    doc.new_page()
    vacio = doc.tobytes()
    doc.close()
    resp = client.post(
        "/extraer-pdf",
        files={"archivo": ("escaneado.pdf", vacio, "application/pdf")},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"].lower()
    assert "buscable" in detail or "texto extraíble" in detail or "texto extraible" in detail


@pytest.mark.regression
def test_extraer_pdf_upload_ok(client):
    data = _pdf_bytes([CLINICA])
    resp = client.post(
        "/extraer-pdf",
        files={"archivo": ("nota_anon.pdf", data, "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert CLINICA in body["texto"]
    assert body["n_oraciones_utiles"] >= 1
    assert body["origen"] == "nota_anon.pdf"


@pytest.mark.regression
def test_extraer_pdf_muestra_id(client, tmp_path, monkeypatch):
    buscable = tmp_path / "salidas_buscable"
    buscable.mkdir()
    (buscable / "hc0001_anon.pdf").write_bytes(_pdf_bytes([CLINICA]))
    monkeypatch.setattr(pdf_extract, "ANON_ROOT", tmp_path)

    resp = client.post(
        "/extraer-pdf",
        json={"muestra_id": "salidas_buscable/hc0001_anon.pdf"},
    )
    assert resp.status_code == 200
    assert CLINICA in resp.json()["texto"]
