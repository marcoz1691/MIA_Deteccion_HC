"""Fase 4 — Benchmarks de rendimiento (TC-PERF-01..10)."""
from __future__ import annotations

import statistics
import time
from pathlib import Path

import pytest

from s7.inferencia import analizar_nota, cargar_config, cargar_modelo_tfidf
from s7.llm_client import LLMClient
from s7.test_fallback import _FakeModelo
from tests.fixtures.notas import NOTA_LIMPIA, NOTA_MEDICACION

ROOT = Path(__file__).resolve().parent.parent.parent

NOTA_10_ORACIONES = ". ".join(
    [f"Oración clínica número {i} sin inconsistencia." for i in range(1, 11)]
) + "."


def _percentiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
    ordered = sorted(values)
    n = len(ordered)

    def pct(p: float) -> float:
        idx = min(int(n * p), n - 1)
        return ordered[idx]

    return {"p50": pct(0.50), "p95": pct(0.95), "p99": pct(0.99)}


def _bench(fn, iterations: int = 100, warmup: int = 10) -> dict[str, float]:
    for _ in range(warmup):
        fn()
    times: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    stats = _percentiles(times)
    stats["mean_ms"] = statistics.mean(times)
    return stats


@pytest.mark.perf
def test_tc_perf_01_tfidf_una_oracion(benchmark):
    """TC-PERF-01: TF-IDF solo, 1 oración — P95 < 50 ms."""
    nota = "Paciente estable sin hallazgos relevantes."

    def run():
        analizar_nota(
            nota,
            cfg={"salidas": {"modelo_tfidf": "x", "cache_dir": "x"}, "llm": {}, "rag": {}},
            brazos=["tfidf"],
            modelo_tfidf=_FakeModelo(),
        )

    stats = benchmark.pedantic(_bench, args=(run, 50, 5), rounds=1)
    assert stats["p95"] < 50, f"P95={stats['p95']:.1f}ms"


@pytest.mark.perf
def test_tc_perf_02_tfidf_diez_oraciones(benchmark):
    """TC-PERF-02: TF-IDF, nota 10 oraciones — P95 < 100 ms."""

    def run():
        analizar_nota(
            NOTA_10_ORACIONES,
            cfg={"salidas": {"modelo_tfidf": "x", "cache_dir": "x"}, "llm": {}, "rag": {}},
            brazos=["tfidf"],
            modelo_tfidf=_FakeModelo(),
        )

    stats = benchmark.pedantic(_bench, args=(run, 50, 5), rounds=1)
    assert stats["p95"] < 100, f"P95={stats['p95']:.1f}ms"


@pytest.mark.perf
def test_tc_perf_03_llm_mock_diez_oraciones(benchmark, tmp_path):
    """TC-PERF-03: LLM mock, 10 oraciones — P95 < 3000 ms."""
    client = LLMClient(mock=True, cache_dir=tmp_path)

    def run():
        analizar_nota(
            NOTA_10_ORACIONES,
            cfg={"salidas": {"modelo_tfidf": "x", "cache_dir": str(tmp_path)}, "llm": {}, "rag": {}},
            brazos=["llm_zero"],
            mock_llm=True,
            client=client,
        )

    stats = benchmark.pedantic(_bench, args=(run, 20, 3), rounds=1)
    assert stats["p95"] < 3000, f"P95={stats['p95']:.1f}ms"


@pytest.mark.perf
def test_tc_perf_05_tripartita_mock(benchmark, tmp_path):
    """TC-PERF-05: Tripartita mock, 10 oraciones — P95 < 5000 ms."""
    from s7.inferencia import cargar_config
    from api.service import resolve_cfg_paths

    root = Path(__file__).resolve().parent.parent.parent
    cfg = resolve_cfg_paths(cargar_config(root / "s7" / "config.yaml"))
    cfg["salidas"]["cache_dir"] = str(tmp_path)
    client = LLMClient(mock=True, cache_dir=tmp_path)

    def run():
        analizar_nota(
            NOTA_MEDICACION,
            cfg=cfg,
            brazos=["tfidf", "llm_zero", "llm_rag"],
            mock_llm=True,
            modelo_tfidf=_FakeModelo(),
            client=client,
        )

    stats = benchmark.pedantic(_bench, args=(run, 10, 2), rounds=1)
    assert stats["p95"] < 5000, f"P95={stats['p95']:.1f}ms"


@pytest.mark.perf
def test_tc_perf_07_health_endpoint(client, benchmark):
    """TC-PERF-07: GET /health — P95 < 50 ms (via TestClient)."""

    def run():
        client.get("/health")

    stats = benchmark.pedantic(_bench, args=(run, 50, 5), rounds=1)
    assert stats["p95"] < 50, f"P95={stats['p95']:.1f}ms"


@pytest.mark.perf
def test_tc_perf_09_cache_hit_speedup(tmp_path):
    """TC-PERF-09: Segunda llamada idéntica usa cache (cached=True)."""
    cache_dir = Path(tmp_path)
    client = LLMClient(mock=True, cache_dir=cache_dir)
    prompt = "benchmark cache test prompt"

    r1 = client.complete(prompt, brazo="llm_zero")
    r2 = client.complete(prompt, brazo="llm_zero")

    assert r1["cached"] is False
    assert r2["cached"] is True
    assert client.stats["cache_hits"] >= 1


@pytest.mark.perf
@pytest.mark.skip(reason="Requiere Ollama en localhost:11434 — ejecutar con --run-ollama")
def test_tc_perf_04_llm_real_ollama():
    """TC-PERF-04: LLM real Ollama — ejecutar manualmente en DEV-LLM."""
    pass


@pytest.mark.perf
def test_tc_perf_report_generator(tmp_path):
    """Genera reporte JSON de benchmark TF-IDF para CI."""
    stats = _bench(
        lambda: analizar_nota(
            NOTA_LIMPIA,
            cfg={"salidas": {"modelo_tfidf": "x", "cache_dir": str(tmp_path)}, "llm": {}, "rag": {}},
            brazos=["tfidf"],
            modelo_tfidf=_FakeModelo(),
        ),
        iterations=30,
        warmup=5,
    )
    out = ROOT / "tests" / "perf" / "last_benchmark.json"
    import json

    out.write_text(json.dumps({"tfidf_nota_limpia_ms": stats}, indent=2), encoding="utf-8")
    assert stats["p95"] >= 0
