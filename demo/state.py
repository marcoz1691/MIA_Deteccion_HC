"""Session state y recursos cacheados para la demo."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from demo.bootstrap import ROOT
from s7.inferencia import cargar_config, cargar_modelo_tfidf
from s7.rag_index import RAGIndex

CONFIG_DEFAULTS = {
    "usar_tfidf": True,
    "usar_llm_zero": True,
    "usar_llm_rag": True,
    "mock_llm": True,
    "idioma": "spanish",
    "umbral": 0.5,
    "consent_phi": False,
    "ultimo_ejemplo": "— Escribir nota propia —",
    "nota_clinica": "",
}


def init_session_state() -> None:
    for key, value in CONFIG_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_brazos() -> list[str]:
    brazos: list[str] = []
    if st.session_state.get("usar_tfidf"):
        brazos.append("tfidf")
    if st.session_state.get("usar_llm_zero"):
        brazos.append("llm_zero")
    if st.session_state.get("usar_llm_rag"):
        brazos.append("llm_rag")
    return brazos


@st.cache_resource
def get_config():
    return cargar_config(ROOT / "s7" / "config.yaml")


@st.cache_resource
def get_modelo_tfidf(model_path: str):
    return cargar_modelo_tfidf(model_path)


@st.cache_resource
def get_rag_index(
    _cfg_hash: str,
    knowledge_dir: str,
    embedding_model: str,
    index_path: str,
    top_k: int,
):
    return RAGIndex(
        knowledge_dir=ROOT / knowledge_dir,
        embedding_model=embedding_model,
        index_path=ROOT / index_path,
        top_k=top_k,
    ).load()


def model_path_from_config(cfg: dict) -> Path:
    return ROOT / cfg["salidas"]["modelo_tfidf"]
