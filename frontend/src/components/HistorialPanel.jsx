import { formatHistorialFecha, previewNota } from "../historial";

export default function HistorialPanel({ items, activeId, error, onSelect, onRemove, onClear }) {
  return (
    <section className="card historial" aria-labelledby="historial-title">
      <div className="card-head historial-head">
        <div>
          <p className="eyebrow">Persistencia</p>
          <h2 id="historial-title">Historial de análisis</h2>
          <p className="hint">
            Últimos análisis guardados en SQLite en el servidor ({items.length} visibles).
          </p>
        </div>
        {items.length > 0 && (
          <button type="button" className="ghost-btn" onClick={onClear}>
            Vaciar
          </button>
        )}
      </div>

      {error && (
        <div className="banner error" role="alert">
          <p>{error}</p>
        </div>
      )}

      {items.length === 0 ? (
        <p className="hint historial-empty">
          Aún no hay análisis guardados. Al pulsar Analizar nota, el resultado aparecerá aquí.
        </p>
      ) : (
        <ul className="historial-list">
          {items.map((item) => {
            const alerta = Boolean(item.resultado?.top1?.alerta);
            const active = item.id === activeId;
            return (
              <li key={item.id} className={active ? "active" : ""}>
                <button type="button" className="historial-item" onClick={() => onSelect(item)}>
                  <span className="historial-meta">
                    <time dateTime={item.ts}>{formatHistorialFecha(item.ts)}</time>
                    <span className={`pill ${alerta ? "danger" : "ok"}`}>
                      {alerta ? "Alerta" : "Sin alerta"}
                    </span>
                  </span>
                  <span className="historial-preview">{previewNota(item.nota)}</span>
                  <span className="historial-sub">
                    {item.ejemploId === "propia" ? "Nota propia" : "Ejemplo"} ·{" "}
                    {item.mockLlm ? "Mock" : "LLM real"}
                  </span>
                </button>
                <button
                  type="button"
                  className="historial-remove"
                  aria-label="Eliminar del historial"
                  onClick={() => onRemove(item.id)}
                >
                  ×
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
