"""Servicio de inferencia para la API FastAPI."""
from __future__ import annotations

from pathlib import Path

from s7.inferencia import Brazo, Idioma, ResultadoNota, ResultadoOracion, analizar_nota, cargar_config, cargar_modelo_tfidf
from s7.llm_client import LLMClient, LLMUnavailableError
from s7.rag_index import RAGIndex

from api.db import HistorialDB
from api.schemas import (
    GenerarRequest,
    GenerarResponse,
    HistorialItemResponse,
    OracionResponse,
    RagFuenteResponse,
    Top1Response,
)
from api.settings import resolve_mock_llm

ROOT = Path(__file__).resolve().parent.parent


def resolve_cfg_paths(cfg: dict, root: Path = ROOT) -> dict:
    """Convierte rutas relativas del config a absolutas respecto a la raíz del repo."""
    out = dict(cfg)
    out["salidas"] = dict(cfg["salidas"])
    out["salidas"]["dir"] = str(root / cfg["salidas"]["dir"])
    out["salidas"]["cache_dir"] = str(root / cfg["salidas"]["cache_dir"])
    out["salidas"]["modelo_tfidf"] = str(root / cfg["salidas"]["modelo_tfidf"])
    out["rag"] = dict(cfg["rag"])
    out["rag"]["knowledge_dir"] = str(root / cfg["rag"]["knowledge_dir"])
    out["rag"]["index_path"] = str(root / cfg["rag"]["index_path"])
    return out


class InferenceService:
    """Carga recursos compartidos y ejecuta analizar_nota()."""

    def __init__(self, historial_db: HistorialDB | None = None) -> None:
        self.cfg = resolve_cfg_paths(cargar_config(ROOT / "s7" / "config.yaml"))
        self.model_path = Path(self.cfg["salidas"]["modelo_tfidf"])
        self.modelo_tfidf = None
        self._rag: RAGIndex | None = None
        self.historial_db = historial_db

        if self.model_path.exists():
            self.modelo_tfidf = cargar_modelo_tfidf(self.model_path)

    @property
    def modelo_tfidf_disponible(self) -> bool:
        return self.modelo_tfidf is not None

    def get_rag_index(self) -> RAGIndex:
        if self._rag is None:
            rag_cfg = self.cfg["rag"]
            self._rag = RAGIndex(
                knowledge_dir=rag_cfg["knowledge_dir"],
                embedding_model=rag_cfg["embedding_model"],
                index_path=rag_cfg["index_path"],
                top_k=rag_cfg["top_k"],
            ).load()
        return self._rag

    def _build_llm_client(self, mock_llm: bool) -> LLMClient:
        llm_cfg = self.cfg.get("llm", {})
        return LLMClient(
            model=llm_cfg.get("model", "gpt-4o-mini"),
            temperature=llm_cfg.get("temperature", 0),
            max_tokens=llm_cfg.get("max_tokens", 10),
            cache_dir=self.cfg["salidas"]["cache_dir"],
            mock=mock_llm,
            cost_input_per_1m=llm_cfg.get("cost_input_per_1m", 0.15),
            cost_output_per_1m=llm_cfg.get("cost_output_per_1m", 0.60),
            max_retries=llm_cfg.get("max_retries", 3),
            retry_base_delay_s=llm_cfg.get("retry_base_delay_s", 0.5),
            allow_mock_without_key=bool(mock_llm),
        )

    def _validate_resources(self, request: GenerarRequest, mock_llm: bool) -> None:
        brazos = list(request.brazos)
        needs_tfidf = "tfidf" in brazos
        needs_llm = any(b.startswith("llm_") for b in brazos)

        if needs_tfidf and not self.modelo_tfidf_disponible:
            raise FileNotFoundError(
                f"Modelo TF-IDF no encontrado en {self.model_path}. "
                "Entrena con: python s6/modelo_ajustado.py"
            )

        if needs_llm and not mock_llm:
            try:
                self._build_llm_client(mock_llm=False)
            except LLMUnavailableError as exc:
                if not self.modelo_tfidf_disponible:
                    raise LLMUnavailableError(
                        "API LLM no disponible y no hay modelo TF-IDF para fallback."
                    ) from exc

    def generar(self, request: GenerarRequest) -> GenerarResponse:
        mock_llm, _ = resolve_mock_llm(request.mock_llm)
        self._validate_resources(request, mock_llm)

        brazos: list[Brazo] = list(request.brazos)  # type: ignore[assignment]
        idioma: Idioma = request.idioma  # type: ignore[assignment]

        client = None
        rag = None
        rag_aviso: str | None = None
        if any(b.startswith("llm_") for b in brazos):
            client = self._build_llm_client(mock_llm=mock_llm)
            if "llm_rag" in brazos:
                try:
                    rag = self.get_rag_index()
                except Exception:
                    brazos = [b for b in brazos if b != "llm_rag"]
                    rag = None
                    rag_aviso = (
                        "Índice RAG no disponible (embeddings/HuggingFace). "
                        "Se continúa con TF-IDF y LLM zero-shot."
                    )

        resultado = analizar_nota(
            request.nota_clinica.strip(),
            cfg=self.cfg,
            brazos=brazos,
            mock_llm=mock_llm,
            idioma=idioma,
            modelo_tfidf=self.modelo_tfidf,
            client=client,
            rag=rag,
            fallback_tfidf=self.modelo_tfidf_disponible,
        )
        if rag_aviso:
            resultado.modo_degradado = True
            previo = resultado.mensaje_fallback
            resultado.mensaje_fallback = f"{previo} {rag_aviso}".strip() if previo else rag_aviso
            resultado.brazos_efectivos = [
                b for b in (resultado.brazos_efectivos or brazos) if b != "llm_rag"
            ]
        response = serialize_resultado(resultado, request.umbral)

        if request.guardar_historial and self.historial_db is not None:
            nota = request.nota_clinica.strip()
            alerta = bool(response.top1 and response.top1.alerta)
            pdf_origen = request.pdf_origen if request.ejemplo_id == "pdf" else None
            pdf_muestra_id = request.pdf_muestra_id if request.ejemplo_id == "pdf" else None
            saved = self.historial_db.save_analisis(
                nota=nota,
                resultado=response.model_dump(mode="json"),
                ejemplo_id=request.ejemplo_id,
                idioma=request.idioma,
                mock_llm=mock_llm,
                alerta=alerta,
                pdf_origen=pdf_origen,
                pdf_muestra_id=pdf_muestra_id,
            )
            response = response.model_copy(update={"historial_id": saved["id"]})

        return response

    def list_historial(self, limit: int = 10) -> list[HistorialItemResponse]:
        if self.historial_db is None:
            return []
        rows = self.historial_db.list_analisis(limit=limit)
        return [_historial_item_from_row(r) for r in rows]

    def delete_historial(self, entry_id: str) -> bool:
        if self.historial_db is None:
            return False
        return self.historial_db.delete_analisis(entry_id)

    def clear_historial(self) -> int:
        if self.historial_db is None:
            return 0
        return self.historial_db.clear_analisis()

    def historial_count(self) -> int:
        if self.historial_db is None:
            return 0
        return self.historial_db.count()


def serialize_oracion(res: ResultadoOracion, brazos: list[Brazo], umbral: float) -> OracionResponse:
    score_loc = res.score_localizacion(brazos)
    rag_fuentes = [
        RagFuenteResponse(fuente=f["fuente"], extracto=f["extracto"])
        for f in (res.rag_fuentes or [])
    ]
    return OracionResponse(
        sid=res.sid,
        oracion=res.oracion,
        score_tfidf=res.score_tfidf,
        score_llm_zero=res.score_llm_zero,
        score_llm_rag=res.score_llm_rag,
        score_localizacion=score_loc,
        alerta=res.alerta(umbral, brazos),
        brazo_localizacion=res.brazo_localizacion(brazos),
        respuesta_llm_zero=res.respuesta_llm_zero,
        respuesta_llm_rag=res.respuesta_llm_rag,
        latencia_llm_zero_ms=res.latencia_llm_zero_ms,
        latencia_llm_rag_ms=res.latencia_llm_rag_ms,
        rag_fuentes=rag_fuentes,
    )


def serialize_resultado(resultado: ResultadoNota, umbral: float) -> GenerarResponse:
    brazos = resultado.brazos_efectivos or ["tfidf"]
    oraciones = [serialize_oracion(r, brazos, umbral) for r in resultado.oraciones]
    top = resultado.top1(brazos)
    top1 = None
    if top is not None:
        score_loc = top.score_localizacion(brazos)
        top1 = Top1Response(
            sid=top.sid,
            oracion=top.oracion,
            score_localizacion=score_loc,
            alerta=top.alerta(umbral, brazos),
        )
    return GenerarResponse(
        oraciones=oraciones,
        top1=top1,
        truncado=resultado.truncado,
        n_total=resultado.n_total,
        modo_degradado=resultado.modo_degradado,
        brazos_efectivos=list(brazos),
        mensaje_fallback=resultado.mensaje_fallback,
        historial_id=None,
    )


def _historial_item_from_row(row: dict) -> HistorialItemResponse:
    resultado = GenerarResponse.model_validate(row["resultado"])
    return HistorialItemResponse(
        id=row["id"],
        created_at=row["created_at"],
        nota=row["nota"],
        resultado=resultado,
        ejemplo_id=row["ejemplo_id"],
        idioma=row["idioma"],
        mock_llm=row["mock_llm"],
        alerta=row["alerta"],
        pdf_origen=row.get("pdf_origen"),
        pdf_muestra_id=row.get("pdf_muestra_id"),
    )
