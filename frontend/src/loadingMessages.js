/** Mensajes de progreso mientras se analiza una historia clínica. */

const MOCK_MESSAGES = [
  {
    title: "Analizando historia clínica…",
    hint: "Modo demo: respuesta simulada en pocos segundos.",
  },
  {
    title: "Revisando frases de ejemplo…",
    hint: "No se consulta OpenAI; útil para probar la interfaz.",
  },
];

const REAL_MESSAGES = [
  {
    title: "Iniciando revisión del expediente…",
    hint: "Segmentando la nota en frases para evaluarlas una a una.",
  },
  {
    title: "Preparando referencias clínicas…",
    hint: "La primera vez puede armar el índice GPC (~30 s). Las siguientes cargas son más rápidas.",
  },
  {
    title: "Comparando con patrones conocidos…",
    hint: "TF-IDF busca frases con un perfil parecido a inconsistencias ya documentadas.",
  },
  {
    title: "Consultando modelos de lenguaje…",
    hint: "El LLM contrasta cada frase con lateralidad, sexo, alergias y edad en el resto de la nota.",
  },
  {
    title: "Aplicando guías clínicas (RAG)…",
    hint: "Se consultan fragmentos de GPC cuando aportan contexto al eje evaluado.",
  },
  {
    title: "Priorizando frases a revisar…",
    hint: "Se combinan los scores para resaltar las inconsistencias más probables.",
  },
  {
    title: "Todavía procesando…",
    hint: "PDFs extensos o notas con cientos de frases pueden tardar varios minutos. No cierre esta pestaña.",
  },
  {
    title: "Finalizando el análisis…",
    hint: "El tiempo depende del tamaño del expediente y del uso de la API. Espere un momento más.",
  },
];

const ROTATE_EVERY_S = 8;

export function getLoadingMessage(elapsed, mockLlm = true) {
  const messages = mockLlm ? MOCK_MESSAGES : REAL_MESSAGES;
  const index = Math.min(Math.floor(Math.max(0, elapsed) / ROTATE_EVERY_S), messages.length - 1);
  return messages[index];
}

export function getLoadingStep(elapsed, mockLlm = true) {
  const messages = mockLlm ? MOCK_MESSAGES : REAL_MESSAGES;
  const index = Math.min(Math.floor(Math.max(0, elapsed) / ROTATE_EVERY_S), messages.length - 1);
  return { current: index + 1, total: messages.length };
}
