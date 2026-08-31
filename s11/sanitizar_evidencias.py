"""Sanitiza el informe de una corrida del anonimizador OCR para poder publicarla.

El `informe.json` que produce `anonimizador_ocr.pipeline` contiene PHI: cada hallazgo
guarda en el campo `texto` el nombre, la cedula o el numero de historia clinica real que
se detecto. Ese archivo, junto con `hallazgos.csv` y las imagenes de revision, permanece
fuera del repositorio (ver `.gitignore`).

Este script lee ese informe y emite un JSON de agregados apto para publicacion: totales,
conteos por etiqueta y por origen, metricas OCR por pagina y estadisticas de confianza.
Nunca copia texto libre procedente del documento.

La estrategia es de lista blanca: el JSON de salida se construye campo a campo y despues
se valida contra `REGLAS_CAMPO`. Cualquier clave desconocida, cualquier valor de texto que
no encaje en su vocabulario controlado y cualquier cadena con aspecto de identificador
abortan la escritura con un error explicito.

Uso:
    python s11/sanitizar_evidencias.py
    python s11/sanitizar_evidencias.py --entrada otra/corrida/informe.json --salida out.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent
ENTRADA_POR_DEFECTO = RAIZ / "anonimizador_ocr" / "salidas" / "informe.json"
SALIDA_POR_DEFECTO = RAIZ / "evidencias" / "anonimizacion_agregados.json"

NOTA_PHI = (
    "Este archivo contiene unicamente agregados y conteos derivados de la corrida del "
    "anonimizador OCR. No contiene texto clinico, nombres, cedulas, numeros de historia "
    "clinica, telefonos, correos, direcciones ni fechas del documento original. El informe "
    "detallado, el CSV de hallazgos y las imagenes de revision si contienen PHI y no salen "
    "del equipo local."
)

# --------------------------------------------------------------------------- vocabularios controlados

# `config.Config.etiquetas_a_redactar`. Las etiquetas compuestas ("NOMBRE+HC") se validan por partes.
ETIQUETAS_VALIDAS = {
    "NOMBRE", "CEDULA", "RUC", "TELEFONO", "EMAIL", "FECHA", "HC",
    "DIRECCION", "ZONA", "ETIQUETA", "EDAD",
}
# `deteccion.Hallazgo.origen` mas los origenes que añade `zonas`/`mapeo`.
ORIGENES_VALIDOS = {"regex", "contexto", "ner", "etiqueta", "celda", "zona"}
# `pipeline.procesar_pagina`.
FUENTES_VALIDAS = {"capa_texto", "tesseract", "easyocr"}

# Plantillas exactas de `motivo_revision` en `pipeline.procesar_pagina`. Solo varian los numeros.
MOTIVOS_VALIDOS = (
    re.compile(r"^solo \d+ palabras reconocidas \(¿manuscrito / imagen en blanco / mala calidad\?\)$"),
    re.compile(r"^confianza OCR media \d+ < \d+ \(probable manuscrito\)$"),
    re.compile(r"^no se detecto ningun identificador$"),
    re.compile(r"^no se detectó ningún identificador$"),
)

# Nombre de archivo pseudonimizado admisible: "hc0001.pdf", "form008_2.pdf". Un nombre real
# de paciente no encaja aqui, asi que se sustituye por un identificador correlativo.
PSEUDONIMO_ARCHIVO = re.compile(r"^[A-Za-z_\-]{0,8}\d{1,6}(?:[_\-]\d{1,4})?$")

# Claves que jamas deben aparecer en la salida (son las que transportan PHI en el informe crudo).
CLAVES_PROHIBIDAS = {"texto", "texto_detectado", "hallazgos", "archivo", "salida", "ocr", "palabras"}

# Cadenas con aspecto de identificador: rachas largas de digitos o direcciones de correo.
RACHA_DIGITOS = re.compile(r"\d{6,}")
CORREO = re.compile(r"[\w.+-]+@[\w-]+\.\w+")


class ErrorSanitizacion(RuntimeError):
    """La salida no supero la comprobacion defensiva: no se escribe nada."""


# --------------------------------------------------------------------------- validadores de campo

def _texto_libre(valor: str, campo: str) -> None:
    raise ErrorSanitizacion(
        f"campo de texto libre '{campo}' con valor de longitud {len(valor)}: "
        f"la salida publicable no admite texto procedente del documento"
    )


def _en_conjunto(nombre: str, permitidos: set[str]):
    def _val(valor: str, campo: str) -> None:
        if valor not in permitidos:
            raise ErrorSanitizacion(
                f"campo '{campo}' con valor fuera del vocabulario {nombre}: "
                f"{sorted(permitidos)}. Valor no reconocido de longitud {len(valor)}"
            )
    return _val


def _etiqueta(valor: str, campo: str) -> None:
    for parte in valor.split("+"):
        if parte not in ETIQUETAS_VALIDAS:
            raise ErrorSanitizacion(
                f"campo '{campo}': componente de etiqueta no reconocido. "
                f"Etiquetas admitidas: {sorted(ETIQUETAS_VALIDAS)}"
            )


def _motivo(valor: str, campo: str) -> None:
    if valor == "":
        return
    for trozo in valor.split("; "):
        if not any(p.match(trozo) for p in MOTIVOS_VALIDOS):
            raise ErrorSanitizacion(
                f"campo '{campo}': el motivo de revision no coincide con ninguna plantilla "
                f"conocida de pipeline.procesar_pagina. Podria arrastrar texto del documento, "
                f"asi que se aborta en lugar de publicarlo"
            )


def _patron(expr: str, descripcion: str):
    compilado = re.compile(expr)

    def _val(valor: str, campo: str) -> None:
        if not compilado.match(valor):
            raise ErrorSanitizacion(f"campo '{campo}': se esperaba {descripcion}")
    return _val


def _literal(esperado: str):
    def _val(valor: str, campo: str) -> None:
        if valor != esperado:
            raise ErrorSanitizacion(f"campo '{campo}': se esperaba el literal fijado por el script")
    return _val


# Lista blanca: toda clave de la salida cuyo valor sea una cadena debe figurar aqui.
REGLAS_CAMPO: dict[str, Any] = {
    "generado_en": _patron(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$", "una fecha ISO-8601 UTC"),
    "generado_por": _literal("s11/sanitizar_evidencias.py"),
    "version_anonimizador": _patron(r"^(?:\d+\.\d+\.\d+|desconocida)$", "una version semantica"),
    "entrada_nombre": _patron(r"^[A-Za-z0-9_.\-]{1,64}$", "un nombre de archivo simple"),
    "entrada_sha256": _patron(r"^[0-9a-f]{64}$", "un digest sha256 hexadecimal"),
    "nota_phi": _literal(NOTA_PHI),
    "documento": _patron(r"^(?:documento_\d{2}|[A-Za-z_\-]{0,8}\d{1,6}(?:[_\-]\d{1,4})?)$",
                         "un identificador pseudonimizado"),
    "fuente_palabras": _en_conjunto("de fuentes de palabras", FUENTES_VALIDAS),
    "motivo_revision": _motivo,
    "etiqueta": _etiqueta,
    "origen": _en_conjunto("de origenes de deteccion", ORIGENES_VALIDOS),
}


# --------------------------------------------------------------------------- comprobacion defensiva

def validar_publicable(nodo: Any, ruta: str = "$") -> None:
    """Recorre la estructura de salida y aborta ante cualquier rastro de texto libre o PHI."""
    if isinstance(nodo, dict):
        for clave, valor in nodo.items():
            if not isinstance(clave, str):
                raise ErrorSanitizacion(f"{ruta}: clave no textual en el JSON de salida")
            if clave.lower() in CLAVES_PROHIBIDAS:
                raise ErrorSanitizacion(
                    f"{ruta}.{clave}: clave prohibida en la salida publicable. "
                    f"Las claves {sorted(CLAVES_PROHIBIDAS)} transportan PHI en el informe crudo"
                )
            # En los diccionarios de conteo la clave es la etiqueta o el origen: tambien se valida.
            if ruta.endswith("por_etiqueta"):
                _etiqueta(clave, f"{ruta}.<clave>")
            elif ruta.endswith("por_origen") or ruta.endswith("fuentes_de_palabras"):
                REGLAS_CAMPO["origen" if ruta.endswith("por_origen") else "fuente_palabras"](
                    clave, f"{ruta}.<clave>")
            validar_publicable(valor, f"{ruta}.{clave}")
    elif isinstance(nodo, list):
        for i, valor in enumerate(nodo):
            validar_publicable(valor, f"{ruta}[{i}]")
    elif isinstance(nodo, str):
        campo = ruta.rsplit(".", 1)[-1].split("[", 1)[0]
        regla = REGLAS_CAMPO.get(campo)
        if regla is None:
            _texto_libre(nodo, ruta)
        regla(nodo, ruta)
        if campo != "entrada_sha256" and RACHA_DIGITOS.search(nodo):
            raise ErrorSanitizacion(
                f"{ruta}: la cadena contiene una racha de 6 o mas digitos, compatible con una "
                f"cedula, un RUC, un telefono o un numero de historia clinica"
            )
        if CORREO.search(nodo):
            raise ErrorSanitizacion(f"{ruta}: la cadena contiene algo con forma de correo electronico")
    elif not isinstance(nodo, (int, float, bool)) and nodo is not None:
        raise ErrorSanitizacion(f"{ruta}: tipo de valor no admitido ({type(nodo).__name__})")


# --------------------------------------------------------------------------- construccion de agregados

def _version_anonimizador(entrada: Path) -> str:
    """Lee `__version__` del paquete sin importarlo (evita depender de PyMuPDF, spaCy, etc.)."""
    for base in [entrada.resolve()] + list(entrada.resolve().parents):
        init = base / "anonimizador_ocr" / "__init__.py"
        if init.is_file():
            m = re.search(r'__version__\s*=\s*"([^"]+)"', init.read_text(encoding="utf-8"))
            if m:
                return m.group(1)
    return "desconocida"


def _identificador_documento(ruta_archivo: str, indice: int) -> str:
    """Devuelve el nombre base solo si es claramente un pseudonimo; si no, uno correlativo."""
    stem = Path(ruta_archivo.replace("\\", "/")).stem
    return stem if PSEUDONIMO_ARCHIVO.match(stem) else f"documento_{indice:02d}"


def _conteos(valores) -> dict[str, int]:
    return dict(sorted(Counter(valores).items(), key=lambda kv: (-kv[1], kv[0])))


def _estadisticas(valores: list[float]) -> dict[str, float]:
    if not valores:
        return {"minimo": None, "maximo": None, "media": None, "mediana": None}
    return {
        "minimo": round(min(valores), 1),
        "maximo": round(max(valores), 1),
        "media": round(statistics.mean(valores), 2),
        "mediana": round(statistics.median(valores), 2),
    }


def construir_agregados(informes: list[dict], entrada: Path) -> dict:
    if not isinstance(informes, list) or not informes:
        raise ErrorSanitizacion(f"{entrada}: se esperaba una lista no vacia de informes de archivo")

    paginas_salida: list[dict] = []
    etiquetas: Counter = Counter()
    origenes: Counter = Counter()
    confianzas: list[float] = []
    total_hallazgos = 0
    total_cajas = 0
    total_palabras = 0
    segundos = 0.0

    for i, informe in enumerate(informes, start=1):
        documento = _identificador_documento(str(informe.get("archivo", "")), i)
        segundos += float(informe.get("segundos", 0.0))
        for pagina in informe["paginas"]:
            hallazgos = pagina.get("hallazgos", [])
            et_pagina = _conteos(h["etiqueta"] for h in hallazgos)
            or_pagina = _conteos(h["origen"] for h in hallazgos)
            etiquetas.update(h["etiqueta"] for h in hallazgos)
            origenes.update(h["origen"] for h in hallazgos)
            total_hallazgos += len(hallazgos)
            total_cajas += int(pagina["n_cajas"])
            total_palabras += int(pagina["n_palabras"])
            confianzas.append(float(pagina["conf_media"]))
            paginas_salida.append({
                "documento": documento,
                "pagina": int(pagina["pagina"]),
                "fuente_palabras": pagina["fuente_palabras"],
                "n_palabras": int(pagina["n_palabras"]),
                "conf_media": round(float(pagina["conf_media"]), 1),
                "angulo_corregido": round(float(pagina["angulo_corregido"]), 2),
                "n_cajas": int(pagina["n_cajas"]),
                "n_hallazgos": len(hallazgos),
                "requiere_revision": bool(pagina["revisar"]),
                "motivo_revision": pagina.get("motivo_revision", ""),
                "hallazgos_por_etiqueta": et_pagina,
                "hallazgos_por_origen": or_pagina,
            })

    a_revisar = [
        {"documento": p["documento"], "pagina": p["pagina"], "conf_media": p["conf_media"],
         "n_palabras": p["n_palabras"], "motivo_revision": p["motivo_revision"]}
        for p in paginas_salida if p["requiere_revision"]
    ]

    return {
        "metadatos": {
            "generado_en": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "generado_por": "s11/sanitizar_evidencias.py",
            "version_anonimizador": _version_anonimizador(entrada),
            "entrada_nombre": entrada.name,
            "entrada_sha256": hashlib.sha256(entrada.read_bytes()).hexdigest(),
            "nota_phi": NOTA_PHI,
        },
        "resumen": {
            "n_documentos": len(informes),
            "n_paginas": len(paginas_salida),
            "n_hallazgos": total_hallazgos,
            "n_cajas_tachadas": total_cajas,
            "n_palabras_reconocidas": total_palabras,
            "segundos_procesamiento": round(segundos, 1),
            "n_paginas_a_revisar": len(a_revisar),
        },
        "hallazgos_por_etiqueta": _conteos(etiquetas.elements()),
        "hallazgos_por_origen": _conteos(origenes.elements()),
        "confianza_ocr_por_pagina": _estadisticas(confianzas),
        "fuentes_de_palabras": _conteos(p["fuente_palabras"] for p in paginas_salida),
        "paginas": paginas_salida,
        "paginas_a_revisar": a_revisar,
    }


# --------------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Genera la version publicable (solo agregados, sin PHI) del informe del anonimizador OCR.")
    ap.add_argument("--entrada", type=Path, default=ENTRADA_POR_DEFECTO,
                    help=f"informe.json de la corrida (por defecto: {ENTRADA_POR_DEFECTO})")
    ap.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO,
                    help=f"JSON de agregados a escribir (por defecto: {SALIDA_POR_DEFECTO})")
    args = ap.parse_args(argv)

    if not args.entrada.is_file():
        print(f"[ERROR] No existe el informe de entrada: {args.entrada}", file=sys.stderr)
        return 2

    try:
        informes = json.loads(args.entrada.read_text(encoding="utf-8"))
        agregados = construir_agregados(informes, args.entrada)
        validar_publicable(agregados)
    except ErrorSanitizacion as e:
        print(f"[ERROR] Comprobacion de privacidad fallida, no se escribe nada: {e}", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        print(f"[ERROR] El informe de entrada no tiene la estructura esperada: {e}", file=sys.stderr)
        return 2

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(agregados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    r = agregados["resumen"]
    print(f"[ok] {args.salida}")
    print(f"     {r['n_paginas']} paginas, {r['n_hallazgos']} hallazgos, "
          f"{r['n_cajas_tachadas']} cajas tachadas, {r['segundos_procesamiento']}s")
    print(f"     etiquetas: {agregados['hallazgos_por_etiqueta']}")
    print(f"     origenes:  {agregados['hallazgos_por_origen']}")
    print(f"     confianza OCR: {agregados['confianza_ocr_por_pagina']}")
    print(f"     paginas a revisar: {[p['pagina'] for p in agregados['paginas_a_revisar']]}")
    print("     comprobacion defensiva de PHI: superada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
