import { useEffect, useState } from "react";

import { analizarNota, healthCheck } from "./api/client";
import NotaInput from "./components/NotaInput";
import ResultadosPanel from "./components/ResultadosPanel";
import { EJEMPLOS } from "./ejemplos";

export default function App() {
  const [ejemploId, setEjemploId] = useState("medicacion");
  const [nota, setNota] = useState(EJEMPLOS.find((e) => e.id === "medicacion").texto);
  const [idioma, setIdioma] = useState("spanish");
  const [mockLlm, setMockLlm] = useState(true);
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState(null);

  const isDev = import.meta.env.DEV;

  useEffect(() => {
    if (!isDev) return;
    healthCheck()
      .then((data) => {
        setHealth(data);
        if (data.mock_llm_forzado) {
          setMockLlm(data.mock_llm);
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
      const data = await analizarNota({ nota: texto, mockLlm: isDev ? mockLlm : undefined, idioma });
      setResultado(data);
    } catch (exc) {
      setResultado(null);
      setError(exc.message || "No se pudo analizar la nota.");
    } finally {
      setLoading(false);
    }
  }

  // En producción el usuario ve una sola app; el estado del backend es interno (LB/K8s).
  const backendOk = isDev ? health?.status === "ok" : true;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="mark" aria-hidden="true" />
          <div>
            <p className="brand-kicker">MIA · CITIMED</p>
            <h1>Detección de inconsistencias</h1>
          </div>
        </div>
        <div className="topbar-meta">
          <p className="lede">Análisis por oración · TF-IDF · LLM · RAG</p>
          {isDev && (
            <div className={`status ${backendOk ? "ok" : "down"}`}>
              <span className="dot" />
              {backendOk
                ? `Backend listo${health.modelo_tfidf_disponible ? " · TF-IDF" : " · sin TF-IDF"}`
                : "Backend no disponible"}
            </div>
          )}
        </div>
      </header>

      <div className="shell">
        <p className="disclaimer">
          Prototipo de investigación. No sustituye el criterio clínico ni debe usarse para
          decisiones terapéuticas.
        </p>

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
            canAnalyze={Boolean(nota.trim())}
            backendOk={backendOk}
            showBackendHint={isDev}
            onAnalizar={handleAnalizar}
          />
          <ResultadosPanel resultado={resultado} error={error} loading={loading} />
        </main>
      </div>
    </div>
  );
}
