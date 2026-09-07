const API_BASE = import.meta.env?.VITE_API_URL ?? "";

export function mensajeErrorRed(exc) {
  const msg = String(exc?.message || exc || "");
  if (/failed to fetch|networkerror|load failed|network request failed/i.test(msg)) {
    return (
      "No se pudo conectar con la API. El análisis se cortó (servidor recargado, " +
      "límite de OpenAI o espera larga). Espere unos segundos y vuelva a pulsar Analizar."
    );
  }
  return msg || "No se pudo completar la petición.";
}

async function parseError(res) {
  const payload = await res.json().catch(() => ({}));
  const detail = payload.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg ?? JSON.stringify(item)).join("; ");
  }
  return `Error ${res.status}`;
}

async function apiFetch(url, init) {
  let res;
  try {
    res = await fetch(url, init);
  } catch (exc) {
    throw new Error(mensajeErrorRed(exc));
  }
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function healthCheck({ retries = 0, delayMs = 600 } = {}) {
  let last;
  const attempts = Math.max(0, retries) + 1;
  for (let i = 0; i < attempts; i += 1) {
    try {
      return await apiFetch(`${API_BASE}/health`);
    } catch (exc) {
      last = exc;
      if (i + 1 < attempts) {
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
    }
  }
  throw last;
}

export async function analizarNota({
  nota,
  mockLlm,
  idioma = "spanish",
  ejemploId = "propia",
  pdfOrigen = null,
  pdfMuestraId = null,
  brazos = ["tfidf", "llm_zero", "llm_rag"],
  umbral = 0.5,
  guardarHistorial = true,
}) {
  const body = {
    nota_clinica: nota,
    idioma,
    brazos,
    umbral,
    ejemplo_id: ejemploId,
    guardar_historial: guardarHistorial,
  };
  if (pdfOrigen) {
    body.pdf_origen = pdfOrigen;
  }
  if (pdfMuestraId) {
    body.pdf_muestra_id = pdfMuestraId;
  }
  if (mockLlm !== undefined) {
    body.mock_llm = mockLlm;
  }

  return apiFetch(`${API_BASE}/generar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function fetchHistorial(limit = 10) {
  return apiFetch(`${API_BASE}/historial?limit=${limit}`);
}

export async function deleteHistorialItem(id) {
  return apiFetch(`${API_BASE}/historial/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export async function clearHistorialApi() {
  return apiFetch(`${API_BASE}/historial`, { method: "DELETE" });
}

export async function listarMuestrasPdf() {
  return apiFetch(`${API_BASE}/muestras-pdf`);
}

async function postPdf(path, { file, muestraId }) {
  if (file) {
    const form = new FormData();
    form.append("archivo", file);
    return apiFetch(`${API_BASE}${path}`, { method: "POST", body: form });
  }
  return apiFetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ muestra_id: muestraId }),
  });
}

export async function extraerPdf({ file, muestraId }) {
  return postPdf("/extraer-pdf", { file, muestraId });
}

export async function extraerPdfEstructurado({ file, muestraId }) {
  return postPdf("/extraer-pdf-estructurado", { file, muestraId });
}
