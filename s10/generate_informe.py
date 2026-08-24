"""
Genera S10_Avance_Consolidado.docx y .pdf desde métricas del repositorio,
incluyendo figuras y capturas de demo en s10/evidencias/.

Ejecutar desde la raíz: python s10/generate_informe.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DOCS = Path(__file__).resolve().parent / "docs"
EVID = Path(__file__).resolve().parent / "evidencias"
CAP = EVID / "capturas"

GRUPO = "Patricio Bayas Meza · José Puebla Paladines · Marco Zurita Rojas"
REPO_URL = "https://github.com/marcoz1691/MIA_Deteccion_HC"

# (marker_en_seccion, path_relativo_a_EVID_o_CAP, caption, width_inches)
FIGURES = {
    "4. Resultados TF-IDF ajustado (test MEDEC)": [
        ("figura_ajuste.png", EVID / "figura_ajuste.png", "Figura 1. Curvas ROC/PR y lift — TF-IDF ajustado (MEDEC).", 6.2),
        ("curvas_tfidf.png", CAP / "curvas_tfidf.png", "Figura 1b. Curvas TF-IDF (evidencia S6).", 5.5),
    ],
    "5. Resultados S7 extendido": [
        (
            "figura_comparacion_tripartita.png",
            CAP / "figura_comparacion_tripartita.png",
            "Figura 2. Comparacion tripartita TF-IDF / LLM / LLM+RAG.",
            5.8,
        ),
        (
            "heatmap_recall_por_tipo.png",
            CAP / "heatmap_recall_por_tipo.png",
            "Figura 3. Recall por ErrorType (TF-IDF).",
            5.8,
        ),
        (
            "shap_summary_bar.png",
            CAP / "shap_summary_bar.png",
            "Figura 4. Interpretabilidad SHAP (TF-IDF).",
            5.5,
        ),
    ],
    "6. Demo, API y robustez operativa": [
        ("demo_analisis.png", CAP / "demo_analisis.png", "Figura 5. Demo — analisis ejemplo medicacion (mock LLM).", 6.0),
        ("demo_metricas.png", CAP / "demo_metricas.png", "Figura 6. Demo — pagina Metricas.", 5.8),
        ("demo_fallback.png", CAP / "demo_fallback.png", "Figura 7. Fallback TF-IDF (modo degradado).", 5.8),
    ],
}


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _fmt(x: float, nd: int = 3) -> str:
    return f"{x:.{nd}f}"


def _ascii_safe(text: str) -> str:
    out = (
        text.replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        .replace("Á", "A").replace("É", "E").replace("Í", "I")
        .replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N")
        .replace("→", "->").replace("≈", "~").replace("Δ", "Delta ")
        .replace("—", "-").replace("–", "-").replace("·", " - ")
        .replace("±", "+/-").replace("•", "-")
    )
    return out.encode("ascii", "replace").decode("ascii")


def _first_existing(*paths: Path) -> Path | None:
    for p in paths:
        if p and p.exists():
            return p
    return None


def _load_metrics() -> dict:
    tfidf = _load_json(ROOT / "s6" / "metricas_ajuste.json")
    if not tfidf:
        tfidf = _load_json(ROOT / "salidas_ajuste" / "metricas_ajuste.json")
    return {
        "tfidf": tfidf,
        "tripartita": _load_json(ROOT / "salidas_s7" / "metricas_tripartita.json")
        or _load_json(EVID / "metricas_tripartita.json"),
        "por_tipo": _load_json(ROOT / "salidas_s7" / "analisis_por_tipo.json")
        or _load_json(EVID / "analisis_por_tipo.json"),
        "idioma": _load_json(ROOT / "salidas_s7" / "eval_idioma_en_es.json")
        or _load_json(EVID / "eval_idioma_en_es.json"),
        "tfidf_idioma": _load_json(ROOT / "salidas_s7" / "eval_tfidf_idioma.json")
        or _load_json(EVID / "eval_tfidf_idioma.json"),
    }


def _build_sections(m: dict) -> list[tuple[str, list[str]]]:
    prueba = m["tfidf"].get("prueba", {})
    roc = prueba.get("roc_auc", 0.949)
    auprc = prueba.get("auprc", 0.419)
    loc = m["tfidf"].get("localizacion_top1_test", 0.846)
    n_notas = m["tfidf"].get("notas_con_error_test", 311)
    aciertos = int(round(loc * n_notas))
    prev = m["tfidf"].get("prevalencia_oracion_error_train", 0.045) * 100

    trip = m["tripartita"].get("brazos", {})
    tf_trip = trip.get("tfidf", {}).get("oracion", {})
    llm_trip = trip.get("llm_zero", {}).get("oracion", {})
    rag_trip = trip.get("llm_rag", {}).get("oracion", {})
    mock = m["tripartita"].get("llm_stats", {}).get("mock_mode", True)

    tipos = m["por_tipo"].get("tipos", [])
    filas_tipo = [
        f"{t['error_type']}: recall={_fmt(t['recall'])}, loc top-1={_fmt(t['localizacion_top1'])} "
        f"(n={t['n_oraciones']})"
        for t in tipos
    ]

    idioma = m["idioma"]
    delta_auc = idioma.get("delta_auc_en_minus_es", 0)
    tfidf_id = m.get("tfidf_idioma", {})
    tfidf_en = tfidf_id.get("english", {}).get("test", {})
    tfidf_es = tfidf_id.get("spanish", {}).get("test", {})
    tfidf_none = tfidf_id.get("none", {}).get("test", {})

    sections: list[tuple[str, list[str]]] = [
        (
            "1. Resumen ejecutivo",
            [
                "Este informe consolida el avance del proyecto MIA_Deteccion_HC: detección de "
                "inconsistencias en historias clínicas a nivel de oración, con evaluación sobre "
                "MEDEC (Ben Abacha et al., 2025) y prototipo demo para CITIMED.",
                f"Resultado principal: reformular la tarea de nivel nota a nivel oración eleva el "
                f"ROC-AUC de 0.504 (baseline) a {_fmt(roc)} (IC95 "
                f"{_fmt(prueba.get('roc_auc_ci95', [0, 0, 0])[1])}–"
                f"{_fmt(prueba.get('roc_auc_ci95', [0, 0, 0])[2])}) y localiza la oración "
                f"errónea en {loc * 100:.1f} % de las notas con error ({aciertos}/{n_notas}).",
                f"AUPRC test = {_fmt(auprc)} con prevalencia de oración-error {prev:.1f} % — "
                "métrica complementaria al F1 en clases desbalanceadas.",
                "Se implementaron tres brazos (TF-IDF, LLM zero-shot, LLM+RAG), demo Streamlit, "
                "API REST FastAPI (POST /generar), frontend React, fallback explícito a TF-IDF, "
                "soporte Ollama on-premise para PHI y evaluaciones por tipo de error y sesgo EN-ES.",
                f"Repositorio: {REPO_URL}",
                "Disclaimer: prototipo de investigación; no sustituye criterio clínico ni decisiones terapéuticas.",
            ],
        ),
        (
            "2. Metodología",
            [
                "2.1 Unidad de predicción: oración clínica segmentada desde la nota completa "
                "(Error Sentence ID en MEDEC). Localización = oración con mayor score dentro de la nota.",
                "2.2 Stack implementado (alineado con el repositorio):",
                "  • TF-IDF + rasgos numéricos + Regresión Logística (s6/modelo_ajustado.py)",
                "  • LLM zero-shot vía cliente OpenAI-compatible (s7/llm_client.py, s7/prompts.py)",
                "  • RAG: sentence-transformers + FAISS sobre guías en s7/knowledge/ (s7/rag_index.py)",
                "  • Inferencia unificada: s7/inferencia.py (demo, API y scripts de evaluación)",
                "  • API REST: FastAPI en api/ — GET /health, POST /generar (InferenceService)",
                "  • Frontend React + Vite en frontend/ — proxy a la API en puerto 8000",
                "  • Config centralizada: s7/config.yaml; seed global SEED=42",
                "2.3 Trabajo futuro (NO implementado en S10): LangChain/LlamaIndex, Docker Compose, "
                "DVC, MLflow operativo (requirements-optional.txt), cascada TF-IDF→LLM en inferencia, "
                "corrección sugerida/faithfulness RAG, índice CIE-10 formal, corpus CITIMED anonimizado.",
            ],
        ),
        (
            "3. Implementación — capacidades entregadas",
            [
                "La tabla siguiente corrige el borrador S8 (§132–148): todas estas capacidades están "
                "implementadas en el repositorio con rutas verificables.",
                "",
                "| Capacidad | Módulo | Evidencia |",
                "|-----------|--------|-----------|",
                "| Comparación tripartita TF-IDF/LLM/LLM+RAG | s7/eval_tripartita.py | salidas_s7/metricas_tripartita.json |",
                "| Índice FAISS + RAG | s7/rag_index.py, s7/knowledge/ | salidas_s7/faiss_index/ |",
                "| Inferencia unificada | s7/inferencia.py | s7/test_fallback.py |",
                "| Análisis por ErrorType | s7/analisis_por_tipo.py | salidas_s7/analisis_por_tipo.json |",
                "| Sesgo EN-ES | s7/eval_idioma.py, s7/eval_tfidf_idioma.py | salidas_s7/eval_idioma_en_es.json |",
                "| Demo Streamlit | demo/ | demo/README.md + capturas s10/evidencias/capturas/ |",
                "| API REST FastAPI | api/main.py, api/service.py | GET /health, POST /generar, OpenAPI /docs |",
                "| Frontend React | frontend/ | NotaInput + ResultadosPanel, proxy Vite → :8000 |",
                "| Fallback API → TF-IDF | s7/inferencia.py, api/service.py | modo_degradado=True, test_fallback |",
                "| SHAP/LIME (figuras) | salidas_s7/shap_*.png, lime_*.png | s7/docs/reporte_interpretabilidad_etica.md |",
                "| Mock LLM + consentimiento PHI + auditoría SHA-256 | demo/components/security.py | salidas_s7/audit.log |",
                "| Ollama on-premise (PHI CITIMED) | s7/llm_client.py, s7/docs/informe_produccion.md | OPENAI_BASE_URL=http://localhost:11434/v1 |",
            ],
        ),
        (
            "4. Resultados TF-IDF ajustado (test MEDEC)",
            [
                f"ROC-AUC = {_fmt(roc)} (IC95 {_fmt(prueba.get('roc_auc_ci95', [0, 0, 0])[1])}–"
                f"{_fmt(prueba.get('roc_auc_ci95', [0, 0, 0])[2])})",
                f"AUPRC = {_fmt(auprc)} (IC95 {_fmt(prueba.get('auprc_ci95', [0, 0, 0])[1])}–"
                f"{_fmt(prueba.get('auprc_ci95', [0, 0, 0])[2])})",
                f"F1 = {_fmt(prueba.get('f1', 0))}, Precision = {_fmt(prueba.get('precision', 0))}, "
                f"Recall = {_fmt(prueba.get('recall', 0))}",
                f"CV 5-fold AUC = {_fmt(m['tfidf'].get('cv_auc_mean', 0.965))} ± "
                f"{_fmt(m['tfidf'].get('cv_auc_sd', 0.007))}",
                f"Localización top-1 = {loc * 100:.1f} % ({aciertos}/{n_notas} notas)",
                "Baseline a nivel nota: ROC-AUC = 0.504 (sin señal léxica). McNemar baseline vs "
                "ajustado a nivel nota: p = 0.53 — el valor está en la localización, no en el flag binario por nota.",
                "Figuras embebidas a continuación (origen: s6/figura_ajuste.png y s10/evidencias/).",
            ],
        ),
        (
            "5. Resultados S7 extendido",
            [
                "5.1 Comparación tripartita (subset test, mock LLM declarado como limitación):",
                f"  • TF-IDF: ROC-AUC = {_fmt(tf_trip.get('roc_auc', roc))}, "
                f"AUPRC = {_fmt(tf_trip.get('auprc', auprc))}, "
                f"latencia ≈ {trip.get('tfidf', {}).get('latency_ms_per_oracion', 0.4):.2f} ms/oración",
                f"  • LLM zero-shot: ROC-AUC = {_fmt(llm_trip.get('roc_auc', 0.5))} "
                f"({'mock' if mock else 'API real'})",
                f"  • LLM+RAG: ROC-AUC = {_fmt(rag_trip.get('roc_auc', 0.5))}",
                "En modo mock, LLM no discrimina (AUC ≈ 0.5); TF-IDF mantiene ventaja estadística "
                "(McNemar TF-IDF vs LLM: p ≈ 0.11 en subset 500 oraciones). Evaluación con API real "
                "pendiente para latencias y costos de producción.",
                "",
                "5.2 Análisis por ErrorType (TF-IDF, test):",
                *filas_tipo,
                "Errores críticos (pharmacotherapy, diagnosis) mantienen recall > 0.86.",
                "",
                f"5.3 Sesgo EN-ES (subset n={idioma.get('subset_n', 200)}, mock LLM): "
                f"ΔAUC EN−ES = {_fmt(delta_auc)}. Sin ventaja mensurable en mock; "
                "para CITIMED se recomienda prompts en español + modelo local (Ollama).",
                "",
                "5.4 TF-IDF por stop_words (test MEDEC, eval_tfidf_idioma.py):",
                f"  • english: AUC={_fmt(tfidf_en.get('roc_auc', 0))}, AUPRC={_fmt(tfidf_en.get('auprc', 0))}",
                f"  • spanish: AUC={_fmt(tfidf_es.get('roc_auc', 0))}, AUPRC={_fmt(tfidf_es.get('auprc', 0))}",
                f"  • bilingue (none): AUC={_fmt(tfidf_none.get('roc_auc', 0))}, AUPRC={_fmt(tfidf_none.get('auprc', 0))}",
            ],
        ),
        (
            "6. Demo, API y robustez operativa",
            [
                "6.1 Demo Streamlit (demo/app.py): análisis tripartita, página Métricas, configuración de brazos.",
                "6.2 API FastAPI (api/): expone el mismo pipeline que la demo vía HTTP.",
                "  • GET /health — estado del servicio y disponibilidad del modelo TF-IDF",
                "  • POST /generar — payload JSON: nota_clinica, mock_llm (default true), idioma, brazos, umbral",
                "  • InferenceService carga TF-IDF, LLMClient y RAGIndex al arrancar (lifespan)",
                "  • CORS habilitado para el frontend React; documentación OpenAPI en /docs",
                "  • Arranque: uvicorn api.main:app --reload --port 8000",
                "6.3 Frontend React (frontend/): cliente mínimo con Vite.",
                "  • npm run dev → http://localhost:5173; proxy /generar y /health hacia :8000",
                "  • Muestra top1 (oración sospechosa) y tabla de scores por brazo",
                "6.4 Seguridad y fallback:",
                "Mock LLM activo por defecto — ningún dato sale del equipo sin consentimiento explícito (Streamlit).",
                "Fallback: si la API LLM falla (LLMUnavailableError), inferencia continúa con TF-IDF, "
                "modo_degradado=True y mensaje en la respuesta JSON (verificado en s7/test_fallback.py).",
                "Ollama on-premise: mismo LLMClient con OPENAI_BASE_URL=http://localhost:11434/v1 "
                "para datos PHI CITIMED sin egress a nube.",
                "Auditoría Streamlit: salidas_s7/audit.log registra hash SHA-256 de la nota — sin texto clínico.",
                "Capturas del prototipo embebidas a continuación (s10/evidencias/capturas/).",
            ],
        ),
        (
            "7. Pitch (escrito)",
            [
                "Problema: las inconsistencias clínicas son contradicciones semánticas (p. ej. alergia "
                "a penicilina + prescripción de amoxicilina), invisibles para TF-IDF a nivel nota.",
                "Solución: segmentar la nota, puntuar cada oración y resaltar la más sospechosa; "
                "opcionalmente enriquecer con LLM+RAG anclado en guías clínicas.",
                "Evidencia: ROC-AUC 0.949 y localización 84.6 % sobre MEDEC; demo Streamlit o "
                "frontend React + API FastAPI en minutos.",
                "Valor: apoyo a auditoría clínica y seguridad del paciente; despliegue recomendado "
                "en cascada TF-IDF local → LLM solo en candidatas; Ollama para PHI; fallback transparente.",
                "Mensaje clave: el prototipo no diagnostica ni prescribe — prioriza oraciones sospechosas "
                "para revisión humana, con trazabilidad (scores, RAG, auditoría).",
            ],
        ),
        (
            "8. Reflexión y retroalimentación",
            [
                "Feedback del curso integrado: reportar AUPRC además de F1 (prevalencia 4.5 %); "
                "diagnosticar sesgo EN-ES; documentar riesgos PHI antes de piloto CITIMED.",
                "Lección S6: datos sintéticos generaron métricas engañosas (AUC 0.845) — "
                "validación solo sobre MEDEC real.",
                "Lección S7: el valor clínico está en localizar la oración, no en clasificar la nota entera.",
                "Corrección documental S10: el borrador S8 listaba capacidades ya implementadas como "
                "pendientes; este informe se reescribió desde el repositorio (rutas, métricas JSON, "
                "FastAPI/React) y separa claramente trabajo futuro (LangChain, Docker, DVC, MLflow).",
                "Mejora aplicada post-feedback: eval_tfidf_idioma.py (stop words español) eleva test "
                "AUC a ~0.959 vs 0.949 english-only — evidencia en s10/evidencias/eval_tfidf_idioma.json.",
            ],
        ),
        (
            "9. Limitaciones y trabajo futuro",
            [
                "• LLM evaluado principalmente en mock — conclusiones semánticas requieren API/Ollama real.",
                "• Subset tripartita (500 oraciones) — métricas completas en test requieren más compute.",
                "• Corpus CITIMED anonimizado pendiente (organizacional + ética).",
                "• Cascada TF-IDF→LLM documentada pero no codificada en inferencia.py.",
                "• Docker Compose para empaquetar API + frontend: plan futuro (FastAPI ya implementada).",
                "• LangChain, DVC, MLflow: plan futuro, no entregados en S10.",
            ],
        ),
        (
            "10. Anexo técnico",
            [
                "Estructura del repositorio:",
                "  MIA_Deteccion_HC/",
                "  ├── s6/          # TF-IDF ajustado + BITACORA",
                "  ├── s7/          # LLM, RAG, evaluaciones, inferencia",
                "  ├── api/         # FastAPI — POST /generar, GET /health",
                "  ├── frontend/    # React + Vite (cliente HTTP)",
                "  ├── demo/        # Streamlit (demo alternativa)",
                "  ├── s8/docs/     # Borrador histórico S8",
                "  ├── s10/         # Entrega S10 (evidencias + PDF)",
                "  ├── salidas_ajuste/   # modelo_ajustado.joblib (generado)",
                "  └── salidas_s7/       # métricas eval, FAISS, caché (generado)",
                "",
                "Comandos de reproducción (desde raíz, venv activo, MEDEC en medec_try/MEDEC-MS/):",
                "  python s6/modelo_ajustado.py",
                "  python s7/analisis_por_tipo.py",
                "  python s7/eval_tripartita.py --mock-llm --max-oraciones 500",
                "  python s7/eval_idioma.py --mock-llm --subset 200",
                "  python s7/eval_tfidf_idioma.py",
                "  python s7/test_fallback.py",
                "  python s10/capture_demo.py",
                "  python s10/organize_evidencias.py",
                "  python s10/generate_informe.py",
                "  uvicorn api.main:app --reload --port 8000",
                "  cd frontend && npm install && npm run dev",
                "  streamlit run demo/app.py",
                "",
                "Anexo A — Evidencias cuantitativas y capturas en s10/evidencias/ del repositorio.",
            ],
        ),
        (
            "11. Referencias",
            [
                "Ben Abacha, A. B., et al. (2025). MEDEC: A Benchmark for Medical Error Detection "
                "and Correction in Clinical Notes.",
                f"Repositorio del proyecto: {REPO_URL}",
                "Documentación complementaria: s7/docs/informe_produccion.md, "
                "s7/docs/reporte_interpretabilidad_etica.md, s6/BITACORA.md, s10/README.md.",
            ],
        ),
    ]
    return sections


def _figures_for(heading: str) -> list[tuple[Path, str, float]]:
    out: list[tuple[Path, str, float]] = []
    for _name, path, caption, width in FIGURES.get(heading, []):
        alt = None
        if path.name == "figura_ajuste.png":
            alt = ROOT / "s6" / "figura_ajuste.png"
        resolved = _first_existing(path, alt) if alt else (_first_existing(path))
        if resolved:
            out.append((resolved, caption, width))
    return out


def generate_docx(sections: list[tuple[str, list[str]]], out: Path) -> None:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt

    doc = Document()
    title = doc.add_heading("S10 — Avance Consolidado", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = meta.add_run(f"{GRUPO}\n{date.today().isoformat()}\n{REPO_URL}")
    run.font.size = Pt(11)

    doc.add_paragraph(
        "Detección de inconsistencias en historias clínicas (CITIMED / MEDEC). "
        "Documento generado desde métricas del repositorio, con figuras y capturas del prototipo."
    )

    for heading, paragraphs in sections:
        doc.add_heading(heading, level=1)
        for para in paragraphs:
            if para == "":
                continue
            if para.startswith("|"):
                p = doc.add_paragraph(para)
                p.style = "No Spacing"
            elif para.startswith("  "):
                doc.add_paragraph(para.strip(), style="List Bullet")
            else:
                doc.add_paragraph(para)

        for img_path, caption, width in _figures_for(heading):
            try:
                doc.add_picture(str(img_path), width=Inches(width))
                cap = doc.add_paragraph(caption)
                cap.runs[0].italic = True if cap.runs else False
                cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            except Exception as e:
                doc.add_paragraph(f"[Figura no insertada: {img_path.name} — {e}]")

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    print(f"[ok] Word -> {out}")


def generate_pdf(sections: list[tuple[str, list[str]]], out: Path) -> None:
    from fpdf import FPDF

    class InformePDF(FPDF):
        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 10, f"Pagina {self.page_no()}/{{nb}}", align="C")

    pdf = InformePDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "S10 - Avance Consolidado", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _ascii_safe(GRUPO), ln=True, align="C")
    pdf.cell(0, 6, str(date.today()), ln=True, align="C")
    pdf.cell(0, 6, REPO_URL, ln=True, align="C")
    pdf.ln(4)

    for heading, paragraphs in sections:
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, _ascii_safe(heading))
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 10)
        for para in paragraphs:
            if para == "":
                pdf.ln(2)
                continue
            pdf.multi_cell(0, 5, _ascii_safe(para))
            pdf.ln(1)

        for img_path, caption, width_in in _figures_for(heading):
            try:
                # Ancho útil ~180 mm; width_in ~5.5-6.2 → mm
                w_mm = min(180, width_in * 25.4)
                # Reservar espacio; si no cabe, nueva página
                if pdf.get_y() > 200:
                    pdf.add_page()
                pdf.ln(2)
                pdf.image(str(img_path), w=w_mm)
                pdf.set_font("Helvetica", "I", 9)
                pdf.multi_cell(0, 5, _ascii_safe(caption), align="C")
                pdf.set_font("Helvetica", "", 10)
                pdf.ln(2)
            except Exception as e:
                pdf.multi_cell(0, 5, _ascii_safe(f"[Figura no insertada: {img_path.name} — {e}]"))

        pdf.ln(3)

    out.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out))
    print(f"[ok] PDF -> {out}")


def main() -> None:
    metrics = _load_metrics()
    if not metrics["tfidf"]:
        print("[warn] metricas_ajuste.json no encontrado; ejecutar python s6/modelo_ajustado.py")
    # Asegurar capturas demo
    demo_analisis = CAP / "demo_analisis.png"
    if not demo_analisis.exists():
        print("[info] Generando capturas demo...")
        from s10.capture_demo import main as capture_main

        capture_main()

    sections = _build_sections(metrics)
    generate_docx(sections, DOCS / "S10_Avance_Consolidado.docx")
    generate_pdf(sections, DOCS / "S10_Avance_Consolidado.pdf")


if __name__ == "__main__":
    main()
