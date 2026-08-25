"""TC-API-22 — Modo degradado vía API."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from s7.inferencia import analizar_nota
from s7.llm_client import LLMClient, LLMUnavailableError
from s7.test_fallback import (
    _FakeModelo,
    _client_que_falla,
    test_analizar_nota_degrada_a_tfidf,
    test_llm_unavailable_tras_reintentos,
    test_sin_fallback_propaga_error,
)
from tests.fixtures.notas import NOTA_MEDICACION


@pytest.mark.regression
def test_tc_api_22_modo_degradado_pipeline():
    """TC-API-22: LLM falla → modo_degradado via analizar_nota (mismo path que API)."""
    test_analizar_nota_degrada_a_tfidf()


@pytest.mark.regression
class TestFallbackReexports:
    """Re-exporta tests de s7/test_fallback.py para suite unificada."""

    def test_llm_unavailable_tras_reintentos(self):
        test_llm_unavailable_tras_reintentos()

    def test_sin_fallback_propaga_error(self):
        test_sin_fallback_propaga_error()


@pytest.mark.integration
def test_tc_api_22_modo_degradado_api_endpoint(patch_inference_service, monkeypatch):
    """TC-API-22: Endpoint /generar retorna modo_degradado cuando LLM falla."""
    monkeypatch.setenv("MOCK_LLM", "false")

    import api.main as main_module
    from api.service import InferenceService

    original_build = InferenceService._build_llm_client

    def failing_build(self, mock_llm: bool) -> LLMClient:
        tmp = tempfile.mkdtemp()
        return _client_que_falla(Path(tmp))

    monkeypatch.setattr(InferenceService, "_build_llm_client", failing_build)

    main_module._service = None
    from api.main import app

    with TestClient(app) as client:
        resp = client.post(
            "/generar",
            json={
                "nota_clinica": NOTA_MEDICACION,
                "mock_llm": False,
                "brazos": ["tfidf", "llm_zero"],
                "umbral": 0.5,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["modo_degradado"] is True
    assert data["brazos_efectivos"] == ["tfidf"]
    assert data["mensaje_fallback"] is not None
