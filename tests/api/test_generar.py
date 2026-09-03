"""TC-API-03..18, TC-API-20..25 — POST /generar y validaciones."""
from __future__ import annotations

import pytest

from s7.inferencia import MAX_ORACIONES_DEMO
from tests.fixtures.notas import NOTA_LIMPIA, NOTA_MEDICACION, NOTA_PLAN, NOTAS_IDIOMA


@pytest.mark.regression
class TestGenerarHappyPath:
    def test_tc_api_03_nota_limpia_sin_alerta(self, client):
        """TC-API-03: Nota limpia — sin alerta (mock LLM)."""
        resp = client.post(
            "/generar",
            json={
                "nota_clinica": NOTA_LIMPIA,
                "mock_llm": True,
                "brazos": ["llm_zero"],
                "umbral": 0.5,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["top1"] is not None
        assert data["top1"]["alerta"] is False
        assert all("score_localizacion" in o for o in data["oraciones"])

    def test_tc_api_04_error_medicacion(self, client):
        """TC-API-04: Error medicación — alerta amoxicilina."""
        resp = client.post(
            "/generar",
            json={
                "nota_clinica": NOTA_MEDICACION,
                "mock_llm": True,
                "brazos": ["llm_zero"],
                "umbral": 0.5,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "amoxicilina" in data["top1"]["oracion"].lower()
        assert data["top1"]["alerta"] is True
        assert any(o["alerta"] for o in data["oraciones"])

    def test_tc_api_05_error_plan(self, client):
        """TC-API-05: Error plan — extracción excesiva."""
        resp = client.post(
            "/generar",
            json={
                "nota_clinica": NOTA_PLAN,
                "mock_llm": True,
                "brazos": ["llm_zero"],
                "umbral": 0.5,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["top1"]["alerta"] is True
        top_oracion = data["top1"]["oracion"].lower()
        assert "extracción" in top_oracion or "piezas" in top_oracion

    def test_tc_api_06_solo_tfidf(self, client):
        """TC-API-06: Solo brazo TF-IDF."""
        resp = client.post(
            "/generar",
            json={
                "nota_clinica": NOTA_MEDICACION,
                "mock_llm": True,
                "brazos": ["tfidf"],
                "umbral": 0.5,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["brazos_efectivos"] == ["tfidf"]
        assert all(o["score_tfidf"] is not None for o in data["oraciones"])

    def test_tc_api_07_tres_brazos(self, client):
        """TC-API-07: Todos los brazos (mock)."""
        resp = client.post(
            "/generar",
            json={
                "nota_clinica": NOTA_MEDICACION,
                "mock_llm": True,
                "brazos": ["tfidf", "llm_zero", "llm_rag"],
                "umbral": 0.5,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["brazos_efectivos"]) == 3
        assert data["top1"]["alerta"] is True

    def test_tc_api_08_umbral_alto(self, client):
        """TC-API-08: Umbral alto (1.0) — ninguna alerta en nota limpia."""
        resp = client.post(
            "/generar",
            json={
                "nota_clinica": NOTA_LIMPIA,
                "mock_llm": True,
                "brazos": ["llm_zero"],
                "umbral": 1.0,
            },
        )
        assert resp.status_code == 200
        assert all(not o["alerta"] for o in resp.json()["oraciones"])

    def test_tc_api_16_truncado(self, client):
        """TC-API-16: Nota más larga que el tope — truncado."""
        nota = ". ".join(
            [f"Oracion numero {i} sin inconsistencia aparente" for i in range(1, MAX_ORACIONES_DEMO + 6)]
        ) + "."
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
        assert data["n_total"] > MAX_ORACIONES_DEMO
        assert len(data["oraciones"]) == MAX_ORACIONES_DEMO

    def test_tc_api_24_umbral_cero(self, client):
        """TC-API-24: Umbral 0.0 — todas las oraciones alertan."""
        resp = client.post(
            "/generar",
            json={
                "nota_clinica": NOTA_LIMPIA,
                "mock_llm": True,
                "brazos": ["llm_zero"],
                "umbral": 0.0,
            },
        )
        assert resp.status_code == 200
        assert all(o["alerta"] for o in resp.json()["oraciones"])


@pytest.mark.regression
class TestGenerarValidation:
    def test_tc_api_09_nota_vacia(self, client):
        resp = client.post("/generar", json={"nota_clinica": "", "mock_llm": True})
        assert resp.status_code == 422

    def test_tc_api_10_sin_nota_clinica(self, client):
        resp = client.post("/generar", json={"mock_llm": True})
        assert resp.status_code == 422

    def test_tc_api_11_brazos_vacio(self, client):
        resp = client.post(
            "/generar",
            json={"nota_clinica": NOTA_LIMPIA, "brazos": []},
        )
        assert resp.status_code == 422

    def test_tc_api_12_brazo_invalido(self, client):
        resp = client.post(
            "/generar",
            json={"nota_clinica": NOTA_LIMPIA, "brazos": ["invalido"]},
        )
        assert resp.status_code == 422

    def test_tc_api_13_idioma_invalido(self, client):
        resp = client.post(
            "/generar",
            json={"nota_clinica": NOTA_LIMPIA, "idioma": "frances"},
        )
        assert resp.status_code == 422

    def test_tc_api_14_json_malformado(self, client):
        resp = client.post(
            "/generar",
            content="{nota_clinica: broken",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_tc_api_25_content_type_incorrecto(self, client):
        resp = client.post(
            "/generar",
            content="nota_clinica=prueba",
            headers={"Content-Type": "text/plain"},
        )
        assert resp.status_code == 422


@pytest.mark.regression
def test_tc_api_15_ruta_inexistente(client):
    resp = client.get("/no-existe")
    assert resp.status_code == 404


@pytest.mark.regression
def test_tc_api_17_cors_preflight(client):
    resp = client.options(
        "/generar",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code in (200, 204)


@pytest.mark.regression
def test_tc_api_20_503_sin_modelo_tfidf(client_no_model):
    """TC-API-20: 503 sin modelo TF-IDF."""
    resp = client_no_model.post(
        "/generar",
        json={
            "nota_clinica": NOTA_LIMPIA,
            "brazos": ["tfidf"],
        },
    )
    assert resp.status_code == 503


@pytest.mark.regression
def test_tc_api_21_503_sin_llm_ni_tfidf(client_no_model, monkeypatch):
    """TC-API-21: 503 sin LLM ni TF-IDF."""
    monkeypatch.setenv("MOCK_LLM", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    import api.main as main_module

    main_module._service = None
    from api.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        resp = c.post(
            "/generar",
            json={
                "nota_clinica": NOTA_LIMPIA,
                "mock_llm": False,
                "brazos": ["llm_zero"],
            },
        )
    assert resp.status_code == 503


@pytest.mark.integration
@pytest.mark.parametrize(
    "idioma,nota_key,expect_alerta",
    [
        ("spanish", "es_medicacion", True),
        ("spanish", "es_limpia", False),
        ("english", "en_medicacion", True),
        ("english", "en_limpia", False),
    ],
)
def test_tc_api_23_idioma_matrix(client, idioma, nota_key, expect_alerta):
    """TC-API-23: Idioma ES vs EN."""
    resp = client.post(
        "/generar",
        json={
            "nota_clinica": NOTAS_IDIOMA[nota_key],
            "mock_llm": True,
            "idioma": idioma,
            "brazos": ["llm_zero"],
            "umbral": 0.5,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["top1"]["alerta"] is expect_alerta
