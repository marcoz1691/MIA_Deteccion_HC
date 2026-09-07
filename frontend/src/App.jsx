import { useEffect, useState } from "react";

import {
  analizarNota,
  clearHistorialApi,
  deleteHistorialItem,
  extraerPdfEstructurado,
  fetchHistorial,
  healthCheck,
  listarMuestrasPdf,
} from "./api/client";
import EvolucionPreview from "./components/EvolucionPreview";
import HeaderBrand from "./components/HeaderBrand";
import HistorialPanel from "./components/HistorialPanel";
import NotaInput from "./components/NotaInput";
import ResultadosPanel from "./components/ResultadosPanel";
import { EJEMPLOS } from "./ejemplos";
import { mapHistorialList } from "./historial";

async function loadHistorialFromApi() {
  const data = await fetchHistorial(50);
  return mapHistorialList(data);
}

export default function App() {
  const [ejemploId, setEjemploId] = useState("propia");
  const [nota, setNota] = useState("");
  const [idioma, setIdioma] = useState("spanish");
  const [mockLlm, setMockLlm] = useState(true);
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState(null);
  const [historial, setHistorial] = useState([]);
  const [historialActivoId, setHistorialActivoId] = useState(null);
  const [historialError, setHistorialError] = useState(null);
  const [historialRailOpen, setHistorialRailOpen] = useState(true);
  const [muestrasPdf, setMuestrasPdf] = useState([]);
  const [pdfExtrayendo, setPdfExtrayendo] = useState(false);
  const [pdfAviso, setPdfAviso] = useState(null);
  const [pdfError, setPdfError] = useState(null);
  const [pdfCargado, setPdfCargado] = useState(null);
  const [evolucion, setEvolucion] = useState(null);

  const isDev = import.meta.env.DEV;

  useEffect(() => {
    if (!isDev) return;
    healthCheck({ retries: 3, delayMs: 700 })
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

  useEffect(() => {
    listarMuestrasPdf()
      .then((data) => setMuestrasPdf(data.muestras ?? []))
      .catch(() => setMuestrasPdf([]));
  }, []);

  function handleEjemploChange(id) {
    const ejemplo = EJEMPLOS.find((e) => e.id === id);
    setEjemploId(id);
    setNota(ejemplo?.texto ?? "");
    setResultado(null);
    setError(null);
    setHistorialActivoId(null);
    setPdfAviso(null);
    setPdfError(null);
    setPdfCargado(null);
    setEvolucion(null);
  }

  async function aplicarExtraccion(promesa, muestraId = null, nombreLocal = null) {
    setPdfExtrayendo(true);
    setEjemploId("pdf");
    setPdfError(null);
    setPdfAviso(null);
    setEvolucion(null);
    if (nombreLocal) {
      setPdfCargado({ nombre: nombreLocal, muestraId });
    }
    try {
      const data = await promesa;
      setNota(data.texto_plano ?? "");
      setEjemploId("pdf");
      setPdfCargado({
        nombre: data.origen || "documento.pdf",
        muestraId,
      });
      setEvolucion({
        entries: data.entries ?? [],
        motor: data.motor,
        aviso: data.aviso ?? null,
        paginasSinContenido: data.paginas_sin_contenido ?? [],
      });
      setResultado(null);
      setError(null);
      setHistorialActivoId(null);
    } catch (exc) {
      setPdfCargado(null);
      setEjemploId("propia");
      setPdfError(exc.message || "No se pudo extraer el texto del PDF.");
    } finally {
      setPdfExtrayendo(false);
    }
  }

  function handlePdfFile(file) {
    if (!file) return;
    void aplicarExtraccion(extraerPdfEstructurado({ file }), null, file.name);
  }

  function handlePdfMuestra(muestraId) {
    const muestra = muestrasPdf.find((item) => item.id === muestraId);
    void aplicarExtraccion(
      extraerPdfEstructurado({ muestraId }),
      muestraId,
      muestra?.nombre ?? "muestra.pdf",
    );
  }

  function handlePdfQuitar() {
    setPdfCargado(null);
    setPdfAviso(null);
    setPdfError(null);
    setEvolucion(null);
    setEjemploId("propia");
    setNota("");
    setResultado(null);
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
      setError("Ingresa el texto de la historia clínica o selecciona un caso de demostración.");
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
        pdfOrigen: pdfCargado?.nombre ?? null,
        pdfMuestraId: pdfCargado?.muestraId ?? null,
      });
      setResultado(data);
      setLoading(false);
      void refreshHistorial(data.historial_id ?? null);
    } catch (exc) {
      setResultado(null);
      setError(exc.message || "No se pudo analizar la historia clínica.");
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
    setPdfAviso(null);
    setPdfError(null);
    setEvolucion(null);
    if (item.pdfOrigen) {
      setPdfCargado({
        nombre: item.pdfOrigen,
        muestraId: item.pdfMuestraId ?? null,
        soloLectura: true,
      });
    } else if (item.ejemploId === "pdf") {
      setPdfCargado({
        nombre: "Expediente PDF (nombre no guardado)",
        muestraId: null,
        soloLectura: true,
      });
    } else {
      setPdfCargado(null);
    }
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

  function handleNuevaRevision() {
    setEjemploId("propia");
    setNota("");
    setResultado(null);
    setError(null);
    setHistorialActivoId(null);
    setPdfAviso(null);
    setPdfError(null);
    setPdfCargado(null);
    setEvolucion(null);
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
    <div className="app app-libre">
      <HistorialPanel
        open={historialRailOpen}
        items={historial}
        activeId={historialActivoId}
        error={historialError}
        onToggle={() => setHistorialRailOpen((open) => !open)}
        onNew={handleNuevaRevision}
        onSelect={handleHistorialSelect}
        onRemove={handleHistorialRemove}
        onClear={handleHistorialClear}
      />
      <div className="app-stage">
        <HeaderBrand
          isDev={isDev}
          backendOk={backendOk}
          healthReady={healthReady}
          health={health}
        />

        <div className="shell shell-workspace">
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
            loading={loading || pdfExtrayendo}
            canAnalyze={Boolean(nota.trim()) && healthReady && !pdfExtrayendo}
            backendOk={backendOk && healthReady}
            showBackendHint={isDev}
            onAnalizar={handleAnalizar}
            muestrasPdf={muestrasPdf}
            pdfAviso={pdfAviso}
            pdfError={pdfError}
            pdfCargado={pdfCargado}
            pdfExtrayendo={pdfExtrayendo}
            onPdfFile={handlePdfFile}
            onPdfMuestra={handlePdfMuestra}
            onPdfQuitar={handlePdfQuitar}
            evolucionPreview={
              evolucion?.entries?.length ? (
                <EvolucionPreview
                  entries={evolucion.entries}
                  motor={evolucion.motor}
                  aviso={evolucion.aviso}
                  paginasSinContenido={evolucion.paginasSinContenido}
                />
              ) : null
            }
            pdfResumen={
              evolucion?.entries?.length
                ? `${evolucion.entries.length} evolución${evolucion.entries.length === 1 ? "" : "es"} en el expediente`
                : null
            }
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
    </div>
  );
}
