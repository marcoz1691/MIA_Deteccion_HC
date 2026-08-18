"""Panel de entrada: ejemplos, nota clínica y CTA."""
from __future__ import annotations

import streamlit as st

from demo.components.ui import render_step


def _on_ejemplo_change(ejemplos: dict[str, str]) -> None:
    sel = st.session_state.ultimo_ejemplo
    st.session_state.nota_clinica = (
        ejemplos.get(sel, "") if sel != "— Escribir nota propia —" else ""
    )


def render_input_panel(
    ejemplos: dict[str, str],
    *,
    solo_tfidf: bool,
    can_analyze: bool,
) -> tuple[str, bool]:
    """Renderiza entrada y retorna (nota, clicked_analizar)."""
    opciones = ["— Escribir nota propia —"] + list(ejemplos.keys())

    col_ej, col_nota = st.columns([1, 2])
    with col_ej:
        render_step(1, "Cargar ejemplo")
        st.selectbox(
            "Ejemplo precargado",
            opciones,
            key="ultimo_ejemplo",
            on_change=_on_ejemplo_change,
            args=(ejemplos,),
            label_visibility="collapsed",
        )

    with col_nota:
        render_step(2, "Nota clínica")
        nota = st.text_area(
            "Nota clínica",
            key="nota_clinica",
            height=160,
            placeholder="Pega aquí una historia clínica odontológica o de medicina general…",
            label_visibility="collapsed",
        )

    if solo_tfidf:
        st.warning(
            "Solo TF-IDF: el modelo se entrenó en MEDEC (inglés). "
            "En notas en español puede marcar oraciones incorrectas; "
            "activa LLM mock para mejor localización."
        )

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        analizar = st.button(
            "Analizar nota",
            type="primary",
            use_container_width=True,
            disabled=not can_analyze,
        )

    if not can_analyze:
        st.caption("Acepta el consentimiento de privacidad para habilitar el análisis.")

    return nota, analizar
