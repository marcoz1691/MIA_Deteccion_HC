"""
Consolida la plantilla de verificacion humana con:
  - tachados: hallazgos sanitizados del pipeline (sin texto)
  - escapados_capa_texto: residuos detectados sobre el OCR del PDF YA tachado
  - presentes: cota inferior (tachados + escapados de capa de texto)

No imprime ni escribe identificadores. El CSV de salida solo tiene conteos.

Uso:
  python s11/consolidar_verificacion.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGREGADOS = ROOT / "s11" / "evidencias" / "anonimizacion_agregados.json"
PLANTILLA = ROOT / "s11" / "evidencias" / "verificacion_humana_plantilla.csv"
SALIDA = ROOT / "s11" / "evidencias" / "verificacion_humana.csv"
REPORTE = ROOT / "s11" / "evidencias" / "verificacion_humana_resumen.json"

CATEGORIAS = ("NOMBRE", "CEDULA", "HC", "TELEFONO", "EMAIL", "FECHA", "DIRECCION")


def _etiquetas_a_categorias(etiqueta: str) -> list[str]:
    parts = [p for p in etiqueta.split("+") if p in CATEGORIAS]
    return parts or ([etiqueta] if etiqueta in CATEGORIAS else [])


def _cargar_tachados(agregados: dict) -> dict[tuple[int, str], int]:
    counts: dict[tuple[int, str], int] = defaultdict(int)
    for pagina in agregados.get("paginas", []):
        n = int(pagina["pagina"])
        for etiq, k in (pagina.get("hallazgos_por_etiqueta") or {}).items():
            for cat in _etiquetas_a_categorias(etiq):
                counts[(n, cat)] += int(k)
    return counts


def _residuos_capa_texto() -> dict[tuple[int, str], int]:
    """Cuenta residuos en oraciones extraidas del PDF buscable, sin guardar texto."""
    sys.path.insert(0, str(ROOT / "s11"))
    from extraer_corpus import extraer_paginas, segmentar, es_oracion_util, tamizar_phi

    pdf = ROOT / "s11" / "anonimizador_ocr" / "salidas_buscable" / "hc0001_anon.pdf"
    if not pdf.exists():
        return {}
    filas = []
    for numero, texto in extraer_paginas(pdf):
        for oracion in segmentar(texto):
            if not es_oracion_util(oracion):
                continue
            filas.append({"oracion": oracion, "oracion_id": len(filas), "pagina": numero})
    residuos = tamizar_phi(filas, usar_ner=False)
    counts: dict[tuple[int, str], int] = defaultdict(int)
    for r in residuos:
        cat = r.get("categoria", "")
        if cat in CATEGORIAS:
            counts[(int(r["pagina"]), cat)] += 1
    return counts


def main() -> int:
    agregados = json.loads(AGREGADOS.read_text(encoding="utf-8"))
    tachados = _cargar_tachados(agregados)
    escapados = _residuos_capa_texto()
    paginas_revision = {int(p["pagina"]) for p in agregados.get("paginas_a_revisar", [])}

    filas_out: list[dict] = []
    with open(PLANTILLA, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        campos = reader.fieldnames or []
        for row in reader:
            pag = int(row["pagina"])
            cat = row["categoria"]
            t = tachados.get((pag, cat), 0)
            e = escapados.get((pag, cat), 0)
            presentes = t + e
            obs = "pagina_manuscrito_conf_ocr_baja" if pag in paginas_revision else ""
            if e:
                obs = (obs + "; " if obs else "") + "residuo_capa_texto_omitido_del_corpus"
            filas_out.append(
                {
                    "pagina": pag,
                    "categoria": cat,
                    "presentes": presentes,
                    "tachados": t,
                    "escapados": e,
                    "sobre_tachado": "",
                    "revisor": "pipeline+capa_texto",
                    "observacion_sin_texto": obs,
                }
            )

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with open(SALIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas_out)

    por_cat: dict[str, dict[str, int]] = {c: {"presentes": 0, "tachados": 0, "escapados": 0} for c in CATEGORIAS}
    for row in filas_out:
        c = row["categoria"]
        por_cat[c]["presentes"] += int(row["presentes"] or 0)
        por_cat[c]["tachados"] += int(row["tachados"] or 0)
        por_cat[c]["escapados"] += int(row["escapados"] or 0)

    recall = {}
    for c, v in por_cat.items():
        recall[c] = (v["tachados"] / v["presentes"]) if v["presentes"] else None

    criticos = ["NOMBRE", "CEDULA", "HC"]
    bloqueo_ok = all((recall[c] or 0) == 1.0 or por_cat[c]["presentes"] == 0 for c in criticos)

    resumen = {
        "fuente_tachados": "s11/evidencias/anonimizacion_agregados.json",
        "fuente_escapados": "OCR sobre PDF ya tachado (--buscable); detector sin NER",
        "nota": (
            "presentes es cota inferior (tachados + residuos de capa de texto). "
            "No sustituye la revision visual de las 20 paginas originales por dos revisores. "
            "No contiene texto clinico."
        ),
        "por_categoria": por_cat,
        "recall_capa_texto": recall,
        "criterio_bloqueo_nombre_cedula_hc": bloqueo_ok,
        "paginas_manuscrito": sorted(paginas_revision),
        "n_filas": len(filas_out),
    }
    REPORTE.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] {SALIDA}")
    print(f"[ok] {REPORTE}")
    print(f"[info] recall_capa_texto={ {k: (round(v, 3) if v is not None else None) for k, v in recall.items()} }")
    print(f"[info] criterio_bloqueo_criticos={'OK' if bloqueo_ok else 'NO'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
