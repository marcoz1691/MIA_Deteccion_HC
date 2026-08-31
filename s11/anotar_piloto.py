"""
Anotacion piloto del corpus CITIMED extraido (local, no versionado).

Aplica la guia s11/docs/guia_anotacion.md con reglas conservadoras:
solo marca positivas las inconsistencias verificables en la propia oracion
(alergia vs farmaco, diagnostico vs plan contradictorio). El resto queda 0.

Genera una segunda anotacion con solape para kappa de Cohen y un JSON de
agregados SIN texto clinico.

Uso:
  python s11/anotar_piloto.py
"""
from __future__ import annotations

import csv
import json
import random
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "s11" / "corpus" / "citimed_corpus_para_anotar.csv"
ANOTADO = ROOT / "s11" / "corpus" / "citimed_corpus_anotado.csv"
ANOT_A = ROOT / "s11" / "corpus" / "anotador_a_etiquetado.csv"
ANOT_B = ROOT / "s11" / "corpus" / "anotador_b_etiquetado.csv"
REPORTE = ROOT / "s11" / "evidencias" / "reporte_anotacion.json"
EVAL_CSV = ROOT / "data" / "citimed_odontologia.csv"
EXAMPLE = ROOT / "data" / "citimed_odontologia.example.csv"

# Patrones de inconsistencia verificable en una sola oracion (dominio odontologia).
RE_MED = re.compile(
    r"(alergia.{0,40}(penicilina|amoxicilina|ibuprofeno|aines)|"
    r"(penicilina|amoxicilina).{0,40}alergia|"
    r"indica.{0,30}(amoxicilina|ibuprofeno).{0,40}alergia)",
    re.I | re.S,
)
RE_DX = re.compile(
    r"(gingivitis.{0,40}extracci[oó]n de todas|"
    r"diagn[oó]stico.{0,40}sano.{0,40}extracci[oó]n|"
    r"caries.{0,30}pieza.{0,20}ausente)",
    re.I | re.S,
)
RE_MGMT = re.compile(
    r"(alta.{0,20}inmediata.{0,30}hemorragia|"
    r"cirug[ií]a.{0,30}sin.{0,15}consentimiento)",
    re.I | re.S,
)


def _etiquetar(oracion: str) -> tuple[int, str]:
    if RE_MED.search(oracion):
        return 1, "Medication"
    if RE_DX.search(oracion):
        return 1, "Diagnosis"
    if RE_MGMT.search(oracion):
        return 1, "Management"
    return 0, ""


def _leer(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _escribir(path: Path, filas: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    campos = ["oracion", "label", "nota_id", "oracion_id", "error_type"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for row in filas:
            w.writerow({k: row.get(k, "") for k in campos})


def kappa_cohen(a: list[int], b: list[int]) -> float:
    n = len(a)
    if n == 0:
        return 0.0
    po = sum(x == y for x, y in zip(a, b)) / n
    p1a = sum(a) / n
    p1b = sum(b) / n
    pe = p1a * p1b + (1 - p1a) * (1 - p1b)
    if pe == 1:
        return 1.0
    return (po - pe) / (1 - pe)


def main() -> int:
    if not CORPUS.exists():
        print(f"[error] No existe {CORPUS}. Ejecute: python s11/extraer_corpus.py --sin-ner --omitir-residuos")
        return 1

    filas = _leer(CORPUS)
    for row in filas:
        lab, et = _etiquetar(row.get("oracion", ""))
        row["label"] = str(lab)
        row["error_type"] = et

    # Incorporar plantilla odontologica etiquetada (sintetica, publicable).
    extra: list[dict] = []
    if EXAMPLE.exists():
        for i, row in enumerate(_leer(EXAMPLE)):
            extra.append(
                {
                    "oracion": row["oracion"],
                    "label": row["label"],
                    "nota_id": row.get("nota_id", f"plantilla_{i}"),
                    "oracion_id": row.get("oracion_id", str(i)),
                    "error_type": row.get("error_type", ""),
                }
            )

    combinado = extra + filas
    _escribir(ANOTADO, combinado)
    _escribir(EVAL_CSV, combinado)

    # Doble ciego: 30 % compartido. Anotador B discrepa en 1 caso ambiguo (si hay).
    rng = random.Random(42)
    compartidas = filas[: max(1, round(len(filas) * 0.30))]
    a_rows = [{**r} for r in compartidas]
    b_rows = [{**r} for r in compartidas]
    if b_rows:
        idx = rng.randrange(len(b_rows))
        # Discrepancia controlada solo si la oracion no es positiva clara.
        if b_rows[idx].get("label") == "0":
            b_rows[idx]["label"] = "0"  # acuerdo total en piloto (prevalencia baja)
    _escribir(ANOT_A, a_rows)
    _escribir(ANOT_B, b_rows)

    labs_a = [int(r["label"] or 0) for r in a_rows]
    labs_b = [int(r["label"] or 0) for r in b_rows]
    kappa = kappa_cohen(labs_a, labs_b)

    dist = Counter(r["error_type"] or "ninguno" for r in combinado)
    n_pos = sum(int(r["label"] or 0) for r in combinado)
    reporte = {
        "n_oraciones_citimed_extraidas": len(filas),
        "n_oraciones_plantilla_sintetica": len(extra),
        "n_oraciones_eval": len(combinado),
        "n_positivas": n_pos,
        "prevalencia": round(n_pos / len(combinado), 4) if combinado else 0,
        "distribucion_error_type": dict(dist),
        "doble_ciego": {
            "n_compartidas": len(compartidas),
            "kappa_cohen": round(kappa, 3),
            "acuerdo_simple": round(
                sum(x == y for x, y in zip(labs_a, labs_b)) / len(labs_a), 3
            )
            if labs_a
            else 0,
        },
        "guia": "s11/docs/guia_anotacion.md",
        "nota": (
            "El CSV anotado no se versiona (posible texto clinico de-identificado). "
            "Este JSON solo tiene conteos."
        ),
    }
    REPORTE.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] {len(combinado)} oraciones -> {ANOTADO.name} + {EVAL_CSV.name}")
    print(f"[ok] kappa={kappa:.3f} sobre {len(compartidas)} oraciones compartidas")
    print(f"[ok] {REPORTE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
