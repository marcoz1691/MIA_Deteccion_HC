"""Ejemplos precargados para la demo Streamlit."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from s10.citimed_utils import leer_archivo_anon, texto_clinico_desde_anon
CSV_CITIMED = ROOT / "data" / "citimed_odontologia.csv"
CSV_EJEMPLO = ROOT / "data" / "citimed_odontologia.example.csv"
CSV_ANON_DIR = ROOT / "s10" / "anonimizador" / "salidas"

EJEMPLOS_HARDCODE = {
    "Nota sin inconsistencias (odontología)": (
        "Paciente de 45 años acude por control periodontal rutinario. "
        "Examen: encías rosadas, sin sangrado al sondaje. "
        "Plan: profilaxis y control en 6 meses."
    ),
    "Error de medicación (alergia a penicilina)": (
        "Paciente refiere dolor en molar 36 desde hace 3 días. "
        "Antecedentes: alergia documentada a penicilina. "
        "Se indica amoxicilina 500 mg cada 8 h pese a alergia documentada a penicilina."
    ),
    "Error de diagnóstico/plan (extracción excesiva)": (
        "Paciente con gingivitis leve confirmada en examen clínico. "
        "Encías levemente inflamadas, sin movilidad dental. "
        "Diagnóstico: gingivitis leve; plan: extracción de todas las piezas."
    ),
}


def _notas_desde_csv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    if "nota_id" not in df.columns or "oracion" not in df.columns:
        return {}
    out: dict[str, str] = {}
    for nota_id, grupo in df.groupby("nota_id"):
        tiene_error = (grupo["label"] == 1).any()
        tipo = ""
        if tiene_error and "error_type" in grupo.columns:
            tipos = grupo.loc[grupo["label"] == 1, "error_type"].dropna().unique()
            tipo = f" ({tipos[0]})" if len(tipos) else ""
        titulo = f"CITIMED ejemplo nota {nota_id}{tipo}"
        out[titulo] = " ".join(grupo.sort_values("oracion_id")["oracion"].astype(str).tolist())
    return out


def _notas_desde_anon_txt(carpeta: Path) -> dict[str, str]:
    if not carpeta.exists():
        return {}
    out: dict[str, str] = {}
    paths = sorted(carpeta.glob("*_ANON.txt"))
    txt_stems = {p.stem.replace("_ANON", "") for p in paths}
    for pdf in sorted(carpeta.glob("*_ANON.pdf")):
        if pdf.stem.replace("_ANON", "") not in txt_stems:
            paths.append(pdf)
    for path in paths:
        raw = leer_archivo_anon(path)
        nota = texto_clinico_desde_anon(raw)
        if nota:
            out[f"CITIMED anon — {path.stem.replace('_ANON', '')}"] = nota
    return out


def listar_ejemplos() -> dict[str, str]:
    """Retorna {titulo: texto_nota} para el selectbox de la demo."""
    ejemplos = dict(EJEMPLOS_HARDCODE)
    csv_path = CSV_CITIMED if CSV_CITIMED.exists() else CSV_EJEMPLO
    ejemplos.update(_notas_desde_csv(csv_path))
    ejemplos.update(_notas_desde_anon_txt(CSV_ANON_DIR))
    return ejemplos
