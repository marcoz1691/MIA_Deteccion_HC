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
