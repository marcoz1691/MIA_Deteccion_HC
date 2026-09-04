"""Extracción estructurada de historias clínicas (POST /extraer-pdf-estructurado)."""
from __future__ import annotations

import pytest

fitz = pytest.importorskip("fitz")

from api import pdf_estructura
from api.pdf_extract import PdfExtractError


def _pdf_con_texto(paginas: list[str]) -> bytes:
    doc = fitz.open()
    for texto in paginas:
        page = doc.new_page()
        if texto:
            page.insert_text((72, 72), texto)
    data = doc.tobytes()
    doc.close()
    return data


def _pdf_escaneado(n: int = 1) -> bytes:
    doc = fitz.open()
    for _ in range(n):
        doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


CRUDO_VISION = {
    "entries": [
        {
            "evolucion_n": 1,
            "fecha": "2026-07-06",
            "hora": "11:31",
            "notas_evolucion": (
                "PROCEDIMIENTO REALIZADO: ENDOSCOPIA DIGESTIVA ALTA\n"
                "SIGNOS VITALES: SATO2: 90 AIRE AMBIENTE, TEMP: 36.5\n"
                "La cedula 1712345678 aparece en la nota."
            ),
            "ordenes_medicas": [
                "CONTROL DE SIGNOS VITALES PREVIO AL ALTA",
                "CONTROL EN CONSULTA EXTERNA CON RESULTADOS DE BIOPSIA",
            ],
        },
        {"evolucion_n": 2, "notas_evolucion": "", "ordenes_medicas": []},
    ],
    "paginas_sin_contenido": [3],
}


NOTA_INGRESO = """\
**** NOTA DE INGRESO *****
PACIENTE MASCULINO DE 39 AÑOS, EMPLEADO PÚBLICO, RELIGIÓN CATÓLICA.
APP: NO REFIERE
APF:(ANTECEDENTES PATOLÓGICOS FAMILIARES):
ABUELO MATERNO: CÁNCER PRÓSTATA
ABUELA MATERNA: CANCER ESTOMAGO
ENFERMEDAD ACTUAL:
PACIENTE MASCULINO CON ANTECEDENTE DE METAPLASIA GÁSTRICA DIAGNOSTICADA HACE UN AÑO Y MEDIO.
SIGNOS VITALES: PA: 120/77 FC: 82 SAT: 92 FR: 18 T: 36.5
PACIENTE CONSCIENTE, ORIENTADO EN TIEMPO Y ESPACIO.
CABEZA NORMACTIVA A LA LUZ Y ACOMODACIÓN
ANÁLISIS:
PACIENTE MASCULINO ACUDE PARA PROCEDIMIENTO PROGRAMADO, HEMODINÁMICAMENTE ESTABLE.
"""


def test_vision_estructura_entries_y_texto_plano():
    res = pdf_estructura.extraer_estructurado(
        _pdf_escaneado(),
        origen="hc_anon.pdf",
        transcriptor=lambda imgs: CRUDO_VISION,
        tiene_identificador=lambda t: "1712345678" in t,
    )
    assert res["motor"] == "vision"
    assert len(res["entries"]) == 1  # la entrada vacía se descarta
    e = res["entries"][0]
    assert e["fecha"] == "2026-07-06" and e["hora"] == "11:31"
    assert "SATO2: 90" in e["notas_evolucion"]
    assert "1712345678" not in e["notas_evolucion"]
    assert "[dato omitido]" in e["notas_evolucion"]
    assert len(e["ordenes_medicas"]) == 2
    assert "--- EVOLUCIÓN 1 ---" in res["texto_plano"]
    assert "ORDENES MEDICAS GENERALES:" in res["texto_plano"]
    assert res["paginas_sin_contenido"] == [3]


def test_vision_renumera_correlativo():
    crudo = {"entries": [
        {"evolucion_n": 7, "notas_evolucion": "nota uno", "ordenes_medicas": []},
        {"evolucion_n": 9, "notas_evolucion": "nota dos", "ordenes_medicas": []},
    ]}
    res = pdf_estructura.extraer_estructurado(
        _pdf_escaneado(), origen="x.pdf", transcriptor=lambda imgs: crudo,
        tiene_identificador=lambda t: False,
    )
    assert [e["evolucion_n"] for e in res["entries"]] == [1, 2]


def test_fecha_hora_invalidas_se_descartan():
    crudo = {"entries": [
        {"evolucion_n": 1, "fecha": "ayer", "hora": "25:99",
         "notas_evolucion": "algo", "ordenes_medicas": []},
    ]}
    res = pdf_estructura.extraer_estructurado(
        _pdf_escaneado(), origen="x.pdf", transcriptor=lambda imgs: crudo,
        tiene_identificador=lambda t: False,
    )
    assert res["entries"][0]["fecha"] is None
    assert res["entries"][0]["hora"] is None


def test_tope_de_paginas_avisa():
    crudo = {"entries": [{"evolucion_n": 1, "notas_evolucion": "n", "ordenes_medicas": []}]}
    capturado = {}

    def _t(imgs):
        capturado["n"] = len(imgs)
        return crudo

    res = pdf_estructura.extraer_estructurado(
        _pdf_escaneado(n=20), origen="x.pdf", transcriptor=_t,
        tiene_identificador=lambda t: False, max_paginas=3,
    )
    assert capturado["n"] == 3
    assert "3 de 20" in res["aviso"]


def test_sin_entradas_lanza_422():
    with pytest.raises(PdfExtractError) as exc:
        pdf_estructura.extraer_estructurado(
            _pdf_escaneado(), origen="x.pdf",
            transcriptor=lambda imgs: {"entries": []},
            tiene_identificador=lambda t: False,
        )
    assert exc.value.status == 422


def test_pdf_invalido_lanza_400():
    with pytest.raises(PdfExtractError) as exc:
        pdf_estructura.extraer_estructurado(
            b"no soy un pdf", origen="x.pdf", transcriptor=lambda imgs: CRUDO_VISION,
        )
    assert exc.value.status == 400


def test_fallback_capa_texto_sin_vision():
    frase = "Paciente refiere dolor persistente en molar treinta y seis desde hace tres dias."
    res = pdf_estructura.extraer_estructurado(
        _pdf_con_texto([frase]), origen="buscable.pdf",
        transcriptor=None, tiene_identificador=lambda t: False,
    )
    assert res["motor"] == "capa_texto"
    assert frase in res["entries"][0]["notas_evolucion"]
    assert "no se separan" in res["aviso"]


@pytest.mark.regression
def test_endpoint_estructurado_fallback(client):
    frase = "Paciente refiere dolor persistente en molar treinta y seis desde hace tres dias."
    resp = client.post(
        "/extraer-pdf-estructurado",
        files={"archivo": ("nota_anon.pdf", _pdf_con_texto([frase]), "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["motor"] == "capa_texto"
    assert body["origen"] == "nota_anon.pdf"
    assert "--- EVOLUCIÓN 1 ---" in body["texto_plano"]


@pytest.mark.regression
def test_endpoint_estructurado_escaneado_sin_motor_422(client, monkeypatch):
    monkeypatch.setattr(
        pdf_estructura, "_crudo_desde_ocr",
        lambda *a, **k: (_ for _ in ()).throw(PdfExtractError("sin motor", 422)),
    )
    resp = client.post(
        "/extraer-pdf-estructurado",
        files={"archivo": ("escaneado.pdf", _pdf_escaneado(), "application/pdf")},
    )
    assert resp.status_code == 422


def test_no_omite_bloques_clinicos_de_ingreso():
    """Religión, profesión, APF, enfermedad actual, signos y análisis no se tapan."""
    crudo = {
        "entries": [
            {
                "evolucion_n": 1,
                "fecha": "2026-07-06",
                "hora": "09:06",
                "notas_evolucion": NOTA_INGRESO,
                "ordenes_medicas": ["NPO", "CONTROL DE SIGNOS VITALES"],
            },
            {
                "evolucion_n": 2,
                "fecha": "2026-07-06",
                "hora": "10:15",
                "notas_evolucion": (
                    "ANÁLISIS:\n"
                    "PACIENTE MASCULINO ACUDE PARA PROCEDIMIENTO PROGRAMADO, "
                    "HEMODINÁMICAMENTE ESTABLE, FIRMA CONSENTIMIENTO INFORMADO."
                ),
                "ordenes_medicas": [],
            },
            {
                "evolucion_n": 3,
                "fecha": "2026-07-06",
                "hora": "11:31",
                "notas_evolucion": (
                    "NOTA DE ALTA\n"
                    "ANÁLISIS:\n"
                    "PACIENTE MASCULINO EN CONDICIONES DE ALTA TRAS VALORACIÓN MÉDICA."
                ),
                "ordenes_medicas": ["RETIRO DE VIA PERIFERICA"],
            },
        ]
    }
    res = pdf_estructura.extraer_estructurado(
        _pdf_escaneado(),
        origen="hc.pdf",
        transcriptor=lambda imgs: crudo,
    )
    plano = res["texto_plano"]
    assert "[dato omitido]" not in plano
    assert "RELIGIÓN CATÓLICA" in plano
    assert "EMPLEADO PÚBLICO" in plano
    assert "APF:(ANTECEDENTES PATOLÓGICOS FAMILIARES)" in plano
    assert "ABUELO MATERNO: CÁNCER PRÓSTATA" in plano
    assert "ENFERMEDAD ACTUAL:" in plano
    assert "METAPLASIA GÁSTRICA" in plano
    assert "SAT: 92" in plano
    assert "CABEZA NORMACTIVA" in plano
    assert plano.count("ANÁLISIS:") == 3
    assert "EVOLUCIÓN 2" in plano and "EVOLUCIÓN 3" in plano
    assert "CONDICIONES DE ALTA" in plano


def test_nota_cortada_en_preposicion_marca_corte_y_avisa():
    """Columna izquierda que muere en el pie ('MOLESTIAS AL') no se da por completa."""
    crudo = {
        "entries": [
            {
                "evolucion_n": 1,
                "fecha": "2026-08-24",
                "hora": "23:30",
                "notas_evolucion": (
                    "IMPRESIONES DIAGNÓSTICAS:\n"
                    "MATERIAL DE OSTEOSINTESIS EN PIE IZQUIERDO\n"
                    "SUBJETIVO:\n"
                    "PACIENTE NO REFIERE DOLOR NI MOLESTIAS AL"
                ),
                "ordenes_medicas": [
                    "ALTA MEDICA",
                    "RETIRO DE VÍA PERIFÉRICA",
                    "CERTIFICADO MÉDICO DE REPOSO 8 DÍAS",
                ],
            }
        ],
        "paginas_sin_contenido": [],
    }
    res = pdf_estructura.extraer_estructurado(
        _pdf_escaneado(n=3),
        origen="hc_citimed.pdf",
        transcriptor=lambda imgs: crudo,
        tiene_identificador=lambda t: False,
    )
    notas = res["entries"][0]["notas_evolucion"]
    assert notas.rstrip().endswith("[corte]")
    assert "MOLESTIAS AL" in notas
    assert res["aviso"]
    assert "media frase" in res["aviso"].lower() or "hoja siguiente" in res["aviso"].lower()
    assert "ALTA MEDICA" in res["texto_plano"]


def test_nota_completa_no_marca_corte_ni_aviso_de_salto():
    crudo = {
        "entries": [
            {
                "evolucion_n": 1,
                "notas_evolucion": (
                    "ANÁLISIS:\n"
                    "PACIENTE EN CONDICIONES DE ALTA TRAS VALORACIÓN MÉDICA."
                ),
                "ordenes_medicas": ["ALTA MEDICA"],
            }
        ]
    }
    res = pdf_estructura.extraer_estructurado(
        _pdf_escaneado(n=3),
        origen="hc.pdf",
        transcriptor=lambda imgs: crudo,
        tiene_identificador=lambda t: False,
    )
    assert not res["entries"][0]["notas_evolucion"].endswith("[corte]")
    assert res["aviso"] is None or "media frase" not in res["aviso"].lower()


def test_cedula_se_redacta_sin_borrar_el_resto_de_la_nota():
    crudo = {
        "entries": [
            {
                "evolucion_n": 1,
                "notas_evolucion": (
                    "ENFERMEDAD ACTUAL: PACIENTE MASCULINO CON METAPLASIA GÁSTRICA. "
                    "CI 1712345678 en la nota."
                ),
                "ordenes_medicas": [],
            }
        ]
    }
    res = pdf_estructura.extraer_estructurado(
        _pdf_escaneado(),
        origen="hc.pdf",
        transcriptor=lambda imgs: crudo,
        tiene_identificador=lambda t: "1712345678" in t,
    )
    notas = res["entries"][0]["notas_evolucion"]
    assert "1712345678" not in notas
    assert "[dato omitido]" in notas
    assert "METAPLASIA GÁSTRICA" in notas
    assert "ENFERMEDAD ACTUAL:" in notas


def test_nombres_y_apellidos_nunca_quedan_en_claro():
    crudo = {
        "entries": [
            {
                "evolucion_n": 1,
                "notas_evolucion": (
                    "PACIENTE: ROSA ELENA QUISHPE REFIERE DOLOR EN PIE IZQUIERDO.\n"
                    "PACIENTE MASCULINO CON METAPLASIA GÁSTRICA."
                ),
                "ordenes_medicas": [
                    "CONTROL POR CONSULTA EXTERNA DR. JUAN PEREZ",
                    "ALTA MEDICA",
                ],
            }
        ]
    }
    res = pdf_estructura.extraer_estructurado(
        _pdf_escaneado(),
        origen="hc.pdf",
        transcriptor=lambda imgs: crudo,
        tiene_identificador=lambda t: False,
    )
    plano = res["texto_plano"]
    assert "ROSA ELENA QUISHPE" not in plano
    assert "JUAN PEREZ" not in plano
    assert "[dato omitido]" in plano
    assert "REFIERE DOLOR EN PIE IZQUIERDO" in plano
    assert "METAPLASIA GÁSTRICA" in plano
    assert "ALTA MEDICA" in plano
    assert "CONTROL POR CONSULTA EXTERNA DR." in plano
