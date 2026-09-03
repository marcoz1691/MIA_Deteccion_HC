import { useEffect, useRef, useState } from "react";

import {
  createEggTracker,
  markThemeUnlocked,
  toggleTheme,
} from "../theme";
import ThemeToast from "./ThemeToast";

export default function HeaderBrand({
  isDev,
  backendOk,
  healthReady,
  health,
  onThemeChange,
}) {
  const eggRef = useRef(createEggTracker());
  const [toast, setToast] = useState("");

  useEffect(() => {
    if (!toast) return undefined;
    const id = window.setTimeout(() => setToast(""), 1800);
    return () => window.clearTimeout(id);
  }, [toast]);

  function announce(next) {
    setToast(next === "dark" ? "Modo oscuro" : "Modo claro");
    onThemeChange?.(next);
  }

  function handleMarkClick() {
    if (eggRef.current.registerClick()) {
      markThemeUnlocked();
      announce(toggleTheme());
    }
  }

  return (
    <>
      <header className="topbar">
        <div className="brand">
          <button
            type="button"
            className="mark-btn"
            aria-label="MIA CITIMED"
            onClick={handleMarkClick}
          >
            <span className="mark" aria-hidden="true" />
          </button>
          <div>
            <p className="brand-kicker">MIA · CITIMED</p>
            <h1>Consistencia de historias clínicas</h1>
          </div>
        </div>
        <div className="topbar-meta">
          <p className="lede disclaimer-inline">
            Localiza la frase que no cuadra. El criterio sigue siendo médico.
          </p>
          {isDev && (
            <div className={`status ${backendOk ? "ok" : "down"}`}>
              <span className="dot" />
              {backendOk
                ? `Backend listo${health?.modelo_tfidf_disponible ? " · TF-IDF" : ""}${health?.llm_api_configurada ? " · OpenAI" : ""}`
                : healthReady
                  ? "Backend no disponible"
                  : "Conectando…"}
            </div>
          )}
        </div>
      </header>
      <ThemeToast message={toast} />
    </>
  );
}
