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
  muestrasPdf = [],
  pdfAviso = null,
  pdfError = null,
  pdfCargado = null,
  pdfExtrayendo = false,
  onPdfFile,
  onPdfMuestra,
  onPdfQuitar,
  pdfResumen = null,
  evolucionPreview = null,
}) {
  const chars = nota.trim().length;
  const casoActivo = EJEMPLOS.find((ej) => ej.id === ejemploId);
  const pdfActivo = pdfExtrayendo || Boolean(pdfCargado) || ejemploId === "pdf";

  return (
    <section className="card intake-card" aria-labelledby="nota-title" aria-busy={loading}>
      <div className="card-head">
        <p className="eyebrow">Historia clínica</p>
        <h2 id="nota-title">Revise el expediente ahora</h2>
        <p className="hint">Elija un caso o pegue el expediente. Luego analice.</p>
      </div>

      <div className="intake-split">
        <aside className="intake-origen">
          <p className="field-label">Casos de demostración</p>
          <div className="case-list" role="listbox" aria-label="Origen del expediente">
            {EJEMPLOS.map((ej) => {
              const active = !pdfActivo && ejemploId === ej.id;
              return (
                <button
                  key={ej.id}
                  type="button"
                  role="option"
                  aria-selected={active}
                  className={`case-card ${active ? "active" : ""}`}
                  onClick={() => onEjemploChange(ej.id)}
                  disabled={loading}
                >
                  <span className="case-kicker">{ej.etiqueta}</span>
                  <span className="case-title">{ej.titulo}</span>
                  <span className="case-resumen">{ej.resumen}</span>
                </button>
              );
            })}
          </div>

          <div className={`intake-pdf ${pdfActivo ? "is-active" : ""}`}>
            <p className="field-label">Documento PDF</p>
            <p className="hint">
              Opcional. Solo <strong>NOTAS DE EVOLUCIÓN</strong> y{" "}
              <strong>ORDENES MEDICAS GENERALES</strong>.
            </p>
            <div className="pdf-fuente">
              <label className="chip pdf-file-chip">
                <input
                  type="file"
                  accept="application/pdf,.pdf"
                  disabled={loading || pdfExtrayendo || !onPdfFile}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    e.target.value = "";
                    if (file && onPdfFile) onPdfFile(file);
                  }}
                />
                {pdfExtrayendo ? "Extrayendo…" : pdfCargado ? "Cambiar PDF" : "Cargar PDF"}
              </label>
              {pdfCargado && (
                <span className="pdf-loaded" title={pdfCargado.nombre}>
                  <span className="pdf-loaded-name">{pdfCargado.nombre}</span>
                  <button
                    type="button"
                    className="pdf-loaded-clear"
                    aria-label={`Quitar ${pdfCargado.nombre}`}
                    onClick={onPdfQuitar}
                    disabled={loading || pdfExtrayendo}
                  >
                    ×
                  </button>
                </span>
              )}
            </div>
            {!pdfCargado && muestrasPdf.length > 0 && (
              <details className="pdf-muestras">
                <summary>Muestras anonimizadas de demostración</summary>
                <div className="chips" role="group" aria-label="Muestras anonimizadas locales">
                  {muestrasPdf.map((muestra) => (
                    <button
                      key={muestra.id}
                      type="button"
                      className="chip chip-quiet"
                      onClick={() => onPdfMuestra?.(muestra.id)}
                      disabled={loading || pdfExtrayendo}
                    >
                      {muestra.nombre}
                      {muestra.carpeta === "salidas_buscable" ? " · buscable" : ""}
                    </button>
                  ))}
                </div>
              </details>
            )}
            {pdfError && (
              <p className="hint warn-text" role="alert">
                {pdfError}
              </p>
            )}
            {pdfAviso && <p className="hint pdf-aviso">{pdfAviso}</p>}
            {pdfResumen && evolucionPreview && (
              <details className="evol-preview-wrap">
                <summary>{pdfResumen}</summary>
                {evolucionPreview}
              </details>
            )}
          </div>
        </aside>

        <div className="intake-expediente">
          <label htmlFor="nota">
            {pdfExtrayendo
              ? "Extrayendo historia clínica"
              : ejemploId === "pdf"
                ? "Historia clínica extraída"
                : casoActivo
                  ? casoActivo.titulo
                  : "Historia clínica"}
          </label>
          <p className="hint">
            Contrasta <strong>lateralidad</strong>, <strong>sexo</strong>,{" "}
            <strong>alergias</strong>, <strong>medicamentos</strong> y{" "}
            <strong>edad</strong>. El umbral 0.50 usa TF-IDF + LLM.
          </p>
          <div className="expediente-editor">
            {pdfExtrayendo && (
              <div className="expediente-extracting" role="status">
                <div className="spinner" aria-hidden="true" />
                <p>Extrayendo el PDF. El texto aparecerá aquí.</p>
              </div>
            )}
            <textarea
              id="nota"
              className="nota-textarea"
              value={nota}
              onChange={(e) => onNotaChange(e.target.value)}
              placeholder="Pegue aquí la evolución, las prescripciones y el plan. O elija un caso a la izquierda."
              rows={12}
              disabled={loading}
            />
          </div>
          <div className="meta-row">
            <span>{chars} caracteres</span>
            {showMockOption ? (
              <span>{mockLlm ? "Mock LLM · local" : "LLM real · API key"}</span>
            ) : (
              <span>TF-IDF · LLM · RAG</span>
            )}
          </div>
        </div>
      </div>

      <div className="intake-sticky">
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
          {loading ? "Analizando historia clínica…" : "Analizar historia clínica"}
        </button>
        {showBackendHint && !backendOk && (
          <p className="hint warn-text">Arranca FastAPI en el puerto 8000 para habilitar el análisis.</p>
        )}
      </div>
    </section>
  );
}
