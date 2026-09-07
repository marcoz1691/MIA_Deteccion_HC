"""Transcripción estructurada de páginas escaneadas mediante un modelo de visión.

El objetivo NO es transcribir la página completa: solo el contenido clínico
(notas de evolución y órdenes médicas), tanto del formulario CITIMED de dos
columnas como de una hoja posterior «EVOLUCION - HOSPITALARIA» en tabla.

Se descarta la cabecera (datos del paciente), los rótulos preimpresos, las firmas
y los sellos. La salida es JSON para que la detección de inconsistencias consuma
campos, no texto libre.
"""
from __future__ import annotations

import base64
import json
import os
import time
from typing import Callable

from dotenv import load_dotenv

load_dotenv()

# Contrato: recibe la lista de PNG (una por página) y devuelve el dict ya parseado
# con las claves "entries" y "paginas_sin_contenido".
Transcriptor = Callable[[list[bytes]], dict]


class VisionUnavailableError(RuntimeError):
    """No hay modelo de visión disponible (sin API key) y el caller debe degradar."""


SYSTEM_PROMPT = """\
Eres un transcriptor clínico literal. Recibes imágenes escaneadas de historias
CITIMED: el formulario MSP de dos columnas y, a menudo, una hoja posterior
"EVOLUCION - HOSPITALARIA" en formato de tabla. Transcribes el contenido
manuscrito/mecanografiado clínico y descartas el andamiaje impreso.

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
- Hoja hospitalaria en tabla (Inicio, OBJETIVO, EXAMEN FISICO, ANÁLISIS,
  signos vitales, alta): ES una evolución propia aunque el encabezado esté
  tachado/redactado y aunque no tenga las dos columnas del formulario MSP.
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
- Números de cédula, teléfono o historia clínica.
- Nombres y apellidos de personas (paciente, familiares, médicos, enfermeras).
  Sustitúyelos por "[dato omitido]" y conserva el resto clínico: parentesco
  (ABUELO MATERNO), diagnósticos, "DR." / "DRA.", órdenes, signos vitales y
  análisis. Nunca dejes un nombre o apellido en claro.
- Nunca sustituyas un párrafo clínico entero por "[dato omitido]": si hay un
  identificador o un nombre, omite solo ese dato.

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
   texto en una sola entrada. Si la columna izquierda muere a media frase
   (p. ej. "MOLESTIAS AL" al pie de página) y la imagen siguiente NO continúa
   esa frase, cierra la nota con [corte] y transcribe la siguiente hoja como
   otra evolución.
6. paginas_sin_contenido solo para páginas SIN texto clínico (cabecera/firmas).
   Nunca marques así una página con OBJETIVO, EXAMEN FISICO, ANALISIS,
   SIGNOS VITALES o ALTA.

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
    "Transcribe estas {n} imágenes (página 1 a {n}) siguiendo tus reglas. "
    "Son páginas consecutivas de la misma historia clínica. "
    "Revisa CADA imagen. No te detengas porque una columna termine a media frase. "
    "Una hoja hospitalaria posterior (OBJETIVO, EXAMEN FISICO, ANÁLISIS) no la descartes."
)

USER_PROMPT_PAGINA = (
    "Transcribe esta imagen (una sola página de la historia clínica). "
    "No asumas que el contenido ya se transcribió en páginas anteriores. "
    "Si es una hoja hospitalaria en tabla (OBJETIVO, EXAMEN FISICO, ANÁLISIS, "
    "signos vitales, alta), devuélvela como evolución; no la descartes. "
    "Nombres y apellidos van como [dato omitido]; el resto clínico se conserva."
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


def transcribir_por_pagina(imagenes: list[bytes], transcribir_lote: Transcriptor) -> dict:
    """Una llamada de visión por página para que la última hoja no se omita."""
    entradas: list[dict] = []
    sin_contenido: list[int] = []
    for i, png in enumerate(imagenes, start=1):
        crudo = transcribir_lote([png])
        if not isinstance(crudo, dict):
            sin_contenido.append(i)
            continue
        brutos = [e for e in (crudo.get("entries") or []) if isinstance(e, dict)]
        if brutos:
            entradas.extend(brutos)
        else:
            sin_contenido.append(i)
    for n, entrada in enumerate(entradas, start=1):
        entrada["evolucion_n"] = n
    return {"entries": entradas, "paginas_sin_contenido": sin_contenido}


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

    def _lote(imgs: list[bytes]) -> dict:
        contenido = [{"type": "text", "text": USER_PROMPT_PAGINA}]
        for png in imgs:
            contenido.append(
                {"type": "image_url", "image_url": {"url": _data_uri(png), "detail": "high"}}
            )
        last_err: BaseException | None = None
        for attempt in range(3):
            try:
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
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                detalle = str(exc).lower()
                if "429" not in detalle and "rate_limit" not in detalle:
                    raise
                if attempt >= 2:
                    break
                time.sleep(2.0 * (attempt + 1))
        raise last_err  # type: ignore[misc]

    def _run(imagenes: list[bytes]) -> dict:
        return transcribir_por_pagina(imagenes, _lote)

    return _run
