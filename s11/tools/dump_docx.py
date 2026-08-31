"""Volcado de la estructura de un .docx para inspección (párrafos, estilos, tablas, imágenes)."""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def iter_block_items(parent):
    from docx.document import Document as _Doc
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P

    if isinstance(parent, _Doc):
        parent_elm = parent.element.body
    else:
        parent_elm = parent._element
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def main() -> None:
    ruta = Path(sys.argv[1])
    doc = Document(str(ruta))
    idx = 0
    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            texto = block.text.strip()
            tiene_img = "graphicData" in block._p.xml
            if not texto and not tiene_img:
                idx += 1
                continue
            marca = " [IMG]" if tiene_img else ""
            print(f"[{idx}] <{block.style.name}>{marca} {texto}")
        else:
            filas = len(block.rows)
            cols = len(block.columns)
            print(f"[{idx}] <<TABLA {filas}x{cols}>>")
            for r in block.rows[: min(filas, 40)]:
                celdas = [c.text.replace("\n", " / ").strip() for c in r.cells]
                print("      | " + " | ".join(celdas))
        idx += 1


if __name__ == "__main__":
    main()
