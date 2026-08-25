"""Fase 5 — Pruebas de estrés y fault injection (TC-STR-06..09)."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from s7.llm_client import LLMUnavailableError
from s7.test_fallback import _client_que_falla
from tests.fixtures.notas import NOTA_LIMPIA, NOTA_MEDICACION


@pytest.mark.stress
def test_tc_str_04_payload_grande_truncado(client):
    """TC-STR-04: Nota 500 oraciones → 200 + truncado=true."""
    nota = ". ".join([f"Oración {i}." for i in range(500)])
    resp = client.post(
        "/generar",
        json={
            "nota_clinica": nota,
            "mock_llm": True,
            "brazos": ["llm_zero"],
            "umbral": 0.5,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["truncado"] is True
    assert len(data["oraciones"]) == 20


@pytest.mark.stress
def test_tc_str_06_api_llm_caida_modo_degradado(patch_inference_service, monkeypatch):
    """TC-STR-06: API LLM caída → modo_degradado=true, HTTP 200."""
    monkeypatch.setenv("MOCK_LLM", "false")

    import api.main as main_module
    from api.service import InferenceService

    def failing_build(self, mock_llm: bool) -> LLMClient:
        from s7.llm_client import LLMClient

        tmp = tempfile.mkdtemp()
        return _client_que_falla(Path(tmp))

    monkeypatch.setattr(InferenceService, "_build_llm_client", failing_build)
    main_module._service = None
    from api.main import app

    with TestClient(app) as c:
        resp = c.post(
            "/generar",
            json={
                "nota_clinica": NOTA_MEDICACION,
                "mock_llm": False,
                "brazos": ["tfidf", "llm_zero"],
            },
        )
    assert resp.status_code == 200
    assert resp.json()["modo_degradado"] is True


@pytest.mark.stress
def test_tc_str_07_modelo_ausente_503(client_no_model):
    """TC-STR-07: Modelo joblib ausente → 503 claro."""
    resp = client_no_model.post(
        "/generar",
        json={"nota_clinica": NOTA_LIMPIA, "brazos": ["tfidf"]},
    )
    assert resp.status_code == 503
    assert "detail" in resp.json()


@pytest.mark.stress
def test_tc_str_09_llm_unavailable_error_propagates():
    """TC-STR-09: LLM unavailable tras reintentos."""
    with tempfile.TemporaryDirectory() as tmp:
        client = _client_que_falla(Path(tmp))
        with pytest.raises(LLMUnavailableError):
            client.complete("prompt", brazo="llm_zero")


@pytest.mark.stress
@pytest.mark.skip(reason="TC-STR-10: reinicio uvicorn bajo carga — prueba manual/chaos")
def test_tc_str_10_reinicio_bajo_carga():
    pass
