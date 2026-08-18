"""Ejecuta la batería de verificación S10 y escribe log en s10/evidencias/."""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVID = ROOT / "s10" / "evidencias"
EVID.mkdir(parents=True, exist_ok=True)

COMANDOS = [
    ("s6/modelo_ajustado.py", []),
    ("s7/analisis_por_tipo.py", []),
    ("s7/eval_tripartita.py", ["--mock-llm", "--max-oraciones", "500"]),
    ("s7/eval_idioma.py", ["--mock-llm", "--subset", "200"]),
    ("s7/eval_tfidf_idioma.py", []),
    ("s7/test_fallback.py", []),
]

ARCHIVOS_ESPERADOS = [
    "salidas_ajuste/modelo_ajustado.joblib",
    "s6/metricas_ajuste.json",
    "salidas_s7/metricas_tripartita.json",
    "salidas_s7/analisis_por_tipo.json",
    "salidas_s7/eval_idioma_en_es.json",
    "salidas_s7/eval_tfidf_idioma.json",
    "salidas_s7/recall_por_tipo_error.csv",
]


def main() -> int:
    log_path = EVID / "verificacion_s10.txt"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"=== S10 Verificación {ts} ===", ""]

    for script, args in COMANDOS:
        label = Path(script).stem
        lines.append(f"--- {label} ---")
        cmd = [sys.executable, str(ROOT / script), *args]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (proc.stdout or "") + (proc.stderr or "")
        lines.append(out.rstrip())
        lines.append(f"EXIT CODE: {proc.returncode}")
        lines.append("")
        print(out, end="")
        if proc.returncode != 0:
            print(f"[warn] {label} terminó con código {proc.returncode}")

    lines.append("--- archivos esperados ---")
    ok = True
    for rel in ARCHIVOS_ESPERADOS:
        p = ROOT / rel
        status = "[ok]" if p.exists() else "[FALTA]"
        if not p.exists():
            ok = False
        lines.append(f"{status} {rel}")

    log_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[ok] Log -> {log_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
