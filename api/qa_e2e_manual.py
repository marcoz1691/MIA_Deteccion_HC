"""Suite QA E2E manual contra servidor FastAPI en ejecución."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from s7.inferencia import MAX_ORACIONES_DEMO

BASE = "http://127.0.0.1:8000"

NOTA_LIMPIA = (
    "Paciente de 45 años acude por control periodontal rutinario. "
    "Examen: encías rosadas, sin sangrado al sondaje. "
    "Plan: profilaxis y control en 6 meses."
)
NOTA_MEDICACION = (
    "Paciente refiere dolor en molar 36 desde hace 3 días. "
    "Antecedentes: alergia documentada a penicilina. "
    "Se indica amoxicilina 500 mg cada 8 h pese a alergia documentada a penicilina."
)
NOTA_PLAN = (
    "Paciente con gingivitis leve confirmada en examen clínico. "
    "Encías levemente inflamadas, sin movilidad dental. "
    "Diagnóstico: gingivitis leve; plan: extracción de todas las piezas."
)


@dataclass
class Case:
    id: str
    name: str
    method: str
    path: str
    body: dict | str | None = None
    headers: dict = field(default_factory=dict)
    expect_status: int = 200
    checks: list = field(default_factory=list)


def http_call(method: str, path: str, body=None, headers=None):
    url = BASE + path
    hdrs = {"Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    data = None
    if body is not None:
        if isinstance(body, str):
            data = body.encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        else:
            data = json.dumps(body).encode("utf-8")
            hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            try:
                payload = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                payload = raw
            return resp.status, payload, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return e.code, payload, raw


def check(cond: bool, msg: str):
    return cond, msg


def build_cases() -> list[Case]:
    nota_larga = ". ".join(
        [f"Oracion numero {i} sin inconsistencia aparente" for i in range(1, MAX_ORACIONES_DEMO + 6)]
    ) + "."

    return [
        Case(
            "TC-01",
            "Health check",
            "GET",
            "/health",
            checks=[
                lambda s, p: check(s == 200, f"status={s}"),
                lambda s, p: check(p.get("status") == "ok", "status field ok"),
                lambda s, p: check("modelo_tfidf_disponible" in p, "has modelo_tfidf_disponible"),
                lambda s, p: check(
                    "modelo_tfidf_path" in p and p["modelo_tfidf_path"].endswith(".joblib"),
                    "model path",
                ),
            ],
        ),
        Case("TC-02", "OpenAPI docs", "GET", "/docs", expect_status=200),
        Case(
            "TC-03",
            "Nota limpia — sin alerta (mock LLM)",
            "POST",
            "/generar",
            body={
                "nota_clinica": NOTA_LIMPIA,
                "mock_llm": True,
                "brazos": ["llm_zero"],
                "umbral": 0.5,
            },
            checks=[
                lambda s, p: check(s == 200, f"status={s}"),
                lambda s, p: check(p.get("top1") is not None, "top1 present"),
                lambda s, p: check(p["top1"]["alerta"] is False, "top1 sin alerta"),
                lambda s, p: check(
                    all("score_localizacion" in o for o in p["oraciones"]),
                    "score_localizacion en oraciones",
                ),
            ],
        ),
        Case(
            "TC-04",
            "Error medicación — alerta amoxicilina",
            "POST",
            "/generar",
            body={
                "nota_clinica": NOTA_MEDICACION,
                "mock_llm": True,
                "brazos": ["llm_zero"],
                "umbral": 0.5,
            },
            checks=[
                lambda s, p: check(s == 200, f"status={s}"),
                lambda s, p: check("amoxicilina" in p["top1"]["oracion"].lower(), "top1 es amoxicilina"),
                lambda s, p: check(p["top1"]["alerta"] is True, "top1 con alerta"),
                lambda s, p: check(any(o["alerta"] for o in p["oraciones"]), "al menos una alerta"),
            ],
        ),
        Case(
            "TC-05",
            "Error plan — extracción excesiva",
            "POST",
            "/generar",
            body={
                "nota_clinica": NOTA_PLAN,
                "mock_llm": True,
                "brazos": ["llm_zero"],
                "umbral": 0.5,
            },
            checks=[
                lambda s, p: check(s == 200, f"status={s}"),
                lambda s, p: check(p["top1"]["alerta"] is True, "top1 con alerta"),
                lambda s, p: check(
                    "extracción" in p["top1"]["oracion"].lower()
                    or "piezas" in p["top1"]["oracion"].lower(),
                    "top1 oracion plan",
                ),
            ],
        ),
        Case(
            "TC-06",
            "Solo brazo TF-IDF",
            "POST",
            "/generar",
            body={
                "nota_clinica": NOTA_MEDICACION,
                "mock_llm": True,
                "brazos": ["tfidf"],
                "umbral": 0.5,
            },
            checks=[
                lambda s, p: check(s == 200, f"status={s}"),
                lambda s, p: check(p["brazos_efectivos"] == ["tfidf"], f"brazos={p.get('brazos_efectivos')}"),
                lambda s, p: check(all(o["score_tfidf"] is not None for o in p["oraciones"]), "scores tfidf"),
            ],
        ),
        Case(
            "TC-07",
            "Todos los brazos (mock)",
            "POST",
            "/generar",
            body={
                "nota_clinica": NOTA_MEDICACION,
                "mock_llm": True,
                "brazos": ["tfidf", "llm_zero", "llm_rag"],
                "umbral": 0.5,
            },
            checks=[
                lambda s, p: check(s == 200, f"status={s}"),
                lambda s, p: check(len(p["brazos_efectivos"]) == 3, f"brazos={p.get('brazos_efectivos')}"),
                lambda s, p: check(p["top1"]["alerta"] is True, "alerta con tripartita"),
            ],
        ),
        Case(
            "TC-08",
            "Umbral alto (1.0) — ninguna alerta",
            "POST",
            "/generar",
            body={
                "nota_clinica": NOTA_MEDICACION,
                "mock_llm": True,
                "brazos": ["llm_zero"],
                "umbral": 1.0,
            },
            checks=[
                lambda s, p: check(s == 200, f"status={s}"),
                lambda s, p: check(all(not o["alerta"] for o in p["oraciones"]), "sin alertas umbral 1.0"),
            ],
        ),
        Case(
            "TC-09",
            "Nota vacía — 422",
            "POST",
            "/generar",
            body={"nota_clinica": "", "mock_llm": True},
            expect_status=422,
            checks=[lambda s, p: check(s == 422, f"status={s}")],
        ),
        Case(
            "TC-10",
            "Sin campo nota_clinica — 422",
            "POST",
            "/generar",
            body={"mock_llm": True},
            expect_status=422,
            checks=[lambda s, p: check(s == 422, f"status={s}")],
        ),
        Case(
            "TC-11",
            "Brazos vacío — 422",
            "POST",
            "/generar",
            body={"nota_clinica": NOTA_LIMPIA, "brazos": []},
            expect_status=422,
            checks=[lambda s, p: check(s == 422, f"status={s}")],
        ),
        Case(
            "TC-12",
            "Brazo inválido — 422",
            "POST",
            "/generar",
            body={"nota_clinica": NOTA_LIMPIA, "brazos": ["invalido"]},
            expect_status=422,
            checks=[lambda s, p: check(s == 422, f"status={s}")],
        ),
        Case(
            "TC-13",
            "Idioma inválido — 422",
            "POST",
            "/generar",
            body={"nota_clinica": NOTA_LIMPIA, "idioma": "frances"},
            expect_status=422,
            checks=[lambda s, p: check(s == 422, f"status={s}")],
        ),
        Case(
            "TC-14",
            "JSON malformado — 422",
            "POST",
            "/generar",
            body="{nota_clinica: broken",
            expect_status=422,
            checks=[lambda s, p: check(s == 422, f"status={s}")],
        ),
        Case(
            "TC-15",
            "Ruta inexistente — 404",
            "GET",
            "/no-existe",
            expect_status=404,
            checks=[lambda s, p: check(s == 404, f"status={s}")],
        ),
        Case(
            "TC-16",
            "Nota larga — truncado al tope de oraciones",
            "POST",
            "/generar",
            body={
                "nota_clinica": nota_larga,
                "mock_llm": True,
                "brazos": ["llm_zero"],
                "umbral": 0.5,
            },
            checks=[
                lambda s, p: check(s == 200, f"status={s}"),
                lambda s, p: check(p["truncado"] is True, f"truncado={p.get('truncado')}"),
                lambda s, p: check(p["n_total"] > MAX_ORACIONES_DEMO, f"n_total={p.get('n_total')}"),
                lambda s, p: check(len(p["oraciones"]) == MAX_ORACIONES_DEMO, f"oraciones={len(p.get('oraciones', []))}"),
            ],
        ),
        Case(
            "TC-17",
            "CORS preflight OPTIONS",
            "OPTIONS",
            "/generar",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
            expect_status=200,
            checks=[lambda s, p: check(s in (200, 204), f"status={s}")],
        ),
        Case(
            "TC-18",
            "Contrato JSON respuesta completo",
            "POST",
            "/generar",
            body={"nota_clinica": NOTA_LIMPIA, "mock_llm": True, "brazos": ["llm_zero"]},
            checks=[
                lambda s, p: check(
                    {"oraciones", "top1", "truncado", "n_total", "modo_degradado", "brazos_efectivos", "mensaje_fallback"}.issubset(p.keys()),
                    f"root keys ok",
                ),
                lambda s, p: check(
                    all(
                        {"sid", "oracion", "score_localizacion", "alerta"}.issubset(o.keys())
                        for o in p["oraciones"]
                    ),
                    "oracion keys ok",
                ),
            ],
        ),
    ]


def main() -> int:
    passed = failed = 0
    results = []

    for tc in build_cases():
        status, payload, _raw = http_call(tc.method, tc.path, tc.body, tc.headers)
        case_pass = True
        detail_lines: list[str] = []

        if tc.path == "/docs":
            detail_lines.append(f"HTML docs status={status}")
            if status != tc.expect_status:
                case_pass = False
        else:
            if status != tc.expect_status:
                case_pass = False
                detail_lines.append(f"Expected HTTP {tc.expect_status}, got {status}")
            for chk in tc.checks:
                try:
                    ok, msg = chk(status, payload if isinstance(payload, dict) else {})
                    detail_lines.append(f"{'PASS' if ok else 'FAIL'}: {msg}")
                    if not ok:
                        case_pass = False
                except Exception as exc:
                    detail_lines.append(f"ERROR: {exc}")
                    case_pass = False

        if isinstance(payload, dict) and payload.get("top1") and tc.id in ("TC-04", "TC-06", "TC-07"):
            top = payload["top1"]
            detail_lines.append(
                f"  top1 sid={top['sid']} alerta={top['alerta']} score={top['score_localizacion']}"
            )

        verdict = "PASS" if case_pass else "FAIL"
        if case_pass:
            passed += 1
        else:
            failed += 1
        results.append((tc.id, tc.name, verdict, status, detail_lines))

    print("=" * 72)
    print("REPORTE QA E2E — API FastAPI POST /generar")
    print("=" * 72)
    for tc_id, name, verdict, status, lines in results:
        icon = "OK" if verdict == "PASS" else "XX"
        print(f"[{icon}] {tc_id} | {name} | HTTP {status}")
        for line in lines:
            print(f"      {line}")
    print("-" * 72)
    print(f"TOTAL: {passed + failed} | PASS: {passed} | FAIL: {failed}")
    print("=" * 72)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
