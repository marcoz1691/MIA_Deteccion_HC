"""FastAPI — POST /generar para análisis de inconsistencias en notas clínicas."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from s7.llm_client import LLMUnavailableError

from api.schemas import GenerarRequest, GenerarResponse, HealthResponse
from api.service import InferenceService

_service: InferenceService | None = None


def get_service() -> InferenceService:
    if _service is None:
        raise RuntimeError("Servicio de inferencia no inicializado.")
    return _service


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _service
    _service = InferenceService()
    yield
    _service = None


app = FastAPI(
    title="MIA Detección HC",
    description=(
        "Backend para detección de inconsistencias en historias clínicas. "
        "El frontend envía la nota; el servicio carga TF-IDF/LLM/RAG y retorna el análisis."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    svc = get_service()
    return HealthResponse(
        status="ok",
        modelo_tfidf_disponible=svc.modelo_tfidf_disponible,
        modelo_tfidf_path=str(svc.model_path),
    )


@app.post("/generar", response_model=GenerarResponse)
def generar(request: GenerarRequest) -> GenerarResponse:
    svc = get_service()
    try:
        return svc.generar(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
