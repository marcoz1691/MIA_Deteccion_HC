"""Plantillas de prompt para LLM zero-shot y LLM+RAG (inglés y español)."""

EJES_MVP_ES = (
    "Ejes MVP a revisar siempre (contra el resto de la nota, solo estos cinco): "
    "1) lateralidad (izquierda/derecha), "
    "2) sexo/género del paciente, "
    "3) alergias vs prescripciones, "
    "4) medicamentos (dosis, duplicidad, contradicción con la nota), "
    "5) edad vs hallazgos o procedimientos. "
    "Marca SI únicamente si la oración contradice la nota en uno de esos cinco ejes. "
    "Responde NO si el posible problema es de otro tipo clínico: "
    "tolerancia oral o dieta vs alta, signos vitales vs plan, "
    "procedimiento vs complicaciones, hemodinamia, náuseas, dolor o indicaciones de egreso. "
    "No infieras contraindicaciones farmacológicas finas de un modelo médico; "
    "eso queda para una etapa posterior. "
    "No marques SI si el texto es solo un título o subtítulo de sección "
    "(NOTA DE INGRESO, ENFERMEDAD ACTUAL, EXAMEN FISICO, EVOLUCIÓN, "
    "ORDENES MEDICAS, APP, APF, ALERGIAS, ANÁLISIS, SUBJETIVO, OBJETIVO)."
)

EJES_MVP_EN = (
    "MVP axes to always check (against the rest of the note, only these five): "
    "1) laterality (left/right), "
    "2) patient sex/gender, "
    "3) allergies vs prescriptions, "
    "4) medications (dose, duplication, contradiction with the note), "
    "5) age vs findings or procedures. "
    "Reply YES only if the sentence contradicts the note on one of those five axes. "
    "Reply NO for other clinical judgments: oral intake or diet vs discharge, "
    "vital signs vs plan, procedure vs complications, hemodynamics, nausea, pain, or discharge orders. "
    "Do not infer fine-grained drug-disease contraindications; that is a later medical model. "
    "Do not mark YES for section titles or headings "
    "(admission note, current illness, physical exam, evolution, orders, allergies, analysis)."
)

ZERO_SHOT_EN = """You are a clinical documentation reviewer. Judge whether the sentence is inconsistent with the rest of the medical note on the five MVP axes only (laterality, sex, allergies, medications, age). If it is not one of those axes, reply NO.

{ejes}

Full note:
{nota}

Sentence: "{oracion}"

Reply with ONLY one word: YES if inconsistent, NO if consistent."""

ZERO_SHOT_ES = """Eres un revisor de historias clínicas. Determina si la oración es inconsistente con el resto de la nota solo en los cinco ejes MVP (lateralidad, sexo, alergias, medicamentos, edad). Si no encaja en esos ejes, responde NO.

{ejes}

Nota completa:
{nota}

Oración: "{oracion}"

Responde SOLO con una palabra: SI si es inconsistente, NO si es consistente."""

RAG_EN = """You are a clinical documentation reviewer. Use the reference knowledge only when it maps to an MVP axis. Judge whether the sentence is a clinical inconsistency on laterality, sex, allergies, medications, or age. Otherwise reply NO.

{ejes}

Reference knowledge:
{contexto}

Full note:
{nota}

Sentence from medical note: "{oracion}"

Reply with ONLY one word: YES if inconsistent, NO if consistent."""

RAG_ES = """Eres un revisor de historias clínicas. Usa el conocimiento de referencia solo si aplica a un eje MVP. Determina si la oración es inconsistente en lateralidad, sexo, alergias, medicamentos o edad. Si no, responde NO.

{ejes}

Conocimiento de referencia:
{contexto}

Nota completa:
{nota}

Oración de la nota médica: "{oracion}"

Responde SOLO con una palabra: SI si es inconsistente, NO si es consistente."""

NOTA_MAX_CHARS = 8000


def _nota_para_prompt(nota: str) -> str:
    texto = (nota or "").strip()
    if not texto:
        return "(sin nota de contexto; juzga solo la oración)"
    if len(texto) > NOTA_MAX_CHARS:
        return texto[:NOTA_MAX_CHARS] + "\n[nota recortada]"
    return texto


def get_prompt(mode: str, idioma: str, oracion: str, contexto: str = "", nota: str = "") -> str:
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
    ejes = EJES_MVP_EN if key[1] == "english" else EJES_MVP_ES
    kwargs = {
        "oracion": oracion,
        "ejes": ejes,
        "nota": _nota_para_prompt(nota),
    }
    if mode == "rag":
        kwargs["contexto"] = contexto
    return tmpl.format(**kwargs)


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
