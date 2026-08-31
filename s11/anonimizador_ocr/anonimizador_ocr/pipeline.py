"""Orquestación: PDF o imagen de entrada -> PDF anonimizado + material de revisión."""
from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # PyMuPDF < 1.24
    import fitz
from PIL import Image

from . import deteccion, mapeo, ocr, redaccion, zonas as zonas_mod
from .config import Config

EXT_IMAGEN = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


@dataclass
class InformePagina:
    pagina: int
    fuente_palabras: str          # "capa_texto" | "tesseract" | "easyocr"
    n_palabras: int
    conf_media: float
    angulo_corregido: float
    n_cajas: int
    revisar: bool
    motivo_revision: str = ""
    hallazgos: list[dict] = field(default_factory=list)


@dataclass
class InformeArchivo:
    archivo: str
    salida: str
    paginas: list[InformePagina]
    segundos: float

    @property
    def paginas_a_revisar(self) -> list[int]:
        return [p.pagina for p in self.paginas if p.revisar]


# --------------------------------------------------------------------------- utilidades

def _pixmap_a_pil(pix: fitz.Pixmap) -> Image.Image:
    modo = "RGB" if pix.n < 4 else "RGBA"
    return Image.frombytes(modo, (pix.width, pix.height), pix.samples).convert("RGB")


def _paginas_de(ruta: Path, dpi: int):
    """Genera (num, imagen PIL, ancho_pt, alto_pt, pagina_fitz|None)."""
    if ruta.suffix.lower() in EXT_IMAGEN:
        img = Image.open(ruta).convert("RGB")
        w_pt, h_pt = img.width * 72 / dpi, img.height * 72 / dpi
        yield 1, img, w_pt, h_pt, None
        return
    doc = fitz.open(ruta)
    try:
        for i, pagina in enumerate(doc, start=1):
            pix = pagina.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
            yield i, _pixmap_a_pil(pix), pagina.rect.width, pagina.rect.height, pagina
    finally:
        doc.close()


def _pagina_tiene_texto(pagina) -> bool:
    return bool(pagina) and len(pagina.get_text("text").strip()) > 20


# --------------------------------------------------------------------------- procesado de una página

def procesar_pagina(num: int, img: Image.Image, pagina_fitz, cfg: Config, zonas_json: list[dict]):
    escala = cfg.dpi / 72.0
    angulo = 0.0

    if cfg.usar_capa_texto and _pagina_tiene_texto(pagina_fitz):
        palabras = ocr.palabras_desde_capa_texto(pagina_fitz, escala)
        fuente = "capa_texto"
        conf_media = 100.0
    else:
        res = ocr.reconocer(img, cfg.motor, cfg.idioma, cfg.psm, cfg.umbral_conf_palabra, cfg.deskew)
        palabras, fuente, conf_media, angulo, img = res.palabras, res.motor, res.conf_media, res.angulo_corregido, res.imagen

    texto = mapeo.construir_texto(palabras)
    hallazgos = deteccion.detectar(texto, cfg.usar_ner, cfg.modelo_spacy, cfg.fechas)

    cajas: list[mapeo.Caja] = []
    for h in hallazgos:
        cajas.extend(mapeo.cajas_desde_span(palabras, h.ini, h.fin, h.etiqueta, h.origen, cfg.margen_px))

    # Solo en páginas OCR: en una página con capa de texto el valor ya se lee y lo cubren las reglas;
    # el tachado "a ciegas" junto a etiquetas existe para valores manuscritos que el OCR no lee.
    if cfg.redactar_junto_a_etiquetas and fuente != "capa_texto":
        mascara = zonas_mod.mascara_tinta(img)
        cajas.extend(zonas_mod.cajas_junto_a_etiquetas(palabras, img.width, cfg.ancho_max_etiqueta,
                                                       cfg.margen_px, cfg.alto_celda, mascara))

    if zonas_json:
        cajas.extend(zonas_mod.cajas_desde_zonas(zonas_json, num, img.width, img.height))

    cajas = [c for c in cajas if c.etiqueta.split("+")[0] in cfg.etiquetas_a_redactar]
    cajas = mapeo.fusionar_cajas(cajas)

    revisar, motivo = False, ""
    if fuente != "capa_texto":
        if len(palabras) < cfg.min_palabras_pagina:
            revisar, motivo = True, f"solo {len(palabras)} palabras reconocidas (¿manuscrito / imagen en blanco / mala calidad?)"
        elif conf_media < cfg.umbral_pagina_manuscrita:
            revisar, motivo = True, f"confianza OCR media {conf_media:.0f} < {cfg.umbral_pagina_manuscrita:.0f} (probable manuscrito)"
    if not cajas and fuente != "capa_texto":
        revisar, motivo = True, (motivo + "; " if motivo else "") + "no se detectó ningún identificador"

    informe = InformePagina(
        pagina=num, fuente_palabras=fuente, n_palabras=len(palabras), conf_media=round(conf_media, 1),
        angulo_corregido=round(angulo, 2), n_cajas=len(cajas), revisar=revisar, motivo_revision=motivo,
        hallazgos=[{"etiqueta": h.etiqueta, "texto": h.texto, "origen": h.origen, "conf": h.conf} for h in hallazgos]
                  + [{"etiqueta": c.etiqueta, "texto": c.texto, "origen": c.origen, "conf": c.conf} for c in cajas if c.origen in ("etiqueta", "celda", "zona")],
    )
    tachada = redaccion.tachar(img, cajas, cfg.etiquetar_cajas)
    revision_img = redaccion.dibujar_revision(img, cajas) if cfg.revision else None
    return tachada, revision_img, informe, texto


# --------------------------------------------------------------------------- archivo completo

def procesar_archivo(ruta: Path, dir_salida: Path, cfg: Config) -> InformeArchivo:
    t0 = time.time()
    dir_salida.mkdir(parents=True, exist_ok=True)
    dir_rev = dir_salida / "revision" / ruta.stem
    if cfg.revision:
        dir_rev.mkdir(parents=True, exist_ok=True)

    zonas_json = zonas_mod.cargar_zonas(cfg.zonas) if cfg.zonas else []
    texto_pagina: dict[int, str] = {}
    constructor = redaccion.ConstructorPDF(cfg.buscable, cfg.idioma, cfg.calidad_jpeg)
    informes: list[InformePagina] = []

    for num, img, w_pt, h_pt, pagina in _paginas_de(ruta, cfg.dpi):
        tachada, rev, inf, texto_pg = procesar_pagina(num, img, pagina, cfg, zonas_json)
        texto_pagina[num] = texto_pg
        constructor.agregar_pagina(tachada, w_pt, h_pt)
        informes.append(inf)
        if cfg.revision and rev is not None:
            rev.save(dir_rev / f"p{num:03d}_revision.png")
            tachada.save(dir_rev / f"p{num:03d}_anonimizada.png")
        if cfg.volcar_ocr:
            with open(dir_rev / f"p{num:03d}_ocr.txt", "w", encoding="utf-8") as fo:
                fo.write(texto_pagina.get(num, ""))

    salida = dir_salida / f"{ruta.stem}_anon.pdf"
    constructor.guardar(salida)
    return InformeArchivo(str(ruta), str(salida), informes, round(time.time() - t0, 1))


def procesar_lote(entrada: Path, dir_salida: Path, cfg: Config, log=print) -> list[InformeArchivo]:
    if entrada.is_file():
        archivos = [entrada]
    else:
        archivos = sorted(p for p in entrada.rglob("*") if p.suffix.lower() in EXT_IMAGEN | {".pdf"})
    if not archivos:
        log(f"[aviso] No hay PDF ni imágenes en {entrada}")
        return []

    if cfg.usar_ner and deteccion.cargar_ner(cfg.modelo_spacy) is False:
        log(f"[AVISO] No se pudo cargar el modelo spaCy '{cfg.modelo_spacy}'. Los nombres sueltos NO se redactarán "
            f"(solo los que van tras 'Paciente:', 'Nombre:', etc.). Instálalo antes de procesar historias reales.")

    resultados = []
    for i, f in enumerate(archivos, start=1):
        log(f"[{i}/{len(archivos)}] {f.name}")
        try:
            inf = procesar_archivo(f, dir_salida, cfg)
        except Exception as e:  # no abortar el lote por un archivo corrupto
            log(f"   ERROR: {e}")
            continue
        resultados.append(inf)
        rev = inf.paginas_a_revisar
        aviso = f"  ⚠ revisar páginas {rev}" if rev else ""
        log(f"   -> {Path(inf.salida).name}  ({len(inf.paginas)} pág., "
            f"{sum(p.n_cajas for p in inf.paginas)} cajas, {inf.segundos}s){aviso}")

    escribir_informes(resultados, dir_salida)
    return resultados


def escribir_informes(resultados: list[InformeArchivo], dir_salida: Path) -> None:
    with open(dir_salida / "informe.json", "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in resultados], f, ensure_ascii=False, indent=2)

    with open(dir_salida / "hallazgos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["archivo", "pagina", "etiqueta", "texto_detectado", "origen", "confianza"])
        for r in resultados:
            for p in r.paginas:
                for h in p.hallazgos:
                    w.writerow([Path(r.archivo).name, p.pagina, h["etiqueta"], h["texto"], h["origen"], h["conf"]])

    with open(dir_salida / "paginas_a_revisar.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["archivo", "pagina", "motivo", "fuente", "n_palabras", "conf_media"])
        for r in resultados:
            for p in r.paginas:
                if p.revisar:
                    w.writerow([Path(r.archivo).name, p.pagina, p.motivo_revision, p.fuente_palabras, p.n_palabras, p.conf_media])
