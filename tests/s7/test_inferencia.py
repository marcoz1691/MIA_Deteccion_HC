"""TC-ML-01..09 — Pipeline s7/inferencia.py."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from s7.inferencia import (
    ResultadoOracion,
    analizar_nota,
    segmentar_nota,
)
from s7.llm_client import LLMClient
from s7.prompts import parse_yes_no
from s7.test_fallback import _FakeModelo
from tests.fixtures.notas import NOTA_MEDICACION, NOTA_PLAN


@pytest.mark.regression
def test_tc_ml_01_segmentacion_minima():
    """TC-ML-01: Oraciones <3 chars ignoradas."""
    segmentos = segmentar_nota("Ok. AB. Texto válido aquí.")
    textos = [t for _, t in segmentos]
    assert "AB" not in textos
    assert any("Texto válido" in t for t in textos)


@pytest.mark.regression
def test_no_segmenta_titulos_ni_subtitulos_de_la_hc():
    nota = """
    --- EVOLUCIÓN 1 ---
    FECHA: 2026-07-06  HORA: 09:06
    NOTAS DE EVOLUCIÓN:
    NOTA DE INGRESO
    PACIENTE MASCULINO DE 39 AÑOS.
    ENFERMEDAD ACTUAL:
    PACIENTE FEMENINO CON ANTECEDENTE DE METAPLASIA.
    EXAMEN FISICO:
    SIGNOS VITALES: PA: 120/77 FC: 82
    """
    textos = [t for _, t in segmentar_nota(nota)]
    assert not any(t.upper().strip(": ").endswith("INGRESO") and len(t) < 40 for t in textos if "PACIENTE" not in t.upper())
    assert "NOTA DE INGRESO" not in textos
    assert "ENFERMEDAD ACTUAL:" not in textos
    assert "EXAMEN FISICO:" not in textos
    assert "--- EVOLUCIÓN 1 ---" not in textos
    assert any("PACIENTE MASCULINO" in t for t in textos)
    assert any("PACIENTE FEMENINO" in t for t in textos)
    assert any("PA: 120/77" in t for t in textos)


@pytest.mark.regression
def test_tc_ml_02_formula_combinada():
    """TC-ML-02: score_localizacion = 0.65×LLM + 0.35×TF-IDF."""
    res = ResultadoOracion(sid=0, oracion="test", score_tfidf=0.4, score_llm_zero=0.8)
    score = res.score_localizacion(["tfidf", "llm_zero"])
    assert score == pytest.approx(0.8 * 0.65 + 0.4 * 0.35)


@pytest.mark.regression
def test_tc_ml_03_preferencia_llm_rag():
    """TC-ML-03: llm_rag preferido sobre llm_zero en score_localizacion."""
    res = ResultadoOracion(
        sid=0,
        oracion="test",
        score_tfidf=0.2,
        score_llm_zero=0.5,
        score_llm_rag=0.9,
    )
    score = res.score_localizacion(["tfidf", "llm_zero", "llm_rag"])
    assert score == pytest.approx(0.9 * 0.65 + 0.2 * 0.35)


@pytest.mark.regression
@pytest.mark.parametrize(
    "respuesta,idioma,esperado",
    [
        ("YES", "english", 1.0),
        ("SI", "spanish", 1.0),
        ("SÍ", "spanish", 1.0),
        ("NO", "english", 0.0),
        ("maybe", "english", 0.5),
    ],
)
def test_tc_ml_04_parsing_llm(respuesta, idioma, esperado):
    """TC-ML-04: Parsing LLM YES/NO/SÍ."""
    assert parse_yes_no(respuesta, idioma) == esperado


@pytest.mark.regression
def test_tc_ml_05_mock_heuristics_medicacion():
    """TC-ML-05: Mock detecta penicilina+amoxicilina."""
    with tempfile.TemporaryDirectory() as tmp:
        client = LLMClient(mock=True, cache_dir=Path(tmp))
        resultado = analizar_nota(
            NOTA_MEDICACION,
            cfg={"salidas": {"modelo_tfidf": "x", "cache_dir": tmp}, "llm": {}, "rag": {}},
            brazos=["llm_zero"],
            mock_llm=True,
            idioma="spanish",
            client=client,
        )
    alertas = [o for o in resultado.oraciones if o.score_llm_zero == 1.0]
    assert len(alertas) >= 1
    assert any("amoxicilina" in o.oracion.lower() for o in alertas)


@pytest.mark.regression
def test_mvp_sexo_lo_marca_el_llm_con_la_nota_completa():
    """PACIENTE FEMENINO contradice MASCULINO en la nota → score LLM, no regla forzada."""
    nota = (
        "PACIENTE MASCULINO DE 39 AÑOS. "
        "ENFERMEDAD ACTUAL: PACIENTE FEMENINO CON ANTECEDENTE DE METAPLASIA GASTRICA."
    )
    with tempfile.TemporaryDirectory() as tmp:
        client = LLMClient(mock=True, cache_dir=Path(tmp))
        resultado = analizar_nota(
            nota,
            cfg={"salidas": {"modelo_tfidf": "x", "cache_dir": tmp}, "llm": {}, "rag": {}},
            brazos=["llm_zero"],
            mock_llm=True,
            idioma="spanish",
            client=client,
        )
    femeninas = [o for o in resultado.oraciones if "femenino" in o.oracion.lower()]
    assert femeninas
    assert femeninas[0].score_llm_zero == 1.0
    assert femeninas[0].alerta(0.5, ["llm_zero"]) is True


@pytest.mark.regression
def test_tc_ml_06_top1_tie_break():
    """TC-ML-06: Empate de score → menor sid."""
    oraciones = [
        ResultadoOracion(sid=2, oracion="b", score_tfidf=0.7),
        ResultadoOracion(sid=0, oracion="a", score_tfidf=0.7),
        ResultadoOracion(sid=1, oracion="c", score_tfidf=0.5),
    ]
    from s7.inferencia import oracion_top1

    top = oracion_top1(oraciones, ["tfidf"])
    assert top.sid == 0


@pytest.mark.regression
def test_tc_ml_07_cache_llm():
    """TC-ML-07: Segunda llamada idéntica usa cache."""
    with tempfile.TemporaryDirectory() as tmp:
        client = LLMClient(mock=True, cache_dir=Path(tmp))
        prompt = "test prompt"
        r1 = client.complete(prompt, brazo="llm_zero")
        r2 = client.complete(prompt, brazo="llm_zero")
        assert r1["cached"] is False
        assert r2["cached"] is True
        assert client.stats["cache_hits"] >= 1


@pytest.mark.regression
def test_tc_ml_08_rag_lazy_load():
    """TC-ML-08: Primera llamada llm_rag construye índice FAISS."""
    from s7.inferencia import cargar_config
    from api.service import resolve_cfg_paths

    root = Path(__file__).resolve().parent.parent.parent
    cfg = resolve_cfg_paths(cargar_config(root / "s7" / "config.yaml"))

    with tempfile.TemporaryDirectory() as tmp:
        cfg["salidas"]["cache_dir"] = tmp
        client = LLMClient(mock=True, cache_dir=Path(tmp))
        resultado = analizar_nota(
            NOTA_PLAN,
            cfg=cfg,
            brazos=["llm_rag"],
            mock_llm=True,
            client=client,
        )
    assert len(resultado.oraciones) >= 1
    assert any(o.score_llm_rag is not None for o in resultado.oraciones)


@pytest.mark.regression
def test_tc_ml_09_fallback_happy_path():
    """TC-ML-09: Happy path TF-IDF sin LLM."""
    with tempfile.TemporaryDirectory() as tmp:
        resultado = analizar_nota(
            NOTA_MEDICACION,
            cfg={"salidas": {"modelo_tfidf": "x", "cache_dir": tmp}, "llm": {}, "rag": {}},
            brazos=["tfidf"],
            modelo_tfidf=_FakeModelo(),
        )
    assert resultado.modo_degradado is False
    assert all(o.score_tfidf is not None for o in resultado.oraciones)
    assert resultado.top1() is not None


@pytest.mark.regression
def test_analiza_todas_las_frases_no_solo_las_primeras_20():
    """Una nota de 84 frases debe analizarse completa, no truncarse a 20."""
    texto = ". ".join(
        f"Frase clinica numero {i} para revision del prototipo" for i in range(1, 85)
    ) + "."
    with tempfile.TemporaryDirectory() as tmp:
        client = LLMClient(mock=True, cache_dir=Path(tmp))
        resultado = analizar_nota(
            texto,
            cfg={"salidas": {"modelo_tfidf": "x", "cache_dir": tmp}, "llm": {}, "rag": {}},
            brazos=["llm_zero"],
            mock_llm=True,
            client=client,
        )
    assert resultado.n_total == 84
    assert resultado.truncado is False
    assert len(resultado.oraciones) == 84
