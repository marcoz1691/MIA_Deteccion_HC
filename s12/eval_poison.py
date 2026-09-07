"""S12 — Evaluacion dirigida del detector sobre el conjunto adversarial CITIMED.

El conjunto `s12/poison/` reune expedientes reales anonimizados en los que se
indujo de forma controlada una inconsistencia de tipo conocido. El tipo se
declara en el nombre del archivo (`PO007-GENERO_anon.pdf`), lo que permite
evaluar el detector sin publicar ni una linea de texto clinico.

La evaluacion se organiza en dos mitades, porque el detector opera bajo un
alcance declarado de cuatro ejes MVP (lateralidad, sexo, alergias, edad):

  * EN ALCANCE   -> se mide la tasa de deteccion: el sistema debe alertar.
  * FUERA DE ALCANCE -> se mide la tasa de abstencion: el sistema debe NO
    alertar. Abstenerse correctamente fuera del alcance declarado es un
    resultado positivo, no un fallo: acredita que el detector respeta su
    delimitacion en lugar de emitir alertas indiscriminadas.

Los expedientes del conjunto no traen capa de texto (son imagen escaneada), de
modo que la extraccion recorre la misma cascada del prototipo: modelo de vision
-> OCR local -> capa de texto. El analisis se ejecuta por la ruta de inferencia
de produccion (`api.service.InferenceService`), no por un camino paralelo.

PRIVACIDAD
    El JSON de resultados contiene unicamente agregados, etiquetas y puntajes.
    Nunca texto clinico. La transcripcion intermedia se cachea en
    `s12/salidas_poison/cache_extraccion/` para no repagar la corrida de vision:
    ese directorio SI contiene texto clinico y no debe versionarse.

    Al enviar paginas al modelo de vision, el material sale del equipo hacia el
    proveedor de inferencia. Ejecutar solo sobre expedientes ya anonimizados, o
    apuntar OPENAI_BASE_URL a un modelo on-premise.

Uso:
    python s12/eval_poison.py --dry-run          # inventario, sin gastar API
    python s12/eval_poison.py --limit 3          # prueba sobre 3 expedientes
    python s12/eval_poison.py                    # corrida completa
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Los expedientes viven FUERA del repositorio: contienen PHI (las firmas de los
# profesionales no estan tachadas en la salida del anonimizador v1) y no deben
# versionarse jamas. La ruta se toma de POISON_DIR o se pasa con --poison-dir.
POISON_DIR = Path(os.environ.get("POISON_DIR") or Path.home() / "datos_citimed" / "poison")
SALIDA_DIR = ROOT / "s12" / "salidas_poison"
CACHE_DIR = SALIDA_DIR / "cache_extraccion"
EVIDENCIAS = ROOT / "s12" / "evidencias" / "poison_resultados.json"

RE_CASO = re.compile(r"^(?P<id>PO\d+)-(?P<etiqueta>[A-ZÁÉÍÓÚÑ]+)_anon\.pdf$", re.IGNORECASE)

# Ejes MVP declarados en s7/prompts.py y s7/knowledge/mvp_consistencia.txt.
# DIAGNOSTICO se clasifica fuera de alcance porque el MVP solo contrasta el
# diagnostico con el examen fisico por la via de lateralidad; un diagnostico
# discordante por otra razon no es uno de los cuatro ejes. La bandera
# --diagnostico-en-alcance permite reclasificarlo y rehacer el conteo.
EN_ALCANCE = {"GENERO", "SEXO", "LATERALIDAD", "EDAD", "ALERGIA", "ALERGIAS"}
FUERA_ALCANCE = {"INESTABLE", "DIAGNOSTICO", "MEDICACION", "DOSIS"}


def _dentro_del_repo(ruta: Path) -> bool:
    """Salvaguarda: los expedientes con PHI no deben vivir en el arbol de git."""
    try:
        ruta.resolve().relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def descubrir_casos(directorio: Path) -> list[dict]:
    casos = []
    for pdf in sorted(directorio.glob("*.pdf")):
        m = RE_CASO.match(pdf.name)
        if not m:
            print(f"[aviso] nombre fuera de convencion, se omite: {pdf.name}")
            continue
        casos.append(
            {
                "caso_id": m.group("id").upper(),
                "etiqueta": m.group("etiqueta").upper(),
                "ruta": pdf,
            }
        )
    return casos


def clasificar(etiqueta: str, diagnostico_en_alcance: bool) -> str:
    if diagnostico_en_alcance and etiqueta == "DIAGNOSTICO":
        return "en_alcance"
    if etiqueta in EN_ALCANCE:
        return "en_alcance"
    if etiqueta in FUERA_ALCANCE:
        return "fuera_alcance"
    return "sin_clasificar"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extraer_con_cache(ruta: Path, transcriptor, usar_cache: bool = True) -> dict:
    """Transcribe el expediente reutilizando cache por hash del PDF."""
    data = ruta.read_bytes()
    clave = _sha256(data)
    destino = CACHE_DIR / f"{clave}.json"

    if usar_cache and destino.exists():
        payload = json.loads(destino.read_text(encoding="utf-8"))
        payload["_cache"] = True
        return payload

    from api.pdf_estructura import extraer_estructurado

    payload = extraer_estructurado(data, origen=ruta.name, transcriptor=transcriptor)
    payload["_cache"] = False
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def construir_transcriptor(sin_vision: bool):
    """Devuelve (transcriptor, etiqueta_motor). None => cascada OCR/capa de texto."""
    if sin_vision:
        return None, "sin_vision (OCR local / capa de texto)"

    from api.settings import vision_configurada, vision_model
    from api.vision_client import VisionUnavailableError, transcriptor_openai

    if not vision_configurada():
        print(
            "[aviso] No hay clave de vision configurada (o MOCK_LLM esta activo).\n"
            "        Los expedientes son imagen escaneada y sin vision la extraccion\n"
            "        dependera de Tesseract. Continua con --sin-vision si es lo que quieres."
        )
        return None, "sin_vision (degradado)"
    try:
        modelo = vision_model()
        return transcriptor_openai(model=modelo), f"vision ({modelo})"
    except VisionUnavailableError as exc:
        print(f"[aviso] Modelo de vision no disponible: {exc}")
        return None, "sin_vision (degradado)"


def analizar(servicio, texto: str, umbral: float, brazos: list[str], mock_llm: bool):
    from api.schemas import GenerarRequest

    peticion = GenerarRequest(
        nota_clinica=texto,
        mock_llm=mock_llm,
        idioma="spanish",
        brazos=brazos,
        umbral=umbral,
        ejemplo_id="poison",
        guardar_historial=False,
    )
    return servicio.generar(peticion)


def resumir_respuesta(respuesta, umbral: float) -> dict:
    """Agregados por expediente. Sin texto clinico: solo conteos y puntajes."""
    alertadas = [o for o in respuesta.oraciones if o.alerta]
    scores = [o.score_localizacion for o in respuesta.oraciones]
    return {
        "alerta": bool(alertadas),
        "n_oraciones": respuesta.n_total,
        "n_oraciones_alertadas": len(alertadas),
        "score_top1": round(respuesta.top1.score_localizacion, 4) if respuesta.top1 else None,
        "score_maximo": round(max(scores), 4) if scores else None,
        "umbral": umbral,
        "modo_degradado": respuesta.modo_degradado,
        "brazos_efectivos": list(respuesta.brazos_efectivos),
    }


def agregar(resultados: list[dict]) -> dict:
    en = [r for r in resultados if r["alcance"] == "en_alcance" and r["estado"] == "ok"]
    fuera = [r for r in resultados if r["alcance"] == "fuera_alcance" and r["estado"] == "ok"]

    detectados = [r for r in en if r["analisis"]["alerta"]]
    abstenidos = [r for r in fuera if not r["analisis"]["alerta"]]

    por_etiqueta: dict[str, dict] = defaultdict(lambda: {"n": 0, "alertados": 0, "alcance": ""})
    for r in resultados:
        if r["estado"] != "ok":
            continue
        fila = por_etiqueta[r["etiqueta"]]
        fila["n"] += 1
        fila["alertados"] += int(r["analisis"]["alerta"])
        fila["alcance"] = r["alcance"]

    def tasa(num: int, den: int):
        return round(num / den, 4) if den else None

    return {
        "en_alcance": {
            "n": len(en),
            "detectados": len(detectados),
            "tasa_deteccion": tasa(len(detectados), len(en)),
        },
        "fuera_alcance": {
            "n": len(fuera),
            "abstenciones_correctas": len(abstenidos),
            "tasa_abstencion": tasa(len(abstenidos), len(fuera)),
            "alertas_indebidas": len(fuera) - len(abstenidos),
        },
        "por_etiqueta": {k: dict(v) for k, v in sorted(por_etiqueta.items())},
        "errores": Counter(r["estado"] for r in resultados if r["estado"] != "ok"),
    }


def imprimir_inventario(casos: list[dict], diagnostico_en_alcance: bool) -> None:
    print(f"\nConjunto adversarial: {len(casos)} expedientes en {POISON_DIR}\n")
    conteo: Counter = Counter()
    for c in casos:
        alcance = clasificar(c["etiqueta"], diagnostico_en_alcance)
        conteo[(alcance, c["etiqueta"])] += 1
    print(f"{'ALCANCE':16} {'ETIQUETA':16} {'N':>3}")
    print("-" * 38)
    for (alcance, etiqueta), n in sorted(conteo.items()):
        print(f"{alcance:16} {etiqueta:16} {n:>3}")
    en = sum(n for (a, _), n in conteo.items() if a == "en_alcance")
    fuera = sum(n for (a, _), n in conteo.items() if a == "fuera_alcance")
    otros = len(casos) - en - fuera
    print("-" * 38)
    print(f"{'TOTAL':16} {'en alcance':16} {en:>3}")
    print(f"{'':16} {'fuera de alcance':16} {fuera:>3}")
    if otros:
        print(f"{'':16} {'sin clasificar':16} {otros:>3}")


def main() -> int:
    parser = argparse.ArgumentParser(description="S12 — evaluacion dirigida sobre el conjunto adversarial")
    parser.add_argument("--poison-dir", default=str(POISON_DIR))
    parser.add_argument("--out", default=str(EVIDENCIAS))
    parser.add_argument("--umbral", type=float, default=0.5)
    parser.add_argument(
        "--brazos",
        default="tfidf,llm_zero,llm_rag",
        help="brazos separados por coma (por defecto los tres)",
    )
    parser.add_argument("--limit", type=int, default=None, help="procesar solo los primeros N expedientes")
    parser.add_argument("--dry-run", action="store_true", help="inventario y clasificacion, sin llamar a ninguna API")
    parser.add_argument("--sin-vision", action="store_true", help="no usar modelo de vision (OCR local / capa de texto)")
    parser.add_argument("--sin-cache", action="store_true", help="ignorar la cache de transcripcion y repagar la vision")
    parser.add_argument("--mock-llm", action="store_true", help="analizar con LLM simulado (no consume API de texto)")
    parser.add_argument(
        "--diagnostico-en-alcance",
        action="store_true",
        help="clasificar DIAGNOSTICO como eje en alcance y rehacer los conteos",
    )
    args = parser.parse_args()

    poison_dir = Path(args.poison_dir)
    if not poison_dir.is_dir():
        print(f"[error] No existe el directorio {poison_dir}", file=sys.stderr)
        print(
            "        Los expedientes viven fuera del repositorio por contener PHI.\n"
            "        Indica la ruta con --poison-dir o exporta POISON_DIR.",
            file=sys.stderr,
        )
        return 1
    if _dentro_del_repo(poison_dir):
        print(
            f"[error] {poison_dir} esta dentro del repositorio.\n"
            "        Estos expedientes contienen PHI (firmas sin tachar) y no deben\n"
            "        versionarse. Muevelos fuera del arbol de git antes de continuar.",
            file=sys.stderr,
        )
        return 2

    casos = descubrir_casos(poison_dir)
    if not casos:
        print(f"[error] No se hallaron expedientes con la convencion PO###-ETIQUETA_anon.pdf", file=sys.stderr)
        return 1

    imprimir_inventario(casos, args.diagnostico_en_alcance)

    if args.dry_run:
        print("\n--dry-run activo: no se proceso ningun expediente ni se llamo a ninguna API.")
        return 0

    if args.limit:
        casos = casos[: args.limit]
        print(f"\n[info] --limit {args.limit}: se procesaran {len(casos)} expedientes.")

    transcriptor, motor_label = construir_transcriptor(args.sin_vision)
    brazos = [b.strip() for b in args.brazos.split(",") if b.strip()]

    print(f"\n[info] Motor de extraccion : {motor_label}")
    print(f"[info] Brazos de analisis  : {', '.join(brazos)}")
    print(f"[info] Umbral de alerta    : {args.umbral}")
    if not args.sin_vision and transcriptor is not None:
        print("[aviso] Las paginas se enviaran al proveedor de inferencia. Solo material anonimizado.")

    from api.pdf_extract import PdfExtractError
    from api.service import InferenceService

    servicio = InferenceService(historial_db=None)

    resultados: list[dict] = []
    t0 = time.perf_counter()

    for i, caso in enumerate(casos, start=1):
        alcance = clasificar(caso["etiqueta"], args.diagnostico_en_alcance)
        fila = {
            "caso_id": caso["caso_id"],
            "etiqueta": caso["etiqueta"],
            "alcance": alcance,
            "estado": "ok",
            "extraccion": None,
            "analisis": None,
        }
        print(f"\n[{i}/{len(casos)}] {caso['caso_id']} ({caso['etiqueta']}, {alcance})")

        try:
            extraido = extraer_con_cache(caso["ruta"], transcriptor, usar_cache=not args.sin_cache)
            fila["extraccion"] = {
                "motor": extraido.get("motor"),
                "n_paginas": extraido.get("n_paginas"),
                "n_evoluciones": len(extraido.get("entries", [])),
                "desde_cache": extraido.get("_cache", False),
            }
            print(
                f"      extraccion: motor={extraido.get('motor')} "
                f"paginas={extraido.get('n_paginas')} "
                f"evoluciones={len(extraido.get('entries', []))}"
                f"{' (cache)' if extraido.get('_cache') else ''}"
            )
        except PdfExtractError as exc:
            fila["estado"] = f"extraccion_fallida_{exc.status}"
            print(f"      [error] extraccion: {exc}")
            resultados.append(fila)
            continue
        except Exception as exc:  # noqa: BLE001 — un expediente no debe tumbar la corrida
            fila["estado"] = "extraccion_error"
            print(f"      [error] extraccion inesperada: {exc}")
            resultados.append(fila)
            continue

        texto = (extraido.get("texto_plano") or "").strip()
        if not texto:
            fila["estado"] = "sin_texto"
            print("      [error] la extraccion no produjo texto analizable")
            resultados.append(fila)
            continue

        try:
            respuesta = analizar(servicio, texto, args.umbral, brazos, args.mock_llm)
            fila["analisis"] = resumir_respuesta(respuesta, args.umbral)
            esperado = "ALERTA" if alcance == "en_alcance" else "SIN ALERTA"
            obtenido = "ALERTA" if fila["analisis"]["alerta"] else "SIN ALERTA"
            marca = "OK " if esperado == obtenido else "-- "
            print(
                f"      {marca}esperado={esperado:10} obtenido={obtenido:10} "
                f"score_top1={fila['analisis']['score_top1']} "
                f"oraciones={fila['analisis']['n_oraciones']}"
            )
        except Exception as exc:  # noqa: BLE001
            fila["estado"] = "analisis_error"
            print(f"      [error] analisis: {exc}")

        resultados.append(fila)

    elapsed = time.perf_counter() - t0
    resumen = agregar(resultados)

    export = {
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "comando": "python " + " ".join([Path(sys.argv[0]).as_posix(), *sys.argv[1:]]),
        "conjunto": "s12/poison (expedientes CITIMED anonimizados con inconsistencia inducida)",
        "n_expedientes": len(resultados),
        "motor_extraccion": motor_label,
        "brazos": brazos,
        "umbral": args.umbral,
        "mock_llm": args.mock_llm,
        "diagnostico_en_alcance": args.diagnostico_en_alcance,
        "segundos_corrida": round(elapsed, 2),
        "ejes_mvp": ["lateralidad", "sexo", "alergias", "edad"],
        "resumen": resumen,
        "por_expediente": resultados,
        "nota_phi": (
            "Agregados, etiquetas y puntajes. No contiene texto clinico, nombres, "
            "cedulas ni numeros de historia clinica. La transcripcion intermedia queda "
            "en s12/salidas_poison/cache_extraccion/ y no debe versionarse."
        ),
    }
    export["resumen"]["errores"] = dict(export["resumen"]["errores"])

    destino = Path(args.out)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")

    en, fuera = resumen["en_alcance"], resumen["fuera_alcance"]
    print("\n" + "=" * 62)
    print("RESULTADO")
    print("=" * 62)
    print(f"En alcance        : {en['detectados']}/{en['n']} detectados   (tasa {en['tasa_deteccion']})")
    print(f"Fuera de alcance  : {fuera['abstenciones_correctas']}/{fuera['n']} abstenciones correctas (tasa {fuera['tasa_abstencion']})")
    if fuera["alertas_indebidas"]:
        print(f"                    {fuera['alertas_indebidas']} alerta(s) fuera del alcance declarado")
    if resumen["errores"]:
        print(f"Errores           : {dict(resumen['errores'])}")
    print(f"Tiempo            : {elapsed:.1f} s")
    print(f"\nEvidencia (sin PHI): {destino}")
    print(f"Cache con texto clinico (NO versionar): {CACHE_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
