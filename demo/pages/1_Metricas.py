"""Métricas de evaluación S6/S7."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "_demo_boot", Path(__file__).resolve().parent.parent / "_boot.py"
)
_boot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_boot)
ROOT = _boot.repo_root(__file__)

import pandas as pd
import streamlit as st
from demo.components.auth import logout_button, require_auth
from demo.components.ui import STRINGS_ES, page_config, render_footer, render_hero
from demo.state import init_session_state

METRICAS_REF = STRINGS_ES["metricas_referencia"]

COMPARATIVA_BRAZOS = [
    {"Brazo": "TF-IDF ajustado", "ROC-AUC": "0.949", "Latencia/oración": "1–5 ms", "Costo/1000 notas": "$0", "Privacidad": "On-premise"},
    {"Brazo": "LLM zero-shot", "ROC-AUC": "Ver eval S7", "Latencia/oración": "200–800 ms", "Costo/1000 notas": "$0.50–2.00", "Privacidad": "API externa"},
    {"Brazo": "LLM + RAG", "ROC-AUC": "Ver eval S7", "Latencia/oración": "500–1500 ms", "Costo/1000 notas": "$1.00–3.00", "Privacidad": "API + chunks"},
]


def _load_json(path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    page_config("Métricas", icon="📊")
    init_session_state()
    if not require_auth():
        st.stop()
    logout_button()

    render_hero("Métricas de evaluación", "Resultados S6 (TF-IDF) y S7 (comparación tripartita)")

    st.subheader("Referencia rápida")
    cols = st.columns(3)
    for col, (k, v) in zip(cols, METRICAS_REF.items()):
        col.metric(k.split("(")[0].strip(), v.split(" ")[0] if " " in v else v)

    metricas_s6 = _load_json(ROOT / "s6" / "metricas_ajuste.json")
    if metricas_s6:
        st.subheader("S6 — Modelo TF-IDF ajustado (test)")
        prueba = metricas_s6.get("prueba", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("ROC-AUC", f"{prueba.get('roc_auc', 0):.3f}")
        c2.metric("AUPRC", f"{prueba.get('auprc', 0):.3f}")
        c3.metric("Recall", f"{prueba.get('recall', 0):.3f}")
        c4.metric("Top-1 loc.", f"{metricas_s6.get('localizacion_top1_test', 0):.1%}")

    metricas_s7 = _load_json(ROOT / "salidas_s7" / "metricas_tripartita.json")
    if metricas_s7:
        st.subheader("S7 — Evaluación tripartita")
        st.json(metricas_s7)
    else:
        st.info(
            "Ejecuta la evaluación S7 para generar métricas:\n\n"
            "`python s7/eval_tripartita.py --mock-llm --max-oraciones 500`"
        )

    st.subheader("Comparativa de brazos")
    st.dataframe(pd.DataFrame(COMPARATIVA_BRAZOS), use_container_width=True, hide_index=True)

    st.markdown(
        """
        **Notas metodológicas**
        - Dataset principal: MEDEC (inglés, particiones oficiales).
        - Tarea: clasificación y localización a nivel de **oración**.
        - En notas en español (CITIMED), TF-IDF puede degradarse; LLM+RAG es preferible.
        - Latencias LLM dependen de API real vs mock.
        """
    )
    render_footer()


main()
