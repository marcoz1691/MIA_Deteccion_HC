"""FastAPI — POST /generar para análisis de inconsistencias en historias clínicas."""
from __future__ import annotations

from contextlib import asynccontextmanager

from json import JSONDecodeError

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from s7.llm_client import LLMUnavailableError

from api.db import HistorialDB
from api.pdf_estructura import extraer_estructurado
from api.pdf_extract import PdfExtractError, extraer_de_bytes, extraer_de_ruta, listar_muestras, resolver_muestra
from api.schemas import (
    ExtraerPdfEstructuradoResponse,
    ExtraerPdfRequest,
    ExtraerPdfResponse,
    GenerarRequest,
    GenerarResponse,
    HealthResponse,
    HistorialListResponse,
    MuestrasPdfResponse,
)
from api.service import InferenceService
from api.settings import (
    historial_max_items,
    llm_api_configurada,
    resolve_mock_llm,
    sqlite_db_path,
    vision_configurada,
    vision_model,
)
from api.vision_client import VisionUnavailableError, transcriptor_openai

_service: InferenceService | None = None
_historial_db: HistorialDB | None = None


def get_service() -> InferenceService:
    if _service is None:
        raise RuntimeError("Servicio de inferencia no inicializado.")
    return _service


def get_historial_db() -> HistorialDB:
    if _historial_db is None:
        raise RuntimeError("Base SQLite de historial no inicializada.")
    return _historial_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _service, _historial_db
    _historial_db = HistorialDB(sqlite_db_path(), max_items=historial_max_items())
    _service = InferenceService(historial_db=_historial_db)
    yield
    _service = None
    _historial_db = None


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
    db = get_historial_db()
    mock_llm, mock_forzado = resolve_mock_llm(True)
    return HealthResponse(
        status="ok",
        modelo_tfidf_disponible=svc.modelo_tfidf_disponible,
        modelo_tfidf_path=str(svc.model_path),
        mock_llm=mock_llm,
        mock_llm_forzado=mock_forzado,
        llm_api_configurada=llm_api_configurada(),
        historial_sqlite=str(db.db_path),
        historial_count=db.count(),
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


@app.get("/historial", response_model=HistorialListResponse)
def listar_historial(limit: int = 10) -> HistorialListResponse:
    svc = get_service()
    items = svc.list_historial(limit=limit)
    return HistorialListResponse(items=items, total=svc.historial_count())


@app.delete("/historial/{entry_id}")
def eliminar_historial(entry_id: str) -> dict:
    svc = get_service()
    if not svc.delete_historial(entry_id):
        raise HTTPException(status_code=404, detail="Análisis no encontrado en el historial.")
    return {"ok": True, "id": entry_id}


@app.delete("/historial")
def vaciar_historial() -> dict:
    svc = get_service()
    n = svc.clear_historial()
    return {"ok": True, "deleted": n}


def _pdf_http_error(exc: PdfExtractError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=str(exc))


@app.get("/muestras-pdf", response_model=MuestrasPdfResponse)
def muestras_pdf() -> MuestrasPdfResponse:
    return MuestrasPdfResponse(muestras=listar_muestras())


@app.post("/extraer-pdf", response_model=ExtraerPdfResponse)
async def extraer_pdf(request: Request) -> ExtraerPdfResponse:
    ctype = (request.headers.get("content-type") or "").lower()
    try:
        if ctype.startswith("multipart/form-data"):
            form = await request.form()
            archivo = form.get("archivo")
            if archivo is None or not getattr(archivo, "read", None):
                raise HTTPException(
                    status_code=400,
                    detail="Envíe un PDF en el campo 'archivo' o un JSON con muestra_id.",
                )
            data = await archivo.read()
            nombre = getattr(archivo, "filename", None) or "documento.pdf"
            resultado = extraer_de_bytes(data, origen=nombre)
        else:
            try:
                raw = await request.json()
                payload = ExtraerPdfRequest.model_validate(raw)
            except (JSONDecodeError, ValidationError) as exc:
                raise HTTPException(
                    status_code=400,
                    detail="Envíe un PDF en el campo 'archivo' o un JSON con muestra_id.",
                ) from exc
            ruta = resolver_muestra(payload.muestra_id)
            resultado = extraer_de_ruta(ruta)
    except PdfExtractError as exc:
        raise _pdf_http_error(exc) from exc
    return ExtraerPdfResponse(**resultado)


async def _leer_pdf_de_request(request: Request) -> tuple[bytes, str]:
    """Devuelve (bytes, origen) desde multipart 'archivo' o JSON {muestra_id}."""
    ctype = (request.headers.get("content-type") or "").lower()
    if ctype.startswith("multipart/form-data"):
        form = await request.form()
        archivo = form.get("archivo")
        if archivo is None or not getattr(archivo, "read", None):
            raise HTTPException(
                status_code=400,
                detail="Envíe un PDF en el campo 'archivo' o un JSON con muestra_id.",
            )
        data = await archivo.read()
        nombre = getattr(archivo, "filename", None) or "documento.pdf"
        return data, nombre
    try:
        payload = ExtraerPdfRequest.model_validate(await request.json())
    except (JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Envíe un PDF en el campo 'archivo' o un JSON con muestra_id.",
        ) from exc
    ruta = resolver_muestra(payload.muestra_id)
    return ruta.read_bytes(), ruta.name


@app.post("/extraer-pdf-estructurado", response_model=ExtraerPdfEstructuradoResponse)
async def extraer_pdf_estructurado(request: Request) -> ExtraerPdfEstructuradoResponse:
    try:
        data, origen = await _leer_pdf_de_request(request)
    except PdfExtractError as exc:
        raise _pdf_http_error(exc) from exc

    transcriptor = None
    if vision_configurada():
        try:
            transcriptor = transcriptor_openai(model=vision_model())
        except VisionUnavailableError:
            transcriptor = None

    try:
        resultado = extraer_estructurado(data, origen=origen, transcriptor=transcriptor)
    except PdfExtractError as exc:
        raise _pdf_http_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ExtraerPdfEstructuradoResponse(**resultado)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
