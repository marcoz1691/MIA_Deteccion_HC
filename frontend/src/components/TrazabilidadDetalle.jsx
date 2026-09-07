import { construirTrazabilidad } from "../trazabilidadOracion";

export default function TrazabilidadDetalle({
  oracion,
  brazosEfectivos,
  compact = false,
  label = "Ver trazabilidad",
}) {
  const items = construirTrazabilidad(oracion, brazosEfectivos);
  if (!items.length) {
    return <span className="hint">—</span>;
  }

  if (compact) {
    return (
      <details className="trazabilidad-details">
        <summary>{label}</summary>
        <TrazabilidadLista items={items} />
      </details>
    );
  }

  return (
    <div className="trazabilidad-block">
      <p className="trazabilidad-kicker">Trazabilidad</p>
      <TrazabilidadLista items={items} />
    </div>
  );
}

function TrazabilidadLista({ items }) {
  return (
    <ol className="trazabilidad-list">
      {items.map((item) => (
        <li key={item.id} className={`trazabilidad-item trazabilidad-${item.id}`}>
          <strong>{item.titulo}</strong>
          <p>{item.texto}</p>
          {item.detalle ? <p className="hint trazabilidad-detalle">{item.detalle}</p> : null}
        </li>
      ))}
    </ol>
  );
}
