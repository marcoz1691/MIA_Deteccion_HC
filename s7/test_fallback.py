"""Prueba del fallback producción: API LLM caída → TF-IDF solo + alerta."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from s7.inferencia import analizar_nota
from s7.llm_client import LLMClient, LLMUnavailableError


class _FakeModelo:
    def predict_proba(self, texts):
        n = len(list(texts))
        # Score creciente por posición para verificar localización
        scores = np.linspace(0.1, 0.9, n).reshape(-1, 1)
        return np.hstack([1 - scores, scores])


class _FailingCompletions:
    def create(self, **kwargs):
        raise ConnectionError("simulated API outage")


class _FailingOpenAI:
    def __init__(self):
        self.chat = type("chat", (), {"completions": _FailingCompletions()})()


def _client_que_falla(cache_dir: Path) -> LLMClient:
    # Construir en mock y luego forzar ruta API que siempre falla (sin key real).
    client = LLMClient(
        mock=True,
        cache_dir=cache_dir,
        max_retries=2,
        retry_base_delay_s=0.01,
    )
    client.mock = False
    client._client = _FailingOpenAI()
    return client


def test_llm_unavailable_tras_reintentos():
    with tempfile.TemporaryDirectory() as tmp:
        client = _client_que_falla(Path(tmp))
        try:
            client.complete("prompt de prueba", brazo="llm_zero")
            raise AssertionError("debía lanzar LLMUnavailableError")
        except LLMUnavailableError:
            pass
        assert client.stats["api_errors"] >= 2
        assert client.stats["retries"] >= 1


def test_analizar_nota_degrada_a_tfidf():
    nota = (
        "Paciente con alergia a penicilina. "
        "Se prescribe amoxicilina 500 mg. "
        "Control en una semana."
    )
    with tempfile.TemporaryDirectory() as tmp:
        client = _client_que_falla(Path(tmp))
        resultado = analizar_nota(
            nota,
            cfg={
                "salidas": {"modelo_tfidf": "unused.joblib", "cache_dir": tmp},
                "llm": {},
                "rag": {},
            },
            brazos=["tfidf", "llm_zero"],
            mock_llm=False,
            idioma="spanish",
            modelo_tfidf=_FakeModelo(),
            client=client,
            rag=None,
            fallback_tfidf=True,
        )

    assert resultado.modo_degradado is True
    assert resultado.brazos_efectivos == ["tfidf"]
    assert resultado.mensaje_fallback is not None
    assert "TF-IDF" in resultado.mensaje_fallback
    assert len(resultado.oraciones) >= 2
    for res in resultado.oraciones:
        assert res.score_tfidf is not None
        assert res.score_llm_zero is None
        assert res.score_llm_rag is None

    top = resultado.top1()
    assert top is not None
    assert top.brazo_localizacion(["tfidf"]) == "TF-IDF"


def test_sin_fallback_propaga_error():
    with tempfile.TemporaryDirectory() as tmp:
        client = _client_que_falla(Path(tmp))
        try:
            analizar_nota(
                "Oración corta de prueba.",
                cfg={"salidas": {"modelo_tfidf": "x", "cache_dir": tmp}, "llm": {}, "rag": {}},
                brazos=["llm_zero"],
                mock_llm=False,
                modelo_tfidf=_FakeModelo(),
                client=client,
                fallback_tfidf=False,
            )
            raise AssertionError("debía propagar LLMUnavailableError")
        except LLMUnavailableError:
            pass


if __name__ == "__main__":
    test_llm_unavailable_tras_reintentos()
    test_analizar_nota_degrada_a_tfidf()
    test_sin_fallback_propaga_error()
    print("OK — fallback TF-IDF verificado")
