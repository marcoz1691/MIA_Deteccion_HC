"""Herramienta para crear una plantilla de zonas fijas dibujando rectángulos con el ratón.

Uso:
    python herramientas/medir_zonas.py mi_historia.pdf plantillas/mi_form.json [pagina]

Se abre la página; dibuja un rectángulo sobre cada casilla que quieras tachar SIEMPRE
(arrastrando con el botón izquierdo). Al soltar, escribe la etiqueta en la consola
(Enter = ZONA). Teclas: `d` borra el último rectángulo, `g` o cerrar la ventana guarda el JSON.

La plantilla resultante se usa con:
    python -m anonimizador_ocr --entrada historias\\ --salida salidas\\ --zonas plantillas\\mi_form.json

Las zonas fijas no dependen del OCR: se tachan aunque la casilla esté manuscrita o borrosa.
Sirve cuando el formulario es estandarizado (misma casilla en el mismo sitio en todas las hojas).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    import fitz
try:
    import tkinter as tk
    from PIL import Image, ImageTk
except ImportError as e:
    sys.exit(f"Falta tkinter o Pillow ({e}). El instalador de Python de python.org incluye tkinter.")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    pdf, salida = Path(sys.argv[1]), Path(sys.argv[2])
    num_pag = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    doc = fitz.open(pdf)
    pagina = doc[num_pag - 1]
    pix = pagina.get_pixmap(dpi=150, colorspace=fitz.csRGB, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    raiz = tk.Tk()
    raiz.title(f"Medir zonas — {pdf.name} pág. {num_pag}  |  arrastra rectángulos, d=deshacer, g=guardar")
    esc = min((raiz.winfo_screenwidth() - 100) / img.width, (raiz.winfo_screenheight() - 140) / img.height, 1.0)
    vista = img.resize((int(img.width * esc), int(img.height * esc)))
    foto = ImageTk.PhotoImage(vista)
    lienzo = tk.Canvas(raiz, width=vista.width, height=vista.height)
    lienzo.pack()
    lienzo.create_image(0, 0, anchor="nw", image=foto)

    zonas: list[dict] = []
    rects: list[int] = []
    actual = {"id": None, "x": 0, "y": 0}

    def al_presionar(e):
        actual.update(x=e.x, y=e.y, id=lienzo.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=2))

    def al_arrastrar(e):
        lienzo.coords(actual["id"], actual["x"], actual["y"], e.x, e.y)

    def al_soltar(e):
        x0, y0 = min(actual["x"], e.x), min(actual["y"], e.y)
        x1, y1 = max(actual["x"], e.x), max(actual["y"], e.y)
        if x1 - x0 < 5 or y1 - y0 < 5:
            lienzo.delete(actual["id"])
            return
        etiqueta = input(f"Etiqueta para la zona {len(zonas) + 1} (Enter = ZONA): ").strip().upper() or "ZONA"
        zonas.append({"nombre": f"zona_{len(zonas) + 1}", "pagina": num_pag, "etiqueta": etiqueta,
                      "x0": round(x0 / vista.width, 4), "y0": round(y0 / vista.height, 4),
                      "x1": round(x1 / vista.width, 4), "y1": round(y1 / vista.height, 4)})
        rects.append(actual["id"])
        lienzo.create_text(x0 + 4, y0 + 4, text=etiqueta, anchor="nw", fill="red")
        print(f"  -> {zonas[-1]}")

    def deshacer(_=None):
        if zonas:
            zonas.pop()
            lienzo.delete(rects.pop())
            print("  (última zona borrada)")

    def guardar(_=None):
        salida.parent.mkdir(parents=True, exist_ok=True)
        with open(salida, "w", encoding="utf-8") as f:
            json.dump({"nombre": pdf.stem, "zonas": zonas}, f, ensure_ascii=False, indent=2)
        print(f"Guardado {salida} con {len(zonas)} zona(s).")
        raiz.destroy()

    lienzo.bind("<ButtonPress-1>", al_presionar)
    lienzo.bind("<B1-Motion>", al_arrastrar)
    lienzo.bind("<ButtonRelease-1>", al_soltar)
    raiz.bind("d", deshacer)
    raiz.bind("g", guardar)
    raiz.protocol("WM_DELETE_WINDOW", guardar)
    raiz.mainloop()


if __name__ == "__main__":
    main()
