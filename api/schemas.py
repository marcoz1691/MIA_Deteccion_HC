"""Esquemas Pydantic para la API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BrazoLiteral = Literal["tfidf", "llm_zero", "llm_rag"]
IdiomaLiteral = Literal["english", "spanish"]


class GenerarRequest(BaseModel):
    nota_clinica: str = Field(..., min_length=1, description="Texto libre de la nota clínica.")
    mock_llm: bool = Field(
        True,
        description=(
            "Solicitar respuestas LLM simuladas. Puede ser ignorado si el servidor "
            "define la variable de entorno MOCK_LLM."
        ),
    )
    idioma: IdiomaLiteral = "spanish"
    brazos: list[BrazoLiteral] = Field(
        default_factory=lambda: ["tfidf", "llm_zero", "llm_rag"],
        min_length=1,
    )
    umbral: float = Field(0.5, ge=0.0, le=1.0, description="Umbral de alerta para localización.")
    ejemplo_id: str = Field("propia", description="Identificador del caso demo o 'propia'.")
    guardar_historial: bool = Field(True, description="Persistir el análisis en SQLite.")


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
    historial_id: str | None = None


class HistorialItemResponse(BaseModel):
    id: str
    created_at: str
    nota: str
    resultado: GenerarResponse
    ejemplo_id: str
    idioma: IdiomaLiteral
    mock_llm: bool
    alerta: bool


class HistorialListResponse(BaseModel):
    items: list[HistorialItemResponse]
    total: int


class HealthResponse(BaseModel):
    status: str
    modelo_tfidf_disponible: bool
    modelo_tfidf_path: str
    mock_llm: bool = Field(description="Modo mock LLM efectivo en el servidor.")
    mock_llm_forzado: bool = Field(
        description="True si MOCK_LLM está definido en el entorno (ignora el cliente)."
    )
    llm_api_configurada: bool = Field(
        description="True si hay OPENAI_API_KEY o MISTRAL_API_KEY en el servidor."
    )
    historial_sqlite: str = Field(description="Ruta absoluta de la base SQLite del historial.")
    historial_count: int = Field(description="Número de análisis almacenados.")
