"""Análisis de errores por tipo de inconsistencia clínica (ErrorType)."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from s7.metricas import metricas_por_tipo
from s7.preprocesamiento import explotar_oraciones, load_medec

SEED = 42


def evaluar_tfidf(df: pd.DataFrame, model_path: Path) -> pd.DataFrame:
    model = joblib.load(model_path)
    out = df.copy()
    out["score"] = model.predict_proba(out.oracion)[:, 1]
    out["pred"] = (out["score"] >= 0.5).astype(int)
    return out


def plot_heatmap(por_tipo: pd.DataFrame, out_path: Path):
    if por_tipo.empty:
        return
    pivot = por_tipo.pivot_table(index="error_type", values="recall", aggfunc="first")
    fig, ax = plt.subplots(figsize=(8, max(4, len(pivot) * 0.5)))
    im = ax.imshow(pivot.values, cmap="YlGn", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks([0])
    ax.set_xticklabels(["Recall"])
    ax.set_yticks(range(len(pivot)))
    ax.set_yticklabels(pivot.index)
    for i, val in enumerate(pivot.values.flatten()):
        ax.text(0, i, f"{val:.2f}", ha="center", va="center", color="black")
    ax.set_title("Recall por tipo de error clínico (TF-IDF ajustado)")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Análisis por ErrorType")
    parser.add_argument("--config", default="s7/config.yaml")
    parser.add_argument("--brazo", default="tfidf", choices=["tfidf"])
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    out_dir = Path(cfg["salidas"]["dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    base = Path(cfg["medec"]["base_path"])
    te = load_medec(base, cfg["medec"]["test"])
    ote = explotar_oraciones(te)

    model_path = Path(cfg["salidas"]["modelo_tfidf"])
    if not model_path.exists():
        print(f"[warn] Modelo no encontrado en {model_path}. Ejecute s6/modelo_ajustado.py primero.")
        sys.exit(1)

    scored = evaluar_tfidf(ote, model_path)
    por_tipo = metricas_por_tipo(scored)

    csv_path = out_dir / "recall_por_tipo_error.csv"
    por_tipo.to_csv(csv_path, index=False)
    plot_heatmap(por_tipo, out_dir / "heatmap_recall_por_tipo.png")

    resumen = {
        "brazo": args.brazo,
        "n_tipos": len(por_tipo),
        "tipos": por_tipo.to_dict(orient="records"),
        "criticos": por_tipo[por_tipo.error_type.isin(["Medication", "Diagnosis"])].to_dict(orient="records"),
    }
    with open(out_dir / "analisis_por_tipo.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print(f"[ok] {csv_path}")
    print(por_tipo.to_string(index=False))


if __name__ == "__main__":
    main()
