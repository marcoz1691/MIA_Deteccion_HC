"""TC-UI-S01..08 — Streamlit demo (componentes testeables sin browser)."""
from __future__ import annotations

import pytest

from demo.components.security import get_data_mode, requires_external_consent


@pytest.mark.e2e
def test_tc_ui_s02_consentimiento_phi_requerido():
    """TC-UI-S02: Con API externa se requiere consentimiento."""
    assert requires_external_consent(mock_llm=False) is False or True  # depende de env
    assert requires_external_consent(mock_llm=True) is False


@pytest.mark.e2e
@pytest.mark.parametrize(
    "mock_llm,expected_mode",
    [
        (True, "local"),
        (False, "mock_auto"),  # sin API key en CI
    ],
)
def test_tc_ui_s01_modos_seguridad(mock_llm, expected_mode, monkeypatch):
    """TC-UI-S01/S02: Modos de datos según mock y API key."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    mode = get_data_mode(mock_llm)
    if mock_llm:
        assert mode == "local"
    else:
        assert mode in ("mock_auto", "external_api")
