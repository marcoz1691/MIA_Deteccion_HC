"""Esquemas Pydantic para la API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BrazoLiteral = Literal["tfidf", "llm_zero", "llm_rag"]
IdiomaLiteral = Literal["english", "spanish"]


class GenerarRequest(BaseModel):
    nota_clinica: str = Field(..., min_length=1, description="Texto libre de la nota clínica.")
    mock_llm: bool = Field(True, description="Usar respuestas LLM simuladas (sin API key).")
    idioma: IdiomaLiteral = "spanish"
    brazos: list[BrazoLiteral] = Field(
        default_factory=lambda: ["tfidf", "llm_zero", "llm_rag"],
        min_length=1,
    )
    umbral: float = Field(0.5, ge=0.0, le=1.0, description="Umbral de alerta para localización.")


class OracionResponse(BaseModel):
    sid: int
    oracion: str
    score_tfidf: float | None = None
    score_llm_zero: float | None = None
    score_llm_rag: float | None = None
    score_localizacion: float
    alerta: bool
    respuesta_llm_zero: str | None = None
    respuesta_llm_rag: str | None = None
    latencia_llm_zero_ms: float | None = None
    latencia_llm_rag_ms: float | None = None


class Top1Response(BaseModel):
    sid: int
    oracion: str
    score_localizacion: float
    alerta: bool


class GenerarResponse(BaseModel):
    oraciones: list[OracionResponse]
    top1: Top1Response | None
    truncado: bool
    n_total: int
    modo_degradado: bool
    brazos_efectivos: list[str]
    mensaje_fallback: str | None


class HealthResponse(BaseModel):
    status: str
    modelo_tfidf_disponible: bool
    modelo_tfidf_path: str
