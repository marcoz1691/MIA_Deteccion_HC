"""Estilos y widgets compartidos para la demo Streamlit."""
from __future__ import annotations

import streamlit as st

PALETTE = {
    "primary": "#1565C0",
    "primary_dark": "#0D47A1",
    "accent": "#00838F",
    "success": "#2E7D32",
    "warning": "#F9A825",
    "danger": "#C62828",
    "surface": "#F8FAFC",
    "border": "#E2E8F0",
    "text_muted": "#64748B",
}

STRINGS_ES = {
    "hero_title": "Detección de inconsistencias clínicas",
    "hero_subtitle": "Prototipo CITIMED · Análisis por oración · TF-IDF vs LLM vs LLM+RAG",
    "disclaimer": (
        "Prototipo de investigación. No sustituye el criterio clínico. "
        "No usar para decisiones terapéuticas."
    ),
    "empty_step_1": "Elige un ejemplo o pega una nota clínica en el panel de entrada.",
    "empty_step_2": "Pulsa **Analizar nota** para ejecutar los brazos activos.",
    "empty_step_3": "Revisa la oración marcada y el contexto RAG si está disponible.",
    "card_tfidf": "Modelo léxico entrenado en MEDEC. Rápido, local, sin envío de datos.",
    "card_llm": "Razonamiento semántico con LLM. Detecta contradicciones que el léxico no ve.",
    "card_rag": "LLM anclado en guías clínicas vía FAISS. Más interpretable para el revisor.",
    "explicacion_brazos": """
**TF-IDF (léxico):** modelo entrenado sobre MEDEC que puntúa cada oración según patrones
de texto. Rápido, local y sin enviar datos fuera del equipo.

**LLM zero-shot:** un modelo de lenguaje juzga si la oración es inconsistente sin
conocimiento externo adicional. Captura contradicciones semánticas que el léxico no ve.

**LLM + RAG:** el LLM recibe fragmentos de guías clínicas (medicación, diagnóstico,
odontología) recuperados con FAISS antes de decidir. Es el enfoque más interpretable
para el médico revisor.
""",
    "metricas_referencia": {
        "ROC-AUC (TF-IDF ajustado)": "0.949",
        "Localización top-1": "84.6 % (263/311 notas MEDEC)",
        "AUPRC": "0.419 (prevalencia 4.5 %)",
    },
}


def inject_styles() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        .block-container {{
            padding-top: 1.5rem;
            max-width: 1200px;
        }}

        .mia-hero {{
            background: linear-gradient(135deg, {PALETTE["primary"]} 0%, {PALETTE["accent"]} 100%);
            color: white;
            border-radius: 16px;
            padding: 2rem 2.25rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 24px rgba(21, 101, 192, 0.18);
        }}

        .mia-hero h1 {{
            color: white !important;
            font-size: 2rem !important;
            margin-bottom: 0.35rem !important;
        }}

        .mia-hero p {{
            color: rgba(255,255,255,0.92);
            font-size: 1.05rem;
            margin: 0;
        }}

        .mia-card {{
            background: white;
            border: 1px solid {PALETTE["border"]};
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
        }}

        .mia-card h3 {{
            margin-top: 0;
            color: {PALETTE["primary_dark"]};
            font-size: 1rem;
        }}

        .mia-card p {{
            color: {PALETTE["text_muted"]};
            margin-bottom: 0;
            line-height: 1.5;
        }}

        .mia-badge {{
            display: inline-block;
            padding: 0.2rem 0.65rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
        }}

        .mia-badge-ok {{
            background: #E8F5E9;
            color: {PALETTE["success"]};
        }}

        .mia-badge-warn {{
            background: #FFF8E1;
            color: #E65100;
        }}

        .mia-badge-danger {{
            background: #FFEBEE;
            color: {PALETTE["danger"]};
        }}

        .mia-step {{
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
        }}

        .mia-step-num {{
            background: {PALETTE["primary"]};
            color: white;
            width: 1.6rem;
            height: 1.6rem;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8rem;
            font-weight: 700;
            flex-shrink: 0;
        }}

        .mia-security-banner {{
            border-radius: 10px;
            padding: 0.75rem 1rem;
            margin-bottom: 1.25rem;
            font-size: 0.92rem;
            font-weight: 500;
        }}

        .mia-security-local {{
            background: #E8F5E9;
            border: 1px solid #A5D6A7;
            color: {PALETTE["success"]};
        }}

        .mia-security-warn {{
            background: #FFF8E1;
            border: 1px solid #FFE082;
            color: #E65100;
        }}

        .mia-security-danger {{
            background: #FFEBEE;
            border: 1px solid #EF9A9A;
            color: {PALETTE["danger"]};
        }}

        .mia-footer {{
            margin-top: 2.5rem;
            padding-top: 1rem;
            border-top: 1px solid {PALETTE["border"]};
            color: {PALETTE["text_muted"]};
            font-size: 0.85rem;
            text-align: center;
        }}

        .mia-sentence-card {{
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
        }}

        .mia-sentence-top {{
            background: #FFEBEE;
            border: 2px solid {PALETTE["danger"]};
        }}

        .mia-sentence-warn {{
            background: #FFF8E1;
            border: 1px solid {PALETTE["warning"]};
        }}

        .mia-sentence-ok {{
            background: #F5F5F5;
            border: 1px solid {PALETTE["border"]};
        }}

        .mia-rag-cite {{
            background: {PALETTE["surface"]};
            border-left: 4px solid {PALETTE["accent"]};
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            border-radius: 0 8px 8px 0;
            font-size: 0.9rem;
            line-height: 1.5;
        }}

        div[data-testid="stSidebar"] {{
            background: {PALETTE["surface"]};
        }}

        div[data-testid="stSidebar"] .block-container {{
            padding-top: 1rem;
        }}

        .stButton > button[kind="primary"] {{
            background: {PALETTE["primary"]};
            border: none;
            font-weight: 600;
        }}

        .stButton > button[kind="primary"]:hover {{
            background: {PALETTE["primary_dark"]};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_config(page_title: str, *, icon: str = "🏥") -> None:
    st.set_page_config(
        page_title=f"{page_title} · MIA Detección HC",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()


def render_hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="mia-hero">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_card(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="mia-card">
            <h3>{title}</h3>
            <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_step(number: int, text: str) -> None:
    st.markdown(
        f"""
        <div class="mia-step">
            <div class="mia-step-num">{number}</div>
            <div>{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer(disclaimer: str | None = None) -> None:
    text = disclaimer or STRINGS_ES["disclaimer"]
    st.markdown(f'<div class="mia-footer">{text}</div>', unsafe_allow_html=True)


def render_empty_state() -> None:
    st.subheader("Cómo usar esta demo")
    col1, col2, col3 = st.columns(3)
    with col1:
        render_card("TF-IDF", STRINGS_ES["card_tfidf"])
    with col2:
        render_card("LLM zero-shot", STRINGS_ES["card_llm"])
    with col3:
        render_card("LLM + RAG", STRINGS_ES["card_rag"])
    render_step(1, STRINGS_ES["empty_step_1"])
    render_step(2, STRINGS_ES["empty_step_2"])
    render_step(3, STRINGS_ES["empty_step_3"])


def render_score_bar(score: float, umbral: float) -> None:
    pct = min(max(score, 0.0), 1.0)
    color = PALETTE["danger"] if score >= umbral else PALETTE["success"]
    st.markdown(
        f"""
        <div style="margin: 0.5rem 0 1rem;">
            <div style="display:flex; justify-content:space-between; font-size:0.85rem; color:{PALETTE["text_muted"]};">
                <span>Score vs umbral ({umbral:.2f})</span>
                <span>{score:.2f}</span>
            </div>
            <div style="background:#E2E8F0; border-radius:999px; height:8px; overflow:hidden;">
                <div style="width:{pct*100:.0f}%; background:{color}; height:100%; border-radius:999px;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge_html(estado: str) -> str:
    mapping = {
        "ok": ("Sin alerta", "mia-badge-ok"),
        "warn": ("Revisar", "mia-badge-warn"),
        "danger": ("Alerta", "mia-badge-danger"),
    }
    label, css = mapping.get(estado, ("—", "mia-badge-ok"))
    return f'<span class="mia-badge {css}">{label}</span>'


def estado_texto(estado: str) -> str:
    mapping = {"ok": "Sin alerta", "warn": "Revisar", "danger": "Alerta"}
    return mapping.get(estado, "—")


def nivel_alerta(score: float, umbral: float) -> str:
    if score >= umbral:
        return "danger"
    if score >= umbral - 0.15:
        return "warn"
    return "ok"
