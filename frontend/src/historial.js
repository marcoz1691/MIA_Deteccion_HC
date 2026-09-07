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
    pdfOrigen: item.pdf_origen ?? null,
    pdfMuestraId: item.pdf_muestra_id ?? null,
  };
}

export function mapHistorialList(payload) {
  return (payload?.items ?? []).map(mapHistorialItem);
}

export function previewNota(texto, max = 108) {
  const t = String(texto)
    .replace(/---\s*EVOLUCI[OÓ]N\s+\d+\s*---/gi, " ")
    .replace(/FECHA:\s*\S+/gi, " ")
    .replace(/HORA:\s*\S+/gi, " ")
    .replace(/NOTAS DE EVOLUCI[OÓ]N:\s*/gi, " ")
    .replace(/ORDENES? MEDICAS? GENERALES:\s*/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
  const shown = t || "Historia clínica";
  if (shown.length <= max) return shown;
  return `${shown.slice(0, max - 1)}…`;
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

function startOfLocalDay(value) {
  const date = new Date(value);
  date.setHours(0, 0, 0, 0);
  return date.getTime();
}

export function groupHistorialByDate(items) {
  const today = startOfLocalDay(new Date());
  const yesterday = today - 86_400_000;
  const week = today - 7 * 86_400_000;
  const groups = [
    { id: "hoy", label: "Hoy", items: [] },
    { id: "ayer", label: "Ayer", items: [] },
    { id: "semana", label: "Últimos 7 días", items: [] },
    { id: "anteriores", label: "Anteriores", items: [] },
  ];
  for (const item of items) {
    const day = startOfLocalDay(item.ts);
    if (Number.isNaN(day)) {
      groups[3].items.push(item);
    } else if (day >= today) {
      groups[0].items.push(item);
    } else if (day >= yesterday) {
      groups[1].items.push(item);
    } else if (day >= week) {
      groups[2].items.push(item);
    } else {
      groups[3].items.push(item);
    }
  }
  return groups.filter((group) => group.items.length > 0);
}
