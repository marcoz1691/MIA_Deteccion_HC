"""Fixtures compartidas para la suite SDET."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent


class FakeModeloTfidf:
    """Modelo TF-IDF simulado para pruebas sin joblib entrenado."""

    def predict_proba(self, texts):
        n = len(list(texts))
        if n == 0:
            return np.empty((0, 2))
        scores = np.linspace(0.1, 0.9, n).reshape(-1, 1)
        return np.hstack([1 - scores, scores])


@pytest.fixture
def fake_modelo_tfidf():
    return FakeModeloTfidf()


@pytest.fixture
def patch_inference_service(monkeypatch, fake_modelo_tfidf):
    """Inyecta modelo TF-IDF simulado en InferenceService."""
    from s7.inferencia import cargar_config
    from api.service import InferenceService, resolve_cfg_paths

    def _init(self, historial_db=None) -> None:
        self.cfg = resolve_cfg_paths(cargar_config(ROOT / "s7" / "config.yaml"))
        self.model_path = ROOT / "tests" / "fixtures" / "modelo_test.joblib"
        self.modelo_tfidf = fake_modelo_tfidf
        self._rag = None
        self.historial_db = historial_db

    monkeypatch.setattr(InferenceService, "__init__", _init)
    return fake_modelo_tfidf


@pytest.fixture
def patch_inference_no_model(monkeypatch):
    """InferenceService sin modelo TF-IDF (TC-API-20/21)."""
    from s7.inferencia import cargar_config
    from api.service import InferenceService, resolve_cfg_paths

    def _init(self, historial_db=None) -> None:
        self.cfg = resolve_cfg_paths(cargar_config(ROOT / "s7" / "config.yaml"))
        self.model_path = ROOT / "tests" / "fixtures" / "missing.joblib"
        self.modelo_tfidf = None
        self._rag = None
        self.historial_db = historial_db

    monkeypatch.setattr(InferenceService, "__init__", _init)


@pytest.fixture
def client(patch_inference_service, monkeypatch):
    """TestClient con MOCK_LLM=true y modelo simulado."""
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    import api.main as main_module

    main_module._service = None
    from api.main import app

    with TestClient(app) as test_client:
        yield test_client
    main_module._service = None


@pytest.fixture
def client_no_model(patch_inference_no_model, monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    import api.main as main_module

    main_module._service = None
    from api.main import app

    with TestClient(app) as test_client:
        yield test_client
    main_module._service = None


@pytest.fixture
def client_mock_forced(patch_inference_service, monkeypatch):
    """Servidor con MOCK_LLM=true forzado (TC-API-19)."""
    monkeypatch.setenv("MOCK_LLM", "true")
    import api.main as main_module

    main_module._service = None
    from api.main import app

    with TestClient(app) as test_client:
        yield test_client
    main_module._service = None


@pytest.fixture
def medec_available():
    return (ROOT / "medec_try" / "MEDEC-MS").exists()


@pytest.fixture
def modelo_tfidf_available():
    from s7.inferencia import cargar_config

    cfg = cargar_config(ROOT / "s7" / "config.yaml")
    return (ROOT / cfg["salidas"]["modelo_tfidf"]).exists()
