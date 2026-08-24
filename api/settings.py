"""Variables de entorno del backend (mock LLM, claves API)."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str) -> bool | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    return raw.strip().lower() in ("1", "true", "yes", "on")


def llm_api_configurada() -> bool:
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("MISTRAL_API_KEY"))


def resolve_mock_llm(request_mock_llm: bool) -> tuple[bool, bool]:
    """Resuelve si usar mock LLM.

    Returns:
        (mock_efectivo, forzado_por_env): si ``MOCK_LLM`` está definido en el entorno
        del servidor, ignora el valor enviado por el cliente.
    """
    forced = _env_bool("MOCK_LLM")
    if forced is not None:
        return forced, True
    return request_mock_llm, False
