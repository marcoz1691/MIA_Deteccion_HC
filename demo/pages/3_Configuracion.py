"""Configuración avanzada: brazos, umbral, idioma."""
from __future__ import annotations

import os

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "_demo_boot", Path(__file__).resolve().parent.parent / "_boot.py"
)
_boot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_boot)
_boot.repo_root(__file__)

import streamlit as st

from demo.components.auth import logout_button, require_auth
from demo.components.security import get_data_mode, render_security_banner
from demo.components.ui import page_config, render_footer, render_hero
from demo.state import get_config, init_session_state, model_path_from_config


def main() -> None:
    page_config("Configuración", icon="⚙️")
    init_session_state()
    if not require_auth():
        st.stop()
    logout_button()

    render_hero("Configuración", "Brazos de detección, umbral e idioma de prompts")

    cfg = get_config()
    model_path = model_path_from_config(cfg)

    st.subheader("Brazos activos")
    st.checkbox("TF-IDF", key="usar_tfidf")
    st.checkbox("LLM zero-shot", key="usar_llm_zero")
    st.checkbox("LLM + RAG", key="usar_llm_rag")

    st.subheader("Parámetros")
    st.selectbox(
        "Idioma de prompts",
        ["spanish", "english"],
        key="idioma",
        format_func=lambda x: "Español" if x == "spanish" else "Inglés",
    )
    st.slider("Umbral de alerta", 0.3, 0.7, key="umbral", step=0.05)

    st.subheader("Modo LLM")
    st.toggle("Modo mock LLM (sin API)", key="mock_llm")
    render_security_banner(st.session_state.mock_llm)

    st.subheader("Estado del sistema")
    modelo_ok = model_path.exists()
    api_key = bool(os.getenv("OPENAI_API_KEY") or os.getenv("MISTRAL_API_KEY"))
    try:
        api_key = api_key or bool(
            st.secrets.get("OPENAI_API_KEY") or st.secrets.get("MISTRAL_API_KEY")
        )
    except Exception:
        pass

    mode = get_data_mode(st.session_state.mock_llm)
    st.write("Modelo TF-IDF:", "Disponible" if modelo_ok else "No encontrado — ejecuta `python s6/modelo_ajustado.py`")
    st.write("Modo de datos:", {
        "local": "Local (mock)",
        "mock_auto": "Mock automático",
        "external_api": "API externa",
    }[mode])
    st.write("API key:", "Presente" if api_key else "No configurada")
    st.write("Modelo LLM:", cfg["llm"]["model"])
    st.write("Embedding RAG:", cfg["rag"]["embedding_model"])

    if not st.session_state.usar_tfidf and not st.session_state.usar_llm_zero and not st.session_state.usar_llm_rag:
        st.error("Debes activar al menos un brazo.")

    st.page_link("app.py", label="Volver al análisis", icon="🏠")
    render_footer()


main()
