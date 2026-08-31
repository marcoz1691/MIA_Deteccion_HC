import { EJEMPLOS } from "../ejemplos";

export default function NotaInput({
  nota,
  onNotaChange,
  ejemploId,
  onEjemploChange,
  idioma,
  onIdiomaChange,
  mockLlm,
  onMockLlmChange,
  showMockOption = false,
  mockLlmForced = false,
  loading,
  canAnalyze,
  backendOk,
  showBackendHint = false,
  onAnalizar,
}) {
  const chars = nota.trim().length;

  return (
    <section className="card" aria-labelledby="nota-title" aria-busy={loading}>
      <div className="card-head">
        <p className="eyebrow">Nota</p>
        <h2 id="nota-title">Decisión médica</h2>
        <p className="hint">Elige un caso o pega el texto. El análisis corre en el backend.</p>
      </div>

      <p className="field-label">Casos de demostración</p>
      <div className="chips" role="group" aria-label="Ejemplos precargados">
        {EJEMPLOS.map((ej) => (
          <button
            key={ej.id}
            type="button"
            className={`chip ${ejemploId === ej.id ? "active" : ""}`}
            onClick={() => onEjemploChange(ej.id)}
            disabled={loading}
          >
            {ej.titulo}
          </button>
        ))}
      </div>

      <label htmlFor="nota">Texto de la nota</label>
      <textarea
        id="nota"
        className="nota-textarea"
        value={nota}
        onChange={(e) => onNotaChange(e.target.value)}
        placeholder="Pega aquí una nota médica odontológica…"
        rows={6}
        disabled={loading}
      />
      <div className="meta-row">
        <span>{chars} caracteres</span>
        {showMockOption ? (
          <span>{mockLlm ? "Mock LLM · local" : "LLM real · API key"}</span>
        ) : (
          <span>TF-IDF · LLM · RAG</span>
        )}
      </div>

      <details className="advanced">
        <summary>Opciones de análisis</summary>
        <div className="row">
          <label className="inline">
            Idioma
            <select
              value={idioma}
              onChange={(e) => onIdiomaChange(e.target.value)}
              disabled={loading}
            >
              <option value="spanish">Español</option>
              <option value="english">English</option>
            </select>
          </label>
          {showMockOption && (
            <label className="inline checkbox">
              <input
                type="checkbox"
                checked={mockLlm}
                onChange={(e) => onMockLlmChange(e.target.checked)}
                disabled={loading || mockLlmForced}
              />
              Mock LLM (sin API key)
            </label>
          )}
        </div>
        {showMockOption && mockLlmForced && (
          <p className="hint">Modo LLM fijado por el servidor (MOCK_LLM en el entorno).</p>
        )}
      </details>

      <button
        type="button"
        className="cta"
        onClick={onAnalizar}
        disabled={loading || !canAnalyze || !backendOk}
      >
        <span className="cta-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
            <path
              d="M12 3.5l1.2 4.2L17.5 9l-4.3 1.3L12 14.5l-1.2-4.2L6.5 9l4.3-1.3L12 3.5z"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinejoin="round"
            />
            <path
              d="M18.2 14.2l.7 2.3 2.3.7-2.3.7-.7 2.3-.7-2.3-2.3-.7 2.3-.7.7-2.3z"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinejoin="round"
            />
            <path
              d="M5.8 15.5l.45 1.5 1.5.45-1.5.45-.45 1.5-.45-1.5-1.5-.45 1.5-.45.45-1.5z"
              stroke="currentColor"
              strokeWidth="1.3"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        {loading ? "Analizando frases…" : "Analizar nota"}
      </button>
      {showBackendHint && !backendOk && (
        <p className="hint warn-text">Arranca FastAPI en el puerto 8000 para habilitar el análisis.</p>
      )}
    </section>
  );
}
