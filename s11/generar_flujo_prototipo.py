"""Genera el diagrama de flujo del prototipo real (análisis + OCR CITIMED)."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent / "evidencias" / "capturas" / "flujo_prototipo.png"

TEAL = "#0D9488"
TEAL_D = "#0F766E"
SLATE = "#F4F6F8"
WHITE = "#FFFFFF"
INK = "#1E293B"
MUTED = "#475569"
AMBER = "#D97706"
AMBER_BG = "#FFFBEB"
GREEN = "#059669"
GREEN_BG = "#ECFDF5"
VIOLET = "#6D28D9"
VIOLET_BG = "#F5F3FF"
LINE = "#94A3B8"


def _box(ax, x, y, w, h, text, *, fc=WHITE, ec=TEAL, r=0.08, fw="medium", fs=8.2, tc=INK):
    p = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle=f"round,pad=0.02,rounding_size={r}",
        linewidth=1.35,
        edgecolor=ec,
        facecolor=fc,
        zorder=2,
    )
    ax.add_patch(p)
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=tc, fontweight=fw, zorder=3, linespacing=1.25)
    return (x, y, w, h)


def _arrow(ax, x1, y1, x2, y2, text=""):
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(arrowstyle="-|>", color=TEAL_D, lw=1.4, mutation_scale=11),
        zorder=1,
    )
    if text:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx + 0.18, my, text, fontsize=6.6, color=MUTED, va="center", ha="left")


def _lane(ax, x, y, w, h, title, color):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor="#E2E8F0", lw=0.8, zorder=0))
    ax.text(x + 0.12, y + h - 0.18, title, fontsize=8.5, fontweight="bold", color=TEAL_D, va="top")


def main() -> None:
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(11.2, 13.2), dpi=180)
    ax.set_xlim(0, 11.2)
    ax.set_ylim(0, 13.2)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)

    ax.text(
        5.6,
        12.92,
        "Flujo operativo del prototipo MIA · Detección HC",
        ha="center",
        fontsize=13.5,
        fontweight="bold",
        color=INK,
    )
    ax.text(
        5.6,
        12.62,
        "Lo que hace el sistema entregado: de-identificación local de PDF escaneados y análisis a nivel de oración.",
        ha="center",
        fontsize=8,
        color=MUTED,
    )

    # --- Panel A: OCR ---
    _lane(ax, 0.25, 7.55, 10.7, 4.85, "A. Preparación de historias CITIMED (100 % local, sin API externa)", SLATE)

    _box(ax, 1.55, 11.55, 2.2, 0.72, "PDF escaneado\n(formulario + manuscrito)", ec="#64748B")
    _box(ax, 4.05, 11.55, 2.2, 0.72, "Tesseract OCR\n+ corrección de inclinación", fc="#ECFEFF", ec=TEAL)
    _arrow(ax, 2.65, 11.55, 2.95, 11.55)

    _box(ax, 6.55, 11.55, 2.15, 0.72, "Fusión de cajas\ny tachado en píxel", fc="#ECFEFF", ec=TEAL)
    _box(ax, 9.15, 11.55, 2.2, 0.72, "PDF anonimizado\nbuscable + revisión", fc=GREEN_BG, ec=GREEN)
    _arrow(ax, 5.15, 11.55, 5.47, 11.55)
    _arrow(ax, 7.63, 11.55, 8.05, 11.55)

    # four layers
    ax.text(5.6, 10.85, "Cuatro capas de detección (de más a menos dependencia del OCR)", ha="center", fontsize=8, color=MUTED)
    layers = [
        (1.55, "1. Reglas Ecuador\ncédula módulo 10, RUC,\nteléfono, HCU, edad ≥ 90"),
        (4.05, "2. Contexto + NER\nspaCy es_core_news_md\nnombres en prosa"),
        (6.55, "3. Etiqueta + tinta\nlee la etiqueta impresa;\ntacha el valor manuscrito"),
        (9.15, "4. Zonas fijas\nplantilla JSON\nfirmas, sellos, cabecera"),
    ]
    for x, t in layers:
        _box(ax, x, 9.85, 2.2, 1.05, t, fs=7.4, fc=WHITE, ec=TEAL_D)
    for x1, x2 in [(1.55, 4.05), (4.05, 6.55), (6.55, 9.15)]:
        _arrow(ax, x1 + 1.1, 9.85, x2 - 1.1, 9.85)

    _box(ax, 3.2, 8.35, 3.5, 0.78, "Página con OCR < 55 %\n→ revisión humana (p. ej. pág. 10)", fc=AMBER_BG, ec=AMBER, fs=7.8)
    _box(ax, 7.9, 8.35, 3.7, 0.78, "Texto clínico tachado\n→ corpus piloto / análisis Ollama", fc=GREEN_BG, ec=GREEN, fs=7.8)
    _arrow(ax, 6.55, 9.32, 3.2, 8.74)
    _arrow(ax, 9.15, 9.32, 7.9, 8.74)

    # --- Panel B: analysis ---
    _lane(ax, 0.25, 0.28, 10.7, 7.1, "B. Análisis de una nota en el prototipo (human-in-the-loop)", "#F8FAFC")

    _box(ax, 5.6, 6.85, 3.6, 0.7, "Auditor clínico — workspace React\nhistorial  |  nota  |  hallazgo", fc=VIOLET_BG, ec=VIOLET, fw="bold")
    _arrow(ax, 5.6, 6.5, 5.6, 6.22)

    _box(ax, 5.6, 5.88, 3.5, 0.58, "POST /generar   ·   FastAPI", fc="#ECFEFF", ec=TEAL, fw="bold")
    _arrow(ax, 5.6, 5.59, 5.6, 5.32)

    _box(ax, 5.6, 5.02, 3.5, 0.52, "Segmentar la nota en oraciones", fc=WHITE, ec=TEAL)

    # three arms
    _arrow(ax, 5.6, 4.76, 2.15, 4.28)
    _arrow(ax, 5.6, 4.76, 5.6, 4.28)
    _arrow(ax, 5.6, 4.76, 9.05, 4.28)

    _box(ax, 2.15, 3.88, 2.5, 0.78, "TF-IDF + LR\nsiempre · ~0,4 ms/oración", fc=WHITE, ec=TEAL_D, fs=7.6)
    _box(ax, 5.6, 3.88, 2.5, 0.78, "LLM zero-shot\nMEDEC: API · CITIMED: Ollama", fc=WHITE, ec=TEAL_D, fs=7.6)
    _box(ax, 9.05, 3.88, 2.5, 0.78, "LLM + RAG\nFAISS + guías / CIE-10", fc=WHITE, ec=TEAL_D, fs=7.6)

    _arrow(ax, 2.15, 3.49, 5.6, 3.12)
    _arrow(ax, 5.6, 3.49, 5.6, 3.12)
    _arrow(ax, 9.05, 3.49, 5.6, 3.12)

    # diamond-ish decision via rounded box
    _box(ax, 5.6, 2.78, 3.7, 0.58, "¿LLM disponible?", fc=AMBER_BG, ec=AMBER, r=0.28, fw="bold")

    _arrow(ax, 3.75, 2.78, 2.3, 2.78, "")
    _arrow(ax, 7.45, 2.78, 8.9, 2.78, "")
    ax.text(3.0, 2.98, "No", fontsize=7.2, color=AMBER, fontweight="bold", ha="center")
    ax.text(8.2, 2.98, "Sí", fontsize=7.2, color=GREEN, fontweight="bold", ha="center")

    _box(ax, 2.15, 2.15, 2.5, 0.7, "Fallback TF-IDF\nmodo degradado (banner)", fc=AMBER_BG, ec=AMBER, fs=7.6)
    _box(ax, 9.05, 2.15, 2.5, 0.7, "Scores de los tres brazos\n+ evidencia RAG citada", fc=GREEN_BG, ec=GREEN, fs=7.6)

    _arrow(ax, 2.15, 1.8, 5.6, 1.52)
    _arrow(ax, 9.05, 1.8, 5.6, 1.52)

    _box(ax, 5.6, 1.22, 4.4, 0.55, "Localización top-1  ·  umbral  ·  alerta sí/no", fc="#ECFEFF", ec=TEAL, fw="bold")
    _arrow(ax, 5.6, 0.94, 5.6, 0.78)

    _box(ax, 2.7, 0.52, 2.7, 0.48, "Persistir en SQLite\n(tope HISTORIAL_MAX_ITEMS)", fs=7.2, ec="#64748B")
    _box(ax, 8.4, 0.52, 3.3, 0.48, "Humano confirma o descarta\n(no sustituye criterio clínico)", fs=7.2, fc=VIOLET_BG, ec=VIOLET, fw="bold")
    _arrow(ax, 4.1, 1.05, 2.7, 0.76)
    _arrow(ax, 7.1, 1.05, 8.4, 0.76)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight", facecolor=WHITE, dpi=180)
    plt.close(fig)
    print(f"[ok] {OUT}")


if __name__ == "__main__":
    main()
