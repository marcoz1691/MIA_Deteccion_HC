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
  loading,
  canAnalyze,
  backendOk,
  onAnalizar,
}) {
  const chars = nota.trim().length;

  return (
    <section className="card" aria-labelledby="nota-title">
      <div className="card-head">
        <p className="eyebrow">Nota</p>
        <h2 id="nota-title">Historia clínica</h2>
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

      <label htmlFor="nota">Texto de la historia</label>
      <textarea
        id="nota"
        value={nota}
        onChange={(e) => onNotaChange(e.target.value)}
        placeholder="Pega aquí una historia clínica odontológica…"
        rows={9}
        disabled={loading}
      />
      <div className="meta-row">
        <span>{chars} caracteres</span>
        <span>{mockLlm ? "Mock LLM · local" : "LLM real · API key"}</span>
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
          <label className="inline checkbox">
            <input
              type="checkbox"
              checked={mockLlm}
              onChange={(e) => onMockLlmChange(e.target.checked)}
              disabled={loading}
            />
            Mock LLM (sin API key)
          </label>
        </div>
      </details>

      <button
        type="button"
        className="cta"
        onClick={onAnalizar}
        disabled={loading || !canAnalyze || !backendOk}
      >
        {loading ? "Analizando oraciones…" : "Analizar nota"}
      </button>
      {!backendOk && (
        <p className="hint warn-text">Arranca FastAPI en el puerto 8000 para habilitar el análisis.</p>
      )}
    </section>
  );
}
