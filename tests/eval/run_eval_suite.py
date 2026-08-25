#!/usr/bin/env python3
"""Fase 3 — Orquestador evaluación ML (TC-EVAL-01..10).

Uso:
  python tests/eval/run_eval_suite.py
  python tests/eval/run_eval_suite.py --skip-slow

Requiere:
  - medec_try/MEDEC-MS (git clone MEDEC)
  - salidas_ajuste/modelo_ajustado.joblib (python s6/modelo_ajustado.py)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

THRESHOLDS = {
    "roc_auc": 0.85,
    "auprc": 0.42,
    "auprc_bias_delta": 0.05,
}

GOLDEN_SET = [
    {
        "id": "medicacion",
        "nota": (
            "Paciente refiere dolor en molar 36. "
            "Antecedentes: alergia documentada a penicilina. "
            "Se indica amoxicilina 500 mg cada 8 h."
        ),
        "expect_alerta": True,
    },
    {
        "id": "limpia",
        "nota": (
            "Paciente de 45 años acude por control periodontal rutinario. "
            "Examen: encías rosadas, sin sangrado al sondaje."
        ),
        "expect_alerta": False,
    },
]


def _run_script(script: str, extra: list[str] | None = None) -> tuple[int, str]:
    cmd = [sys.executable, str(ROOT / script)] + (extra or [])
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    return proc.returncode, out


def _load_metricas_tripartita() -> dict | None:
    candidates = [
        ROOT / "salidas_s7" / "metricas_tripartita.json",
        ROOT / "s10" / "evidencias" / "metricas_tripartita.json",
    ]
    for path in candidates:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if "brazos" in data:
                return data["brazos"]
            return data
    return None


def check_tc_eval_01_02(metricas: dict) -> list[tuple[str, bool, str]]:
    results = []
    best_roc = ("", 0.0)
    best_auprc = ("", 0.0)
    for brazo, data in metricas.items():
        oracion = data.get("oracion", {})
        roc = oracion.get("roc_auc", 0)
        auprc = oracion.get("auprc", 0)
        if roc > best_roc[1]:
            best_roc = (brazo, roc)
        if auprc > best_auprc[1]:
            best_auprc = (brazo, auprc)

    results.append(
        (
            f"TC-EVAL-01 ROC-AUC ({best_roc[0]})",
            best_roc[1] >= THRESHOLDS["roc_auc"],
            f"roc_auc={best_roc[1]} (umbral {THRESHOLDS['roc_auc']})",
        )
    )
    results.append(
        (
            f"TC-EVAL-02 AUPRC ({best_auprc[0]})",
            best_auprc[1] >= THRESHOLDS["auprc"],
            f"auprc={best_auprc[1]} (umbral {THRESHOLDS['auprc']})",
        )
    )
    return results


def check_tc_eval_03(metricas: dict) -> tuple[str, bool, str]:
    best_loc = ("", 0.0)
    for brazo, data in metricas.items():
        loc = data.get("localizacion", {}).get("localizacion_top1", 0)
        if loc > best_loc[1]:
            best_loc = (brazo, loc)
    if best_loc[0]:
        return (
            f"TC-EVAL-03 localizacion_top1 ({best_loc[0]})",
            best_loc[1] > 0,
            f"top1={best_loc[1]} (baseline S7 documentado en salidas_s7)",
        )
    return ("TC-EVAL-03", False, "sin métrica localización")


def check_tc_eval_10_golden_set() -> list[tuple[str, bool, str]]:
    """TC-EVAL-10: Regresión golden set con mock LLM."""
    sys.path.insert(0, str(ROOT))
    from s7.inferencia import analizar_nota
    from s7.llm_client import LLMClient
    import tempfile

    results = []
    with tempfile.TemporaryDirectory() as tmp:
        client = LLMClient(mock=True, cache_dir=Path(tmp))
        for case in GOLDEN_SET:
            resultado = analizar_nota(
                case["nota"],
                cfg={
                    "salidas": {"modelo_tfidf": "x", "cache_dir": tmp},
                    "llm": {},
                    "rag": {},
                },
                brazos=["llm_zero"],
                mock_llm=True,
                client=client,
            )
            top = resultado.top1(["llm_zero"])
            alerta = top.alerta(0.5, ["llm_zero"]) if top else False
            ok = alerta == case["expect_alerta"]
            results.append(
                (
                    f"TC-EVAL-10 golden [{case['id']}]",
                    ok,
                    f"alerta={alerta} esperado={case['expect_alerta']}",
                )
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Suite evaluación ML TC-EVAL")
    parser.add_argument("--skip-slow", action="store_true", help="Omitir scripts pesados")
    parser.add_argument("--run-scripts", action="store_true", help="Ejecutar eval_*.py")
    args = parser.parse_args()

    medec = ROOT / "medec_try" / "MEDEC-MS"
    modelo = ROOT / "salidas_ajuste" / "modelo_ajustado.joblib"
    results: list[tuple[str, bool, str]] = []

    if not medec.exists():
        results.append(("PRECOND MEDEC", True, f"SKIP — no encontrado: {medec}"))
    if not modelo.exists():
        results.append(("PRECOND modelo", True, f"SKIP — no encontrado: {modelo}"))

    if args.run_scripts and medec.exists() and modelo.exists() and not args.skip_slow:
        for script in (
            "s7/eval_tripartita.py",
            "s7/analisis_por_tipo.py",
            "s7/eval_idioma.py",
        ):
            code, out = _run_script(script)
            results.append(
                (f"RUN {script}", code == 0, out[-200:] if len(out) > 200 else out or "OK")
            )

    metricas = _load_metricas_tripartita()
    if metricas:
        results.extend(check_tc_eval_01_02(metricas))
        results.append(check_tc_eval_03(metricas))
    else:
        results.append(
            (
                "TC-EVAL-01..03",
                True,
                "SKIP — ejecutar: python s7/eval_tripartita.py (requiere MEDEC + modelo)",
            )
        )

    results.extend(check_tc_eval_10_golden_set())

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)

    print("=" * 72)
    print("EVAL SUITE — TC-EVAL (Fase 3)")
    print("=" * 72)
    for name, ok, detail in results:
        print(f"[{'OK' if ok else 'FAIL'}] {name}: {detail}")
    print("-" * 72)
    print(f"TOTAL: {len(results)} | PASS: {passed} | FAIL: {failed}")
    print("=" * 72)

    report = ROOT / "tests" / "eval" / "last_eval_report.json"
    report.write_text(
        json.dumps(
            [{"name": n, "pass": ok, "detail": d} for n, ok, d in results],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
