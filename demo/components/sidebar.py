"""Sidebar simplificada para la página de análisis."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from demo.components.security import get_data_mode


def render_main_sidebar(model_path: Path, usar_llm_rag: bool) -> None:
    with st.sidebar:
        st.header("Análisis")
        st.toggle(
            "Modo mock LLM (sin API)",
            key="mock_llm",
        )

        st.divider()
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
        st.write("Modelo TF-IDF:", "Disponible" if modelo_ok else "No encontrado")
        st.write("Modo de datos:", {
            "local": "Local (mock)",
            "mock_auto": "Mock automático",
            "external_api": "API externa",
        }[mode])
        st.write("API key:", "Presente" if api_key else "—")
        if usar_llm_rag:
            st.write("Índice RAG:", "Se construye al analizar")

        st.divider()
        st.caption(
            "Configuración avanzada (brazos, umbral, idioma) en la página **Configuración**."
        )
        st.page_link("pages/3_Configuracion.py", label="Ir a Configuración", icon="⚙️")
        st.page_link("pages/1_Metricas.py", label="Ver métricas S7", icon="📊")
