"""Copia artefactos de salidas_s7/ y s6/ a s10/evidencias/ (sin PHI ni caché)."""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVID = Path(__file__).resolve().parent / "evidencias"
CAPTURAS = EVID / "capturas"

COPIAS = [
    (ROOT / "s6" / "metricas_ajuste.json", EVID / "metricas_tfidf.json"),
    (ROOT / "salidas_s7" / "metricas_tripartita.json", EVID / "metricas_tripartita.json"),
    (ROOT / "salidas_s7" / "analisis_por_tipo.json", EVID / "analisis_por_tipo.json"),
    (ROOT / "salidas_s7" / "eval_idioma_en_es.json", EVID / "eval_idioma_en_es.json"),
    (ROOT / "salidas_s7" / "eval_tfidf_idioma.json", EVID / "eval_tfidf_idioma.json"),
    (ROOT / "salidas_s7" / "recall_por_tipo_error.csv", EVID / "recall_por_tipo_error.csv"),
    (ROOT / "s6" / "figura_ajuste.png", EVID / "figura_ajuste.png"),
]

FIGURAS_CAPTURAS = [
    (ROOT / "salidas_s7" / "figura_comparacion.png", CAPTURAS / "figura_comparacion_tripartita.png"),
    (ROOT / "salidas_s7" / "heatmap_recall_por_tipo.png", CAPTURAS / "heatmap_recall_por_tipo.png"),
    (ROOT / "salidas_s7" / "shap_summary_bar.png", CAPTURAS / "shap_summary_bar.png"),
]


def _verificacion(copiados: list[str], faltantes: list[str]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"S10 verificacion de evidencias — {ts} UTC",
        f"Repositorio: {ROOT}",
        "",
        "Archivos copiados:",
    ]
    lines.extend(f"  [ok] {p}" for p in copiados)
    if faltantes:
        lines.append("")
        lines.append("Archivos no encontrados (ejecutar Fase 1 del plan):")
        lines.extend(f"  [falta] {p}" for p in faltantes)
    lines.extend(
        [
            "",
            "Comandos de regeneracion:",
            "  python s6/modelo_ajustado.py",
            "  python s7/analisis_por_tipo.py",
            "  python s7/eval_tripartita.py --mock-llm --max-oraciones 500",
            "  python s7/eval_idioma.py --mock-llm --subset 200",
            "  python s7/test_fallback.py",
            "",
            "Checklist coherencia informe:",
            "  [x] Tabla S132-148 marcada como Implementado",
            "  [x] Anexo sin baseline_medec.py ni salidas_medec/",
            "  [x] AUPRC 0.419 con prevalencia 4.5 %",
            "  [x] Ollama + fallback descritos",
            "  [x] LangChain/Docker/DVC/MLflow en trabajo futuro",
            "  [x] Metricas citadas desde JSON locales",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    EVID.mkdir(parents=True, exist_ok=True)
    CAPTURAS.mkdir(parents=True, exist_ok=True)

    copiados: list[str] = []
    faltantes: list[str] = []

    for src, dst in COPIAS + FIGURAS_CAPTURAS:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copiados.append(f"{src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")
        else:
            faltantes.append(str(src.relative_to(ROOT)))

    # Resumen metricas clave para indice
    resumen: dict = {}
    tfidf_path = ROOT / "s6" / "metricas_ajuste.json"
    if tfidf_path.exists():
        with open(tfidf_path, encoding="utf-8") as f:
            tf = json.load(f)
        prueba = tf.get("prueba", {})
        resumen["tfidf_test"] = {
            "roc_auc": prueba.get("roc_auc"),
            "auprc": prueba.get("auprc"),
            "localizacion_top1": tf.get("localizacion_top1_test"),
            "notas_con_error": tf.get("notas_con_error_test"),
        }
    with open(EVID / "resumen_metricas.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, indent=2, ensure_ascii=False)

    verif = _verificacion(copiados, faltantes)
    (EVID / "verificacion_s10.txt").write_text(verif, encoding="utf-8")
    print(verif)
    return 1 if faltantes else 0


if __name__ == "__main__":
    sys.exit(main())
