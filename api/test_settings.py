"""Tests de configuración del backend."""
from __future__ import annotations

from api.settings import llm_api_configurada, resolve_mock_llm


def test_resolve_mock_llm_usa_request_si_env_ausente(monkeypatch):
    monkeypatch.delenv("MOCK_LLM", raising=False)
    assert resolve_mock_llm(True) == (True, False)
    assert resolve_mock_llm(False) == (False, False)


def test_resolve_mock_llm_forzado_por_env(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "false")
    assert resolve_mock_llm(True) == (False, True)
    assert resolve_mock_llm(False) == (False, True)

    monkeypatch.setenv("MOCK_LLM", "true")
    assert resolve_mock_llm(False) == (True, True)


def test_llm_api_configurada(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm_api_configurada() is False

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert llm_api_configurada() is True

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    assert llm_api_configurada() is True

    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert llm_api_configurada() is True
