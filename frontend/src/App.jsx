import { useEffect, useState } from "react";

import {
  analizarNota,
  clearHistorialApi,
  deleteHistorialItem,
  fetchHistorial,
  healthCheck,
} from "./api/client";
import HeaderBrand from "./components/HeaderBrand";
import HistorialPanel from "./components/HistorialPanel";
import NotaInput from "./components/NotaInput";
import ResultadosPanel from "./components/ResultadosPanel";
import { EJEMPLOS } from "./ejemplos";
import { mapHistorialList } from "./historial";

async function loadHistorialFromApi() {
  const data = await fetchHistorial(10);
  return mapHistorialList(data);
}

export default function App() {
  const [ejemploId, setEjemploId] = useState("medicacion");
  const [nota, setNota] = useState(EJEMPLOS.find((e) => e.id === "medicacion").texto);
  const [idioma, setIdioma] = useState("spanish");
  const [mockLlm, setMockLlm] = useState(true);
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState(null);
  const [historial, setHistorial] = useState([]);
  const [historialActivoId, setHistorialActivoId] = useState(null);
  const [historialError, setHistorialError] = useState(null);
  const [historialRailOpen, setHistorialRailOpen] = useState(false);

  const isDev = import.meta.env.DEV;

  useEffect(() => {
    if (!isDev) return;
    healthCheck()
      .then(async (data) => {
        setHealth(data);
        if (data.mock_llm_forzado) {
          setMockLlm(data.mock_llm);
        } else if (data.llm_api_configurada) {
          setMockLlm(false);
        }
        try {
          const items = await loadHistorialFromApi();
          setHistorial(items);
          setHistorialError(null);
        } catch (exc) {
          const msg = exc.message || "No se pudo cargar el historial.";
          if (msg.toLowerCase().includes("not found") || data.historial_count == null) {
            setHistorialError(
              "El backend no expone /historial. Reinicia uvicorn en la rama feature/sqlite-historial."
            );
          } else {
            setHistorialError(msg);
          }
        }
      })
      .catch(() => setHealth({ status: "offline", modelo_tfidf_disponible: false }));
  }, [isDev]);

  function handleEjemploChange(id) {
    const ejemplo = EJEMPLOS.find((e) => e.id === id);
    setEjemploId(id);
    setNota(ejemplo?.texto ?? "");
    setResultado(null);
    setError(null);
    setHistorialActivoId(null);
  }

  async function refreshHistorial(activeId = null) {
    try {
      const items = await loadHistorialFromApi();
      setHistorial(items);
      setHistorialError(null);
      if (activeId) setHistorialActivoId(activeId);
    } catch (exc) {
      const msg = exc.message || "No se pudo cargar el historial.";
      if (msg.toLowerCase().includes("not found")) {
        setHistorialError(
          "El backend no expone /historial. Reinicia uvicorn en la rama feature/sqlite-historial."
        );
      } else {
        setHistorialError(msg);
      }
    }
  }

  async function handleAnalizar() {
    const texto = nota.trim();
    if (!texto) {
      setError("Ingresa una nota clínica o selecciona un ejemplo.");
      setResultado(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await analizarNota({
        nota: texto,
        mockLlm: isDev ? mockLlm : undefined,
        idioma,
        ejemploId,
      });
      setResultado(data);
      setLoading(false);
      void refreshHistorial(data.historial_id ?? null);
    } catch (exc) {
      setResultado(null);
      setError(exc.message || "No se pudo analizar la nota.");
    } finally {
      setLoading(false);
    }
  }

  function handleHistorialSelect(item) {
    setNota(item.nota);
    setEjemploId(item.ejemploId ?? "propia");
    setIdioma(item.idioma ?? "spanish");
    if (isDev) setMockLlm(Boolean(item.mockLlm));
    setResultado(item.resultado);
    setError(null);
    setHistorialActivoId(item.id);
  }

  async function handleHistorialRemove(id) {
    try {
      await deleteHistorialItem(id);
      if (historialActivoId === id) {
        setHistorialActivoId(null);
      }
      await refreshHistorial();
    } catch (exc) {
      setHistorialError(exc.message || "No se pudo eliminar el análisis.");
    }
  }

  async function handleHistorialClear() {
    try {
      await clearHistorialApi();
      setHistorial([]);
      setHistorialActivoId(null);
      setHistorialError(null);
    } catch (exc) {
      setHistorialError(exc.message || "No se pudo vaciar el historial.");
    }
  }

  const backendOk = isDev ? health?.status === "ok" : true;
  const healthReady = !isDev || health !== null;

  return (
    <div className="app">
      <HeaderBrand
        isDev={isDev}
        backendOk={backendOk}
        healthReady={healthReady}
        health={health}
      />

      <div className="shell shell-workspace">
        <button
          type="button"
          className="ghost-btn historial-toggle"
          aria-controls="historial-rail"
          aria-expanded={historialRailOpen}
          onClick={() => setHistorialRailOpen((open) => !open)}
        >
          {historialRailOpen ? "Ocultar historial" : "Mostrar historial"}
        </button>
        <HistorialPanel
          className={`historial-rail ${historialRailOpen ? "is-open" : ""}`}
          items={historial}
          activeId={historialActivoId}
          error={historialError}
          onSelect={handleHistorialSelect}
          onRemove={handleHistorialRemove}
          onClear={handleHistorialClear}
        />

        <main className="workspace">
          <NotaInput
            nota={nota}
            onNotaChange={(value) => {
              setNota(value);
              setEjemploId("propia");
            }}
            ejemploId={ejemploId}
            onEjemploChange={handleEjemploChange}
            idioma={idioma}
            onIdiomaChange={setIdioma}
            mockLlm={mockLlm}
            onMockLlmChange={setMockLlm}
            showMockOption={isDev}
            mockLlmForced={Boolean(health?.mock_llm_forzado)}
            loading={loading}
            canAnalyze={Boolean(nota.trim()) && healthReady}
            backendOk={backendOk && healthReady}
            showBackendHint={isDev}
            onAnalizar={handleAnalizar}
          />
          <ResultadosPanel
            resultado={resultado}
            error={error}
            loading={loading}
            mockLlm={mockLlm}
          />
        </main>
      </div>
    </div>
  );
}
