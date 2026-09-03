"""Transcripción estructurada de páginas escaneadas mediante un modelo de visión.

El objetivo NO es transcribir la página completa: solo el contenido clínico de
dos columnas del formulario CITIMED «EVOLUCION - HOSPITALARIA»:

  * NOTAS DE EVOLUCIÓN            (sección B.1)
  * ORDENES MEDICAS GENERALES     (contenido de B.2 FARMACOTERAPIA E INDICACIONES)

Se descarta la cabecera (datos del paciente), los rótulos preimpresos, las firmas
y los sellos. La salida es JSON para que la detección de inconsistencias consuma
campos, no texto libre.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Callable

from dotenv import load_dotenv

load_dotenv()

# Contrato: recibe la lista de PNG (una por página) y devuelve el dict ya parseado
# con las claves "entries" y "paginas_sin_contenido".
Transcriptor = Callable[[list[bytes]], dict]


class VisionUnavailableError(RuntimeError):
    """No hay modelo de visión disponible (sin API key) y el caller debe degradar."""


SYSTEM_PROMPT = """\
Eres un transcriptor clínico literal. Recibes imágenes escaneadas de un formulario
CITIMED "EVOLUCION - HOSPITALARIA". Transcribes ÚNICAMENTE el contenido
manuscrito/mecanografiado de dos columnas del cuerpo del formulario y descartas
todo el andamiaje impreso.

TRANSCRIBIR (contenido clínico):
- Columna "NOTAS DE EVOLUCIÓN": el cuerpo de cada nota, incluidas sus
  sub-etiquetas de contenido cuando el médico las escribió (PROCEDIMIENTO
  REALIZADO, IMPRESIONES DIAGNÓSTICAS, SUBJETIVO, OBJETIVO, EXAMEN FISICO,
  SIGNOS VITALES y TODO el texto que sigue a signos vitales, PLAN, APP,
  AQX, APF / ANTECEDENTES PATOLÓGICOS FAMILIARES —no confundir APF con APP—,
  ENFERMEDAD ACTUAL completa, ANÁLISIS de cada evolución, profesión u
  ocupación, religión si aparecen en la nota) y sus valores.
- Columna "FARMACOTERAPIA E INDICACIONES" bajo el título "ORDENES MEDICAS
  GENERALES": cada orden o indicación, una por elemento de lista.
- La FECHA (aaaa-mm-dd) y la HORA (hh:mm) que encabezan cada nota.
- TODAS las evoluciones de todas las páginas (ingreso, evolución 2, alta,
  etc.). No resumas ni cortes una nota a la mitad.

NO TRANSCRIBIR (descartar siempre):
- Sección "A. DATOS DEL USUARIO / PACIENTE": institución, unicódigo,
  establecimiento, número de historia clínica, número de archivo, nro. de hoja.
- Títulos y rótulos preimpresos del formulario.
- Bloques de firma, sello y credencial (nombre del profesional, "Enfermera",
  "Médico", "M.S.P. Reg. ...", "SELLO DE ...", rúbricas, iniciales sueltas).
- Encabezados/pies de página corridos (logo, dirección de la clínica, número de
  página) y la columna estrecha "ADMINSTR. FARMACOS / DISPOSITIVO".
- Números de cédula, teléfono o historia clínica. Nunca sustituyas un párrafo
  clínico por "[dato omitido]": si hay un identificador, omite solo ese dato y
  conserva religión, profesión, APF, enfermedad actual, signos vitales y análisis.

REGLAS DE FIDELIDAD (críticas: no se corrige nada):
1. Transcribe literal. No corrijas ortografía, no normalices unidades, no
   completes abreviaturas, no reordenes, no resumas, no "arregles" valores que
   parezcan raros.
2. Conserva números, unidades, lateralidad (izq/der), nombres de fármacos y
   dosis exactamente como aparecen.
3. Texto ilegible -> [ilegible]. Texto tachado/redactado -> [tachado]. Valor
   cortado por el borde -> [corte]. Nunca adivines.
4. Idioma y mayúsculas originales (español).
5. Si una nota continúa en la siguiente imagen, es la MISMA evolución: fusiona el
   texto en una sola entrada.

SALIDA: responde SOLO con un objeto JSON con esta forma exacta:
{
  "entries": [
    {
      "evolucion_n": 1,
      "fecha": "aaaa-mm-dd" | null,
      "hora": "hh:mm" | null,
      "notas_evolucion": "texto literal con saltos de línea \\n",
      "ordenes_medicas": ["indicación 1", "indicación 2"]
    }
  ],
  "paginas_sin_contenido": [numeros de pagina que solo tenian cabecera/firmas]
}
Numera "evolucion_n" de forma correlativa a lo largo de todas las imágenes.
Si no hay ninguna nota, devuelve {"entries": [], "paginas_sin_contenido": [...]}.
"""

USER_PROMPT = (
    "Transcribe estas {n} imágenes siguiendo tus reglas. "
    "Son páginas consecutivas de la misma historia clínica."
)


def _data_uri(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def _parse_json(texto: str) -> dict:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.split("```", 2)[1]
        if texto.lstrip().lower().startswith("json"):
            texto = texto.lstrip()[4:]
    try:
        data = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ValueError(f"El modelo de visión no devolvió JSON válido: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("El JSON del modelo de visión no es un objeto.")
    data.setdefault("entries", [])
    data.setdefault("paginas_sin_contenido", [])
    return data


def transcriptor_openai(
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    max_tokens: int = 16384,
    temperature: float = 0.0,
) -> Transcriptor:
    """Crea un transcriptor que llama a un endpoint OpenAI-compatible con visión."""
    key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("MISTRAL_API_KEY")
    if not key:
        raise VisionUnavailableError(
            "Modelo de visión no configurado (falta OPENAI_API_KEY)."
        )
    modelo = model or os.getenv("VISION_MODEL") or "gpt-4o-mini"
    url = base_url or os.getenv("OPENAI_BASE_URL")

    from openai import OpenAI

    kwargs = {"api_key": key}
    if url:
        kwargs["base_url"] = url
    client = OpenAI(**kwargs)

    def _run(imagenes: list[bytes]) -> dict:
        contenido = [{"type": "text", "text": USER_PROMPT.format(n=len(imagenes))}]
        for png in imagenes:
            contenido.append(
                {"type": "image_url", "image_url": {"url": _data_uri(png), "detail": "high"}}
            )
        resp = client.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": contenido},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return _parse_json(resp.choices[0].message.content or "{}")

    return _run
