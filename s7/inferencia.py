"""Inferencia interactiva: segmentación de notas y scoring por brazo (TF-IDF / LLM / RAG)."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import yaml

from s7.llm_client import LLMClient
from s7.prompts import get_prompt, parse_yes_no
from s7.rag_index import RAGIndex

Idioma = Literal["english", "spanish"]
Brazo = Literal["tfidf", "llm_zero", "llm_rag"]

MAX_ORACIONES_DEMO = 20


@dataclass
class ResultadoOracion:
    sid: int
    oracion: str
    score_tfidf: float | None = None
    score_llm_zero: float | None = None
    score_llm_rag: float | None = None
    respuesta_llm_zero: str | None = None
    respuesta_llm_rag: str | None = None
    latencia_llm_zero_ms: float | None = None
    latencia_llm_rag_ms: float | None = None
    rag_context: str | None = None

    def score_max(self, brazos: list[Brazo]) -> float:
        scores = []
        if "tfidf" in brazos and self.score_tfidf is not None:
            scores.append(self.score_tfidf)
        if "llm_zero" in brazos and self.score_llm_zero is not None:
            scores.append(self.score_llm_zero)
        if "llm_rag" in brazos and self.score_llm_rag is not None:
            scores.append(self.score_llm_rag)
        return max(scores) if scores else 0.0

    def brazo_top(self, brazos: list[Brazo]) -> str | None:
        candidatos: list[tuple[str, float]] = []
        if "tfidf" in brazos and self.score_tfidf is not None:
            candidatos.append(("TF-IDF", self.score_tfidf))
        if "llm_zero" in brazos and self.score_llm_zero is not None:
            candidatos.append(("LLM zero-shot", self.score_llm_zero))
        if "llm_rag" in brazos and self.score_llm_rag is not None:
            candidatos.append(("LLM + RAG", self.score_llm_rag))
        if not candidatos:
            return None
        return max(candidatos, key=lambda x: x[1])[0]

    def score_localizacion(self, brazos: list[Brazo]) -> float:
        """Score para resaltar la oración a revisar."""
        tf = self.score_tfidf if "tfidf" in brazos else None
        llm = None
        if "llm_rag" in brazos and self.score_llm_rag is not None:
            llm = self.score_llm_rag
        elif "llm_zero" in brazos and self.score_llm_zero is not None:
            llm = self.score_llm_zero
        if llm is not None and tf is not None:
            return llm * 0.65 + tf * 0.35
        if tf is not None:
            return tf
        if llm is not None:
            return llm
        return 0.0

    def brazo_localizacion(self, brazos: list[Brazo]) -> str | None:
        tf = self.score_tfidf if "tfidf" in brazos else None
        llm = None
        llm_name = None
        if "llm_rag" in brazos and self.score_llm_rag is not None:
            llm, llm_name = self.score_llm_rag, "LLM + RAG"
        elif "llm_zero" in brazos and self.score_llm_zero is not None:
            llm, llm_name = self.score_llm_zero, "LLM zero-shot"
        if llm is not None and tf is not None:
            return llm_name if llm >= tf else "TF-IDF"
        if tf is not None:
            return "TF-IDF"
        return llm_name

    def alerta(self, umbral: float, brazos: list[Brazo]) -> bool:
        return self.score_localizacion(brazos) >= umbral


@dataclass
class ResultadoNota:
    oraciones: list[ResultadoOracion] = field(default_factory=list)
    truncado: bool = False
    n_total: int = 0

    def top1(self, brazos: list[Brazo]) -> ResultadoOracion | None:
        if not self.oraciones:
            return None
        return max(
            self.oraciones,
            key=lambda r: (r.score_localizacion(brazos), -r.sid),
        )


def cargar_config(path: str | Path = "s7/config.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def segmentar_nota(texto: str) -> list[tuple[int, str]]:
    """Parte texto libre en oraciones numeradas (sid, texto)."""
    texto = str(texto).strip()
    if not texto:
        return []
    partes = re.split(r"(?<=[.!?])\s+|\n+", texto)
    out: list[tuple[int, str]] = []
    for parte in partes:
        oracion = parte.strip()
        if len(oracion) >= 3:
            out.append((len(out), oracion))
    return out


def cargar_modelo_tfidf(path: str | Path):
    model_path = Path(path)
    if not model_path.exists():
        raise FileNotFoundError(f"Modelo TF-IDF no encontrado: {model_path}")
    return joblib.load(model_path)


def puntuar_tfidf(oraciones: list[str], modelo) -> tuple[np.ndarray, float]:
    t0 = time.perf_counter()
    if not oraciones:
        return np.array([]), 0.0
    scores = modelo.predict_proba(oraciones)[:, 1]
    lat_ms = (time.perf_counter() - t0) / len(oraciones) * 1000
    return scores, lat_ms


def puntuar_llm(
    oracion: str,
    client: LLMClient,
    mode: str,
    idioma: Idioma,
    rag: RAGIndex | None = None,
    nota_context: str = "",
) -> tuple[float, str, float, str | None]:
    contexto = rag.retrieve(oracion) if mode == "rag" and rag else ""
    prompt = get_prompt(mode, idioma, oracion, contexto)
    brazo = f"llm_{mode}"
    resp = client.complete(prompt, brazo=brazo, nota_context=nota_context)
    score = parse_yes_no(resp["text"], idioma)
    return score, resp["text"], resp["latency_ms"], contexto or None


def analizar_nota(
    texto: str,
    cfg: dict | None = None,
    brazos: list[Brazo] | None = None,
    mock_llm: bool = True,
    idioma: Idioma = "spanish",
    modelo_tfidf=None,
    client: LLMClient | None = None,
    rag: RAGIndex | None = None,
    max_oraciones: int = MAX_ORACIONES_DEMO,
) -> ResultadoNota:
    cfg = cfg or cargar_config()
    brazos = brazos or ["tfidf", "llm_zero", "llm_rag"]

    segmentos = segmentar_nota(texto)
    n_total = len(segmentos)
    truncado = n_total > max_oraciones
    if truncado:
        segmentos = segmentos[:max_oraciones]

    textos = [t for _, t in segmentos]
    resultados = [ResultadoOracion(sid=sid, oracion=txt) for sid, txt in segmentos]

    if "tfidf" in brazos:
        if modelo_tfidf is None:
            model_path = Path(cfg["salidas"]["modelo_tfidf"])
            modelo_tfidf = cargar_modelo_tfidf(model_path)
        scores, _ = puntuar_tfidf(textos, modelo_tfidf)
        for i, score in enumerate(scores):
            resultados[i].score_tfidf = float(score)

    llm_brazos = [b for b in brazos if b.startswith("llm_")]
    if llm_brazos:
        if client is None:
            client = LLMClient(
                model=cfg["llm"]["model"],
                temperature=cfg["llm"]["temperature"],
                max_tokens=cfg["llm"]["max_tokens"],
                cache_dir=cfg["salidas"]["cache_dir"],
                mock=mock_llm,
                cost_input_per_1m=cfg["llm"]["cost_input_per_1m"],
                cost_output_per_1m=cfg["llm"]["cost_output_per_1m"],
            )
        if "llm_rag" in llm_brazos and rag is None:
            rag = RAGIndex(
                knowledge_dir=cfg["rag"]["knowledge_dir"],
                embedding_model=cfg["rag"]["embedding_model"],
                index_path=cfg["rag"]["index_path"],
                top_k=cfg["rag"]["top_k"],
            ).load()

        for res in resultados:
            if "llm_zero" in llm_brazos:
                score, text, lat, _ = puntuar_llm(
                    res.oracion, client, "zero_shot", idioma, rag=None, nota_context=texto
                )
                res.score_llm_zero = score
                res.respuesta_llm_zero = text
                res.latencia_llm_zero_ms = lat
            if "llm_rag" in llm_brazos:
                score, text, lat, ctx = puntuar_llm(
                    res.oracion, client, "rag", idioma, rag=rag, nota_context=texto
                )
                res.score_llm_rag = score
                res.respuesta_llm_rag = text
                res.latencia_llm_rag_ms = lat
                res.rag_context = ctx

    return ResultadoNota(oraciones=resultados, truncado=truncado, n_total=n_total)


def oracion_top1(resultados: list[ResultadoOracion], brazos: list[Brazo]) -> ResultadoOracion | None:
    if not resultados:
        return None
    return max(resultados, key=lambda r: (r.score_localizacion(brazos), -r.sid))
