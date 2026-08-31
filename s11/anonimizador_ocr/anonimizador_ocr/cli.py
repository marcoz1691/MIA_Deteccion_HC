"""Uso:
    python -m anonimizador_ocr --entrada historias/ --salida salidas/
    python -m anonimizador_ocr --entrada hc_001.pdf --salida salidas/ --zonas plantillas/form008.json --buscable
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .config import Config
from .pipeline import procesar_lote


def comprobar_entorno(cfg: Config) -> list[str]:
    problemas = []
    if cfg.motor == "tesseract":
        if not shutil.which("tesseract"):
            problemas.append("No se encuentra el binario `tesseract` en el PATH. "
                             "Windows: instala https://github.com/UB-Mannheim/tesseract/wiki y añade C:\\Program Files\\Tesseract-OCR al PATH.")
        else:
            import pytesseract
            langs = pytesseract.get_languages(config="")
            for l in cfg.idioma.split("+"):
                if l not in langs:
                    problemas.append(f"Tesseract no tiene el idioma '{l}'. Copia {l}.traineddata a la carpeta tessdata "
                                     f"(https://github.com/tesseract-ocr/tessdata_best).")
    elif cfg.motor == "easyocr":
        try:
            import easyocr  # noqa: F401
        except ImportError:
            problemas.append("easyocr no está instalado: pip install easyocr")
    return problemas


def _consola_utf8() -> None:
    """La consola de Windows usa cp1252 y aborta el lote al imprimir acentos o simbolos."""
    for flujo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(flujo, "reconfigure", None)
        if reconfigurar is not None:
            try:
                reconfigurar(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def main(argv=None) -> int:
    _consola_utf8()
    ap = argparse.ArgumentParser(description="Anonimizador de historias clínicas escaneadas (OCR + manuscrito).")
    ap.add_argument("--entrada", required=True, help="PDF, imagen o carpeta (se recorre recursivamente)")
    ap.add_argument("--salida", required=True, help="carpeta de salida")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--motor", choices=["tesseract", "easyocr"], default="tesseract")
    ap.add_argument("--idioma", default="spa", help="p. ej. spa o spa+eng")
    ap.add_argument("--psm", type=int, default=3, help="modo de segmentación de tesseract (3 auto, 4 columnas, 6 bloque, 11 disperso)")
    ap.add_argument("--fechas", choices=["todas", "nacimiento", "ninguna"], default="nacimiento")
    ap.add_argument("--zonas", type=Path, help="plantilla JSON de zonas fijas a tachar siempre")
    ap.add_argument("--ancho-etiqueta", type=float, default=0.55, help="fracción del ancho de página a tachar a la derecha de una etiqueta de formulario")
    ap.add_argument("--alto-celda", type=float, default=3.0, help="en tablas: alturas de cabecera que se tachan por debajo de cada etiqueta")
    ap.add_argument("--sin-etiquetas", action="store_true", help="NO tachar el espacio junto a etiquetas (Nombre:, Cédula:...)")
    ap.add_argument("--sin-ner", action="store_true")
    ap.add_argument("--sin-capa-texto", action="store_true", help="forzar OCR aunque el PDF tenga texto")
    ap.add_argument("--sin-deskew", action="store_true")
    ap.add_argument("--buscable", action="store_true", help="PDF de salida con texto (OCR sobre la imagen ya tachada)")
    ap.add_argument("--etiquetar", action="store_true", help="escribir [NOMBRE], [CEDULA]... dentro de los rectángulos")
    ap.add_argument("--volcar-ocr", action="store_true", help="guardar el texto crudo del OCR por página (para diagnosticar etiquetas mal leídas)")
    ap.add_argument("--sin-revision", action="store_true", help="no generar PNG de revisión")
    ap.add_argument("--umbral-manuscrito", type=float, default=55.0, help="conf. OCR media por debajo => marcar página para revisión")
    ap.add_argument("--solo-comprobar", action="store_true", help="comprobar el entorno y salir")
    args = ap.parse_args(argv)

    cfg = Config(
        dpi=args.dpi, motor=args.motor, idioma=args.idioma, psm=args.psm, fechas=args.fechas, zonas=args.zonas,
        ancho_max_etiqueta=args.ancho_etiqueta, alto_celda=args.alto_celda, redactar_junto_a_etiquetas=not args.sin_etiquetas,
        usar_ner=not args.sin_ner, usar_capa_texto=not args.sin_capa_texto, deskew=not args.sin_deskew,
        buscable=args.buscable, etiquetar_cajas=args.etiquetar, revision=not args.sin_revision, volcar_ocr=args.volcar_ocr,
        umbral_pagina_manuscrita=args.umbral_manuscrito,
    )

    problemas = comprobar_entorno(cfg)
    for p in problemas:
        print("[ERROR]", p, file=sys.stderr)
    if problemas:
        return 2
    if args.solo_comprobar:
        print("Entorno OK")
        return 0

    resultados = procesar_lote(Path(args.entrada), Path(args.salida), cfg)
    n_rev = sum(len(r.paginas_a_revisar) for r in resultados)
    print(f"\nListo: {len(resultados)} archivo(s). Páginas marcadas para revisión manual: {n_rev}. "
          f"Ver {args.salida}/paginas_a_revisar.csv y {args.salida}/revision/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
