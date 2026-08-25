# Fase 1 — Regresión funcional (pytest + E2E manual)
# Uso: .\tests\run_phase1.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== Fase 1: Regresion funcional ===" -ForegroundColor Cyan

Write-Host "`n[1/3] pytest unit + integration..." -ForegroundColor Yellow
python -m pytest tests/api tests/s7 tests/s10 tests/security `
    api/test_settings.py s7/test_fallback.py s10/test_citimed_pipeline.py `
    -m "regression or not perf and not stress and not e2e" `
    -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[2/3] pytest e2e streamlit components..." -ForegroundColor Yellow
python -m pytest tests/e2e/streamlit -m e2e -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[3/3] qa_e2e_manual (requiere uvicorn :8000)..." -ForegroundColor Yellow
try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 3
    python api/qa_e2e_manual.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} catch {
    Write-Host "SKIP: uvicorn no disponible en :8000 — ejecutar: uvicorn api.main:app --port 8000" -ForegroundColor DarkYellow
}

Write-Host "`n=== Fase 1 PASS ===" -ForegroundColor Green
