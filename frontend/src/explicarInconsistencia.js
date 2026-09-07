const UMBRAL = 0.5;

const EJES_MVP = [
  {
    id: "lateralidad",
    label: "lateralidad",
    pattern:
      /\b(derech[oa]|izquierd[oa]|bilateral|unilateral|lateral|od\b|oi\b|o\.?\s*d\.?|o\.?\s*i\.?)\b/i,
  },
  {
    id: "sexo",
    label: "sexo o género",
    pattern:
      /\b(masculin[oa]|femenin[oa]|var[oó]n|mujer|embaraz|gestante|vasectom|ginecol|obstetr)/i,
  },
  {
    id: "alergias",
    label: "alergias",
    pattern: /\b(alergi|antial[eé]rg|hipersensib|anafilax)/i,
  },
  {
    id: "edad",
    label: "edad",
    pattern: /\b(\d+\s*a[nñ]os?|\d+\s*meses?|neonat|reci[eé]n\s*nac|pedi[aá]tr|geriatr|a[nñ]os?\s*de\s*edad)/i,
  },
];

export function detectarEjeMvp(oracion) {
  const texto = String(oracion ?? "");
  for (const eje of EJES_MVP) {
    if (eje.pattern.test(texto)) {
      return eje.label;
    }
  }
  return null;
}

function brazoLocalizacion(o, brazosEfectivos = ["tfidf", "llm_zero", "llm_rag"]) {
  const brazos = brazosEfectivos ?? ["tfidf", "llm_zero", "llm_rag"];
  const tf = brazos.includes("tfidf") ? o.score_tfidf : null;
  let llm = null;
  let llmName = null;
  if (brazos.includes("llm_rag") && o.score_llm_rag != null) {
    llm = o.score_llm_rag;
    llmName = "LLM + RAG";
  } else if (brazos.includes("llm_zero") && o.score_llm_zero != null) {
    llm = o.score_llm_zero;
    llmName = "LLM zero-shot";
  }
  if (llm != null && tf != null) {
    return llm >= tf ? llmName : "TF-IDF";
  }
  if (tf != null) return "TF-IDF";
  return llmName;
}

export function explicarInconsistencia(o, brazosEfectivos = ["tfidf", "llm_zero", "llm_rag"]) {
  const brazos = brazosEfectivos ?? ["tfidf", "llm_zero", "llm_rag"];
  const partes = [];
  const eje = detectarEjeMvp(o.oracion);
  const ejeTexto = eje ? ` de ${eje}` : " (lateralidad, sexo, alergias o edad)";

  const llmRag = brazos.includes("llm_rag") ? o.score_llm_rag : null;
  const llmZero = brazos.includes("llm_zero") ? o.score_llm_zero : null;
  const tfidf = brazos.includes("tfidf") ? o.score_tfidf : null;

  const llmAlto =
    (llmRag != null && llmRag >= UMBRAL) || (llmZero != null && llmZero >= UMBRAL);
  const tfidfAlto = tfidf != null && tfidf >= UMBRAL;

  if (llmAlto) {
    partes.push(`El modelo clínico sugiere revisar posible inconsistencia${ejeTexto}.`);
  }
  if (tfidfAlto) {
    partes.push(
      "El comparador estadístico detectó un patrón atípico respecto al resto del expediente.",
    );
  }
  if (!partes.length) {
    const dominante = brazoLocalizacion(o, brazos);
    if (dominante?.startsWith("LLM")) {
      partes.push(
        `La puntuación combinada supera el umbral de revisión (0,50); el ${dominante} la marcó como prioritaria.`,
      );
    } else if (dominante === "TF-IDF") {
      partes.push(
        "La puntuación combinada supera el umbral de revisión (0,50); el comparador estadístico la marcó como prioritaria.",
      );
    } else {
      partes.push("La puntuación combinada supera el umbral de revisión (0,50).");
    }
  }
  return partes.join(" ");
}
