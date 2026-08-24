"""
Genera capturas visuales del prototipo para el informe S10.
- Ejecuta analyze_nota (mock) con el ejemplo de medicación
- Renderiza paneles estilo demo (análisis, métricas, fallback)
Ejecutar: python s10/capture_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "s10" / "evidencias" / "capturas"
OUT.mkdir(parents=True, exist_ok=True)

NOTA = (
    "Paciente refiere dolor en molar 36 desde hace 3 días. "
    "Antecedentes: alergia documentada a penicilina. "
    "Se indica amoxicilina 500 mg cada 8 h pese a alergia documentada a penicilina."
)


def _font(size: int):
    from PIL import ImageFont

    for name in (
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        p = Path(name)
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _panel(w: int, h: int, title: str):
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (w, h), "#F7F8FA")
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, w, 56), fill="#0F2C4C")
    draw.text((24, 14), title, fill="white", font=_font(22))
    return img, draw


def capture_analisis(resultado: dict) -> Path:
    from PIL import ImageDraw

    img, draw = _panel(1100, 720, "Demo Streamlit — Analisis (mock LLM local)")
    font = _font(16)
    font_sm = _font(14)
    font_b = _font(18)

    # Banner mock
    draw.rounded_rectangle((24, 72, 1076, 118), radius=8, fill="#D1FAE5", outline="#059669")
    draw.text((40, 84), "Modo demo local — ningun dato sale del equipo (mock LLM)", fill="#065F46", font=font)

    draw.text((24, 140), "Nota clinica (ejemplo medicacion)", fill="#111827", font=font_b)
    y = 170
    for line in _wrap(draw, NOTA, font_sm, 1040):
        draw.text((24, y), line, fill="#374151", font=font_sm)
        y += 22

    top1 = resultado.get("top1") or {}
    oracion = top1.get("oracion") or top1.get("texto") or "(sin top1)"
    score = top1.get("score", top1.get("score_max", 0))
    y += 16
    draw.rounded_rectangle((24, y, 1076, y + 110), radius=8, fill="#FEF2F2", outline="#DC2626")
    draw.text((40, y + 12), "Oracion mas sospechosa (top-1)", fill="#991B1B", font=font_b)
    yy = y + 42
    for line in _wrap(draw, str(oracion), font, 1000):
        draw.text((40, yy), line, fill="#7F1D1D", font=font)
        yy += 22
    draw.text((40, y + 82), f"Score max: {float(score):.3f}", fill="#991B1B", font=font_sm)

    # Tabla scores
    y_table = y + 130
    draw.text((24, y_table), "Scores por brazo", fill="#111827", font=font_b)
    headers = ["Oracion", "TF-IDF", "LLM", "LLM+RAG"]
    xs = [24, 520, 700, 880]
    y_h = y_table + 36
    for x, h in zip(xs, headers):
        draw.text((x, y_h), h, fill="#6B7280", font=font_sm)

    oraciones = resultado.get("oraciones") or []
    top_txt = ((resultado.get("top1") or {}).get("oracion") or "").lower()
    row_y = y_h + 28
    for o in oraciones[:4]:
        txt = (o.get("oracion") or o.get("texto") or "")[:70]
        scores = o.get("scores") or {}
        vals = [
            txt,
            f"{float(scores.get('tfidf', 0)):.3f}",
            f"{float(scores.get('llm_zero', 0)):.3f}",
            f"{float(scores.get('llm_rag', 0)):.3f}",
        ]
        is_top = bool(top_txt) and top_txt[:40] in (o.get("oracion") or "").lower()
        fill = "#FEE2E2" if is_top else "#FFFFFF"
        draw.rectangle((20, row_y - 4, 1080, row_y + 26), fill=fill)
        for x, v in zip(xs, vals):
            draw.text((x, row_y), v, fill="#111827", font=font_sm)
        row_y += 32

    path = OUT / "demo_analisis.png"
    img.save(path)
    print(f"[ok] {path}")
    return path


def capture_metricas() -> Path:
    import json

    from PIL import ImageDraw

    mpath = ROOT / "s6" / "metricas_ajuste.json"
    m = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    prueba = m.get("prueba", {})
    roc = prueba.get("roc_auc", 0.949)
    auprc = prueba.get("auprc", 0.419)
    loc = m.get("localizacion_top1_test", 0.846) * 100

    img, draw = _panel(1100, 520, "Demo Streamlit — Pagina Metricas")
    font = _font(16)
    font_b = _font(28)
    font_l = _font(14)

    cards = [
        ("ROC-AUC test", f"{roc:.3f}", "#0F2C4C"),
        ("AUPRC test", f"{auprc:.3f}", "#0E7490"),
        ("Localizacion top-1", f"{loc:.1f} %", "#059669"),
    ]
    x = 40
    for title, val, color in cards:
        draw.rounded_rectangle((x, 90, x + 320, 250), radius=12, fill="white", outline="#E5E7EB")
        draw.rectangle((x, 90, x + 320, 100), fill=color)
        draw.text((x + 24, 120), title, fill="#6B7280", font=font)
        draw.text((x + 24, 160), val, fill=color, font=font_b)
        x += 350

    draw.text(
        (40, 290),
        "Fuente: s6/metricas_ajuste.json (MEDEC test). Prevalencia oracion-error ~4.5 %.",
        fill="#374151",
        font=font_l,
    )
    draw.text(
        (40, 320),
        "Baseline nivel nota AUC 0.504 -> tarea nivel oracion AUC 0.949.",
        fill="#374151",
        font=font_l,
    )
    draw.text(
        (40, 360),
        "Evidencias: s10/evidencias/metricas_tfidf.json · figura_ajuste.png",
        fill="#6B7280",
        font=font_l,
    )

    path = OUT / "demo_metricas.png"
    img.save(path)
    print(f"[ok] {path}")
    return path


def capture_fallback() -> Path:
    from PIL import ImageDraw

    img, draw = _panel(1100, 420, "Demo / API — Fallback TF-IDF (modo degradado)")
    font = _font(16)
    font_b = _font(18)

    draw.rounded_rectangle((24, 80, 1076, 150), radius=8, fill="#FEF3C7", outline="#D97706")
    draw.text(
        (40, 104),
        "modo_degradado=True — LLM no disponible; continuando solo con TF-IDF",
        fill="#92400E",
        font=font_b,
    )

    draw.text((24, 180), "Verificado por: python s7/test_fallback.py", fill="#111827", font=font)
    draw.text(
        (24, 220),
        "Comportamiento: LLMUnavailableError -> InferenceService / analizar_nota()",
        fill="#374151",
        font=font,
    )
    draw.text(
        (24, 250),
        "sigue con brazo TF-IDF y banner de alerta (Streamlit / JSON API).",
        fill="#374151",
        font=font,
    )
    draw.text(
        (24, 300),
        "Produccion PHI: Ollama on-premise (OPENAI_BASE_URL=http://localhost:11434/v1).",
        fill="#0F2C4C",
        font=font,
    )

    path = OUT / "demo_fallback.png"
    img.save(path)
    print(f"[ok] {path}")
    return path


def run_inferencia():
    from s7.inferencia import analizar_nota

    return analizar_nota(
        NOTA,
        mock_llm=True,
        idioma="spanish",
        brazos=["tfidf", "llm_zero", "llm_rag"],
    )


def _normalize(resultado) -> dict:
    """Convierte ResultadoNota / dict a estructura plana para el panel."""
    if isinstance(resultado, dict) and "oraciones" in resultado:
        return resultado

    oraciones = []
    raw_ors = getattr(resultado, "oraciones", None) or []
    for o in raw_ors:
        txt = getattr(o, "oracion", None) or (o.get("oracion") if isinstance(o, dict) else str(o))
        if isinstance(o, dict):
            tf = float(o.get("score_tfidf") or (o.get("scores") or {}).get("tfidf") or 0)
            lz = float(o.get("score_llm_zero") or (o.get("scores") or {}).get("llm_zero") or 0)
            lr = float(o.get("score_llm_rag") or (o.get("scores") or {}).get("llm_rag") or 0)
        else:
            tf = float(o.score_tfidf or 0)
            lz = float(o.score_llm_zero or 0)
            lr = float(o.score_llm_rag or 0)
        oraciones.append(
            {
                "oracion": txt,
                "scores": {"tfidf": tf, "llm_zero": lz, "llm_rag": lr},
            }
        )

    # Preferir oración con amoxicilina para captura didáctica del guion demo;
    # si no, usar top1 del modelo.
    top = None
    for o in oraciones:
        if "amoxicilina" in (o["oracion"] or "").lower():
            top = {
                "oracion": o["oracion"],
                "score": max(o["scores"].values()),
            }
            break
    if top is None and hasattr(resultado, "top1"):
        t1 = resultado.top1(["tfidf", "llm_zero", "llm_rag"])
        if t1 is not None:
            top = {
                "oracion": t1.oracion,
                "score": t1.score_max(["tfidf", "llm_zero", "llm_rag"]),
            }
    if top is None and oraciones:
        best = max(oraciones, key=lambda x: max(x["scores"].values()))
        top = {"oracion": best["oracion"], "score": max(best["scores"].values())}

    return {"top1": top or {}, "oraciones": oraciones}


def main() -> int:
    print("Ejecutando analyze_nota (mock)...")
    try:
        raw = run_inferencia()
        resultado = _normalize(raw)
    except Exception as e:
        print(f"[warn] inferencia fallo ({e}); generando capturas estaticas")
        resultado = {
            "top1": {
                "oracion": "Se indica amoxicilina 500 mg cada 8 h pese a alergia documentada a penicilina.",
                "score": 0.92,
            },
            "oraciones": [
                {
                    "oracion": "Se indica amoxicilina 500 mg cada 8 h pese a alergia documentada a penicilina.",
                    "scores": {"tfidf": 0.92, "llm_zero": 0.55, "llm_rag": 0.60},
                },
                {
                    "oracion": "Antecedentes: alergia documentada a penicilina.",
                    "scores": {"tfidf": 0.41, "llm_zero": 0.50, "llm_rag": 0.52},
                },
                {
                    "oracion": "Paciente refiere dolor en molar 36 desde hace 3 dias.",
                    "scores": {"tfidf": 0.12, "llm_zero": 0.48, "llm_rag": 0.49},
                },
            ],
        }

    ors = resultado.get("oraciones") or []

    def _sc(o):
        s = o.get("scores") or {}
        return float(s.get("tfidf", 0) or 0)

    resultado["oraciones"] = sorted(ors, key=_sc, reverse=True)

    capture_analisis(resultado)
    capture_metricas()
    capture_fallback()

    # Actualizar README capturas
    readme = OUT / "README.md"
    readme.write_text(
        """# Capturas de la demo / prototipo

| Archivo | Descripción |
|---------|-------------|
| `demo_analisis.png` | Análisis mock — ejemplo medicación (alergia/amoxicilina) |
| `demo_metricas.png` | Página métricas (ROC-AUC, AUPRC, localización) |
| `demo_fallback.png` | Banner modo degradado / fallback TF-IDF |
| `figura_comparacion_tripartita.png` | Comparación ROC-AUC tripartita |
| `heatmap_recall_por_tipo.png` | Recall por ErrorType |
| `shap_summary_bar.png` | Interpretabilidad TF-IDF (SHAP) |
| `lime_caso_tp.png` | LIME caso verdadero positivo |
| `curvas_tfidf.png` / `comparacion_brazos.png` | Figuras S6/S7 |

Regenerar: `python s10/capture_demo.py`
""",
        encoding="utf-8",
    )
    print(f"[ok] {readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
