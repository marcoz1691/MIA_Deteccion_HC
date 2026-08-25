"""TC-API-01, TC-API-02, TC-API-19 — GET /health."""
from __future__ import annotations

import pytest


@pytest.mark.regression
def test_tc_api_01_health_check(client):
    """TC-API-01: Health check."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "modelo_tfidf_disponible" in data
    assert data["modelo_tfidf_path"].endswith(".joblib")
    assert data["mock_llm"] is True


@pytest.mark.regression
def test_tc_api_02_openapi_docs(client):
    """TC-API-02: OpenAPI docs."""
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "html" in resp.headers.get("content-type", "").lower()


@pytest.mark.regression
def test_tc_api_19_mock_llm_env_override(client_mock_forced):
    """TC-API-19: MOCK_LLM env override ignora cliente mock_llm=false."""
    resp = client_mock_forced.get("/health")
    data = resp.json()
    assert data["mock_llm_forzado"] is True
    assert data["mock_llm"] is True

    resp = client_mock_forced.post(
        "/generar",
        json={
            "nota_clinica": "Oración de prueba clínica.",
            "mock_llm": False,
            "brazos": ["llm_zero"],
        },
    )
    assert resp.status_code == 200
