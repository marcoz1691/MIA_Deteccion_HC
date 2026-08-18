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
  mockLlm = true,
  idioma = "spanish",
  brazos = ["tfidf", "llm_zero", "llm_rag"],
  umbral = 0.5,
}) {
  const res = await fetch(`${API_BASE}/generar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      nota_clinica: nota,
      mock_llm: mockLlm,
      idioma,
      brazos,
      umbral,
    }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}
