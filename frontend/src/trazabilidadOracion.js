const UMBRAL = 0.5;

function fmtScore(score) {
  return score == null ? "—" : Number(score).toFixed(2);
}

export function fmtFuenteGpc(fuente) {
  return String(fuente ?? "desconocida")
    .replace(/^gpc_/, "")
    .replace(/\.txt$/i, "")
    .replace(/_/g, " ");
}

function brazoLocalizacion(o, brazosEfectivos) {
  if (o.brazo_localizacion) return o.brazo_localizacion;
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

/**
 * Construye el tracking de fuentes y argumentos que explican por qué se marcó la frase.
 */
export function construirTrazabilidad(o, brazosEfectivos = ["tfidf", "llm_zero", "llm_rag"]) {
  const brazos = brazosEfectivos ?? ["tfidf", "llm_zero", "llm_rag"];
  const items = [];
  const dominante = brazoLocalizacion(o, brazos);

  if (dominante) {
    items.push({
      id: "senal",
      titulo: "Señal principal",
      texto: `${dominante} aportó el score de localización (${fmtScore(o.score_localizacion)}).`,
    });
  }

  if (brazos.includes("tfidf") && o.score_tfidf != null) {
    items.push({
      id: "tfidf",
      titulo: "TF-IDF (comparador estadístico)",
      texto: `Score ${fmtScore(o.score_tfidf)}${o.score_tfidf >= UMBRAL ? " · supera umbral" : ""}.`,
      detalle:
        "Patrones aprendidos del corpus MEDEC (modelo en salidas_ajuste/). Compara la frase con historias donde ya se conocían inconsistencias.",
    });
  }

  if (brazos.includes("llm_zero") && o.respuesta_llm_zero != null) {
    items.push({
      id: "llm-zero",
      titulo: "LLM zero-shot",
      texto: `Respuesta del modelo: «${o.respuesta_llm_zero.trim()}» (score ${fmtScore(o.score_llm_zero)}).`,
      detalle:
        "El modelo leyó esta frase en el contexto de toda la nota clínica y evaluó posibles contradicciones (lateralidad, sexo, alergias, edad).",
    });
  }

  if (brazos.includes("llm_rag") && o.respuesta_llm_rag != null) {
    items.push({
      id: "llm-rag",
      titulo: "LLM + RAG (guías clínicas)",
      texto: `Respuesta del modelo: «${o.respuesta_llm_rag.trim()}» (score ${fmtScore(o.score_llm_rag)}).`,
      detalle:
        "Igual que LLM zero-shot, pero consultando fragmentos de Guías de Práctica Clínica (GPC) recuperados por similitud semántica.",
    });
  }

  if (o.rag_fuentes?.length) {
    o.rag_fuentes.forEach((f, i) => {
      items.push({
        id: `gpc-${i}`,
        titulo: `GPC: ${fmtFuenteGpc(f.fuente)}`,
        texto: f.extracto,
        detalle: `Archivo: ${f.fuente}`,
      });
    });
  }

  return items;
}
