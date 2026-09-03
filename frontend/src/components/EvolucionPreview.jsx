const MOTOR_LABEL = {
  vision: "Visión (modelo multimodal)",
  ocr: "OCR local",
  capa_texto: "Capa de texto del PDF",
};

export default function EvolucionPreview({ entries = [], motor, aviso, paginasSinContenido = [] }) {
  if (!entries.length) return null;

  return (
    <div className="evol-preview" aria-label="Evoluciones extraídas del PDF">
      <div className="evol-preview-head">
        <span className="evol-motor">{MOTOR_LABEL[motor] ?? motor}</span>
        <span className="evol-count">
          {entries.length} evolución{entries.length === 1 ? "" : "es"}
        </span>
      </div>
      {aviso && <p className="hint pdf-aviso">{aviso}</p>}
      {paginasSinContenido.length > 0 && (
        <p className="hint">
          Páginas sin contenido clínico: {paginasSinContenido.join(", ")}.
        </p>
      )}
      <ol className="evol-list">
        {entries.map((e) => (
          <li key={e.evolucion_n} className="evol-item">
            <div className="evol-item-head">
              <strong>Evolución {e.evolucion_n}</strong>
              <span>
                {e.fecha ?? "fecha ilegible"}
                {e.hora ? ` · ${e.hora}` : ""}
              </span>
            </div>
            <p className="evol-label">Notas de evolución</p>
            <pre className="evol-notas">{e.notas_evolucion || "[ilegible]"}</pre>
            <p className="evol-label">Órdenes médicas generales</p>
            {e.ordenes_medicas?.length ? (
              <ul className="evol-ordenes">
                {e.ordenes_medicas.map((o, i) => (
                  <li key={i}>{o}</li>
                ))}
              </ul>
            ) : (
              <p className="hint">(sin órdenes en esta nota)</p>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
