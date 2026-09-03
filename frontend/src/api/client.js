const API_BASE = import.meta.env.VITE_API_URL ?? "";

async function parseError(res) {
  const payload = await res.json().catch(() => ({}));
  const detail = payload.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg ?? JSON.stringify(item)).join("; ");
  }
  return `Error ${res.status}`;
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function analizarNota({
  nota,
  mockLlm,
  idioma = "spanish",
  ejemploId = "propia",
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
  if (mockLlm !== undefined) {
    body.mock_llm = mockLlm;
  }

  const res = await fetch(`${API_BASE}/generar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchHistorial(limit = 10) {
  const res = await fetch(`${API_BASE}/historial?limit=${limit}`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function deleteHistorialItem(id) {
  const res = await fetch(`${API_BASE}/historial/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function clearHistorialApi() {
  const res = await fetch(`${API_BASE}/historial`, { method: "DELETE" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function listarMuestrasPdf() {
  const res = await fetch(`${API_BASE}/muestras-pdf`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

async function postPdf(path, { file, muestraId }) {
  let res;
  if (file) {
    const form = new FormData();
    form.append("archivo", file);
    res = await fetch(`${API_BASE}${path}`, { method: "POST", body: form });
  } else {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ muestra_id: muestraId }),
    });
  }
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function extraerPdf({ file, muestraId }) {
  return postPdf("/extraer-pdf", { file, muestraId });
}

export async function extraerPdfEstructurado({ file, muestraId }) {
  return postPdf("/extraer-pdf-estructurado", { file, muestraId });
}
