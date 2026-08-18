"""Card de oración con nivel de alerta."""
from __future__ import annotations

import streamlit as st

from demo.components.ui import badge_html, nivel_alerta
from s7.inferencia import Brazo, ResultadoOracion


def render_sentence_card(
    res: ResultadoOracion,
    top_sid: int | None,
    umbral: float,
    brazos: list[Brazo],
    *,
    show_badge: bool = True,
) -> None:
    es_top = res.sid == top_sid
    score = res.score_localizacion(brazos)
    nivel = nivel_alerta(score, umbral)

    if es_top:
        css = "mia-sentence-top"
    elif nivel == "warn":
        css = "mia-sentence-warn"
    else:
        css = "mia-sentence-ok"

    badge = badge_html(nivel) if show_badge else ""
    top_label = " &nbsp; <em>(más sospechosa)</em>" if es_top else ""

    st.markdown(
        f"""
        <div class="mia-sentence-card {css}">
            <strong>Oración {res.sid + 1}</strong>{top_label} &nbsp; {badge}<br/>
            {res.oracion}
        </div>
        """,
        unsafe_allow_html=True,
    )
