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
  brazos = ["tfidf", "llm_zero", "llm_rag"],
  umbral = 0.5,
}) {
  const body = {
    nota_clinica: nota,
    idioma,
    brazos,
    umbral,
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
