"""Métricas compartidas: ROC-AUC, AUPRC, bootstrap, McNemar y localización top-1."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

SEED = 42


def met(y, pred, score) -> dict:
    """Métricas de clasificación binaria incluyendo AUPRC."""
    y = np.asarray(y)
    pred = np.asarray(pred)
    score = np.asarray(score)
    return {
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y, pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y, score)), 4),
        "auprc": round(float(average_precision_score(y, score)), 4),
    }


def bootstrap_ci(y, score, metric: str = "roc_auc", n: int = 1000, seed: int = SEED):
    """IC95 % por bootstrap para roc_auc, auprc o f1."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    score = np.asarray(score)
    vals = []
    idx = np.arange(len(y))
    for _ in range(n):
        s = rng.choice(idx, size=len(idx), replace=True)
        if len(np.unique(y[s])) < 2:
            continue
        if metric == "roc_auc":
            vals.append(roc_auc_score(y[s], score[s]))
        elif metric == "auprc":
            vals.append(average_precision_score(y[s], score[s]))
        else:
            vals.append(f1_score(y[s], (score[s] >= 0.5).astype(int), zero_division=0))
    if not vals:
        return (0.0, 0.0, 0.0)
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return round(float(np.mean(vals)), 4), round(float(lo), 4), round(float(hi), 4)


def mcnemar(y, pred_a, pred_b) -> dict:
    """Prueba de McNemar entre dos clasificadores en las mismas muestras."""
    y = np.asarray(y)
    a = np.asarray(pred_a)
    b = np.asarray(pred_b)
    a_ok, b_ok = (a == y), (b == y)
    n01 = int(np.sum(~a_ok & b_ok))
    n10 = int(np.sum(a_ok & ~b_ok))
    n = n01 + n10
    p = binomtest(min(n01, n10), n, 0.5).pvalue if n > 0 else 1.0
    return {"n01_soloB_acierta": n01, "n10_soloA_acierta": n10, "p_value": round(float(p), 6)}


def localizacion_top1(df: pd.DataFrame, score_col: str = "score") -> dict:
    """Localización top-1: oración de mayor score vs. oración errónea anotada."""
    aciertos, total = 0, 0
    for _, g in df.groupby("text_id"):
        if g.label.sum() == 0:
            continue
        total += 1
        pred_sid = g.loc[g[score_col].idxmax(), "sid"]
        true_sid = g.loc[g.label == 1, "sid"].iloc[0]
        aciertos += int(pred_sid == true_sid)
    rate = round(aciertos / total, 4) if total else 0.0
    return {"localizacion_top1": rate, "notas_con_error": total, "aciertos": aciertos}


def localizacion_top1_por_tipo(df: pd.DataFrame, score_col: str = "score") -> pd.DataFrame:
    """Localización top-1 agrupada por tipo de error clínico."""
    filas = []
    for error_type, gtipo in df.groupby("error_type"):
        if error_type in (None, "", "nan"):
            continue
        sub = gtipo[gtipo.label == 1].drop_duplicates("text_id")
        if sub.empty:
            continue
        notas = []
        for tid in sub.text_id.unique():
            g = gtipo[gtipo.text_id == tid]
            if g.label.sum() == 0:
                continue
            pred_sid = g.loc[g[score_col].idxmax(), "sid"]
            true_sid = g.loc[g.label == 1, "sid"].iloc[0]
            notas.append(int(pred_sid == true_sid))
        if notas:
            filas.append({
                "error_type": error_type,
                "localizacion_top1": round(sum(notas) / len(notas), 4),
                "n_notas": len(notas),
            })
    return pd.DataFrame(filas)


def eval_oraciones(y, pred, score, bootstrap_n: int = 1000) -> dict:
    """Bloque completo de métricas a nivel de oración con IC95."""
    m = met(y, pred, score)
    m["roc_auc_ci95"] = bootstrap_ci(y, score, "roc_auc", n=bootstrap_n)
    m["auprc_ci95"] = bootstrap_ci(y, score, "auprc", n=bootstrap_n)
    m["f1_ci95"] = bootstrap_ci(y, score, "f1", n=bootstrap_n)
    m["matriz_confusion"] = confusion_matrix(y, pred).tolist()
    return m


def metricas_por_tipo(df: pd.DataFrame, score_col: str = "score", umbral: float = 0.5) -> pd.DataFrame:
    """Recall, precision, F1, AUPRC por ErrorType (solo oraciones positivas)."""
    filas = []
    positivos = df[df.label == 1].copy()
    for error_type, g in positivos.groupby("error_type"):
        if error_type in (None, "", "nan"):
            error_type = "Unknown"
        y = g.label.values
        score = g[score_col].values
        pred = (score >= umbral).astype(int)
        filas.append({
            "error_type": error_type,
            "n_oraciones": len(g),
            "recall": round(float(recall_score(y, pred, zero_division=0)), 4),
            "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y, pred, zero_division=0)), 4),
            "auprc": round(float(average_precision_score(y, score)), 4),
        })
    result = pd.DataFrame(filas)
    loc = localizacion_top1_por_tipo(df, score_col)
    if not result.empty and not loc.empty:
        result = result.merge(loc, on="error_type", how="left")
    return result


def curvas_pr(y, score) -> tuple[np.ndarray, np.ndarray]:
    """Curva precision-recall para graficar."""
    return precision_recall_curve(y, score)[:2]


def curvas_roc(y, score) -> tuple[np.ndarray, np.ndarray]:
    """Curva ROC para graficar."""
    fpr, tpr, _ = roc_curve(y, score)
    return fpr, tpr
