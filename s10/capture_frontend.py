"""
Capturas del frontend React + FastAPI para evidencias S10.

Requisitos (desde la raíz, con venv activo):
  uvicorn api.main:app --port 8000          # terminal 1
  cd frontend && npm run dev                # terminal 2

Ejecutar:
  pip install playwright
  playwright install chromium
  python s10/capture_frontend.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "s10" / "evidencias" / "capturas"
OUT.mkdir(parents=True, exist_ok=True)


def _detect_frontend_url() -> str:
    import urllib.error
    import urllib.request

    candidates: list[str] = []
    for port in (5174, 5173, 5175):
        for host in ("localhost", "127.0.0.1"):
            url = f"http://{host}:{port}/"
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    html = resp.read(4096).decode("utf-8", errors="ignore")
                    if "MIA" in html or "Detección clínica" in html or "Deteccion" in html:
                        return url
                    candidates.append(url)
            except (urllib.error.URLError, TimeoutError, OSError):
                continue
    if candidates:
        return candidates[0]
    raise RuntimeError(
        "Frontend MIA no detectado. Arranca: cd frontend && npm run dev (puerto 5173/5174)"
    )


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        print("[error] Instala Playwright: pip install playwright && playwright install chromium")
        raise SystemExit(1) from exc

    base = _detect_frontend_url()
    print(f"[info] Frontend en {base}")

    shots = {
        "frontend_inicio.png": "Vista inicial (ejemplo medicación, backend conectado)",
        "frontend_analisis.png": "Resultado tras Analizar nota (top-1 + scores)",
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(base, wait_until="networkidle", timeout=60000)

        # Esperar health check del backend
        try:
            page.wait_for_selector(".status.ok", timeout=20000)
            print("[ok] Backend conectado (FastAPI vía proxy)")
        except Exception:
            print("[warn] Backend no marcado como ok en UI; intentando analizar igual.")

        page.wait_for_timeout(500)
        p1 = OUT / "frontend_inicio.png"
        page.screenshot(path=str(p1), full_page=True)
        print(f"[ok] {p1}")

        page.wait_for_function(
            """() => {
                const btn = [...document.querySelectorAll('button.cta')]
                  .find(b => b.textContent.includes('Analizar'));
                return btn && !btn.disabled;
            }""",
            timeout=30000,
        )
        page.get_by_role("button", name="Analizar nota").click()
        page.wait_for_selector(".verdict, .sentence, .table-wrap, .banner.error", timeout=180000)
        page.wait_for_timeout(500)
        p2 = OUT / "frontend_analisis.png"
        page.screenshot(path=str(p2), full_page=True)
        print(f"[ok] {p2}")

        browser.close()

    print("\n=== Rutas para copiar y pegar ===")
    for name in shots:
        print(str((OUT / name).resolve()))


if __name__ == "__main__":
    main()
