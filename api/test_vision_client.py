"""Parseo de la respuesta del modelo de visión."""
from __future__ import annotations

import pytest

from api import vision_client


def test_parse_json_directo():
    data = vision_client._parse_json('{"entries": [{"evolucion_n": 1}]}')
    assert data["entries"][0]["evolucion_n"] == 1
    assert data["paginas_sin_contenido"] == []


def test_parse_json_con_fence():
    data = vision_client._parse_json('```json\n{"entries": []}\n```')
    assert data["entries"] == []


def test_parse_json_invalido():
    with pytest.raises(ValueError):
        vision_client._parse_json("lo siento, no puedo")


def test_transcriptor_openai_sin_clave(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    with pytest.raises(vision_client.VisionUnavailableError):
        vision_client.transcriptor_openai()


def test_data_uri_prefijo():
    assert vision_client._data_uri(b"\x89PNG").startswith("data:image/png;base64,")


def test_prompt_no_omite_hoja_hospitalaria_ni_corte_de_pagina():
    """Regresión: PDF de 2 columnas + hoja hospitalaria siguiente.

    El modelo cerraba la evolución en 'MOLESTIAS AL' (pie de página 2) y
    descartaba la hoja EVOLUCION-HOSPITALARIA con OBJETIVO/EXAMEN/ANÁLISIS.
    """
    system = vision_client.SYSTEM_PROMPT
    user = vision_client.USER_PROMPT
    pagina = vision_client.USER_PROMPT_PAGINA
    assert "MOLESTIAS AL" in system or "media frase" in system.lower() or "mitad de frase" in system.lower()
    assert "tabla" in system.lower() or "EVOLUCION - HOSPITALARIA" in system
    assert "paginas_sin_contenido" in system
    assert "OBJETIVO" in system and "EXAMEN FISICO" in system
    assert "no descartes" in system.lower() or "no la descartes" in user.lower() or "Nunca marques" in system
    assert "{n}" in user
    assert "CADA" in user or "cada imagen" in user.lower() or "todas las páginas" in user.lower()
    assert "una sola página" in pagina.lower()
    assert "no la descartes" in pagina.lower()
    assert "nombres" in system.lower() and "apellidos" in system.lower()
    assert "[dato omitido]" in system


def test_transcribir_por_pagina_incluye_la_ultima():
    """Cada PNG se envía solo; la página 3 no puede quedar fuera del lote."""
    vistas: list[int] = []

    def lote(imgs: list[bytes]) -> dict:
        vistas.append(len(imgs))
        n = len(vistas)
        return {
            "entries": [
                {
                    "evolucion_n": 1,
                    "notas_evolucion": f"contenido pagina {n}",
                    "ordenes_medicas": [],
                }
            ],
            "paginas_sin_contenido": [],
        }

    out = vision_client.transcribir_por_pagina([b"p1", b"p2", b"p3"], lote)
    assert vistas == [1, 1, 1]
    assert [e["notas_evolucion"] for e in out["entries"]] == [
        "contenido pagina 1",
        "contenido pagina 2",
        "contenido pagina 3",
    ]
    assert [e["evolucion_n"] for e in out["entries"]] == [1, 2, 3]


def test_transcribir_por_pagina_renumera_vacias():
    def lote(imgs: list[bytes]) -> dict:
        if lote.n == 0:
            lote.n += 1
            return {"entries": [{"notas_evolucion": "nota", "ordenes_medicas": []}], "paginas_sin_contenido": []}
        lote.n += 1
        return {"entries": [], "paginas_sin_contenido": [1]}

    lote.n = 0
    out = vision_client.transcribir_por_pagina([b"a", b"b", b"c"], lote)
    assert len(out["entries"]) == 1
    assert out["paginas_sin_contenido"] == [2, 3]
