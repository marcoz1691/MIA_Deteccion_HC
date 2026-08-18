function fmt(score) {
  return score == null ? "—" : Number(score).toFixed(2);
}

function ScoreBar({ value, umbral = 0.5 }) {
  const pct = Math.max(0, Math.min(100, (value ?? 0) * 100));
  const tone = value >= umbral ? "danger" : "ok";
  return (
    <div className="scorebar" aria-hidden="true">
      <div className={`scorebar-fill ${tone}`} style={{ width: `${pct}%` }} />
      <span className="scorebar-mark" style={{ left: `${umbral * 100}%` }} />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <p>El sistema localiza la oración sospechosa. No es un veredicto clínico.</p>
      <ol className="empty-steps">
        <li>
          <b>01</b> Elige un ejemplo o pega una nota clínica.
        </li>
        <li>
          <b>02</b> Pulsa Analizar nota para ejecutar TF-IDF, LLM y RAG.
        </li>
        <li>
          <b>03</b> Revisa la oración marcada. Un médico debe validar el hallazgo.
        </li>
      </ol>
    </div>
  );
}

export default function ResultadosPanel({ resultado, error, loading }) {
  return (
    <section className="card" aria-labelledby="result-title" aria-live="polite">
      <div className="card-head">
        <p className="eyebrow">Hallazgo</p>
        <h2 id="result-title">Revisión asistida</h2>
        <p className="hint">Se señala la oración a revisar. La decisión sigue siendo clínica.</p>
      </div>

      {loading && (
        <div className="loading">
          <div className="spinner" aria-hidden="true" />
          <div>
            <p className="loading-title">Analizando nota…</p>
            <p className="hint">La primera vez con RAG puede tardar unos 15 segundos.</p>
          </div>
        </div>
      )}

      {!loading && error && (
        <div className="banner error" role="alert">
          <strong>No se pudo completar el análisis.</strong>
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && !resultado && <EmptyState />}

      {!loading && !error && resultado && <ResultadoBody resultado={resultado} />}
    </section>
  );
}

function ResultadoBody({ resultado }) {
  const { top1, oraciones, truncado, n_total, modo_degradado, mensaje_fallback } = resultado;
  const alerta = Boolean(top1?.alerta);

  return (
    <>
      {truncado && (
        <div className="banner warn">
          La nota tiene {n_total} oraciones; se analizaron las primeras {oraciones.length}.
        </div>
      )}
      {modo_degradado && (
        <div className="banner warn">{mensaje_fallback || "Modo degradado: solo TF-IDF."}</div>
      )}

      {top1 ? (
        <div className={`verdict ${alerta ? "alert" : "ok"}`}>
          <p className="verdict-kicker">{alerta ? "Requiere revisión" : "Sin alerta clara"}</p>
          <p className="verdict-title">
            {alerta
              ? `Revisar oración ${top1.sid + 1}`
              : "Ninguna oración supera el umbral de 0.50"}
          </p>
          <ScoreBar value={top1.score_localizacion} />
          <p className="hint">
            Score de localización {fmt(top1.score_localizacion)} · umbral 0.50
          </p>
        </div>
      ) : (
        <div className="banner warn">No se detectaron oraciones. Escribe frases separadas por puntos.</div>
      )}

      {top1 && (
        <article className={`sentence ${alerta ? "alert" : ""}`}>
          <header>
            <span>Oración {top1.sid + 1}</span>
            <span className={`pill ${alerta ? "danger" : "ok"}`}>
              {alerta ? "Sospechosa" : "Bajo umbral"}
            </span>
          </header>
          <p>{top1.oracion}</p>
        </article>
      )}

      <div className="metrics">
        <div>
          <span>Oraciones</span>
          <strong>{oraciones.length}</strong>
        </div>
        <div>
          <span>Score top-1</span>
          <strong>{top1 ? fmt(top1.score_localizacion) : "—"}</strong>
        </div>
        <div>
          <span>Modo</span>
          <strong>{modo_degradado ? "Degradado" : "Normal"}</strong>
        </div>
      </div>

      <h3 className="table-title">Detalle por oración</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Oración</th>
              <th>TF-IDF</th>
              <th>LLM</th>
              <th>RAG</th>
              <th>Loc.</th>
            </tr>
          </thead>
          <tbody>
            {oraciones.map((o) => (
              <tr key={o.sid} className={o.alerta ? "row-alert" : ""}>
                <td>{o.sid + 1}</td>
                <td>{o.oracion}</td>
                <td>{fmt(o.score_tfidf)}</td>
                <td>{fmt(o.score_llm_zero)}</td>
                <td>{fmt(o.score_llm_rag)}</td>
                <td>
                  <strong>{fmt(o.score_localizacion)}</strong>
                  {o.alerta ? " · alerta" : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
