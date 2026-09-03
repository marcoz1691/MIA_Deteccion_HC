import { useMemo, useState } from "react";

import { groupHistorialByDate, previewNota } from "../historial";

function SidebarIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <rect
        x="3.5"
        y="4.5"
        width="17"
        height="15"
        rx="2.2"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <path d="M9 4.5v15" fill="none" stroke="currentColor" strokeWidth="1.7" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path
        d="M12 5v14M5 12h14"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <path d="M16.2 16.2 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

export default function HistorialPanel({
  className = "",
  open = false,
  items,
  activeId,
  error,
  onToggle,
  onNew,
  onSelect,
  onRemove,
  onClear,
}) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) => previewNota(item.nota, 160).toLowerCase().includes(q));
  }, [items, query]);
  const groups = useMemo(() => groupHistorialByDate(filtered), [filtered]);

  return (
    <aside className={`historial-slot ${open ? "is-open" : ""} ${className}`.trim()}>
      <div className="historial-chrome">
        <button
          type="button"
          className="historial-toggle historial-icon-btn"
          aria-controls="historial-rail"
          aria-expanded={open}
          aria-label={open ? "Ocultar historial" : "Mostrar historial"}
          title={open ? "Ocultar historial" : "Mostrar historial"}
          onClick={onToggle}
        >
          <SidebarIcon />
        </button>
        {open ? (
          <button type="button" className="historial-new" onClick={onNew}>
            <PlusIcon />
            Nueva revisión
          </button>
        ) : (
          <button
            type="button"
            className="historial-icon-btn"
            onClick={onNew}
            aria-label="Nueva revisión"
            title="Nueva revisión"
          >
            <PlusIcon />
          </button>
        )}
      </div>

      {open && (
        <label className="historial-search">
          <span className="sr-only">Buscar en el historial</span>
          <SearchIcon />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar chats"
          />
        </label>
      )}

      <section
        id="historial-rail"
        className={`historial-rail ${open ? "is-open" : ""}`}
        aria-labelledby="historial-title"
      >
        <h2 id="historial-title" className="sr-only">
          Chat history
        </h2>

        {error && (
          <div className="banner error" role="alert">
            <p>{error}</p>
          </div>
        )}

        {open && items.length > 0 && (
          <div className="historial-section-head">
            <span>Chats</span>
            <button type="button" className="historial-clear-link" onClick={onClear}>
              Vaciar
            </button>
          </div>
        )}

        {open && filtered.length === 0 ? (
          <p className="hint historial-empty">
            {query.trim() ? "Sin coincidencias." : "Aún no hay chats. Analiza una historia para crear el primero."}
          </p>
        ) : null}

        {open &&
          groups.map((group) => (
            <div key={group.id} className="historial-group">
              <p className="historial-group-label">{group.label}</p>
              <ul className="historial-list">
                {group.items.map((item) => {
                  const alerta = Boolean(item.resultado?.top1?.alerta);
                  const active = item.id === activeId;
                  return (
                    <li key={item.id} className={active ? "active" : ""}>
                      <button
                        type="button"
                        className="historial-item"
                        onClick={() => onSelect(item)}
                      >
                        <span className="historial-preview">{previewNota(item.nota, 52)}</span>
                        <span className={`historial-dot ${alerta ? "danger" : "ok"}`} />
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
            </div>
          ))}
      </section>
    </aside>
  );
}
