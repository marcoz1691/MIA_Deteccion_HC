"""Evaluación cross-domain MEDEC → CITIMED Odontología (preparado para cuando llegue el corpus)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import pandas as pd
import yaml
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from s7.metricas import eval_oraciones, localizacion_top1
from s7.preprocesamiento import RasgosOracion, explotar_oraciones, load_medec, stop_words_tfidf

SEED = 42


def construir_modelo(idioma: str = "spanish"):
    stop = stop_words_tfidf(idioma)  # type: ignore[arg-type]
    return Pipeline([
        ("feats", FeatureUnion([
            ("tfidf", TfidfVectorizer(
                lowercase=True, ngram_range=(1, 2), min_df=2,
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


def cargar_citimed(path: Path, cfg: dict) -> pd.DataFrame:
    """Espera CSV con columnas configurables. Ver data/citimed_odontologia.example.csv."""
    if not path.exists():
        raise FileNotFoundError(
            f"Corpus CITIMED no encontrado en {path}. "
            f"Copie data/citimed_odontologia.example.csv como plantilla."
        )
    df = pd.read_csv(path)
    required = [cfg["col_texto"], cfg["col_label"]]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Columna requerida '{col}' no encontrada en {path}")
    return df.rename(columns={
        cfg["col_texto"]: "oracion",
        cfg["col_label"]: "label",
    })


def main():
    parser = argparse.ArgumentParser(description="Eval CITIMED Odontología")
    parser.add_argument("--config", default="s7/config.yaml")
    parser.add_argument("--modo", default="cross_domain",
                        choices=["cross_domain", "fine_tune"],
                        help="cross_domain: train MEDEC → eval CITIMED; fine_tune: split CITIMED")
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    out_dir = Path(cfg["salidas"]["dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    citimed_path = Path(cfg["citimed"]["data_path"])
    export = {"modo": args.modo, "status": "pending_data"}

    if not citimed_path.exists():
        export["mensaje"] = (
            "Corpus CITIMED Odontología pendiente de anonimización. "
            "Script listo; colocar CSV en data/citimed_odontologia.csv"
        )
        out_path = out_dir / "eval_citimed.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(export, f, ensure_ascii=False, indent=2)
        print(f"[pendiente] {export['mensaje']}")
        print(f"[ok] Plantilla de config -> {out_path}")
        return

    citimed = cargar_citimed(citimed_path, cfg["citimed"])
    base = Path(cfg["medec"]["base_path"])
    tr = load_medec(base, cfg["medec"]["train"])
    otr = explotar_oraciones(tr)

    if args.modo == "cross_domain":
        model = construir_modelo(idioma="spanish")
        model.fit(otr.oracion, otr.label)
        pred = model.predict(citimed.oracion)
        score = model.predict_proba(citimed.oracion)[:, 1]
        export["metricas"] = eval_oraciones(citimed.label, pred, score)
        export["n_oraciones"] = len(citimed)
        export["idioma"] = "spanish"
        export["entrenamiento"] = "MEDEC_train"
    else:
        tr_c, te_c = train_test_split(
            citimed, test_size=0.2, stratify=citimed.label, random_state=SEED
        )
        model = construir_modelo(idioma="spanish")
        model.fit(tr_c.oracion, tr_c.label)
        pred = model.predict(te_c.oracion)
        score = model.predict_proba(te_c.oracion)[:, 1]
        export["metricas"] = eval_oraciones(te_c.label, pred, score)
        export["n_oraciones"] = len(te_c)
        export["idioma"] = "spanish"
        export["entrenamiento"] = "CITIMED_fine_tune_80_20"

    out_path = out_dir / "eval_citimed.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)
    print(f"[ok] AUC={export['metricas']['roc_auc']} AUPRC={export['metricas']['auprc']}")
    print(f"[ok] -> {out_path}")


if __name__ == "__main__":
    main()
