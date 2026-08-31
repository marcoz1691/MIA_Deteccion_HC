"""
Extrae el corpus CITIMED en espanol desde el PDF ya anonimizado y buscable.

El PDF de entrada se genera con `--buscable`, lo que significa que su capa de texto
proviene de un OCR ejecutado sobre la imagen YA TACHADA. Por construccion, entonces,
el texto extraido no puede contener los identificadores redactados: donde habia un
nombre ahora hay pixeles negros. Aun asi el script vuelve a pasar el detector de
identificadores sobre cada oracion y se niega a escribir el corpus si encuentra algo,
porque un tachado incompleto en una sola pagina bastaria para filtrar PHI al
repositorio.

Salidas (en s11/corpus/):
  citimed_corpus_para_anotar.csv  esquema compatible con s7/eval_citimed.py
  reporte_extraccion.json         agregados sin texto clinico
  anotador_a.csv / anotador_b.csv particiones con solape para el kappa

Uso:
  python s11/extraer_corpus.py
  python s11/extraer_corpus.py --entrada <pdf> --salida s11/corpus --solape 0.30
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "s11" / "anonimizador_ocr"))

try:
    import pymupdf as fitz
except ImportError:  # PyMuPDF < 1.24
    import fitz

PDF_POR_DEFECTO = ROOT / "s11" / "anonimizador_ocr" / "salidas_buscable" / "hc0001_anon.pdf"
SALIDA_POR_DEFECTO = ROOT / "s11" / "corpus"

# Abreviaturas tras las que un punto no cierra oracion. Sin esto, el segmentador
# parte "Dr. Perez" o "500 mg. cada 8 h" en dos oraciones falsas.
ABREVIATURAS = {
    "dr", "dra", "sr", "sra", "srta", "lic", "ing", "od", "dr(a)",
    "mg", "ml", "gr", "kg", "cc", "ui", "mcg",
    "aprox", "etc", "obs", "ref", "dx", "tx", "rx", "hx",
    "izq", "der", "sup", "inf", "ant", "post",
    "no", "num", "nro", "hc", "ci", "av", "cia",
    "pza", "pzas", "vol", "max", "min", "seg", "hrs",
}

RE_FIN_ORACION = re.compile(r"(?<=[.!?;])\s+")
RE_ESPACIOS = re.compile(r"\s+")
# Ruido tipico del OCR de formularios: reglones de guiones, puntos o pipes.
RE_SOLO_RUIDO = re.compile(r"^[\W\d_]+$", re.UNICODE)
RE_TIENE_LETRAS = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]")

MIN_PALABRAS = 4
MIN_CARACTERES = 20


def _limpiar(texto: str) -> str:
    texto = texto.replace("\u00ad", "")           # guion blando del OCR
    texto = re.sub(r"-\n(?=[a-záéíóúñ])", "", texto)  # palabra cortada por salto
    texto = texto.replace("\n", " ")
    return RE_ESPACIOS.sub(" ", texto).strip()


def _cierra_oracion(fragmento: str) -> bool:
    ultima = fragmento.rstrip(".!?;").split()[-1] if fragmento.rstrip(".!?;").split() else ""
    return ultima.lower().strip("().,") not in ABREVIATURAS


def segmentar(texto: str) -> list[str]:
    """Segmentacion por puntuacion con reenganche de abreviaturas."""
    piezas = RE_FIN_ORACION.split(texto)
    oraciones: list[str] = []
    acumulado = ""
    for pieza in piezas:
        pieza = pieza.strip()
        if not pieza:
            continue
        acumulado = f"{acumulado} {pieza}".strip() if acumulado else pieza
        if _cierra_oracion(acumulado):
            oraciones.append(acumulado)
            acumulado = ""
    if acumulado:
        oraciones.append(acumulado)
    return oraciones


def es_oracion_util(oracion: str) -> bool:
    """Descarta andamiaje del formulario: rotulos, reglones vacios y ruido de OCR."""
    if len(oracion) < MIN_CARACTERES:
        return False
    if len(oracion.split()) < MIN_PALABRAS:
        return False
    if RE_SOLO_RUIDO.match(oracion):
        return False
    if not RE_TIENE_LETRAS.search(oracion):
        return False
    letras = sum(1 for c in oracion if c.isalpha())
    if letras / len(oracion) < 0.55:
        return False
    return True


def extraer_paginas(pdf: Path) -> list[tuple[int, str]]:
    paginas: list[tuple[int, str]] = []
    with fitz.open(pdf) as doc:
        for indice, pagina in enumerate(doc, start=1):
            paginas.append((indice, _limpiar(pagina.get_text("text"))))
    return paginas


def tamizar_phi(oraciones: list[dict], usar_ner: bool) -> list[dict]:
    """Devuelve los residuos detectados, con categoria y pagina pero SIN el texto."""
    try:
        from anonimizador_ocr import deteccion
    except ImportError as exc:
        raise SystemExit(
            "No se pudo importar el detector de identificadores. El tamizado de PHI "
            f"es obligatorio, asi que el proceso se detiene. Detalle: {exc}"
        ) from exc

    residuos: list[dict] = []
    for fila in oraciones:
        hallazgos = deteccion.detectar(
            fila["oracion"], usar_ner=usar_ner, fechas="nacimiento"
        )
        for h in hallazgos:
            residuos.append(
                {
                    "pagina": fila["pagina"],
                    "oracion_id": fila["oracion_id"],
                    "categoria": getattr(h, "etiqueta", "DESCONOCIDA"),
                    "longitud_detectada": len(getattr(h, "texto", "") or ""),
                }
            )
    return residuos


def escribir_csv(destino: Path, filas: list[dict]) -> None:
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["oracion", "label", "nota_id", "oracion_id", "error_type"])
        for fila in filas:
            w.writerow([fila["oracion"], "", fila["nota_id"], fila["oracion_id"], ""])


def partir_para_kappa(filas: list[dict], solape: float) -> tuple[list[dict], list[dict]]:
    """Dos particiones que comparten un porcentaje de oraciones, para medir acuerdo."""
    total = len(filas)
    n_solape = max(1, round(total * solape)) if total else 0
    compartidas = filas[:n_solape]
    resto = filas[n_solape:]
    mitad = len(resto) // 2
    return compartidas + resto[:mitad], compartidas + resto[mitad:]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entrada", type=Path, default=PDF_POR_DEFECTO, help="PDF anonimizado y buscable")
    ap.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    ap.add_argument("--nota-id", default="citimed_hc0001", help="identificador de la nota de origen")
    ap.add_argument("--solape", type=float, default=0.30, help="fraccion de oraciones en doble ciego")
    ap.add_argument("--sin-ner", action="store_true", help="tamizar PHI solo con reglas, sin spaCy")
    ap.add_argument(
        "--permitir-residuos",
        action="store_true",
        help="escribir el corpus aunque el tamizado encuentre identificadores (NO usar para entrega)",
    )
    ap.add_argument(
        "--omitir-residuos",
        action="store_true",
        help="descartar oraciones con identificador residual y escribir el resto (ciclo de correccion)",
    )
    args = ap.parse_args(argv)

    if not args.entrada.exists():
        print(f"[error] No existe el PDF de entrada: {args.entrada}", file=sys.stderr)
        print("        Genera primero la corrida buscable:", file=sys.stderr)
        print("        python -m anonimizador_ocr --entrada historias/ --salida salidas_buscable/ --buscable", file=sys.stderr)
        return 1

    paginas = extraer_paginas(args.entrada)
    filas: list[dict] = []
    descartadas = 0
    por_pagina: dict[int, int] = {}

    for numero, texto in paginas:
        utiles = 0
        for oracion in segmentar(texto):
            if not es_oracion_util(oracion):
                descartadas += 1
                continue
            filas.append(
                {
                    "oracion": oracion,
                    "nota_id": f"{args.nota_id}_p{numero:03d}",
                    "oracion_id": len(filas),
                    "pagina": numero,
                }
            )
            utiles += 1
        por_pagina[numero] = utiles

    print(f"[info] {len(paginas)} paginas leidas, {len(filas)} oraciones candidatas, {descartadas} descartadas por filtro")

    residuos = tamizar_phi(filas, usar_ner=not args.sin_ner)
    if residuos:
        categorias: dict[str, int] = {}
        for r in residuos:
            categorias[r["categoria"]] = categorias.get(r["categoria"], 0) + 1
        print(f"[ALERTA] El tamizado encontro {len(residuos)} posibles identificadores residuales:", file=sys.stderr)
        for cat, n in sorted(categorias.items()):
            print(f"         {cat}: {n}", file=sys.stderr)
        paginas_afectadas = sorted({r["pagina"] for r in residuos})
        print(f"         Paginas afectadas: {paginas_afectadas}", file=sys.stderr)
        if args.omitir_residuos:
            ids_sucios = {r["oracion_id"] for r in residuos}
            n_antes = len(filas)
            filas = [f for f in filas if f["oracion_id"] not in ids_sucios]
            print(
                f"         --omitir-residuos: se descartan {n_antes - len(filas)} oraciones "
                f"y quedan {len(filas)} para anotar.",
                file=sys.stderr,
            )
        elif not args.permitir_residuos:
            print(
                "         El corpus NO se escribe. Revisa esas paginas, anade zonas fijas o\n"
                "         etiquetas nuevas, re-ejecuta el anonimizador y vuelve a extraer.",
                file=sys.stderr,
            )
            return 3
        else:
            print("         --permitir-residuos activo: se escribe de todas formas.", file=sys.stderr)
    else:
        print("[ok] El tamizado no encontro identificadores residuales")

    args.salida.mkdir(parents=True, exist_ok=True)
    escribir_csv(args.salida / "citimed_corpus_para_anotar.csv", filas)

    parte_a, parte_b = partir_para_kappa(filas, args.solape)
    escribir_csv(args.salida / "anotador_a.csv", parte_a)
    escribir_csv(args.salida / "anotador_b.csv", parte_b)

    reporte = {
        "generado": datetime.now(timezone.utc).isoformat(),
        "pdf_origen": args.entrada.name,
        "nota_id": args.nota_id,
        "paginas": len(paginas),
        "oraciones_totales": len(filas),
        "oraciones_descartadas_por_filtro": descartadas,
        "oraciones_por_pagina": por_pagina,
        "solape_doble_ciego": args.solape,
        "oraciones_anotador_a": len(parte_a),
        "oraciones_anotador_b": len(parte_b),
        "oraciones_compartidas": len(parte_a) + len(parte_b) - len(filas),
        "tamizado_phi": {
            "motor": "reglas + NER spaCy" if not args.sin_ner else "solo reglas",
            "residuos_detectados": len(residuos),
            "oraciones_omitidas": (len(residuos) if args.omitir_residuos else 0),
            "categorias": sorted({r["categoria"] for r in residuos}),
        },
        "nota": "Agregados sin texto clinico. El CSV de oraciones no se publica en el repositorio.",
    }
    with open(args.salida / "reporte_extraccion.json", "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    print(f"[ok] Corpus en {args.salida / 'citimed_corpus_para_anotar.csv'}")
    print(f"[ok] Particiones para kappa: {len(parte_a)} y {len(parte_b)} oraciones, {reporte['oraciones_compartidas']} compartidas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
