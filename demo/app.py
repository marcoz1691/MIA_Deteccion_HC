"""Demo interactiva — detección de inconsistencias en historias clínicas (CITIMED)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demo.ejemplos import listar_ejemplos
from s7.inferencia import (
    Brazo,
    cargar_config,
    cargar_modelo_tfidf,
    analizar_nota,
)
from s7.llm_client import LLMClient
from s7.rag_index import RAGIndex

st.set_page_config(
    page_title="MIA Detección HC — Demo",
    page_icon="🏥",
    layout="wide",
)

METRICAS_REFERENCIA = {
    "ROC-AUC (TF-IDF ajustado)": "0.949",
    "Localización top-1": "84.6 % (263/311 notas MEDEC)",
    "AUPRC": "0.419 (prevalencia 4.5 %)",
}

EXPLICACION_BRAZOS = """
**TF-IDF (léxico):** modelo entrenado sobre MEDEC que puntúa cada oración según patrones
de texto. Rápido, local y sin enviar datos fuera del equipo.

**LLM zero-shot:** un modelo de lenguaje juzga si la oración es inconsistente sin
conocimiento externo adicional. Captura contradicciones semánticas que el léxico no ve.

**LLM + RAG:** el LLM recibe fragmentos de guías clínicas (medicación, diagnóstico,
odontología) recuperados con FAISS antes de decidir. Es el enfoque más interpretable
para el médico revisor.
"""


@st.cache_resource
def get_config():
    return cargar_config(ROOT / "s7" / "config.yaml")


@st.cache_resource
def get_modelo_tfidf(model_path: str):
    return cargar_modelo_tfidf(model_path)


@st.cache_resource
def get_rag_index(_cfg_hash: str, knowledge_dir: str, embedding_model: str, index_path: str, top_k: int):
    return RAGIndex(
        knowledge_dir=ROOT / knowledge_dir,
        embedding_model=embedding_model,
        index_path=ROOT / index_path,
        top_k=top_k,
    ).load()


def _badge_alerta(alerta: bool) -> str:
    return "🔴 Alerta" if alerta else "🟢 OK"


def _fmt_score(score: float | None) -> str:
    return f"{score:.2f}" if score is not None else "—"


def _render_oracion(res, top_sid: int | None, umbral: float, brazos: list[Brazo]):
    es_top = res.sid == top_sid
    alerta = res.alerta(umbral, brazos)
    if es_top:
        bg = "#ffebee"
        border = "2px solid #c62828"
    elif alerta:
        bg = "#fff8e1"
        border = "1px solid #f9a825"
    else:
        bg = "#f5f5f5"
        border = "1px solid #e0e0e0"

    st.markdown(
        f"""
        <div style="background:{bg}; border:{border}; border-radius:8px; padding:12px; margin-bottom:8px;">
            <strong>Oración {res.sid + 1}</strong>
            {" &nbsp; <em>(más sospechosa)</em>" if es_top else ""}<br/>
            {res.oracion}
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    cfg = get_config()
    model_path = ROOT / cfg["salidas"]["modelo_tfidf"]

    st.title("Detección de inconsistencias en historias clínicas")
    st.caption("Prototipo CITIMED · TF-IDF vs LLM vs LLM+RAG · Demo interactiva")

    with st.sidebar:
        st.header("Configuración")
        usar_tfidf = st.checkbox("TF-IDF", value=True)
        usar_llm_zero = st.checkbox("LLM zero-shot", value=True)
        usar_llm_rag = st.checkbox("LLM + RAG", value=True)
        mock_llm = st.toggle("Modo mock LLM (sin API)", value=True)
        idioma = st.selectbox("Idioma de prompts", ["spanish", "english"], format_func=lambda x: "Español" if x == "spanish" else "Inglés")
        umbral = st.slider("Umbral de alerta", 0.3, 0.7, 0.5, 0.05)

        st.divider()
        st.subheader("Estado del sistema")
        modelo_ok = model_path.exists()
        api_key = bool(os.getenv("OPENAI_API_KEY") or os.getenv("MISTRAL_API_KEY"))
        st.write("Modelo TF-IDF:", "✅ cargado" if modelo_ok else "❌ no encontrado")
        st.write("API key:", "✅ presente" if api_key else "— (mock activo)")
        st.write("Índice RAG:", "✅ se construye al analizar" if usar_llm_rag else "—")

        if mock_llm:
            st.info("Demo local: con mock activo no se envían datos a APIs externas.")

        st.divider()
        st.subheader("Métricas de referencia (S7)")
        for k, v in METRICAS_REFERENCIA.items():
            st.write(f"**{k}:** {v}")

    brazos: list[Brazo] = []
    if usar_tfidf:
        brazos.append("tfidf")
    if usar_llm_zero:
        brazos.append("llm_zero")
    if usar_llm_rag:
        brazos.append("llm_rag")

    if not brazos:
        st.warning("Selecciona al menos un brazo en la barra lateral.")
        st.stop()

    if usar_tfidf and not modelo_ok:
        st.error(
            f"Modelo TF-IDF no encontrado en `{model_path}`.\n\n"
            "Entrena el modelo una vez:\n"
            "```bash\n"
            "git clone --depth 1 https://github.com/abachaa/MEDEC.git medec_try\n"
            "python s6/modelo_ajustado.py\n"
            "```"
        )
        st.stop()

    ejemplos = listar_ejemplos()
    opciones = ["— Escribir nota propia —"] + list(ejemplos.keys())
    seleccion = st.selectbox("Cargar ejemplo", opciones)

    default_text = ejemplos.get(seleccion, "") if seleccion != "— Escribir nota propia —" else ""
    nota = st.text_area(
        "Nota clínica",
        value=default_text,
        height=160,
        placeholder="Pega aquí una historia clínica odontológica o de medicina general…",
    )

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        analizar = st.button("Analizar nota", type="primary", use_container_width=True)

    if not analizar:
        with st.expander("¿Qué hace cada brazo?", expanded=False):
            st.markdown(EXPLICACION_BRAZOS)
        st.stop()

    if not nota.strip():
        st.warning("Ingresa una nota clínica o selecciona un ejemplo.")
        st.stop()

    modelo = get_modelo_tfidf(str(model_path)) if usar_tfidf else None
    rag = None
    if usar_llm_rag:
        with st.spinner("Cargando índice RAG (primera vez puede tardar ~15 s)…"):
            rag = get_rag_index(
                "v1",
                cfg["rag"]["knowledge_dir"],
                cfg["rag"]["embedding_model"],
                cfg["rag"]["index_path"],
                cfg["rag"]["top_k"],
            )

    client = None
    if usar_llm_zero or usar_llm_rag:
        client = LLMClient(
            model=cfg["llm"]["model"],
            temperature=cfg["llm"]["temperature"],
            max_tokens=cfg["llm"]["max_tokens"],
            cache_dir=ROOT / cfg["salidas"]["cache_dir"],
            mock=mock_llm,
            cost_input_per_1m=cfg["llm"]["cost_input_per_1m"],
            cost_output_per_1m=cfg["llm"]["cost_output_per_1m"],
        )

    progress = st.progress(0, text="Analizando oraciones…")
    with st.spinner("Procesando nota…"):
        resultado = analizar_nota(
            nota,
            cfg=cfg,
            brazos=brazos,
            mock_llm=mock_llm,
            idioma=idioma,
            modelo_tfidf=modelo,
            client=client,
            rag=rag,
        )
    progress.progress(100, text="Listo")

    if resultado.truncado:
        st.warning(
            f"La nota tiene {resultado.n_total} oraciones; "
            f"se analizaron las primeras 20 en esta demo."
        )

    top = resultado.top1(brazos)
    if top is None:
        st.info("No se detectaron oraciones en la nota.")
        st.stop()

    top_sid = top.sid
    st.subheader("Resumen")
    c1, c2, c3 = st.columns(3)
    c1.metric("Oraciones analizadas", len(resultado.oraciones))
    c2.metric("Score localización", f"{top.score_localizacion(brazos):.2f}")
    c3.metric("Brazo localización", top.brazo_localizacion(brazos) or "—")

    st.markdown("**Oración más sospechosa:**")
    _render_oracion(top, top_sid, umbral, brazos)

    st.subheader("Detalle por oración")
    filas = []
    for res in resultado.oraciones:
        fila = {
            "#": res.sid + 1,
            "Oración": res.oracion[:80] + ("…" if len(res.oracion) > 80 else ""),
            "Estado": _badge_alerta(res.alerta(umbral, brazos)),
        }
        if usar_tfidf:
            fila["TF-IDF"] = _fmt_score(res.score_tfidf)
        if usar_llm_zero:
            fila["LLM zero"] = _fmt_score(res.score_llm_zero)
        if usar_llm_rag:
            fila["LLM+RAG"] = _fmt_score(res.score_llm_rag)
        filas.append(fila)

    st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

    for res in resultado.oraciones:
        if res.sid == top_sid:
            _render_oracion(res, top_sid, umbral, brazos)
        elif res.alerta(umbral, brazos):
            _render_oracion(res, top_sid, umbral, brazos)

    with st.expander("¿Qué hace cada brazo?"):
        st.markdown(EXPLICACION_BRAZOS)

    if usar_llm_rag and top.rag_context:
        with st.expander("Contexto RAG recuperado (oración top-1)"):
            st.text(top.rag_context)

    with st.expander("Métricas de referencia S7"):
        for k, v in METRICAS_REFERENCIA.items():
            st.write(f"**{k}:** {v}")


if __name__ == "__main__":
    main()
