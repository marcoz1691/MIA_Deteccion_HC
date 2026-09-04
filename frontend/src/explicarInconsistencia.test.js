import assert from "node:assert/strict";
import test from "node:test";

import { detectarEjeMvp, explicarInconsistencia } from "./explicarInconsistencia.js";

test("detectarEjeMvp reconoce lateralidad", () => {
  assert.equal(detectarEjeMvp("Fractura de pie derecho."), "lateralidad");
});

test("detectarEjeMvp reconoce sexo", () => {
  assert.equal(detectarEjeMvp("Paciente femenino de 45 años."), "sexo o género");
});

test("explicarInconsistencia combina LLM y TF-IDF altos", () => {
  const texto = explicarInconsistencia(
    {
      oracion: "Examen de pie izquierdo.",
      score_tfidf: 0.72,
      score_llm_zero: 0.81,
      score_llm_rag: null,
    },
    ["tfidf", "llm_zero"],
  );
  assert.match(texto, /modelo clínico/i);
  assert.match(texto, /comparador estadístico/i);
  assert.match(texto, /lateralidad/i);
});

test("explicarInconsistencia usa fallback de umbral", () => {
  const texto = explicarInconsistencia(
    {
      oracion: "Control ambulatorio.",
      score_tfidf: 0.4,
      score_llm_zero: 0.45,
      score_llm_rag: null,
      score_localizacion: 0.55,
    },
    ["tfidf", "llm_zero"],
  );
  assert.match(texto, /umbral de revisión/i);
});
