"""
modelo_ajustado.py
------------------
AJUSTE DEL PROTOTIPO (proyecto CITIMED - detección de inconsistencias).

Cambio principal frente al baseline (S6):
    Baseline  -> clasificaba la NOTA COMPLETA ("¿esta historia tiene un error?").
                 Fracasó (ROC-AUC 0.504) porque la oración errónea es ~9% del texto
                 y el 95.6% del vocabulario se solapa entre clases.
    Ajustado  -> reformula a nivel de ORACIÓN ("¿es ESTA oración la inconsistente?"),
                 usando el campo 'Error Sentence ID' que MEDEC ya provee.
                 Esto eleva la relación señal-ruido y habilita la LOCALIZACIÓN.

Otros ajustes:
    - Preprocesamiento: se separan las oraciones numeradas del campo 'Sentences'.
    - Ingeniería de features: TF-IDF 1-2 n-gramas + rasgos numéricos simples por
      oración (longitud, presencia de dígitos/negaciones) vía FeatureUnion.
    - Hiperparámetros: búsqueda en malla (C, ngram_range) con validación cruzada.
    - Manejo de desbalance: class_weight='balanced' (1 oración positiva por nota).

Comparación estadística: baseline (documento) vs. ajustado (oración) con métricas,
variabilidad por folds (CV) e intervalos de confianza por bootstrap, más prueba de
McNemar sobre el conjunto de prueba con verdad de referencia.

Todo reproducible: SEED=42, particiones OFICIALES de MEDEC.
Salidas -> ./salidas_ajuste/
"""
from __future__ import annotations
import json, random, re
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, GridSearchCV
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, confusion_matrix)

SEED = 42
random.seed(SEED); np.random.seed(SEED)

BASE = Path("medec_try/MEDEC-MS")
OUT = Path("salidas_ajuste"); OUT.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# 1) PREPROCESAMIENTO: nota -> oraciones individuales etiquetadas
# ---------------------------------------------------------------------------
def explotar_oraciones(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte cada nota en varias filas (una por oración) con etiqueta binaria:
       label_oracion = 1 si esa oración es la marcada como errónea, si no 0."""
    filas = []
    for _, r in df.iterrows():
        sents = str(r["Sentences"])
        # el campo 'Sentences' viene como "0 <texto>\n1 <texto>\n..."
        pares = re.findall(r"(?m)^\s*(\d+)\s+(.*)$", sents)
        if not pares:
            continue
        try:
            err_id = int(r["Error Sentence ID"]) if str(r["Error Flag"]) in ("1", "1.0") else -1
        except (ValueError, TypeError):
            err_id = -1
        for sid, texto in pares:
            texto = texto.strip()
            if len(texto) < 3:
                continue
            filas.append({
                "text_id": r["Text ID"],
                "sid": int(sid),
                "oracion": texto,
                "label": 1 if int(sid) == err_id else 0,
            })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# 2) INGENIERÍA DE CARACTERÍSTICAS: rasgos numéricos simples por oración
# ---------------------------------------------------------------------------
NEG = re.compile(r"\b(no|not|without|denies|negative|absent)\b", re.I)

class RasgosOracion(BaseEstimator, TransformerMixin):
    """Rasgos ligeros y verificables que TF-IDF no captura bien."""
    def fit(self, X, y=None): return self
    def transform(self, X):
        out = []
        for t in X:
            t = str(t)
            out.append([
                len(t),                              # longitud
                len(t.split()),                      # nº de palabras
                len(re.findall(r"\d", t)),           # nº de dígitos
                1.0 if NEG.search(t) else 0.0,       # negación presente
            ])
        return np.asarray(out, dtype=float)


def construir_modelo():
    feats = FeatureUnion([
        ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2,
                                  sublinear_tf=True, stop_words="english")),
        ("num", Pipeline([("raw", RasgosOracion()), ("sc", StandardScaler())])),
    ])
    return Pipeline([
        ("feats", feats),
        ("clf", LogisticRegression(solver="liblinear", class_weight="balanced",
                                   random_state=SEED, max_iter=2000)),
    ])


# ---------------------------------------------------------------------------
# 3) MÉTRICAS + utilidades estadísticas
# ---------------------------------------------------------------------------
def met(y, pred, score):
    return {"accuracy": round(accuracy_score(y, pred), 4),
            "precision": round(precision_score(y, pred, zero_division=0), 4),
            "recall": round(recall_score(y, pred, zero_division=0), 4),
            "f1": round(f1_score(y, pred, zero_division=0), 4),
            "roc_auc": round(roc_auc_score(y, score), 4)}


def bootstrap_ci(y, score, metric="roc_auc", n=1000, seed=SEED):
    rng = np.random.default_rng(seed)
    y = np.asarray(y); score = np.asarray(score)
    vals = []
    idx = np.arange(len(y))
    for _ in range(n):
        s = rng.choice(idx, size=len(idx), replace=True)
        if len(np.unique(y[s])) < 2:
            continue
        if metric == "roc_auc":
            vals.append(roc_auc_score(y[s], score[s]))
        else:
            vals.append(f1_score(y[s], (score[s] >= 0.5).astype(int), zero_division=0))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return round(float(np.mean(vals)), 4), round(float(lo), 4), round(float(hi), 4)


def mcnemar(y, pred_a, pred_b):
    """Compara dos clasificadores en las MISMAS muestras (prueba de McNemar)."""
    y = np.asarray(y); a = np.asarray(pred_a); b = np.asarray(pred_b)
    a_ok, b_ok = (a == y), (b == y)
    n01 = int(np.sum(~a_ok & b_ok))   # A falla, B acierta
    n10 = int(np.sum(a_ok & ~b_ok))   # A acierta, B falla
    from scipy.stats import binomtest
    n = n01 + n10
    p = binomtest(min(n01, n10), n, 0.5).pvalue if n > 0 else 1.0
    return {"n01_soloB_acierta": n01, "n10_soloA_acierta": n10, "p_value": round(float(p), 6)}


# ---------------------------------------------------------------------------
# 4) EXPERIMENTO
# ---------------------------------------------------------------------------
def load(f):
    return pd.read_csv(BASE / f).dropna(subset=["Text", "Error Flag"])

def main():
    tr = load("MEDEC-Full-TrainingSet-with-ErrorType.csv")
    va = load("MEDEC-MS-ValidationSet-with-GroundTruth-and-ErrorType.csv")
    te = load("MEDEC-MS-TestSet-with-GroundTruth-and-ErrorType.csv")

    otr, ova, ote = explotar_oraciones(tr), explotar_oraciones(va), explotar_oraciones(te)
    print(f"[oraciones] train={len(otr)} (pos={otr.label.sum()}), "
          f"val={len(ova)} (pos={ova.label.sum()}), test={len(ote)} (pos={ote.label.sum()})")
    prev = otr.label.mean()
    print(f"[oraciones] prevalencia de oración-error en train: {prev:.3%}")

    # --- Búsqueda de hiperparámetros con CV estratificada (5-fold) ---
    modelo = construir_modelo()
    grid = {
        "feats__tfidf__ngram_range": [(1, 1), (1, 2)],
        "clf__C": [0.5, 1.0, 2.0],
    }
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    gs = GridSearchCV(modelo, grid, scoring="roc_auc", cv=cv, n_jobs=-1, refit=True)
    gs.fit(otr.oracion, otr.label)
    print(f"[grid] mejor AUC CV={gs.best_score_:.4f}  params={gs.best_params_}")

    # variabilidad por folds del mejor modelo
    best_idx = gs.best_index_
    fold_scores = [round(float(gs.cv_results_[f"split{k}_test_score"][best_idx]), 4) for k in range(5)]
    print(f"[cv folds AUC] {fold_scores}  -> media={np.mean(fold_scores):.4f} sd={np.std(fold_scores):.4f}")

    best = gs.best_estimator_

    # --- Evaluación en validación y prueba ---
    res = {"config": gs.best_params_,
           "cv_auc_folds": fold_scores,
           "cv_auc_mean": round(float(np.mean(fold_scores)), 4),
           "cv_auc_sd": round(float(np.std(fold_scores)), 4),
           "prevalencia_oracion_error_train": round(float(prev), 4)}

    for nombre, d in [("validacion", ova), ("prueba", ote)]:
        pred = best.predict(d.oracion); score = best.predict_proba(d.oracion)[:, 1]
        m = met(d.label, pred, score)
        auc_ci = bootstrap_ci(d.label, score, "roc_auc")
        f1_ci = bootstrap_ci(d.label, score, "f1")
        m["roc_auc_ci95"] = auc_ci
        m["f1_ci95"] = f1_ci
        m["matriz_confusion"] = confusion_matrix(d.label, pred).tolist()
        res[nombre] = m
        print(f"[{nombre:>10}] acc={m['accuracy']} P={m['precision']} R={m['recall']} "
              f"F1={m['f1']} AUC={m['roc_auc']}  AUC IC95={auc_ci[1:]}")

    # --- Métrica DE NEGOCIO: ¿localiza la oración errónea dentro de la nota? ---
    # Para cada nota con error en test, tomamos la oración de mayor score y vemos
    # si coincide con la oración etiquetada como errónea (localización top-1).
    ote2 = ote.copy()
    ote2["score"] = best.predict_proba(ote2.oracion)[:, 1]
    aciertos, total = 0, 0
    for tid, g in ote2.groupby("text_id"):
        if g.label.sum() == 0:
            continue  # nota sin error
        total += 1
        pred_sid = g.loc[g.score.idxmax(), "sid"]
        true_sid = g.loc[g.label == 1, "sid"].iloc[0]
        aciertos += int(pred_sid == true_sid)
    loc_top1 = round(aciertos / total, 4) if total else 0.0
    res["localizacion_top1_test"] = loc_top1
    res["notas_con_error_test"] = total
    print(f"[localización] top-1 en notas con error (test): {loc_top1:.3%} sobre {total} notas")

    # --- COMPARACIÓN con el baseline (nivel documento) sobre las MISMAS notas ---
    # Reconstruimos la predicción a NIVEL NOTA del modelo ajustado:
    #   nota marcada como "con error" si alguna oración supera el umbral 0.5.
    pred_nota_ajustado, y_nota, score_nota = [], [], []
    for tid, g in ote2.groupby("text_id"):
        y_nota.append(int(g.label.max() > 0))
        pred_nota_ajustado.append(int((g.score >= 0.5).any()))
        score_nota.append(float(g.score.max()))
    y_nota = np.array(y_nota)
    pred_nota_ajustado = np.array(pred_nota_ajustado)
    score_nota = np.array(score_nota)

    m_nota_aj = met(y_nota, pred_nota_ajustado, score_nota)
    res["ajustado_a_nivel_nota"] = m_nota_aj
    print(f"[nota|ajustado] acc={m_nota_aj['accuracy']} P={m_nota_aj['precision']} "
          f"R={m_nota_aj['recall']} F1={m_nota_aj['f1']} AUC={m_nota_aj['roc_auc']}")

    # baseline (documento) sobre las mismas notas de test, para McNemar comparable
    base_pipe = Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2,
                                  sublinear_tf=True, stop_words="english")),
        ("clf", LogisticRegression(solver="liblinear", class_weight="balanced",
                                   random_state=SEED, max_iter=1000))])
    base_pipe.fit(tr.Text.astype(str), tr["Error Flag"].astype(int))
    # alinear por text_id con el mismo orden de y_nota
    ids = list(ote2.groupby("text_id").groups.keys())
    te_por_id = te.set_index("Text ID")
    textos = [str(te_por_id.loc[i, "Text"]) for i in ids]
    y_base = np.array([int(te_por_id.loc[i, "Error Flag"]) for i in ids])
    pred_base = base_pipe.predict(textos)
    score_base = base_pipe.predict_proba(textos)[:, 1]
    m_nota_base = met(y_base, pred_base, score_base)
    res["baseline_a_nivel_nota"] = m_nota_base
    print(f"[nota|baseline] acc={m_nota_base['accuracy']} P={m_nota_base['precision']} "
          f"R={m_nota_base['recall']} F1={m_nota_base['f1']} AUC={m_nota_base['roc_auc']}")

    # McNemar: baseline vs ajustado en las mismas notas
    mc = mcnemar(y_nota, pred_base, pred_nota_ajustado)
    res["mcnemar_baseline_vs_ajustado"] = mc
    print(f"[McNemar] {mc}")

    # --- Interpretabilidad del modelo ajustado ---
    tfidf = best.named_steps["feats"].transformer_list[0][1]
    clf = best.named_steps["clf"]
    nombres = np.array(list(tfidf.get_feature_names_out()) + ["len", "n_palabras", "n_digitos", "negacion"])
    coefs = clf.coef_[0]
    orden = np.argsort(coefs)
    top1 = [(nombres[i], round(float(coefs[i]), 3)) for i in orden[::-1][:15]]
    top0 = [(nombres[i], round(float(coefs[i]), 3)) for i in orden[:15]]
    pd.DataFrame([{"clase": "oracion_erronea", "termino": t, "coef": c} for t, c in top1] +
                 [{"clase": "oracion_normal", "termino": t, "coef": c} for t, c in top0]
                 ).to_csv(OUT / "top_features_ajustado.csv", index=False)
    print("[top -> oración errónea]:", ", ".join(t for t, _ in top1[:8]))

    # --- Guardado ---
    joblib.dump(best, OUT / "modelo_ajustado.joblib")
    res["meta"] = {"semilla": SEED, "dataset": "MEDEC (particiones oficiales)",
                   "tarea": "clasificacion a nivel de ORACION",
                   "versiones": {"scikit_learn": __import__("sklearn").__version__,
                                 "pandas": pd.__version__, "numpy": np.__version__,
                                 "scipy": __import__("scipy").__version__}}
    with open(OUT / "metricas_ajuste.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"\n[ok] Artefactos -> {OUT.resolve()}")
    return res


if __name__ == "__main__":
    main()
