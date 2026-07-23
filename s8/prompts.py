"""Plantillas de prompt para LLM zero-shot y LLM+RAG (inglés y español)."""

ZERO_SHOT_EN = """You are a clinical documentation reviewer. Given a sentence from a medical note, determine if it contains a clinical inconsistency (contradiction with medical facts, other parts of the note, or standard practice).

Sentence: "{oracion}"

Reply with ONLY one word: YES if inconsistent, NO if consistent."""

ZERO_SHOT_ES = """Eres un revisor de historias clínicas. Dada una oración de una nota médica, determina si contiene una inconsistencia clínica (contradicción con hechos médicos, otras partes de la nota o práctica estándar).

Oración: "{oracion}"

Responde SOLO con una palabra: SI si es inconsistente, NO si es consistente."""

RAG_EN = """You are a clinical documentation reviewer. Use the reference knowledge below to judge whether the sentence contains a clinical inconsistency.

Reference knowledge:
{contexto}

Sentence from medical note: "{oracion}"

Reply with ONLY one word: YES if inconsistent, NO if consistent."""

RAG_ES = """Eres un revisor de historias clínicas. Usa el conocimiento de referencia para determinar si la oración contiene una inconsistencia clínica.

Conocimiento de referencia:
{contexto}

Oración de la nota médica: "{oracion}"

Responde SOLO con una palabra: SI si es inconsistente, NO si es consistente."""


def get_prompt(mode: str, idioma: str, oracion: str, contexto: str = "") -> str:
    """mode: zero_shot | rag"""
    templates = {
        ("zero_shot", "english"): ZERO_SHOT_EN,
        ("zero_shot", "spanish"): ZERO_SHOT_ES,
        ("rag", "english"): RAG_EN,
        ("rag", "spanish"): RAG_ES,
    }
    key = (mode, idioma)
    if key not in templates:
        key = (mode, "english")
    tmpl = templates[key]
    if mode == "rag":
        return tmpl.format(oracion=oracion, contexto=contexto)
    return tmpl.format(oracion=oracion)


def parse_yes_no(respuesta: str, idioma: str = "english") -> float:
    """Convierte respuesta LLM a score 0-1."""
    r = respuesta.strip().upper()
    positivos = {"YES", "SI", "SÍ", "Y", "1", "TRUE"}
    negativos = {"NO", "N", "0", "FALSE"}
    if any(r.startswith(p) for p in positivos):
        return 1.0
    if any(r.startswith(n) for n in negativos):
        return 0.0
    return 0.5  # ambiguo
