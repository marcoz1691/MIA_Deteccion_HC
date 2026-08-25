#!/usr/bin/env python3
"""Fase 0 — Smoke test post-deploy (4 checks, ~5 min).

Uso:
  python tests/smoke/smoke.py
  python tests/smoke/smoke.py --api http://127.0.0.1:8000 --frontend http://127.0.0.1:5173

Checks:
  1. GET /health → 200
  2. POST /generar nota medicación mock → alerta=true
  3. POST /generar nota limpia mock → alerta=false
  4. Frontend carga (GET / → 200)
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

ROOT = sys.path[0]
if "tests" in ROOT:
    ROOT = str(__import__("pathlib").Path(ROOT).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tests.fixtures.notas import NOTA_LIMPIA, NOTA_MEDICACION  # noqa: E402


def _get(url: str, timeout: float = 30) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"Accept": "*/*"}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def _post_json(url: str, body: dict, timeout: float = 120) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"raw": raw}


def run_smoke(api_base: str, frontend_base: str | None) -> int:
    api_base = api_base.rstrip("/")
    passed = failed = 0
    results: list[tuple[str, bool, str]] = []

    # Check 1: health
    try:
        status, _ = _get(f"{api_base}/health")
        ok = status == 200
        results.append(("SMOKE-01 GET /health", ok, f"HTTP {status}"))
    except Exception as exc:
        results.append(("SMOKE-01 GET /health", False, str(exc)))

    # Check 2: medicación con alerta
    try:
        status, payload = _post_json(
            f"{api_base}/generar",
            {
                "nota_clinica": NOTA_MEDICACION,
                "mock_llm": True,
                "brazos": ["llm_zero"],
                "umbral": 0.5,
            },
        )
        top1 = payload.get("top1") or {}
        ok = status == 200 and top1.get("alerta") is True
        results.append(
            (
                "SMOKE-02 POST /generar medicación",
                ok,
                f"HTTP {status}, alerta={top1.get('alerta')}",
            )
        )
    except Exception as exc:
        results.append(("SMOKE-02 POST /generar medicación", False, str(exc)))

    # Check 3: nota limpia sin alerta
    try:
        status, payload = _post_json(
            f"{api_base}/generar",
            {
                "nota_clinica": NOTA_LIMPIA,
                "mock_llm": True,
                "brazos": ["llm_zero"],
                "umbral": 0.5,
            },
        )
        top1 = payload.get("top1") or {}
        ok = status == 200 and top1.get("alerta") is False
        results.append(
            (
                "SMOKE-03 POST /generar limpia",
                ok,
                f"HTTP {status}, alerta={top1.get('alerta')}",
            )
        )
    except Exception as exc:
        results.append(("SMOKE-03 POST /generar limpia", False, str(exc)))

    # Check 4: frontend load
    if frontend_base:
        try:
            status, body = _get(frontend_base.rstrip("/") + "/")
            ok = status == 200 and ("html" in body.lower() or "root" in body.lower())
            results.append(
                ("SMOKE-04 Frontend carga", ok, f"HTTP {status}, len={len(body)}")
            )
        except Exception as exc:
            results.append(("SMOKE-04 Frontend carga", False, str(exc)))
    else:
        results.append(("SMOKE-04 Frontend carga", True, "SKIP (sin --frontend)"))

    print("=" * 72)
    print("SMOKE TEST — MIA Detección HC (Fase 0)")
    print("=" * 72)
    for name, ok, detail in results:
        icon = "OK" if ok else "FAIL"
        print(f"[{icon}] {name}: {detail}")
        if ok:
            passed += 1
        else:
            failed += 1
    print("-" * 72)
    print(f"TOTAL: {passed + failed} | PASS: {passed} | FAIL: {failed}")
    print("=" * 72)
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test post-deploy")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="Base URL API")
    parser.add_argument(
        "--frontend",
        default="http://127.0.0.1:5173",
        help="Base URL frontend React (vacío para omitir check 4)",
    )
    parser.add_argument("--skip-frontend", action="store_true", help="Omitir check 4")
    args = parser.parse_args()
    frontend = None if args.skip_frontend else args.frontend
    return run_smoke(args.api, frontend)


if __name__ == "__main__":
    sys.exit(main())
