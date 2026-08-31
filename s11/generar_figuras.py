"""Figuras publicables S11 a partir de JSON sanitizados (sin PHI)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
EVID = ROOT / "s11" / "evidencias"
CAP = EVID / "capturas"
CAP.mkdir(parents=True, exist_ok=True)


def _barh(titulo: str, datos: dict, salida: Path, xlabel: str) -> None:
    items = sorted(datos.items(), key=lambda x: x[1])
    labels = [k for k, _ in items]
    vals = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.barh(labels, vals, color="#2F5D8C")
    ax.set_xlabel(xlabel)
    ax.set_title(titulo)
    fig.tight_layout()
    fig.savefig(salida, dpi=140)
    plt.close(fig)


def main() -> None:
    agg = json.loads((EVID / "anonimizacion_agregados.json").read_text(encoding="utf-8"))
    _barh(
        "Hallazgos de de-identificación por etiqueta (hc0001, n=20 páginas)",
        agg["hallazgos_por_etiqueta"],
        CAP / "hallazgos_por_etiqueta.png",
        "Número de hallazgos",
    )
    _barh(
        "Hallazgos por origen de detección",
        agg["hallazgos_por_origen"],
        CAP / "hallazgos_por_origen.png",
        "Número de hallazgos",
    )

    llm = json.loads((EVID / "metricas_llm_real.json").read_text(encoding="utf-8"))
    brazos = ["tfidf", "llm_zero", "llm_rag"]
    mock = [llm["comparacion_mock"]["brazos"][b]["roc_auc_mock"] for b in brazos]
    real = [llm["comparacion_mock"]["brazos"][b]["roc_auc_real"] for b in brazos]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = range(len(brazos))
    w = 0.35
    ax.bar([i - w / 2 for i in x], mock, w, label="Mock (S10)", color="#9AA8B5")
    ax.bar([i + w / 2 for i in x], real, w, label="LLM real (S11)", color="#2F5D8C")
    ax.set_xticks(list(x))
    ax.set_xticklabels(["TF-IDF", "LLM zero-shot", "LLM+RAG"])
    ax.set_ylabel("ROC-AUC")
    ax.set_ylim(0.45, 1.0)
    ax.axhline(0.5, color="#B33", linestyle="--", linewidth=0.8, label="Azar")
    ax.set_title("Comparación tripartita: mock vs LLM real (MEDEC test)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(CAP / "tripartita_mock_vs_real.png", dpi=140)
    plt.close(fig)

    resumen = json.loads((EVID / "verificacion_humana_resumen.json").read_text(encoding="utf-8"))
    rec = {k: v for k, v in resumen["recall_capa_texto"].items() if v is not None}
    if rec:
        _barh(
            "Recall de de-identificación (capa de texto del PDF tachado)",
            rec,
            CAP / "recall_deidentificacion.png",
            "Recall",
        )
    print(f"[ok] figuras en {CAP}")


if __name__ == "__main__":
    main()
