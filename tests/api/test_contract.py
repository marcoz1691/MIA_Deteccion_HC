"""TC-API-18 — Contrato JSON de respuesta."""
from __future__ import annotations

import pytest

from tests.fixtures.notas import NOTA_LIMPIA

ROOT_KEYS = {
    "oraciones",
    "top1",
    "truncado",
    "n_total",
    "modo_degradado",
    "brazos_efectivos",
    "mensaje_fallback",
}

ORACION_KEYS = {
    "sid",
    "oracion",
    "score_localizacion",
    "alerta",
}


@pytest.mark.regression
def test_tc_api_18_contrato_json_respuesta(client):
    """TC-API-18: Contrato JSON respuesta completo."""
    resp = client.post(
        "/generar",
        json={
            "nota_clinica": NOTA_LIMPIA,
            "mock_llm": True,
            "brazos": ["llm_zero"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert ROOT_KEYS.issubset(data.keys())
    assert all(ORACION_KEYS.issubset(o.keys()) for o in data["oraciones"])
    if data["top1"] is not None:
        assert {"sid", "oracion", "score_localizacion", "alerta"}.issubset(data["top1"].keys())
