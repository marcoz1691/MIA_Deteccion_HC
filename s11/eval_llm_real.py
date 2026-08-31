"""S11 — Evaluación tripartita con LLM real y consolidación de métricas.

Orquesta la corrida de `s7/eval_tripartita.py` SIN modo mock, atribuye tokens,
costo y latencia por brazo leyendo el cache de prompts, y contrasta el resultado
contra la línea base mock registrada en S10.

Uso:
    python s11/eval_llm_real.py --max-oraciones 400
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASELINE_MOCK = ROOT / "s10" / "evidencias" / "metricas_tripartita.json"
SALIDA_DEFAULT = ROOT / "s11" / "evidencias" / "metricas_llm_real.json"

# Nombre del brazo en el JSON de resultados -> modo de prompt usado por eval_tripartita.
MODOS_LLM = {"llm_zero": "zero_shot", "llm_rag": "rag"}

# Estimación a priori publicada en s7/docs/informe_produccion.md §5 (USD/1000 oraciones).
ESTIMACION_PREVIA_USD_1K = {"llm_zero": 0.08, "llm_rag": 0.15}


def correr_eval_tripartita(config: str, max_oraciones: int) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "s7" / "eval_tripartita.py"),
        "--config",
        config,
        "--max-oraciones",
        str(max_oraciones),
    ]
    print(f"[s11] Ejecutando: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def clave_cache(brazo: str, modelo: str, prompt: str) -> str:
    """Replica LLMClient._cache_key en modo real (sin sufijo mock, sin nota_context)."""
    return hashlib.sha256(f"{brazo}|{modelo}|{prompt}|".encode()).hexdigest()


def cargar_oraciones(cfg: dict, max_oraciones: int):
    from s7.preprocesamiento import explotar_oraciones, load_medec

    split = cfg["eval"]["split"]
    archivo = cfg["medec"]["validation"] if split == "validation" else cfg["medec"]["test"]
    df = load_medec(ROOT / cfg["medec"]["base_path"], archivo)
    return split, explotar_oraciones(df).head(max_oraciones)


def consumo_por_brazo(cfg: dict, max_oraciones: int) -> dict:
    """Tokens, costo y latencia por brazo LLM, reconstruyendo las entradas de cache.

    `llm_stats` del script de S7 agrega ambos brazos y omite las respuestas servidas
    desde cache, por lo que subestima el consumo real de una corrida completa.
    """
    from s7.prompts import get_prompt
    from s7.rag_index import RAGIndex

    _, odf = cargar_oraciones(cfg, max_oraciones)
    idioma = cfg["idioma"]["default"]
    modelo = cfg["llm"]["model"]
    cache_dir = ROOT / cfg["salidas"]["cache_dir"]

    rag = RAGIndex(
        knowledge_dir=ROOT / cfg["rag"]["knowledge_dir"],
        embedding_model=cfg["rag"]["embedding_model"],
        index_path=ROOT / cfg["rag"]["index_path"],
        top_k=cfg["rag"]["top_k"],
    ).load()

    consumo: dict[str, dict] = {}
    for brazo, modo in MODOS_LLM.items():
        agregado = {
            "n_oraciones": int(len(odf)),
            "entradas_cache_encontradas": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "costo_usd_total": 0.0,
            "latencias_ms": [],
        }
        for _, fila in odf.iterrows():
            contexto = rag.retrieve(fila.oracion) if modo == "rag" else ""
            prompt = get_prompt(modo, idioma, fila.oracion, contexto)
            ruta = cache_dir / f"{clave_cache(f'llm_{modo}', modelo, prompt)}.json"
            if not ruta.exists():
                continue
            dato = json.loads(ruta.read_text(encoding="utf-8"))
            agregado["entradas_cache_encontradas"] += 1
            agregado["input_tokens"] += int(dato.get("input_tokens", 0))
            agregado["output_tokens"] += int(dato.get("output_tokens", 0))
            agregado["costo_usd_total"] += float(dato.get("cost_usd", 0.0))
            agregado["latencias_ms"].append(float(dato.get("latency_ms", 0.0)))

        lats = sorted(agregado.pop("latencias_ms"))
        n = agregado["entradas_cache_encontradas"]
        agregado["costo_usd_total"] = round(agregado["costo_usd_total"], 6)
        agregado["costo_usd_por_1000_oraciones"] = (
            round(agregado["costo_usd_total"] / n * 1000, 4) if n else None
        )
        agregado["tokens_por_oracion"] = (
            round((agregado["input_tokens"] + agregado["output_tokens"]) / n, 2) if n else None
        )
        agregado["latencia_ms_media"] = round(sum(lats) / n, 2) if n else None
        agregado["latencia_ms_p50"] = round(lats[int(n * 0.50)], 2) if n else None
        agregado["latencia_ms_p95"] = round(lats[min(int(n * 0.95), n - 1)], 2) if n else None
        consumo[brazo] = agregado
    return consumo


def comparar_con_mock(brazos_real: dict) -> dict:
    if not BASELINE_MOCK.exists():
        return {"disponible": False, "motivo": f"No existe {BASELINE_MOCK}"}
    mock = json.loads(BASELINE_MOCK.read_text(encoding="utf-8"))
    detalle = {}
    for brazo, datos in brazos_real.items():
        m = mock["brazos"].get(brazo)
        if not m:
            continue
        real_o, mock_o = datos["oracion"], m["oracion"]
        detalle[brazo] = {
            "roc_auc_mock": mock_o["roc_auc"],
            "roc_auc_real": real_o["roc_auc"],
            "delta_roc_auc": round(real_o["roc_auc"] - mock_o["roc_auc"], 4),
            "auprc_mock": mock_o["auprc"],
            "auprc_real": real_o["auprc"],
            "delta_auprc": round(real_o["auprc"] - mock_o["auprc"], 4),
            "f1_mock": mock_o["f1"],
            "f1_real": real_o["f1"],
            "latencia_ms_mock": m["latency_ms_per_oracion"],
            "latencia_ms_real": datos["latency_ms_per_oracion"],
            "localizacion_top1_mock": m["localizacion"]["localizacion_top1"],
            "localizacion_top1_real": datos["localizacion"]["localizacion_top1"],
        }
    return {
        "disponible": True,
        "fuente": str(BASELINE_MOCK.relative_to(ROOT)).replace("\\", "/"),
        "n_oraciones_mock": mock["n_oraciones"],
        "brazos": detalle,
    }


def cargar_sesgo_idioma(cfg: dict) -> dict:
    ruta = ROOT / cfg["salidas"]["dir"] / "eval_idioma_en_es.json"
    if not ruta.exists():
        return {"disponible": False, "motivo": "no disponible: no se generó el JSON"}
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if datos.get("llm_stats", {}).get("mock_mode", True):
        return {"disponible": False, "motivo": "no disponible: el JSON existente es de modo mock"}
    return {
        "disponible": True,
        "subset_n": datos["subset_n"],
        "roc_auc_english": datos["english"]["roc_auc"],
        "roc_auc_spanish": datos["spanish"]["roc_auc"],
        "auprc_english": datos["english"]["auprc"],
        "auprc_spanish": datos["spanish"]["auprc"],
        "delta_auc_en_minus_es": datos["delta_auc_en_minus_es"],
        "delta_auprc_en_minus_es": datos["delta_auprc_en_minus_es"],
        "llm_stats": datos["llm_stats"],
    }


def construir_export(cfg: dict, max_oraciones: int, comando: str) -> dict:
    ruta_tripartita = ROOT / cfg["salidas"]["dir"] / "metricas_tripartita.json"
    if not ruta_tripartita.exists():
        raise FileNotFoundError(f"No existe {ruta_tripartita}; ejecute sin --solo-consolidar")
    res = json.loads(ruta_tripartita.read_text(encoding="utf-8"))

    if res["llm_stats"].get("mock_mode", True):
        raise RuntimeError(
            "La corrida cargada está en modo mock; se aborta para no publicar métricas simuladas."
        )

    consumo = consumo_por_brazo(cfg, max_oraciones)

    brazos = {}
    for brazo, datos in res["brazos"].items():
        entrada = {
            "roc_auc": datos["oracion"]["roc_auc"],
            "roc_auc_ci95": datos["oracion"]["roc_auc_ci95"],
            "auprc": datos["oracion"]["auprc"],
            "auprc_ci95": datos["oracion"]["auprc_ci95"],
            "f1": datos["oracion"]["f1"],
            "precision": datos["oracion"]["precision"],
            "recall": datos["oracion"]["recall"],
            "accuracy": datos["oracion"]["accuracy"],
            "matriz_confusion": datos["oracion"]["matriz_confusion"],
            "localizacion_top1": datos["localizacion"]["localizacion_top1"],
            "latencia_ms_por_oracion": datos["latency_ms_per_oracion"],
        }
        if brazo == "tfidf":
            entrada.update(
                {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "costo_usd_total": 0.0,
                    "costo_usd_por_1000_oraciones": 0.0,
                    "estimacion_previa_usd_por_1000_oraciones": 0.0,
                }
            )
        else:
            c = consumo[brazo]
            entrada.update(
                {
                    "input_tokens": c["input_tokens"],
                    "output_tokens": c["output_tokens"],
                    "tokens_por_oracion": c["tokens_por_oracion"],
                    "costo_usd_total": c["costo_usd_total"],
                    "costo_usd_por_1000_oraciones": c["costo_usd_por_1000_oraciones"],
                    "estimacion_previa_usd_por_1000_oraciones": ESTIMACION_PREVIA_USD_1K[brazo],
                    "latencia_ms_p50": c["latencia_ms_p50"],
                    "latencia_ms_p95": c["latencia_ms_p95"],
                    "entradas_cache_encontradas": c["entradas_cache_encontradas"],
                }
            )
        brazos[brazo] = entrada

    return {
        "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "comando": comando,
        "dataset": "MEDEC-MS (público, sin datos de pacientes reales)",
        "split": res["split"],
        "n_oraciones": res["n_oraciones"],
        "modelo_llm": cfg["llm"]["model"],
        "temperatura": cfg["llm"]["temperature"],
        "mock": False,
        "tarifas_usd_por_1m_tokens": {
            "input": cfg["llm"]["cost_input_per_1m"],
            "output": cfg["llm"]["cost_output_per_1m"],
        },
        "brazos": brazos,
        "mcnemar": res["mcnemar"],
        "llm_stats_corrida": res["llm_stats"],
        "comparacion_mock": comparar_con_mock(res["brazos"]),
        "sesgo_idioma_llm_real": cargar_sesgo_idioma(cfg),
        "notas": [
            "llm_stats_corrida solo contabiliza las llamadas que salieron a la API en esta "
            "ejecución; el consumo por brazo se reconstruye desde el cache de prompts y cubre "
            "las n oraciones evaluadas.",
            "Las latencias LLM son las medidas en la llamada original a la API, no las de "
            "lectura de cache.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="S11 — métricas con LLM real")
    parser.add_argument("--config", default="s7/config.yaml")
    parser.add_argument("--max-oraciones", type=int, default=400)
    parser.add_argument("--out", default=str(SALIDA_DEFAULT))
    parser.add_argument(
        "--solo-consolidar",
        action="store_true",
        help="Reusa la última corrida de s7/eval_tripartita.py sin volver a llamar a la API",
    )
    args = parser.parse_args()

    cfg = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8"))

    if not args.solo_consolidar:
        correr_eval_tripartita(args.config, args.max_oraciones)

    comando = f"python s11/eval_llm_real.py --max-oraciones {args.max_oraciones}"
    export = construir_export(cfg, args.max_oraciones, comando)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")

    for brazo, datos in export["brazos"].items():
        print(
            f"[{brazo}] ROC-AUC={datos['roc_auc']} AUPRC={datos['auprc']} "
            f"lat={datos['latencia_ms_por_oracion']} ms "
            f"costo/1k={datos['costo_usd_por_1000_oraciones']} USD"
        )
    print(f"\n[ok] -> {out}")


if __name__ == "__main__":
    main()
