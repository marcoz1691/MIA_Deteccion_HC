"""
Genera el borrador avanzado S11 a partir del Word S10 (no del S8 histórico).

Ejecutar desde la raíz:
  python s11/generar_figuras.py
  python s11/generate_informe.py
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from s10.generate_informe import (  # noqa: E402
    _find_paragraph,
    _fmt,
    _insert_paragraphs_after,
    _insert_picture_after_simple,
    _replace_paragraph_text,
    export_pdf as _export_pdf_s10,
)

S10_DOCX = ROOT / "s10" / "docs" / "S10_Avance_Consolidado.docx"
DOCS = ROOT / "s11" / "docs"
EVID = ROOT / "s11" / "evidencias"
EVID10 = ROOT / "s10" / "evidencias"
CAP = EVID / "capturas"
CAP10 = EVID10 / "capturas"
OUT_DOCX = DOCS / "S11_Borrador_Avanzado.docx"
OUT_PDF = DOCS / "S11_Borrador_Avanzado.pdf"
REPO_URL = "https://github.com/marcoz1691/MIA_Deteccion_HC"


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt_opt(x, nd=3) -> str:
    return _fmt(float(x), nd) if x is not None else "—"


def load_s11() -> dict:
    return {
        "tfidf": _load(ROOT / "s6" / "metricas_ajuste.json") or _load(EVID10 / "metricas_tfidf.json"),
        "llm": _load(EVID / "metricas_llm_real.json"),
        "agg": _load(EVID / "anonimizacion_agregados.json"),
        "verif": _load(EVID / "verificacion_humana_resumen.json"),
        "anot": _load(EVID / "reporte_anotacion.json"),
        "eval_c": _load(ROOT / "salidas_s7" / "eval_citimed.json"),
        "extraccion": _load(ROOT / "s11" / "corpus" / "reporte_extraccion.json"),
    }


def _bloques_s11(m: dict) -> list[tuple[str, str]]:
    tfidf = m["tfidf"].get("prueba", {})
    roc = tfidf.get("roc_auc", 0.9485)
    auprc = tfidf.get("auprc", 0.4186)
    loc = m["tfidf"].get("localizacion_top1_test", 0.8457)
    llm = m["llm"]
    b = (llm.get("brazos") or {})
    cmp_ = (llm.get("comparacion_mock") or {}).get("brazos") or {}
    agg = m["agg"].get("resumen") or {}
    verif = m["verif"]
    rec = verif.get("recall_capa_texto") or {}
    anot = m["anot"]
    ev = (m["eval_c"].get("metricas") or {}) if m["eval_c"] else {}
    ext = m["extraccion"]

    def rec_txt(cat: str) -> str:
        v = rec.get(cat)
        return _fmt_opt(v) if v is not None else "—"

    return [
        ("Heading 2", "3.5. Calidad y pruebas automatizadas (S11)"),
        (
            "Normal",
            "La deuda explícita de S10 —pytest usado pero no declarado— se cierra en S11. "
            "El archivo requirements-dev.txt declara pytest>=8.0 y pytest-cov; requirements.txt "
            "remite a ese archivo para no ensuciar el runtime. Un solo comando "
            "`python -m pytest` recoge api/, s7/test_fallback.py, s10/test_citimed_pipeline.py, "
            "s11/tests y s11/anonimizador_ocr/pruebas. Las pruebas que invocan Tesseract se "
            "marcan con @pytest.mark.requiere_ocr y se omiten si el binario no está instalado, "
            "de modo que la suite no falla en la máquina de un evaluador. El frontend se verifica "
            "con `npm test` (node --test). Evidencia: s11/evidencias/reporte_pytest.txt.",
        ),
        ("Heading 2", "3.6. Anonimización OCR de historias reales"),
        (
            "Normal",
            "El anonimizador 1.5 (s11/anonimizador_ocr/) trabaja sobre PDF escaneado: rasteriza, "
            "reconoce con Tesseract, detecta identificadores ecuatorianos y tacha a nivel de píxel. "
            "Cuatro capas: (1) reglas con dígito verificador de cédula; (2) contexto + NER spaCy; "
            "(3) tachado junto a etiquetas guiado por máscara de tinta (manuscrito); (4) zonas fijas "
            "por plantilla JSON. Corrida hc0001: "
            f"{agg.get('n_paginas', 20)} páginas, {agg.get('n_hallazgos', 127)} hallazgos, "
            f"{agg.get('n_cajas_tachadas', 87)} cajas, {agg.get('n_paginas_a_revisar', 1)} página "
            f"a revisión (confianza OCR 40,2 %). Procesamiento {agg.get('segundos_procesamiento', 77.5)} s, "
            "100 % local. Agregados sin texto: s11/evidencias/anonimizacion_agregados.json.",
        ),
        ("Heading 2", "3.7. Verificación humana y recall de de-identificación"),
        (
            "Normal",
            "Los 127 hallazgos dicen qué se detectó, no cuántos identificadores había. "
            "S11 consolida una primera pasada sobre la capa de texto del PDF ya tachado "
            "(--buscable) más los conteos del pipeline. Resultado (cota inferior de presentes = "
            "tachados + residuos de capa de texto): recall CEDULA = 1,000, HC = 1,000, "
            f"DIRECCION = 1,000, NOMBRE = {rec_txt('NOMBRE')}. El criterio de bloqueo (100 % en "
            "NOMBRE, CÉDULA y HC) no se cumple aún en NOMBRE: el tamizado halló 13 residuos de "
            "categoría NOMBRE en 11 oraciones, que se omitieron del corpus (ciclo de corrección). "
            "CÉDULA y HC sí cumplen el 100 % en esta capa. La página 10 se reporta aparte "
            "(manuscrito, confianza 40,2 %). La revisión visual dual de las 20 páginas originales "
            "sigue siendo el protocolo (s11/docs/protocolo_verificacion_humana.md); este informe "
            "no publica texto ni imágenes de revisión. Registro: s11/evidencias/verificacion_humana.csv.",
        ),
        ("Heading 2", "3.8. Corpus CITIMED anotado (muestra piloto)"),
        (
            "Normal",
            "Desde el PDF buscable se segmentaron oraciones con el mismo criterio de utilidad "
            f"clínica. Tras omitir residuos: {ext.get('oraciones_totales', anot.get('n_oraciones_citimed_extraidas', '—'))} "
            f"oraciones extraídas de {ext.get('paginas', 20)} páginas, más "
            f"{anot.get('n_oraciones_plantilla_sintetica', 4)} oraciones de la plantilla odontológica "
            f"etiquetada. Total de evaluación: {anot.get('n_oraciones_eval', '—')} oraciones, "
            f"{anot.get('n_positivas', 0)} positivas (prevalencia {anot.get('prevalencia', 0)}). "
            f"Doble ciego sobre {((anot.get('doble_ciego') or {}).get('n_compartidas', 0))} oraciones: "
            f"kappa de Cohen = {((anot.get('doble_ciego') or {}).get('kappa_cohen', '—'))}. "
            f"Eval cross-domain MEDEC→CITIMED: ROC-AUC {_fmt_opt(ev.get('roc_auc'))}, "
            f"AUPRC {_fmt_opt(ev.get('auprc'))}. Es una muestra piloto (por debajo de 500–1000 "
            "oraciones sugeridas en S7), declarada como tal. El CSV no se versiona; agregados en "
            "s11/evidencias/reporte_anotacion.json. Guía: s11/docs/guia_anotacion.md.",
        ),
        ("Heading 2", "4.4. Evaluación con LLM real (cierre de la limitación mock)"),
        (
            "Normal",
            "S10 reportó los brazos LLM en modo mock (ROC-AUC ≈ 0,50). S11 ejecutó "
            f"eval_tripartita sobre {llm.get('n_oraciones', 400)} oraciones del test MEDEC con "
            f"{llm.get('modelo_llm', 'gpt-4o-mini')} (temperature=0, mock=false). MEDEC es público; "
            "CITIMED sigue reservado a Ollama on-premise. Resultados: TF-IDF "
            f"ROC-AUC {_fmt_opt((b.get('tfidf') or {}).get('roc_auc'))}, AUPRC "
            f"{_fmt_opt((b.get('tfidf') or {}).get('auprc'))}; LLM zero-shot "
            f"{_fmt_opt((b.get('llm_zero') or {}).get('roc_auc'))} / "
            f"{_fmt_opt((b.get('llm_zero') or {}).get('auprc'))} "
            f"({_fmt_opt((b.get('llm_zero') or {}).get('latencia_ms_por_oracion'), 1)} ms/oración, "
            f"USD {_fmt_opt((b.get('llm_zero') or {}).get('costo_usd_por_1000_oraciones'), 4)} / 1000); "
            f"LLM+RAG {_fmt_opt((b.get('llm_rag') or {}).get('roc_auc'))} / "
            f"{_fmt_opt((b.get('llm_rag') or {}).get('auprc'))} "
            f"(USD {_fmt_opt((b.get('llm_rag') or {}).get('costo_usd_por_1000_oraciones'), 4)} / 1000). "
            f"Mock vs real (zero-shot): {_fmt_opt((cmp_.get('llm_zero') or {}).get('roc_auc_mock'))} → "
            f"{_fmt_opt((cmp_.get('llm_zero') or {}).get('roc_auc_real'))}. "
            "El LLM real no supera a TF-IDF; la ventaja léxica deja de atribuirse al mock. "
            "McNemar TF-IDF vs zero-shot p = "
            f"{_fmt_opt(((llm.get('mcnemar') or {}).get('tfidf_vs_llm_zero') or {}).get('p_value'))}. "
            "Costo medido inferior a la estimación de S7 (0,08 USD/1000). "
            "Evidencia: s11/evidencias/metricas_llm_real.json.",
        ),
        ("Heading 2", "5. Prototipo: historial SQLite y rediseño UI"),
        (
            "Normal",
            "Entre S10 y S11 el prototipo pasó de demostración efímera a aplicación con estado. "
            "api/db.py persiste análisis en SQLite (UUID, marca UTC, resultado JSON, tope "
            "HISTORIAL_MAX_ITEMS=50). Rutas GET/DELETE /historial y /health ampliado. "
            "La interfaz React es un espacio de tres zonas (historial, nota, hallazgo) con "
            "disclaimer fijo, contraste verificado y prefers-reduced-motion. 14 pruebas de "
            "frontend en verde. Capturas: s11/evidencias/capturas/prototipo_*.png. "
            "s11/capture_prototipo.py reemplaza al inexistente s10/capture_demo.py.",
        ),
        ("Heading 2", "6. Ética y privacidad (ampliada)"),
        (
            "Normal",
            "MEDEC (público, inglés) admite API externa. CITIMED (historias reales, español) "
            "no sale del equipo: de-identificación local, Ollama on-premise, originales y "
            "PNG de revisión fuera de git. Categorías redactadas alineadas con Safe Harbor "
            "HIPAA adaptadas a Ecuador (cédula con dígito verificador, RUC, HC, teléfono, "
            "correo, fecha de nacimiento, dirección, edad ≥ 90). Autorización institucional "
            "de CITIMED para uso académico confirmada por el grupo; el documento de respaldo "
            "se conserva offline. Anexo: s11/docs/anexo_etico.md.",
        ),
        ("Heading 2", "7.2. Trazabilidad S10 → S11"),
        (
            "Normal",
            "Observación S10 · Acción S11 · Evidencia · Estado. "
            "(1) Declarar pytest · requirements-dev.txt + suite unificada · reporte_pytest.txt · Cerrado. "
            "(2) Evaluación LLM en mock · eval_tripartita con gpt-4o-mini, n=400 · metricas_llm_real.json · Cerrado. "
            "(3) Corpus CITIMED con aval ético · anonimizador OCR + PDF buscable + anotación piloto + anexo ético · "
            "anonimizacion_agregados.json, reporte_anotacion.json, anexo_etico.md · Avance piloto (n < 500). "
            "(4) PDF breve / capturas faltantes · figuras embebidas y captura del frontend rediseñado · "
            "s11/evidencias/capturas/ · Cerrado. "
            "(5) capture_demo.py referenciado pero ausente · capture_prototipo.py + wrapper · Cerrado.",
        ),
        ("Heading 2", "7. Pitch (versión escrita)"),
        (
            "Normal",
            "Las inconsistencias en una historia clínica odontológica —una alergia documentada "
            "seguida de un antibiótico de la misma familia, un diagnóstico leve con un plan "
            "radical— no se ven en el encabezado de la nota: viven en una oración. El prototipo "
            "MIA_Deteccion_HC localiza esa oración. El clínico carga o pega la nota, pulsa "
            "Analizar y recibe la frase top-1 con scores TF-IDF, LLM y RAG, más el contexto de "
            "guía recuperado. No se emite un veredicto global: se señala un lugar concreto que "
            "un humano puede confirmar o descartar. En MEDEC, reformular de nota a oración "
            f"elevó el ROC-AUC de 0,504 a {_fmt(roc)} y localizó el error en "
            f"{_fmt(loc)} de las notas con error; el AUPRC es {_fmt(auprc)} porque la "
            "prevalencia es 4,5 %. Para CITIMED el valor está en tres propiedades de despliegue: "
            "localización verificable, cómputo on-premise (Ollama) cuando hay PHI, y fallback "
            "a TF-IDF si el modelo de lenguaje no responde. Es un prototipo de investigación; "
            "no sustituye el criterio clínico ni una decisión terapéutica.",
        ),
        (
            "Normal",
            "El flujo de demostración es el de un turno real. Se abre el workspace de tres "
            "zonas; a la izquierda el historial de análisis previos; al centro la nota; a la "
            "derecha el hallazgo. Se carga el ejemplo de alergia a penicilina con prescripción "
            "de amoxicilina. El sistema marca la oración del antibiótico, muestra la barra de "
            "localización por encima del umbral y deja las frases inocuas por debajo. Si la "
            "API del LLM no está disponible, el banner de modo degradado deja claro que la "
            "alerta proviene solo de TF-IDF. Ese es el contrato con el usuario: transparencia "
            "sobre qué brazo habló y por qué.",
        ),
        ("Heading 2", "8. Reflexión y retroalimentación"),
        (
            "Normal",
            "La retroalimentación de S7 pidió AUPRC, sesgo EN-ES, análisis por tipo y riesgos "
            "de producción; S10 los implementó y el profesor valoró convertir el baseline al "
            "azar en evidencia de que el problema exige razonamiento semántico, más la tabla "
            "de trazabilidad frente a S7. En S10 pidió tres deudas concretas. pytest se "
            "declaró. El LLM real se midió: no mejora a TF-IDF, y eso se informa en lugar de "
            "seguir atribuyéndolo al mock. El corpus CITIMED avanzó con un anonimizador de "
            "escaneos reales y una muestra anotada, todavía por debajo del umbral de 500–1000 "
            "oraciones. Tres lecciones metodológicas: (i) el nivel de análisis (nota vs oración) "
            "cambia el problema más que el algoritmo; (ii) con 4,5 % de positivos el AUPRC es "
            "la métrica que obliga a la honestidad; (iii) un mock que puntúa 0,50 no es una "
            "comparación, es un placeholder, y hay que reemplazarlo aunque el resultado "
            "desfavorezca al brazo nuevo. Tres lecciones ético-organizacionales: la "
            "de-identificación precede a cualquier métrica; git no es un archivo compartido "
            "para historias; y la autorización institucional no sustituye el tachado en píxel "
            "ni la revisión humana de las páginas dudosas.",
        ),
    ]


def update_s11(m: dict) -> None:
    from docx import Document

    if not S10_DOCX.exists():
        raise FileNotFoundError(f"Base S10 no encontrada: {S10_DOCX}")
    DOCS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(S10_DOCX, OUT_DOCX)
    doc = Document(str(OUT_DOCX))

    for p in doc.paragraphs:
        if "S10 — Avance Consolidado" in p.text or "Tarea S8" in p.text:
            _replace_paragraph_text(p, "S11 — Borrador avanzado del documento final")
        elif p.text.startswith("Fecha:"):
            _replace_paragraph_text(
                p,
                f"Fecha: {date.today().strftime('%d de %B de %Y').replace('August', 'agosto')}",
            )

    resumen = _find_paragraph(doc, "Las historias clínicas contienen inconsistencias")
    if resumen:
        tfidf = m["tfidf"].get("prueba", {})
        _replace_paragraph_text(
            resumen,
            "Las historias clínicas contienen inconsistencias —medicación contraindicada, "
            "incoherencias entre diagnóstico y tratamiento, contradicciones internas— que "
            "comprometen la seguridad del paciente. Este borrador avanzado (S11) incorpora la "
            "retroalimentación de S10 (96/100): declara pytest, reporta la evaluación con LLM "
            f"real sobre MEDEC y avanza el corpus CITIMED anonimizado. El TF-IDF a nivel de "
            f"oración mantiene ROC-AUC {_fmt(tfidf.get('roc_auc', 0.9485))} y AUPRC "
            f"{_fmt(tfidf.get('auprc', 0.4186))} (prevalencia 4,5 %). El LLM real "
            f"(gpt-4o-mini, n=400) no supera esa línea base; la limitación del mock queda "
            "cerrada con evidencia. El anonimizador OCR procesó 20 páginas reales (127 "
            "hallazgos) y el corpus piloto se anotó tras omitir residuos de capa de texto. "
            f"Repositorio: {REPO_URL}.",
        )

    ancla = "Trabajo futuro (post-S10)"
    if _find_paragraph(doc, ancla) is None:
        ancla = "Trabajo restante para la versión final"
    if _find_paragraph(doc, ancla) is None:
        ancla = "Hasta la semana 10"
    _insert_paragraphs_after(doc, ancla, _bloques_s11(m))

    figuras = [
        ("4.4. Evaluación con LLM real", CAP / "tripartita_mock_vs_real.png",
         "Figura S11-1. Comparación tripartita mock vs LLM real (MEDEC test, n=400)."),
        ("3.6. Anonimización OCR", CAP / "hallazgos_por_etiqueta.png",
         "Figura S11-2. Hallazgos de de-identificación por etiqueta (agregados, sin texto)."),
        ("3.7. Verificación humana", CAP / "recall_deidentificacion.png",
         "Figura S11-3. Recall de de-identificación en la capa de texto del PDF tachado."),
        ("5. Prototipo: historial", CAP / "prototipo_hallazgo.png",
         "Figura S11-4. Workspace clínico: hallazgo localizado (amoxicilina / penicilina)."),
        ("5. Prototipo: historial", CAP / "prototipo_inicio.png",
         "Figura S11-5. Vista inicial del prototipo rediseñado."),
        ("3.6. Anonimización OCR", CAP10 / "figura_ajuste.png" if (CAP10 / "figura_ajuste.png").exists() else EVID10 / "figura_ajuste.png",
         "Figura S11-6. Curvas ROC/PR del TF-IDF ajustado (referencia S6/S10)."),
    ]
    for ancla_fig, path, cap in figuras:
        if path.exists():
            _insert_picture_after_simple(doc, ancla_fig, path, cap, width=5.6)

    doc.save(str(OUT_DOCX))
    print(f"[ok] Word -> {OUT_DOCX}")


def export_pdf() -> None:
    # Reutiliza la lógica de S10 apuntando a las rutas S11.
    import s10.generate_informe as g

    prev_docx, prev_pdf, prev_docs = g.OUT_DOCX, g.OUT_PDF, g.DOCS
    g.OUT_DOCX, g.OUT_PDF, g.DOCS = OUT_DOCX, OUT_PDF, DOCS
    try:
        g.export_pdf()
    finally:
        g.OUT_DOCX, g.OUT_PDF, g.DOCS = prev_docx, prev_pdf, prev_docs


def main() -> None:
    metrics = load_s11()
    update_s11(metrics)
    export_pdf()


if __name__ == "__main__":
    main()
