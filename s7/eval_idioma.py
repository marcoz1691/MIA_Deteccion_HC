"""Diagnóstico sesgo inglés-español: LLM zero-shot EN vs ES sobre subset MEDEC."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from s7.llm_client import LLMClient
from s7.metricas import eval_oraciones
from s7.preprocesamiento import explotar_oraciones, load_medec
from s7.prompts import get_prompt, parse_yes_no

SEED = 42


def evaluar_idioma(df: pd.DataFrame, client: LLMClient, idioma: str) -> tuple[np.ndarray, np.ndarray]:
    scores, preds = [], []
    for _, row in df.iterrows():
        prompt = get_prompt("zero_shot", idioma, row.oracion)
        resp = client.complete(prompt, brazo=f"idioma_{idioma}")
        score = parse_yes_no(resp["text"], idioma)
        scores.append(score)
        preds.append(int(score >= 0.5))
    return np.array(preds), np.array(scores)


def main():
    parser = argparse.ArgumentParser(description="Evaluación sesgo EN vs ES")
    parser.add_argument("--config", default="s7/config.yaml")
    parser.add_argument("--subset", type=int, default=200, help="Oraciones de validación")
    parser.add_argument("--mock-llm", action="store_true")
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    out_dir = Path(cfg["salidas"]["dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    base = Path(cfg["medec"]["base_path"])
    va = load_medec(base, cfg["medec"]["validation"])
    ova = explotar_oraciones(va).head(args.subset)

    client = LLMClient(
        model=cfg["llm"]["model"],
        cache_dir=cfg["salidas"]["cache_dir"],
        mock=args.mock_llm,
    )

    y = ova.label.values
    resultados = {}
    for idioma in ("english", "spanish"):
        pred, score = evaluar_idioma(ova, client, idioma)
        resultados[idioma] = eval_oraciones(y, pred, score, bootstrap_n=500)
        print(f"[{idioma}] AUC={resultados[idioma]['roc_auc']} AUPRC={resultados[idioma]['auprc']}")

    delta_auc = round(resultados["english"]["roc_auc"] - resultados["spanish"]["roc_auc"], 4)
    delta_auprc = round(resultados["english"]["auprc"] - resultados["spanish"]["auprc"], 4)

    export = {
        "subset_n": len(ova),
        "english": resultados["english"],
        "spanish": resultados["spanish"],
        "delta_auc_en_minus_es": delta_auc,
        "delta_auprc_en_minus_es": delta_auprc,
        "interpretacion": (
            "Delta positivo indica ventaja del prompt en inglés (corpus MEDEC nativo). "
            "Para CITIMED Odontología se recomienda prompts en español + modelo local."
        ),
        "llm_stats": client.summary(),
    }
    out_path = out_dir / "eval_idioma_en_es.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)
    print(f"\n[ok] Delta AUC (EN-ES)={delta_auc}  Delta AUPRC={delta_auprc}")
    print(f"[ok] -> {out_path}")


if __name__ == "__main__":
    main()
