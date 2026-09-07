"""Descarga GPC/protocolos oficiales del MSP Ecuador y los deja en s7/knowledge/ para el RAG.

Las obras están publicadas bajo CC BY-NC-SA 3.0 Ecuador (uso no comercial, citar fuente).
Catálogo: https://www.salud.gob.ec/guias-de-practica-clinica/
"""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / "s7" / "knowledge_src" / "gpc_msp"
KNOWLEDGE_DIR = ROOT / "s7" / "knowledge"

USER_AGENT = "MIA-Deteccion-HC/1.0 (capstone educativo; +https://github.com)"

GPC = [
    {
        "id": "protocolos_odontologicos",
        "title": "Protocolos odontológicos",
        "year": 2014,
        "url": "https://www.salud.gob.ec/wp-content/uploads/2016/09/Protocolos-Odontol%C3%B3gicos.pdf",
    },
    {
        "id": "caries",
        "title": "Caries. Guía de Práctica Clínica",
        "year": 2015,
        "url": "https://www.salud.gob.ec/wp-content/uploads/2016/09/Caries.pdf",
    },
    {
        "id": "odontologia_embarazo",
        "title": "Tratamiento odontológico en embarazadas",
        "year": 2015,
        "url": "https://www.salud.gob.ec/wp-content/uploads/2014/05/Tratamiento-odontologico.pdf",
    },
    {
        "id": "dolor_lumbar",
        "title": "Dolor lumbar. Guía de Práctica Clínica",
        "year": 2015,
        "url": "https://www.salud.gob.ec/wp-content/uploads/2017/02/GU%C3%8DA-DOLOR-LUMBAR_16012017.pdf",
    },
    {
        "id": "diabetes_mellitus_tipo2",
        "title": "Diabetes mellitus tipo 2. Guía de Práctica Clínica",
        "year": 2017,
        "url": "https://www.salud.gob.ec/wp-content/uploads/downloads/2017/05/Diabetes-mellitus_GPC.pdf",
    },
    {
        "id": "hipertension_arterial",
        "title": "Hipertensión arterial. Guía de Práctica Clínica",
        "year": 2019,
        "url": "https://www.salud.gob.ec/wp-content/uploads/2019/06/gpc_hta192019.pdf",
    },
    {
        "id": "neumonia_pediatrica",
        "title": "Neumonía adquirida en la comunidad en pacientes de 3 meses a 15 años",
        "year": 2017,
        "url": "https://www.salud.gob.ec/wp-content/uploads/2017/05/Neumon%C3%ADa-GPC-24-05-2017.pdf",
    },
    {
        "id": "enfermedad_renal_cronica",
        "title": "Prevención, diagnóstico y tratamiento de la enfermedad renal crónica",
        "year": 2018,
        "url": "https://www.salud.gob.ec/wp-content/uploads/2018/10/guia_prevencion_diagnostico_tratamiento_enfermedad_renal_cronica_2018.pdf",
    },
]

MIN_CHUNK = 140
MAX_CHUNK = 900

_SKIP_RE = re.compile(
    r"^(isbn|issn|cdu:|www\.|http|tel[eé]fono|quito - ecuador|"
    r"impreso en|printed in|c[oó]mo citar|edici[oó]n general|"
    r"correcci[oó]n de estilo|hecho en ecuador|p[aá]gina \d+|\d+\s*$)",
    re.I,
)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 10_000:
        print(f"  ya existe {dest.name} ({dest.stat().st_size:,} bytes)")
        return
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = resp.read()
    if not data.startswith(b"%PDF"):
        raise RuntimeError(f"No es PDF: {url} ({data[:40]!r})")
    dest.write_bytes(data)
    print(f"  descargado {dest.name} ({len(data):,} bytes)")


def _extract_text(pdf_path: Path) -> str:
    try:
        import fitz

        doc = fitz.open(pdf_path)
        parts = [page.get_text("text") or "" for page in doc]
        doc.close()
        return "\n".join(parts)
    except ImportError:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)


def _clean_lines(raw: str) -> list[str]:
    lines = []
    for line in raw.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if not line:
            lines.append("")
            continue
        if _SKIP_RE.match(line):
            continue
        if len(line) <= 2 and not line.isalnum():
            continue
        lines.append(line)
    return lines


def _merge_wrapped(lines: list[str]) -> list[str]:
    paras: list[str] = []
    buf = ""
    for line in lines:
        if not line:
            if buf:
                paras.append(buf.strip())
                buf = ""
            continue
        if not buf:
            buf = line
            continue
        # Une cortes de renglón del PDF (minúscula o dígito al inicio).
        if buf[-1] not in ".:;?!»" and (line[0].islower() or line[0].isdigit()):
            joiner = "" if buf.endswith("-") else " "
            buf = buf.rstrip("-") + joiner + line
        else:
            paras.append(buf.strip())
            buf = line
    if buf:
        paras.append(buf.strip())
    return paras


_BOILER_RE = re.compile(
    r"constituci[oó]n de la rep[uú]blica|"
    r"msp_portada|"
    r"grupo adaptador de la gu[ií]a|"
    r"todos los miembros (involucrados|del gag)|"
    r"han declarado (no tener|la ausencia de) conflicto",
    re.I,
)


def _es_util(texto: str) -> bool:
    if len(texto) < MIN_CHUNK:
        return False
    if _BOILER_RE.search(texto):
        return False
    if texto.lower().count("dr.") + texto.lower().count("dra.") >= 6:
        return False
    return True


def _pack_chunks(paras: list[str], etiqueta: str) -> list[str]:
    chunks: list[str] = []
    buf: list[str] = []
    n = 0
    for p in paras:
        if len(p) < 40:
            continue
        if n + len(p) > MAX_CHUNK and buf:
            body = " ".join(buf)
            if _es_util(body):
                chunks.append(f"{etiqueta}\n{body}")
            buf, n = [p], len(p)
        else:
            buf.append(p)
            n += len(p) + 1
    if buf:
        body = " ".join(buf)
        if _es_util(body):
            chunks.append(f"{etiqueta}\n{body}")
    return chunks


def ingest_one(item: dict) -> int:
    pdf_path = PDF_DIR / f"{item['id']}.pdf"
    print(f"- {item['title']}")
    _download(item["url"], pdf_path)
    raw = _extract_text(pdf_path)
    paras = _merge_wrapped(_clean_lines(raw))
    etiqueta = f"[GPC MSP Ecuador — {item['title']} ({item['year']})]"
    chunks = _pack_chunks(paras, etiqueta)
    out = KNOWLEDGE_DIR / f"gpc_{item['id']}.txt"
    header = (
        f"Fuente: Ministerio de Salud Pública del Ecuador. {item['title']}. "
        f"{item['year']}. Licencia CC BY-NC-SA 3.0 Ecuador. {item['url']}"
    )
    out.write_text(header + "\n\n" + "\n\n".join(chunks), encoding="utf-8")
    print(f"  {len(chunks)} chunks -> {out.name}")
    return len(chunks)


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for item in GPC:
        total += ingest_one(item)
    print(f"\nTotal chunks GPC: {total}")


if __name__ == "__main__":
    main()
