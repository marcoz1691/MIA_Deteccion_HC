"""Panel de resultados: resumen, tabla y RAG."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from demo.components.sentence_card import render_sentence_card
from demo.components.ui import (
    STRINGS_ES,
    estado_texto,
    nivel_alerta,
    render_score_bar,
)
from s7.inferencia import Brazo, ResultadoNota, ResultadoOracion


def _fmt_score(score: float | None) -> str:
    return f"{score:.2f}" if score is not None else "—"


def _accion_texto(top: ResultadoOracion, score: float, umbral: float) -> str:
    if score < umbral:
        return f"Ninguna oración supera el umbral ({umbral:.2f}). La nota no muestra alertas claras."
    return f"Revisar oración {top.sid + 1} — posible inconsistencia clínica (score {score:.2f})."


def _render_rag_context(context: str) -> None:
    chunks = [c.strip() for c in context.split("\n\n") if c.strip()]
    if not chunks:
        st.info("No se recuperó contexto RAG para esta oración.")
        return
    for i, chunk in enumerate(chunks, start=1):
        st.markdown(
            f'<div class="mia-rag-cite"><strong>Fragmento {i}</strong><br/>{chunk}</div>',
            unsafe_allow_html=True,
        )


def render_results_panel(
    resultado: ResultadoNota,
    brazos: list[Brazo],
    umbral: float,
    *,
    usar_tfidf: bool,
    usar_llm_zero: bool,
    usar_llm_rag: bool,
    modo_degradado: bool = False,
) -> None:
    if resultado.truncado:
        st.warning(
            f"La nota tiene {resultado.n_total} oraciones; "
            f"se analizaron las primeras 20 en esta demo."
        )

    top = resultado.top1(brazos)
    if top is None:
        st.warning(
            "No se detectaron oraciones en la nota (texto muy corto o sin puntos). "
            "Escribe frases completas separadas por puntos."
        )
        return

    top_sid = top.sid
    score_loc = top.score_localizacion(brazos)

    st.subheader("Resumen")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Oraciones analizadas", len(resultado.oraciones))
    c2.metric("Score localización", f"{score_loc:.2f}")
    c3.metric("Brazo localización", top.brazo_localizacion(brazos) or "—")
    c4.metric("Modo", "Degradado (TF-IDF)" if modo_degradado else "Normal")

    render_score_bar(score_loc, umbral)

    if score_loc < umbral:
        st.success(_accion_texto(top, score_loc, umbral))
    else:
        st.markdown(f"**{_accion_texto(top, score_loc, umbral)}**")
        render_sentence_card(top, top_sid, umbral, brazos)

    st.subheader("Detalle por oración")
    filas = []
    for res in sorted(
        resultado.oraciones,
        key=lambda r: (-r.score_localizacion(brazos), r.sid),
    ):
        score = res.score_localizacion(brazos)
        fila = {
            "#": res.sid + 1,
            "Oración": res.oracion[:80] + ("…" if len(res.oracion) > 80 else ""),
            "Estado": estado_texto(nivel_alerta(score, umbral)),
            "_score": score,
            "_top": res.sid == top_sid,
        }
        if usar_tfidf:
            fila["TF-IDF"] = _fmt_score(res.score_tfidf)
        if usar_llm_zero:
            fila["LLM zero"] = _fmt_score(res.score_llm_zero)
        if usar_llm_rag:
            fila["LLM+RAG"] = _fmt_score(res.score_llm_rag)
        filas.append(fila)

    df = pd.DataFrame(filas)
    display_cols = [c for c in df.columns if not c.startswith("_")]

    def _highlight_top(row: pd.Series) -> list[str]:
        is_top = bool(df.loc[row.name, "_top"])
        style = "background-color: #FFEBEE" if is_top else ""
        return [style] * len(row)

    styled = df[display_cols].style.apply(_highlight_top, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)

    if usar_tfidf or usar_llm_zero or usar_llm_rag:
        st.subheader("Scores — oración top-1")
        cols = st.columns(sum([usar_tfidf, usar_llm_zero, usar_llm_rag]))
        idx = 0
        if usar_tfidf and top.score_tfidf is not None:
            with cols[idx]:
                st.caption("TF-IDF")
                st.progress(min(top.score_tfidf, 1.0))
            idx += 1
        if usar_llm_zero and top.score_llm_zero is not None:
            with cols[idx]:
                st.caption("LLM zero-shot")
                st.progress(min(top.score_llm_zero, 1.0))
            idx += 1
        if usar_llm_rag and top.score_llm_rag is not None:
            with cols[idx]:
                st.caption("LLM + RAG")
                st.progress(min(top.score_llm_rag, 1.0))

    with st.expander("¿Qué hace cada brazo?"):
        st.markdown(STRINGS_ES["explicacion_brazos"])

    if usar_llm_rag and top.rag_context:
        with st.expander("Contexto RAG recuperado (oración top-1)"):
            _render_rag_context(top.rag_context)
