"""Demo interactiva — detección de inconsistencias en historias clínicas (CITIMED)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "_demo_boot", Path(__file__).resolve().parent / "_boot.py"
)
_boot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_boot)
ROOT = _boot.repo_root(__file__)

import streamlit as st

from demo.components.auth import hash_nota, log_audit_event, logout_button, require_auth
from demo.components.input_panel import render_input_panel
from demo.components.results_panel import render_results_panel
from demo.components.security import render_consent_gate, render_security_banner
from demo.components.sidebar import render_main_sidebar
from demo.components.ui import STRINGS_ES, page_config, render_empty_state, render_footer, render_hero
from demo.ejemplos import listar_ejemplos
from demo.state import (
    get_brazos,
    get_config,
    get_modelo_tfidf,
    get_rag_index,
    init_session_state,
    model_path_from_config,
)
from s7.inferencia import Brazo, analizar_nota
from s7.llm_client import LLMClient, LLMUnavailableError


def main() -> None:
    page_config("Análisis")
    init_session_state()

    if not require_auth():
        st.stop()

    cfg = get_config()
    model_path = model_path_from_config(cfg)
    mock_llm = st.session_state.mock_llm
    brazos: list[Brazo] = get_brazos()  # type: ignore[assignment]

    render_main_sidebar(model_path, st.session_state.usar_llm_rag)
    logout_button()

    render_hero(STRINGS_ES["hero_title"], STRINGS_ES["hero_subtitle"])
    render_security_banner(mock_llm)

    if not brazos:
        st.warning("Selecciona al menos un brazo en la página Configuración.")
        render_empty_state()
        render_footer()
        st.stop()

    modelo_ok = model_path.exists()
    if st.session_state.usar_tfidf and not modelo_ok:
        st.error(
            f"Modelo TF-IDF no encontrado en `{model_path}`.\n\n"
            "Entrena el modelo una vez:\n"
            "```bash\n"
            "git clone --depth 1 https://github.com/abachaa/MEDEC.git medec_try\n"
            "python s6/modelo_ajustado.py\n"
            "```"
        )
        render_footer()
        st.stop()

    can_analyze = render_consent_gate(mock_llm)
    solo_tfidf = (
        st.session_state.usar_tfidf
        and not st.session_state.usar_llm_zero
        and not st.session_state.usar_llm_rag
    )

    ejemplos = listar_ejemplos()
    nota, analizar = render_input_panel(
        ejemplos,
        solo_tfidf=solo_tfidf,
        can_analyze=can_analyze,
    )

    if not analizar:
        render_empty_state()
        with st.expander("¿Qué hace cada brazo?", expanded=False):
            st.markdown(STRINGS_ES["explicacion_brazos"])
        render_footer()
        st.stop()

    if not nota.strip():
        st.warning("Ingresa una nota clínica o selecciona un ejemplo.")
        render_footer()
        st.stop()

    modelo = get_modelo_tfidf(str(model_path)) if st.session_state.usar_tfidf else None
    rag = None
    if st.session_state.usar_llm_rag:
        with st.spinner("Cargando índice RAG (primera vez puede tardar ~15 s)…"):
            rag = get_rag_index(
                "v1",
                cfg["rag"]["knowledge_dir"],
                cfg["rag"]["embedding_model"],
                cfg["rag"]["index_path"],
                cfg["rag"]["top_k"],
            )

    client = None
    if st.session_state.usar_llm_zero or st.session_state.usar_llm_rag:
        llm_cfg = cfg.get("llm", {})
        try:
            client = LLMClient(
                model=llm_cfg.get("model", "gpt-4o-mini"),
                temperature=llm_cfg.get("temperature", 0),
                max_tokens=llm_cfg.get("max_tokens", 10),
                cache_dir=ROOT / cfg["salidas"]["cache_dir"],
                mock=mock_llm,
                cost_input_per_1m=llm_cfg.get("cost_input_per_1m", 0.15),
                cost_output_per_1m=llm_cfg.get("cost_output_per_1m", 0.60),
                max_retries=llm_cfg.get("max_retries", 3),
                retry_base_delay_s=llm_cfg.get("retry_base_delay_s", 0.5),
                allow_mock_without_key=bool(mock_llm),
            )
        except LLMUnavailableError as exc:
            if not modelo_ok:
                st.error(
                    f"API LLM no disponible y no hay modelo TF-IDF para fallback.\n\n{exc}\n\n"
                    "Entrena el modelo TF-IDF o activa el modo mock LLM."
                )
                render_footer()
                st.stop()
            st.warning(
                "API LLM no disponible al iniciar. Se usará solo TF-IDF "
                "(fallback de producción)."
            )
            brazos = ["tfidf"]  # type: ignore[assignment]
            client = None
            if modelo is None:
                modelo = get_modelo_tfidf(str(model_path))

    progress = st.progress(0, text="Analizando oraciones…")
    with st.spinner("Procesando nota…"):
        resultado = analizar_nota(
            nota,
            cfg=cfg,
            brazos=brazos,
            mock_llm=mock_llm,
            idioma=st.session_state.idioma,
            modelo_tfidf=modelo if modelo_ok else None,
            client=client,
            rag=rag,
            fallback_tfidf=modelo_ok,
        )
    progress.progress(100, text="Listo")

    brazos_ui = resultado.brazos_efectivos or brazos

    if resultado.modo_degradado:
        st.error(
            "Modo degradado — fallback a TF-IDF\n\n"
            + (resultado.mensaje_fallback or "API LLM caída; sin detección semántica.")
        )
        st.info(
            "El sistema sigue localizando oraciones sospechosas con el modelo léxico. "
            "Un médico debe revisar la nota; no hay juicio semántico del LLM."
        )

    top = resultado.top1(brazos_ui)
    score_loc = top.score_localizacion(brazos_ui) if top else 0.0
    log_audit_event(
        nota_hash=hash_nota(nota),
        n_oraciones=len(resultado.oraciones),
        brazos=list(brazos_ui),
        mock_llm=mock_llm,
        alerta=score_loc >= st.session_state.umbral,
    )

    render_results_panel(
        resultado,
        brazos_ui,
        st.session_state.umbral,
        usar_tfidf=st.session_state.usar_tfidf or resultado.modo_degradado,
        usar_llm_zero=st.session_state.usar_llm_zero and "llm_zero" in brazos_ui,
        usar_llm_rag=st.session_state.usar_llm_rag and "llm_rag" in brazos_ui,
        modo_degradado=resultado.modo_degradado,
    )
    render_footer()


if __name__ == "__main__":
    main()
