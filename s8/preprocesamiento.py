"""Preprocesamiento MEDEC: explosión a oraciones, rasgos y configuración lingüística."""
from __future__ import annotations

import re
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

StopWordsLang = Literal["english", "spanish", "none"]

NEG_EN = re.compile(r"\b(no|not|without|denies|negative|absent)\b", re.I)
NEG_ES = re.compile(r"\b(no|sin|negativo|niega|niega|ausente|negativa)\b", re.I)
NEG_BILINGUE = re.compile(
    r"\b(no|not|without|denies|negative|absent|sin|negativo|niega|ausente|negativa)\b",
    re.I,
)

# Abreviaturas odontológicas comunes (normalización léxica básica)
ABREV_ODONTO = {
    r"\bO\.?D\.?\b": "odontologia",
    r"\bRx\b": "radiografia",
    r"\bTx\b": "tratamiento",
    r"\bDx\b": "diagnostico",
    r"\bHx\b": "historia",
}


def normalizar_texto(texto: str, idioma: StopWordsLang = "english") -> str:
    """Normalización clínica básica y lowercasing."""
    t = str(texto).lower().strip()
    for patron, repl in ABREV_ODONTO.items():
        t = re.sub(patron, repl, t, flags=re.I)
    return t


def regex_negacion(idioma: StopWordsLang = "english") -> re.Pattern:
    if idioma == "spanish":
        return NEG_ES
    if idioma == "none":
        return NEG_BILINGUE
    return NEG_EN if idioma == "english" else NEG_BILINGUE


def explotar_oraciones(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte cada nota en filas por oración con label y error_type."""
    filas = []
    for _, r in df.iterrows():
        sents = str(r["Sentences"])
        pares = re.findall(r"(?m)^\s*(\d+)\s+(.*)$", sents)
        if not pares:
            continue
        try:
            err_id = int(r["Error Sentence ID"]) if str(r["Error Flag"]) in ("1", "1.0") else -1
        except (ValueError, TypeError):
            err_id = -1
        error_type = r.get("Error Type", r.get("ErrorType", "Unknown"))
        if pd.isna(error_type):
            error_type = "Unknown"
        for sid, texto in pares:
            texto = texto.strip()
            if len(texto) < 3:
                continue
            filas.append({
                "text_id": r["Text ID"],
                "sid": int(sid),
                "oracion": texto,
                "label": 1 if int(sid) == err_id else 0,
                "error_type": str(error_type),
            })
    return pd.DataFrame(filas)


class RasgosOracion(BaseEstimator, TransformerMixin):
    """Rasgos numéricos por oración con negación configurable."""

    def __init__(self, idioma: StopWordsLang = "english"):
        self.idioma = idioma
        self._neg = regex_negacion(idioma)

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        out = []
        for t in X:
            t = str(t)
            out.append([
                len(t),
                len(t.split()),
                len(re.findall(r"\d", t)),
                1.0 if self._neg.search(t) else 0.0,
            ])
        return np.asarray(out, dtype=float)


def load_medec(base_path, filename: str) -> pd.DataFrame:
    """Carga un split MEDEC con columnas mínimas requeridas."""
    from pathlib import Path
    return pd.read_csv(Path(base_path) / filename).dropna(subset=["Text", "Error Flag"])
