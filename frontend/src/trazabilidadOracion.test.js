import assert from "node:assert/strict";
import test from "node:test";

import { construirTrazabilidad, fmtFuenteGpc } from "./trazabilidadOracion.js";

test("fmtFuenteGpc humaniza nombres de archivo GPC", () => {
  assert.equal(fmtFuenteGpc("gpc_dolor_lumbar.txt"), "dolor lumbar");
});

test("construirTrazabilidad incluye señal, LLM y chunks GPC", () => {
  const o = {
    sid: 0,
    oracion: "Dolor en rodilla derecha.",
    score_tfidf: 0.42,
    score_llm_zero: 0.88,
    score_llm_rag: 0.91,
    score_localizacion: 0.78,
    brazo_localizacion: "LLM + RAG",
    respuesta_llm_zero: "SI",
    respuesta_llm_rag: "SI",
    rag_fuentes: [{ fuente: "gpc_dolor_lumbar.txt", extracto: "Evaluar lateralidad del dolor." }],
  };
  const items = construirTrazabilidad(o, ["tfidf", "llm_zero", "llm_rag"]);
  assert.ok(items.some((i) => i.id === "senal"));
  assert.ok(items.some((i) => i.id === "llm-zero" && i.texto.includes("SI")));
  assert.ok(items.some((i) => i.id === "gpc-0" && i.titulo.includes("dolor lumbar")));
});

test("construirTrazabilidad funciona bajo umbral 0.50", () => {
  const o = {
    sid: 2,
    oracion: "Paciente estable.",
    score_tfidf: 0.31,
    score_localizacion: 0.31,
    brazo_localizacion: "TF-IDF",
    alerta: false,
  };
  const items = construirTrazabilidad(o, ["tfidf"]);
  assert.ok(items.some((i) => i.id === "tfidf" && i.texto.includes("0.31")));
  assert.ok(!items.some((i) => i.texto.includes("supera umbral")));
});
