"""Pruebas ES/EN con y sin API LLM."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"

NOTAS = {
    "es_medicacion": (
        "Paciente refiere dolor en molar 36. "
        "Antecedentes: alergia documentada a penicilina. "
        "Se indica amoxicilina 500 mg cada 8 h."
    ),
    "en_medicacion": (
        "Patient reports pain in tooth 36 for 3 days. "
        "History: documented allergy to penicillin. "
        "Amoxicillin 500 mg every 8 hours is prescribed."
    ),
    "es_limpia": (
        "Paciente de 45 años acude por control periodontal rutinario. "
        "Examen: encías rosadas, sin sangrado al sondaje. "
        "Plan: profilaxis y control en 6 meses."
    ),
    "en_limpia": (
        "45-year-old patient presents for routine periodontal checkup. "
        "Exam: pink gums, no bleeding on probing. "
        "Plan: prophylaxis and follow-up in 6 months."
    ),
}


def post(body: dict) -> tuple[int, dict | str | None]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/generar",
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw


def resumen(payload: dict) -> str:
    top = payload.get("top1") or {}
    alertas = sum(1 for o in payload.get("oraciones", []) if o.get("alerta"))
    llm_resp = None
    for o in payload.get("oraciones", []):
        if o.get("respuesta_llm_zero"):
            llm_resp = o["respuesta_llm_zero"]
            break
        if o.get("respuesta_llm_rag"):
            llm_resp = o["respuesta_llm_rag"]
            break
    return (
        f"oraciones={len(payload.get('oraciones', []))} | "
        f"alertas={alertas} | "
        f"top1_sid={top.get('sid')} alerta={top.get('alerta')} "
        f"score={top.get('score_localizacion')} | "
        f"llm_resp={llm_resp!r} | "
        f"degradado={payload.get('modo_degradado')} | "
        f"brazos={payload.get('brazos_efectivos')}"
    )


def main() -> int:
    matrix = [
        ("ES", "sin API (mock explícito)", "es_medicacion", {"idioma": "spanish", "mock_llm": True, "brazos": ["llm_zero"]}),
        ("ES", "sin API (mock explícito)", "es_limpia", {"idioma": "spanish", "mock_llm": True, "brazos": ["llm_zero"]}),
        ("EN", "sin API (mock explícito)", "en_medicacion", {"idioma": "english", "mock_llm": True, "brazos": ["llm_zero"]}),
        ("EN", "sin API (mock explícito)", "en_limpia", {"idioma": "english", "mock_llm": True, "brazos": ["llm_zero"]}),
        ("ES", "sin API LLM (solo TF-IDF)", "es_medicacion", {"idioma": "spanish", "mock_llm": True, "brazos": ["tfidf"]}),
        ("EN", "sin API LLM (solo TF-IDF)", "en_medicacion", {"idioma": "english", "mock_llm": True, "brazos": ["tfidf"]}),
        ("ES", "con API (mock_llm=false)", "es_medicacion", {"idioma": "spanish", "mock_llm": False, "brazos": ["llm_zero"]}),
        ("ES", "con API (mock_llm=false)", "es_limpia", {"idioma": "spanish", "mock_llm": False, "brazos": ["llm_zero"]}),
        ("EN", "con API (mock_llm=false)", "en_medicacion", {"idioma": "english", "mock_llm": False, "brazos": ["llm_zero"]}),
        ("EN", "con API (mock_llm=false)", "en_limpia", {"idioma": "english", "mock_llm": False, "brazos": ["llm_zero"]}),
        ("ES", "tripartita mock", "es_medicacion", {"idioma": "spanish", "mock_llm": True, "brazos": ["tfidf", "llm_zero", "llm_rag"]}),
        ("EN", "tripartita mock", "en_medicacion", {"idioma": "english", "mock_llm": True, "brazos": ["tfidf", "llm_zero", "llm_rag"]}),
    ]

    print("=" * 80)
    print("PRUEBAS IDIOMA + API — POST /generar")
    print("=" * 80)

    api_key = __import__("os").environ.get("OPENAI_API_KEY") or __import__("os").environ.get("MISTRAL_API_KEY")
    print(f"API key en entorno: {'SI' if api_key else 'NO (mock_llm=false usará fallback interno)'}")
    print("-" * 80)

    for lang, modo, nota_key, opts in matrix:
        body = {"nota_clinica": NOTAS[nota_key], "umbral": 0.5, **opts}
        status, payload = post(body)
        if status != 200 or not isinstance(payload, dict):
            print(f"[FAIL] {lang} | {modo} | {nota_key} | HTTP {status} | {payload}")
            continue
        esperada = "alerta" if "medicacion" in nota_key and "mock" in modo and "TF-IDF" not in modo else "sin alerta"
        if "medicacion" in nota_key and "TF-IDF" in modo:
            esperada = "variable (TF-IDF)"
        top_alerta = (payload.get("top1") or {}).get("alerta")
        ok = True
        if esperada == "alerta" and not top_alerta:
            ok = False
        if esperada == "sin alerta" and top_alerta:
            ok = False
        mark = "OK" if ok else "??"
        print(f"[{mark}] {lang} | {modo} | {nota_key}")
        print(f"      {resumen(payload)}")
        if payload.get("top1"):
            print(f"      top1: {payload['top1']['oracion'][:70]}...")
        print()

    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
