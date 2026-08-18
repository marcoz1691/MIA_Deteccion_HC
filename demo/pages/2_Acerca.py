"""Metodología, limitaciones y disclaimer clínico."""
from __future__ import annotations

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
from demo.components.ui import STRINGS_ES, page_config, render_card, render_footer, render_hero
from demo.state import init_session_state


def main() -> None:
    page_config("Acerca de", icon="ℹ️")
    init_session_state()
    if not require_auth():
        st.stop()
    logout_button()

    render_hero("Acerca del prototipo", "MIA Detección HC · Proyecto CITIMED")

    render_card(
        "Objetivo",
        "Detectar inconsistencias en historias clínicas a nivel de oración: "
        "no solo si la nota tiene error, sino cuál frase es sospechosa.",
    )
    render_card(
        "Enfoque tripartito",
        "Comparamos TF-IDF (léxico), LLM zero-shot (semántica) y LLM+RAG "
        "(semántica anclada en guías clínicas vía FAISS).",
    )
    render_card(
        "Limitaciones",
        "Prototipo de investigación entrenado principalmente en MEDEC (inglés). "
        "No validado clínicamente en producción. Requiere revisión humana.",
    )

    st.subheader("Equipo")
    st.markdown(
        "- Proyecto CITIMED — Odontología / Medicina\n"
        "- Grupo: Patricio Bayas · José Puebla · Marco Zurita Rojas"
    )

    st.subheader("Privacidad y despliegue")
    st.markdown(
        """
        - **Demo local:** modo mock activo por defecto; ningún dato sale del equipo.
        - **Piloto CITIMED:** usar Ollama/Mistral on-premise (`OPENAI_BASE_URL` local).
        - **PHI:** desidentificar notas antes de cualquier llamada a API cloud.
        - Ver informe completo en `s7/docs/informe_produccion.md`.
        """
    )

    st.warning(STRINGS_ES["disclaimer"])
    render_footer()


main()
