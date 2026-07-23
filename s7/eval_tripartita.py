"""Comparación tripartita: TF-IDF vs LLM zero-shot vs LLM+RAG."""
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

from s7.llm_client import LLMClient
from s7.metricas import curvas_pr, eval_oraciones, localizacion_top1, mcnemar
from s7.preprocesamiento import explotar_oraciones, load_medec
from s7.prompts import get_prompt, parse_yes_no
from s7.rag_index import RAGIndex

SEED = 42


def cargar_config(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def evaluar_tfidf(df: pd.DataFrame, model_path: Path) -> tuple[np.ndarray, np.ndarray, float]:
    t0 = time.perf_counter()
    model = joblib.load(model_path)
    scores = model.predict_proba(df.oracion)[:, 1]
    preds = (scores >= 0.5).astype(int)
    lat_ms = (time.perf_counter() - t0) / max(len(df), 1) * 1000
    return preds, scores, lat_ms


def evaluar_llm(
    df: pd.DataFrame,
    client: LLMClient,
    mode: str,
    idioma: str,
    rag: RAGIndex | None = None,
) -> tuple[np.ndarray, np.ndarray, list[float]]:
    preds, scores, latencies = [], [], []
    for _, row in df.iterrows():
        contexto = rag.retrieve(row.oracion) if mode == "rag" and rag else ""
        prompt = get_prompt(mode, idioma, row.oracion, contexto)
        resp = client.complete(prompt, brazo=f"llm_{mode}")
        score = parse_yes_no(resp["text"], idioma)
        latencies.append(resp["latency_ms"])
        scores.append(score)
        preds.append(int(score >= 0.5))
    return np.array(preds), np.array(scores), latencies


def plot_comparacion(resultados: dict, out_path: Path):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    brazos = list(resultados.keys())
    aucs = [resultados[b]["oracion"]["roc_auc"] for b in brazos]
    auprcs = [resultados[b]["oracion"]["auprc"] for b in brazos]
    x = np.arange(len(brazos))
    w = 0.35
    axes[0].bar(x - w / 2, aucs, w, label="ROC-AUC", color="#2E7D32")
    axes[0].bar(x + w / 2, auprcs, w, label="AUPRC", color="#1565C0")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(brazos, rotation=15, ha="right")
    axes[0].set_ylim(0, 1.05)
    axes[0].set_title("(a) ROC-AUC vs AUPRC por brazo")
    axes[0].legend()
    axes[0].axhline(0.5, ls="--", color="gray", lw=0.8)

    locs = [resultados[b]["localizacion"]["localizacion_top1"] for b in brazos]
    axes[1].bar(brazos, locs, color="#2E7D32")
    axes[1].set_ylim(0, 1.05)
    axes[1].set_title("(b) Localización top-1")
    for i, v in enumerate(locs):
        axes[1].text(i, v + 0.02, f"{v:.1%}", ha="center", fontsize=9)

    colors = ["#C62828", "#1565C0", "#2E7D32"]
    for i, b in enumerate(brazos):
        if "pr_curve" in resultados[b]:
            prec, rec = resultados[b]["pr_curve"]
            axes[2].plot(rec, prec, label=b, color=colors[i % len(colors)], lw=2)
    axes[2].set_xlabel("Recall")
    axes[2].set_ylabel("Precision")
    axes[2].set_title("(c) Curvas Precision-Recall")
    axes[2].legend(fontsize=8)
    axes[2].set_xlim(0, 1.05)
    axes[2].set_ylim(0, 1.05)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Evaluación tripartita S7")
    parser.add_argument("--config", default="s7/config.yaml")
    parser.add_argument("--brazos", default="tfidf,llm_zero,llm_rag")
    parser.add_argument("--mock-llm", action="store_true")
    parser.add_argument("--max-oraciones", type=int, default=None)
    args = parser.parse_args()

    cfg = cargar_config(args.config)
    out_dir = Path(cfg["salidas"]["dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    split_name = cfg["eval"]["split"]
    split_file = (
        cfg["medec"]["validation"] if split_name == "validation" else cfg["medec"]["test"]
    )
    base = Path(cfg["medec"]["base_path"])
    df = load_medec(base, split_file)
    odf = explotar_oraciones(df)

    max_n = args.max_oraciones or cfg["eval"].get("max_oraciones")
    if max_n:
        odf = odf.head(int(max_n))

    brazos = [b.strip() for b in args.brazos.split(",")]
    idioma = cfg["idioma"]["default"]
    resultados: dict = {}
    preds_por_brazo: dict[str, np.ndarray] = {}
    y = odf.label.values

    if "tfidf" in brazos:
        model_path = Path(cfg["salidas"]["modelo_tfidf"])
        if not model_path.exists():
            print(f"[error] Modelo TF-IDF no encontrado: {model_path}")
            sys.exit(1)
        pred, score, lat = evaluar_tfidf(odf, model_path)
        preds_por_brazo["tfidf"] = pred
        odf_t = odf.copy()
        odf_t["score"] = score
        resultados["tfidf"] = {
            "oracion": eval_oraciones(y, pred, score, bootstrap_n=cfg["eval"]["bootstrap_n"]),
            "localizacion": localizacion_top1(odf_t),
            "latency_ms_per_oracion": round(lat, 3),
            "pr_curve": curvas_pr(y, score),
        }
        print(f"[tfidf] AUC={resultados['tfidf']['oracion']['roc_auc']} "
              f"AUPRC={resultados['tfidf']['oracion']['auprc']}")

    llm_stats = {}
    llm_brazos = [b for b in brazos if b.startswith("llm_")]
    if llm_brazos:
        client = LLMClient(
            model=cfg["llm"]["model"],
            temperature=cfg["llm"]["temperature"],
            max_tokens=cfg["llm"]["max_tokens"],
            cache_dir=cfg["salidas"]["cache_dir"],
            mock=args.mock_llm,
            cost_input_per_1m=cfg["llm"]["cost_input_per_1m"],
            cost_output_per_1m=cfg["llm"]["cost_output_per_1m"],
        )
        rag = RAGIndex(
            knowledge_dir=cfg["rag"]["knowledge_dir"],
            embedding_model=cfg["rag"]["embedding_model"],
            index_path=cfg["rag"]["index_path"],
            top_k=cfg["rag"]["top_k"],
        ).load() if "llm_rag" in llm_brazos else None

        for brazo in llm_brazos:
            mode = "zero_shot" if "zero" in brazo else "rag"
            pred, score, lats = evaluar_llm(odf, client, mode, idioma, rag=rag)
            preds_por_brazo[brazo] = pred
            odf_l = odf.copy()
            odf_l["score"] = score
            resultados[brazo] = {
                "oracion": eval_oraciones(y, pred, score, bootstrap_n=cfg["eval"]["bootstrap_n"]),
                "localizacion": localizacion_top1(odf_l),
                "latency_ms_per_oracion": round(float(np.mean(lats)), 2),
                "pr_curve": curvas_pr(y, score),
            }
            print(f"[{brazo}] AUC={resultados[brazo]['oracion']['roc_auc']} "
                  f"AUPRC={resultados[brazo]['oracion']['auprc']}")
        llm_stats = client.summary()

    mcnemar_pairs = {}
    nombres = list(preds_por_brazo.keys())
    for i in range(len(nombres)):
        for j in range(i + 1, len(nombres)):
            a, b = nombres[i], nombres[j]
            mcnemar_pairs[f"{a}_vs_{b}"] = mcnemar(y, preds_por_brazo[a], preds_por_brazo[b])

    export = {
        "split": split_name,
        "n_oraciones": len(odf),
        "brazos": {
            b: {
                "oracion": resultados[b]["oracion"],
                "localizacion": resultados[b]["localizacion"],
                "latency_ms_per_oracion": resultados[b]["latency_ms_per_oracion"],
            }
            for b in resultados
        },
        "mcnemar": mcnemar_pairs,
        "llm_stats": llm_stats,
        "referencia_s7": {"roc_auc": 0.9485, "auprc": 0.42, "localizacion_top1": 0.8457},
    }

    out_json = out_dir / "metricas_tripartita.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    plot_comparacion(resultados, out_dir / "figura_comparacion.png")
    print(f"\n[ok] Resultados -> {out_json}")


if __name__ == "__main__":
    main()
