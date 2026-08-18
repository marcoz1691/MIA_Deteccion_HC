"""Controles de seguridad y privacidad PHI en la UI."""
from __future__ import annotations

import os
from typing import Literal

import streamlit as st

DataMode = Literal["local", "mock_auto", "external_api"]


def _api_key_present() -> bool:
    if os.getenv("OPENAI_API_KEY") or os.getenv("MISTRAL_API_KEY"):
        return True
    try:
        return bool(st.secrets.get("OPENAI_API_KEY") or st.secrets.get("MISTRAL_API_KEY"))
    except Exception:
        return False


def get_data_mode(mock_llm: bool) -> DataMode:
    if mock_llm:
        return "local"
    if not _api_key_present():
        return "mock_auto"
    return "external_api"


def requires_external_consent(mock_llm: bool) -> bool:
    return get_data_mode(mock_llm) == "external_api"


def render_security_banner(mock_llm: bool) -> None:
    mode = get_data_mode(mock_llm)
    messages = {
        "local": (
            "mia-security-local",
            "Modo demo local — ningún dato sale del equipo.",
        ),
        "mock_auto": (
            "mia-security-warn",
            "Mock automático — configure API en .env o secrets.toml para LLM real.",
        ),
        "external_api": (
            "mia-security-danger",
            "Datos clínicos pueden enviarse a una API externa.",
        ),
    }
    css_class, text = messages[mode]
    st.markdown(
        f'<div class="mia-security-banner {css_class}">{text}</div>',
        unsafe_allow_html=True,
    )


def render_consent_gate(mock_llm: bool) -> bool:
    """Retorna True si el usuario puede analizar (consentimiento OK o no requerido)."""
    if not requires_external_consent(mock_llm):
        return True

    st.warning(
        "Al desactivar el modo mock con API configurada, las oraciones clínicas "
        "pueden enviarse a un proveedor externo."
    )
    consent = st.checkbox(
        "Confirmo que la nota no contiene PHI identificable o tengo autorización para enviarla.",
        value=st.session_state.get("consent_phi", False),
        key="consent_phi",
    )
    return consent
