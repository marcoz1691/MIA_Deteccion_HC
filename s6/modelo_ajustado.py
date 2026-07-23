"""
modelo_ajustado.py
------------------
AJUSTE DEL PROTOTIPO (proyecto CITIMED - detección de inconsistencias).

Reformula a nivel de ORACIÓN usando Error Sentence ID de MEDEC.
Métricas compartidas con S7 (incluye AUPRC). Salidas -> ./salidas_ajuste/
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from s7.metricas import bootstrap_ci, eval_oraciones, localizacion_top1, mcnemar, met
from s7.preprocesamiento import RasgosOracion, explotar_oraciones, load_medec

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

BASE = Path("medec_try/MEDEC-MS")
OUT = Path("salidas_ajuste")
OUT.mkdir(exist_ok=True)


def construir_modelo(idioma: str = "english"):
    stop = None if idioma == "none" else idioma
    feats = FeatureUnion([
        ("tfidf", TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2), min_df=2,
            sublinear_tf=True, stop_words=stop,
        )),
        ("num", Pipeline([
            ("raw", RasgosOracion(idioma=idioma)),
            ("sc", StandardScaler()),
        ])),
    ])
    return Pipeline([
        ("feats", feats),
        ("clf", LogisticRegression(
            solver="liblinear", class_weight="balanced",
            random_state=SEED, max_iter=2000,
        )),
    ])


def main():
    tr = load_medec(BASE, "MEDEC-Full-TrainingSet-with-ErrorType.csv")
    va = load_medec(BASE, "MEDEC-MS-ValidationSet-with-GroundTruth-and-ErrorType.csv")
    te = load_medec(BASE, "MEDEC-MS-TestSet-with-GroundTruth-and-ErrorType.csv")

    otr, ova, ote = explotar_oraciones(tr), explotar_oraciones(va), explotar_oraciones(te)
    print(f"[oraciones] train={len(otr)} (pos={otr.label.sum()}), "
          f"val={len(ova)} (pos={ova.label.sum()}), test={len(ote)} (pos={ote.label.sum()})")
    prev = otr.label.mean()
    print(f"[oraciones] prevalencia de oración-error en train: {prev:.3%}")

    modelo = construir_modelo()
    grid = {
        "feats__tfidf__ngram_range": [(1, 1), (1, 2)],
        "clf__C": [0.5, 1.0, 2.0],
    }
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    gs = GridSearchCV(modelo, grid, scoring="roc_auc", cv=cv, n_jobs=-1, refit=True)
    gs.fit(otr.oracion, otr.label)
    print(f"[grid] mejor AUC CV={gs.best_score_:.4f}  params={gs.best_params_}")

    best_idx = gs.best_index_
    fold_scores = [
        round(float(gs.cv_results_[f"split{k}_test_score"][best_idx]), 4)
        for k in range(5)
    ]
    print(f"[cv folds AUC] {fold_scores}  -> media={np.mean(fold_scores):.4f} sd={np.std(fold_scores):.4f}")

    best = gs.best_estimator_
    res = {
        "config": gs.best_params_,
        "cv_auc_folds": fold_scores,
        "cv_auc_mean": round(float(np.mean(fold_scores)), 4),
        "cv_auc_sd": round(float(np.std(fold_scores)), 4),
        "prevalencia_oracion_error_train": round(float(prev), 4),
    }

    for nombre, d in [("validacion", ova), ("prueba", ote)]:
        pred = best.predict(d.oracion)
        score = best.predict_proba(d.oracion)[:, 1]
        m = eval_oraciones(d.label, pred, score)
        res[nombre] = m
        print(f"[{nombre:>10}] acc={m['accuracy']} P={m['precision']} R={m['recall']} "
              f"F1={m['f1']} AUC={m['roc_auc']} AUPRC={m['auprc']}")

    ote2 = ote.copy()
    ote2["score"] = best.predict_proba(ote2.oracion)[:, 1]
    loc = localizacion_top1(ote2)
    res["localizacion_top1_test"] = loc["localizacion_top1"]
    res["notas_con_error_test"] = loc["notas_con_error"]
    print(f"[localización] top-1: {loc['localizacion_top1']:.3%} sobre {loc['notas_con_error']} notas")

    pred_nota_ajustado, y_nota, score_nota = [], [], []
    for _, g in ote2.groupby("text_id"):
        y_nota.append(int(g.label.max() > 0))
        pred_nota_ajustado.append(int((g.score >= 0.5).any()))
        score_nota.append(float(g.score.max()))
    y_nota = np.array(y_nota)
    pred_nota_ajustado = np.array(pred_nota_ajustado)
    score_nota = np.array(score_nota)

    res["ajustado_a_nivel_nota"] = met(y_nota, pred_nota_ajustado, score_nota)

    base_pipe = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2), min_df=2,
            sublinear_tf=True, stop_words="english",
        )),
        ("clf", LogisticRegression(
            solver="liblinear", class_weight="balanced",
            random_state=SEED, max_iter=1000,
        )),
    ])
    base_pipe.fit(tr.Text.astype(str), tr["Error Flag"].astype(int))
    ids = list(ote2.groupby("text_id").groups.keys())
    te_por_id = te.set_index("Text ID")
    textos = [str(te_por_id.loc[i, "Text"]) for i in ids]
    y_base = np.array([int(te_por_id.loc[i, "Error Flag"]) for i in ids])
    pred_base = base_pipe.predict(textos)
    score_base = base_pipe.predict_proba(textos)[:, 1]
    res["baseline_a_nivel_nota"] = met(y_base, pred_base, score_base)
    res["mcnemar_baseline_vs_ajustado"] = mcnemar(y_nota, pred_base, pred_nota_ajustado)

    tfidf = best.named_steps["feats"].transformer_list[0][1]
    clf = best.named_steps["clf"]
    nombres = np.array(
        list(tfidf.get_feature_names_out()) + ["len", "n_palabras", "n_digitos", "negacion"]
    )
    coefs = clf.coef_[0]
    orden = np.argsort(coefs)
    top1 = [(nombres[i], round(float(coefs[i]), 3)) for i in orden[::-1][:15]]
    top0 = [(nombres[i], round(float(coefs[i]), 3)) for i in orden[:15]]
    pd.DataFrame(
        [{"clase": "oracion_erronea", "termino": t, "coef": c} for t, c in top1]
        + [{"clase": "oracion_normal", "termino": t, "coef": c} for t, c in top0]
    ).to_csv(OUT / "top_features_ajustado.csv", index=False)

    joblib.dump(best, OUT / "modelo_ajustado.joblib")
    res["meta"] = {
        "semilla": SEED,
        "dataset": "MEDEC (particiones oficiales)",
        "tarea": "clasificacion a nivel de ORACION",
        "versiones": {
            "scikit_learn": __import__("sklearn").__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scipy": __import__("scipy").__version__,
        },
    }
    with open(OUT / "metricas_ajuste.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"\n[ok] Artefactos -> {OUT.resolve()}")
    return res


if __name__ == "__main__":
    main()
