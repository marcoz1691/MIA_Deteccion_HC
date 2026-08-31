"""Anonimizador de historias clínicas escaneadas (OCR + manuscrito) — CITIMED.

Flujo por página:
  rasterizar -> OCR (palabras con cajas) -> detección de PHI (reglas + NER)
  -> zonas fijas / zonas junto a etiquetas -> tachado a nivel de píxel
  -> PDF nuevo (sin capa de texto original, sin metadatos) + material de revisión.
"""

__version__ = "0.1.0"
