"""Utilidades compartidas del pipeline CITIMED (anonimización → inferencia → eval)."""
from __future__ import annotations

import re
from pathlib import Path


def texto_clinico_desde_anon(texto: str) -> str:
    """Extrae párrafos clínicos (evolución, diagnóstico, tratamiento) para inferencia."""
    lineas = []
    capturar = False
    for linea in texto.splitlines():
        upper = linea.strip().upper()
        if any(k in upper for k in ("EVOLUCI", "DIAGN", "TRATAMIENTO", "MOTIVO", "PLAN")):
            capturar = True
        if upper.startswith(("DATOS DEL", "N.º DE HISTORIA", "AFILIACI", "INGRESO", "ALTA")):
            if "EVOLUCI" not in upper and "DIAGN" not in upper and "TRATAMIENTO" not in upper:
                capturar = False
        if capturar and linea.strip():
            lineas.append(linea.strip())
    cuerpo = " ".join(lineas).strip()
    return cuerpo if cuerpo else texto.strip()


_PHI_NAME_PATTERN = re.compile(
    r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,2})\b"
)
_PHI_STOP = {
    "Historia", "Clínica", "Citimed", "Datos", "Paciente", "Ingreso", "Evolución",
    "Diagnóstico", "Tratamiento", "Alta", "Motivo", "Antecedentes", "Insuficiencia",
    "Hospital", "Metropolitano", "Quito", "Amazonas", "Colón", "Enalapril",
    "La Dra", "El Dr", "El paciente", "Ejemplo", "Sintético", "Sintetico",
}


def phi_restante(texto: str) -> list[str]:
    """Detecta posibles nombres propios no anonimizados (heurística simple)."""
    hallazgos: list[str] = []
    for m in _PHI_NAME_PATTERN.finditer(texto):
        candidato = m.group(1)
        if candidato not in _PHI_STOP and not candidato.startswith("["):
            hallazgos.append(candidato)
    return hallazgos


def leer_archivo_anon(path: Path) -> str:
    """Lee texto anonimizado desde .txt o extrae texto de .pdf anonimizado."""
    if path.suffix.lower() == ".pdf":
        import fitz  # PyMuPDF

        doc = fitz.open(path)
        try:
            return "\n".join(page.get_text() for page in doc).strip()
        finally:
            doc.close()
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def listar_salidas_anon(salida: Path) -> list[Path]:
    """Lista archivos anonimizados procesables (.txt y .pdf sin .txt homólogo)."""
    paths = sorted(salida.glob("*_ANON.txt"))
    txt_stems = {p.stem.replace("_ANON", "") for p in paths}
    for pdf in sorted(salida.glob("*_ANON.pdf")):
        stem = pdf.stem.replace("_ANON", "")
        if stem not in txt_stems:
            paths.append(pdf)
    return paths
