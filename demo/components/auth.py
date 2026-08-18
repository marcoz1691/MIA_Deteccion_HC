"""Autenticación opcional y registro de auditoría sin texto clínico."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from demo.bootstrap import ROOT

AUDIT_PATH = ROOT / "salidas_s7" / "audit.log"


def _auth_enabled() -> bool:
    try:
        return bool(st.secrets.get("ENABLE_AUTH", False))
    except Exception:
        return False


def _get_users() -> dict[str, str]:
    try:
        users = st.secrets.get("AUTH_USERS", {})
        return dict(users) if users else {}
    except Exception:
        return {}


def require_auth() -> bool:
    """Retorna True si el usuario está autenticado o auth está desactivado."""
    if not _auth_enabled():
        return True

    if st.session_state.get("authenticated"):
        return True

    st.subheader("Inicio de sesión")
    st.caption("Autenticación requerida para acceder al prototipo.")

    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar", type="primary")

    if submitted:
        users = _get_users()
        if username in users and users[username] == password:
            st.session_state.authenticated = True
            st.session_state.auth_user = username
            st.rerun()
        st.error("Credenciales incorrectas.")

    return False


def logout_button() -> None:
    if _auth_enabled() and st.session_state.get("authenticated"):
        if st.sidebar.button("Cerrar sesión"):
            st.session_state.authenticated = False
            st.session_state.pop("auth_user", None)
            st.rerun()


def log_audit_event(
    *,
    nota_hash: str,
    n_oraciones: int,
    brazos: list[str],
    mock_llm: bool,
    alerta: bool,
) -> None:
    """Registra evento de análisis sin almacenar texto clínico."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": st.session_state.get("auth_user", "anonymous"),
        "nota_sha256": nota_hash,
        "n_oraciones": n_oraciones,
        "brazos": brazos,
        "mock_llm": mock_llm,
        "alerta": alerta,
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def hash_nota(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()
