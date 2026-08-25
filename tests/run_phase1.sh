#!/usr/bin/env bash
# Fase 1 — Regresión funcional
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Fase 1: Regresión funcional ==="

python -m pytest tests/api tests/s7 tests/s10 tests/security \
  api/test_settings.py s7/test_fallback.py s10/test_citimed_pipeline.py \
  -m "regression or not perf and not stress and not e2e" \
  -q --tb=short

python -m pytest tests/e2e/streamlit -m e2e -q --tb=short || true

if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
  python api/qa_e2e_manual.py
else
  echo "SKIP: uvicorn no disponible — python api/qa_e2e_manual.py manualmente"
fi

echo "=== Fase 1 PASS ==="
