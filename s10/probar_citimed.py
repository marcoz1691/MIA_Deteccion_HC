"""
Pipeline CITIMED: anonimizar historias → inferencia → CSV → eval cross-domain.

Uso (desde la raíz del repo, venv activo):
  python s10/probar_citimed.py
  python s10/probar_citimed.py --entrada s10/anonimizador/ANONIMIZADOR/ejemplos/historia_ejemplo.sintetico.txt
  python s10/probar_citimed.py --solo-anonimizar
  python s10/probar_citimed.py --sin-eval
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from s10.citimed_utils import leer_archivo_anon, listar_salidas_anon, phi_restante, texto_clinico_desde_anon

ANON_DIR = ROOT / "s10" / "anonimizador" / "ANONIMIZADOR"
EJEMPLO_SINTETICO = ANON_DIR / "ejemplos" / "historia_ejemplo.sintetico.txt"
ANON_SALIDAS = ROOT / "s10" / "anonimizador" / "salidas"
DATA_CSV = ROOT / "data" / "citimed_odontologia.csv"
DATA_EXAMPLE = ROOT / "data" / "citimed_odontologia.example.csv"
SALIDAS_S7 = ROOT / "salidas_s7"


def _import_anonimizador():
    sys.path.insert(0, str(ANON_DIR))
    from anonimizador import Anonimizador, procesar  # type: ignore

    return Anonimizador, procesar


def anonimizar(entrada: Path, salida: Path, sin_ner: bool = False) -> list[Path]:
    """Ejecuta el anonimizador sobre archivo o carpeta."""
    Anonimizador, procesar = _import_anonimizador()
    anon = Anonimizador(usar_ner=not sin_ner)
    if not anon.usar_ner:
        print("[aviso] spaCy no disponible; anonimización solo con reglas.")
    procesar(entrada, salida, anon)
    if entrada.is_file():
        suf = entrada.suffix.lower()
        if suf == ".pdf":
            return [salida / f"{entrada.stem}_ANON.pdf"]
        return [salida / f"{entrada.stem}_ANON{suf}"]
    return listar_salidas_anon(salida)


def inferir_notas(archivos_anon: list[Path], mock_llm: bool = True) -> list[dict]:
    from s7.inferencia import analizar_nota

    resultados = []
    for path in archivos_anon:
        raw = leer_archivo_anon(path)
        nota = texto_clinico_desde_anon(raw)
        phi = phi_restante(nota)
        if phi:
            print(f"[warn] Posible PHI en {path.name}: {phi[:5]}")
        res = analizar_nota(
            nota,
            mock_llm=mock_llm,
            idioma="spanish",
            brazos=["tfidf", "llm_zero", "llm_rag"],
        )
        top = res.top1(["tfidf", "llm_zero", "llm_rag"])
        filas = []
        for o in res.oraciones:
            filas.append(
                {
                    "sid": o.sid,
                    "oracion": o.oracion,
                    "score_tfidf": o.score_tfidf,
                    "score_llm_zero": o.score_llm_zero,
                    "score_llm_rag": o.score_llm_rag,
                }
            )
        resultados.append(
            {
                "archivo": path.name,
                "nota_texto": nota,
                "n_oraciones": len(res.oraciones),
                "modo_degradado": res.modo_degradado,
                "phi_residual": phi,
                "top1": {
                    "oracion": top.oracion if top else None,
                    "score_tfidf": top.score_tfidf if top else None,
                    "score_llm_zero": top.score_llm_zero if top else None,
                    "score_llm_rag": top.score_llm_rag if top else None,
                },
                "oraciones": filas,
            }
        )
        print(f"[inferencia] {path.name}: top1 = {(top.oracion[:70] + '...') if top and top.oracion else '—'}")
    return resultados


def preparar_csv_eval(ejemplo_csv: Path) -> Path:
    """Copia la plantilla odontológica etiquetada para eval cross-domain (sin mezclar piloto)."""
    if not ejemplo_csv.exists():
        raise RuntimeError(f"Plantilla CITIMED no encontrada: {ejemplo_csv}")
    DATA_CSV.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ejemplo_csv, DATA_CSV)
    import pandas as pd

    df = pd.read_csv(DATA_CSV)
    print(
        f"[ok] CSV eval (solo plantilla etiquetada) -> {DATA_CSV} "
        f"({len(df)} oraciones, {df['nota_id'].nunique()} notas)"
    )
    return DATA_CSV


def verificar_phi_inferencias(inferencias: list[dict], force: bool = False) -> list[str]:
    """Aborta si hay PHI residual en textos de inferencia (salvo --force)."""
    todos: list[str] = []
    for inf in inferencias:
        todos.extend(inf.get("phi_residual") or [])
        todos.extend(phi_restante(inf.get("nota_texto", "")))
    unicos = sorted(set(todos))
    if unicos and not force:
        print(f"[error] PHI residual detectado ({len(unicos)}): {unicos[:8]}")
        print("[error] Instale spaCy (es_core_news_md) y re-ejecute sin --sin-ner.")
        print("[error] Use --force solo para depuración local con datos ya revisados.")
        raise SystemExit(2)
    if unicos:
        print(f"[warn] PHI residual (--force): {unicos[:8]}")
    return unicos


def ejecutar_eval_citimed() -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "s7" / "eval_citimed.py"), "--modo", "cross_domain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    out_path = SALIDAS_S7 / "eval_citimed.json"
    payload: dict = {"status": "error", "stderr": proc.stderr}
    if out_path.exists():
        payload = json.loads(out_path.read_text(encoding="utf-8"))
    return proc.returncode, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba pipeline CITIMED (anonimizar + inferir + eval)")
    parser.add_argument(
        "--entrada",
        default=str(EJEMPLO_SINTETICO),
        help="Archivo .txt/.pdf o carpeta con historias CITIMED (usar ejemplos sintéticos en git)",
    )
    parser.add_argument("--salida-anon", default=str(ANON_SALIDAS))
    parser.add_argument("--solo-anonimizar", action="store_true")
    parser.add_argument("--sin-eval", action="store_true")
    parser.add_argument("--sin-ner", action="store_true", help="Anonimizador solo reglas (sin spaCy)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Continuar aunque quede PHI residual (solo depuración local)",
    )
    parser.add_argument(
        "--mock-llm",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Usar LLM simulado (default: true; --no-mock-llm para API/Ollama)",
    )
    args = parser.parse_args()

    entrada = Path(args.entrada)
    salida_anon = Path(args.salida_anon)

    if not entrada.exists():
        print(f"[error] Entrada no encontrada: {entrada}")
        return 1

    print("=== 1. Anonimización ===")
    archivos_anon = anonimizar(entrada, salida_anon, sin_ner=args.sin_ner)
    if not archivos_anon:
        print("[error] No se generaron archivos anonimizados.")
        return 1

    if args.solo_anonimizar:
        return 0

    print("\n=== 2. Inferencia (TF-IDF + LLM) ===")
    inferencias = inferir_notas(archivos_anon, mock_llm=args.mock_llm)
    verificar_phi_inferencias(inferencias, force=args.force)

    print("\n=== 3. CSV CITIMED (plantilla etiquetada para eval) ===")
    preparar_csv_eval(DATA_EXAMPLE)

    reporte: dict = {
        "anonimizados": [str(p) for p in archivos_anon],
        "inferencias_piloto": inferencias,
        "csv_eval": str(DATA_CSV),
        "nota_eval": (
            "Eval cross-domain usa solo data/citimed_odontologia.example.csv (plantilla odontológica "
            "etiquetada). Las historias anonimizadas del piloto se reportan en inferencias_piloto "
            "sin mezclarse en métricas AUC."
        ),
    }

    exit_code = 0
    if not args.sin_eval:
        print("\n=== 4. Eval cross-domain MEDEC -> CITIMED (plantilla etiquetada) ===")
        rc, eval_payload = ejecutar_eval_citimed()
        reporte["eval_citimed"] = eval_payload
        if rc != 0:
            print(f"[error] eval_citimed.py terminó con código {rc}")
            exit_code = rc

    out_report = SALIDAS_S7 / "prueba_citimed.json"
    SALIDAS_S7.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[ok] Reporte -> {out_report}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
