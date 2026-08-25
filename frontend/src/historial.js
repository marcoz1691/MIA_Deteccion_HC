/** Utilidades de presentación del historial (datos en SQLite vía API). */

export function mapHistorialItem(item) {
  return {
    id: item.id,
    ts: item.created_at,
    nota: item.nota,
    resultado: item.resultado,
    ejemploId: item.ejemplo_id ?? "propia",
    idioma: item.idioma ?? "spanish",
    mockLlm: Boolean(item.mock_llm),
    alerta: Boolean(item.alerta),
  };
}

export function mapHistorialList(payload) {
  return (payload?.items ?? []).map(mapHistorialItem);
}

export function previewNota(texto, max = 72) {
  const t = String(texto).replace(/\s+/g, " ").trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

export function formatHistorialFecha(iso) {
  try {
    return new Intl.DateTimeFormat("es-EC", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}
