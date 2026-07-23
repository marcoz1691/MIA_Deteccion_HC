"""Comparación TF-IDF con stop_words english vs spanish vs bilingüe (Fase B sesgo EN-ES)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from s8.metricas import eval_oraciones
from s8.preprocesamiento import RasgosOracion, explotar_oraciones, load_medec

SEED = 42


def construir(idioma: str):
    stop = None if idioma == "none" else idioma
    return Pipeline([
        ("feats", FeatureUnion([
            ("tfidf", TfidfVectorizer(
                lowercase=True, ngram_range=(1, 1), min_df=2,
                sublinear_tf=True, stop_words=stop,
            )),
            ("num", Pipeline([
                ("raw", RasgosOracion(idioma=idioma)),
                ("sc", StandardScaler()),
            ])),
        ])),
        ("clf", LogisticRegression(
            solver="liblinear", class_weight="balanced", random_state=SEED, max_iter=2000,
        )),
    ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="s8/config.yaml")
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    out_dir = Path(cfg["salidas"]["dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    base = Path(cfg["medec"]["base_path"])
    tr = load_medec(base, cfg["medec"]["train"])
    te = load_medec(base, cfg["medec"]["test"])
    otr, ote = explotar_oraciones(tr), explotar_oraciones(te)

    resultados = {}
    for idioma in ("english", "spanish", "none"):
        model = construir(idioma)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
        gs = GridSearchCV(model, {"clf__C": [0.5, 1.0, 2.0]},
                          scoring="roc_auc", cv=cv, n_jobs=-1)
        gs.fit(otr.oracion, otr.label)
        best = gs.best_estimator_
        pred = best.predict(ote.oracion)
        score = best.predict_proba(ote.oracion)[:, 1]
        resultados[idioma] = {
            "cv_auc": round(float(gs.best_score_), 4),
            "test": eval_oraciones(ote.label, pred, score, bootstrap_n=500),
        }
        print(f"[{idioma}] CV AUC={resultados[idioma]['cv_auc']} "
              f"test AUC={resultados[idioma]['test']['roc_auc']} "
              f"AUPRC={resultados[idioma]['test']['auprc']}")

    out_path = out_dir / "eval_tfidf_idioma.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"[ok] -> {out_path}")


if __name__ == "__main__":
    main()
