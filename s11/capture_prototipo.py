"""
Capturas del prototipo (API FastAPI + frontend React) para las evidencias S11.

Reemplaza al antiguo s10/capture_demo.py, que quedo obsoleto tras el rediseno
de la interfaz y la migracion de Streamlit a React.

Requisitos (desde la raiz, con venv activo):
  uvicorn api.main:app --port 8000        # terminal 1
  cd frontend && npm run dev              # terminal 2
  pip install playwright && playwright install chromium

Ejecutar:
  python s11/capture_prototipo.py
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "s11" / "evidencias" / "capturas"

PUERTOS_FRONTEND = (5173, 5174, 5175, 5176)
VIEWPORT = {"width": 1500, "height": 1000}


def detectar_frontend() -> str:
    """Vite cambia de puerto si el anterior esta ocupado, asi que hay que buscarlo."""
    for puerto in PUERTOS_FRONTEND:
        url = f"http://localhost:{puerto}/"
        try:
            with urllib.request.urlopen(url, timeout=4) as resp:
                html = resp.read(4096).decode("utf-8", errors="ignore")
            if "MIA" in html or "root" in html:
                return url
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
    raise RuntimeError(
        "Frontend no detectado en los puertos "
        f"{PUERTOS_FRONTEND}. Arranca: cd frontend && npm run dev"
    )


def verificar_api() -> None:
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as resp:
            print(f"[ok] API FastAPI responde: {resp.status}")
    except Exception as exc:
        print(f"[aviso] API en el puerto 8000 no responde ({exc}). Las capturas saldran sin analisis.")


def _analizar(page) -> bool:
    """Pulsa Analizar nota y espera el resultado. Devuelve si hubo veredicto."""
    page.wait_for_function(
        """() => {
            const btn = [...document.querySelectorAll('button.cta')]
              .find(b => b.textContent.includes('Analizar'));
            return btn && !btn.disabled;
        }""",
        timeout=30000,
    )
    page.get_by_role("button", name="Analizar nota").click()
    try:
        page.wait_for_selector(".verdict, .sentence, .banner.error", timeout=180000)
        page.wait_for_timeout(800)
        return True
    except Exception:
        print("[aviso] No se obtuvo veredicto en el tiempo esperado.")
        return False


def _activar_tema_oscuro(page) -> bool:
    """El tema oscuro esta detras de un easter egg: 5 clics en la marca en menos de 2 s."""
    marca = page.locator("button.mark-btn")
    if marca.count() == 0:
        return False
    for _ in range(5):
        marca.click()
        page.wait_for_timeout(120)
    page.wait_for_timeout(600)
    tema = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
    return tema == "dark"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[error] Falta Playwright: pip install playwright && playwright install chromium")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    verificar_api()
    base = detectar_frontend()
    print(f"[info] Frontend en {base}")

    generadas: list[Path] = []

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True)
        page = navegador.new_page(viewport=VIEWPORT)
        page.goto(base, wait_until="networkidle", timeout=60000)

        try:
            page.wait_for_selector(".status.ok", timeout=20000)
            print("[ok] La UI marca el backend como conectado")
        except Exception:
            print("[aviso] La UI no marca el backend como conectado")

        page.wait_for_timeout(600)
        destino = OUT / "prototipo_inicio.png"
        page.screenshot(path=str(destino), full_page=True)
        generadas.append(destino)

        if _analizar(page):
            destino = OUT / "prototipo_hallazgo.png"
            page.screenshot(path=str(destino), full_page=True)
            generadas.append(destino)

        if _activar_tema_oscuro(page):
            print("[ok] Tema oscuro activado")
            destino = OUT / "prototipo_tema_oscuro.png"
            page.screenshot(path=str(destino), full_page=True)
            generadas.append(destino)
        else:
            print("[aviso] No se pudo activar el tema oscuro")

        historial = page.locator(".card.historial")
        if historial.count() > 0:
            try:
                historial.first.scroll_into_view_if_needed()
                page.wait_for_timeout(400)
                destino = OUT / "prototipo_historial.png"
                historial.first.screenshot(path=str(destino))
                generadas.append(destino)
            except Exception as exc:
                print(f"[aviso] No se pudo capturar el historial: {exc}")

        navegador.close()

    print("\n=== Capturas generadas ===")
    for ruta in generadas:
        print(ruta.resolve())
    return 0 if generadas else 1


if __name__ == "__main__":
    sys.exit(main())
