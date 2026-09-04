import { useEffect, useMemo, useState } from "react";



import { explicarInconsistencia } from "../explicarInconsistencia";
import { getLoadingMessage, getLoadingStep } from "../loadingMessages";
import InfoTip from "./InfoTip";



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

      <p>El hallazgo aparece aquí. No es un veredicto médico.</p>

      <ol className="empty-steps">

        <li>

          <b>01</b> Elija un caso o pegue la historia clínica.

        </li>

        <li>

          <b>02</b> Pulse Analizar historia clínica.

        </li>

        <li>

          <b>03</b> Valide el hallazgo con criterio clínico.

        </li>

      </ol>

    </div>

  );

}



export default function ResultadosPanel({ resultado, error, loading, mockLlm = true }) {

  const [elapsed, setElapsed] = useState(0);



  useEffect(() => {

    if (!loading) {

      setElapsed(0);

      return undefined;

    }

    const t0 = Date.now();

    const id = window.setInterval(() => {

      setElapsed(Math.floor((Date.now() - t0) / 1000));

    }, 1000);

    return () => window.clearInterval(id);

  }, [loading]);

  const loadingMessage = getLoadingMessage(elapsed, mockLlm);
  const loadingStep = getLoadingStep(elapsed, mockLlm);

  return (

    <section

      className="card"

      aria-labelledby="result-title"

      aria-live="polite"

      aria-busy={loading}

    >

      <div className="card-head">

        <p className="eyebrow">Hallazgo</p>

        <h2 id="result-title">Hallazgo a revisar</h2>

        <p className="hint">Un tramo de la nota. Un score. La decisión sigue siendo médica.</p>

      </div>



      {loading && (

        <div className="loading" role="status">

          <div className="spinner" aria-hidden="true" />

          <div>
            <p className="loading-title">
              {loadingMessage.title}
              {elapsed > 0 ? ` (${elapsed}s)` : ""}
            </p>
            <p className="hint loading-hint">{loadingMessage.hint}</p>
            <p className="loading-step" aria-hidden="true">
              Paso {loadingStep.current} de {loadingStep.total}
            </p>
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

  const {

    top1,

    oraciones,

    truncado,

    n_total,

    modo_degradado,

    mensaje_fallback,

    brazos_efectivos: brazosEfectivos,

  } = resultado;

  const alerta = Boolean(top1?.alerta);

  const [verTodas, setVerTodas] = useState(false);



  const alertas = useMemo(() => oraciones.filter((o) => o.alerta), [oraciones]);

  const filas = verTodas ? oraciones : alertas;

  const totalFrases = n_total || oraciones.length;



  return (

    <>

      {truncado && (

        <div className="banner warn">

          <strong>Expediente extenso.</strong> Este documento tiene{" "}

          <strong>{n_total} frases</strong>; el sistema revisó las{" "}

          <strong>primeras {oraciones.length}</strong> para mantener un tiempo de respuesta

          razonable. Si la inconsistencia pudiera estar más adelante, copie y analice ese tramo

          por separado.

        </div>

      )}

      {(modo_degradado || mensaje_fallback) && (

        <div className="banner warn">{mensaje_fallback || "Modo degradado: solo TF-IDF."}</div>

      )}



      {top1 ? (

        <div className={`banner verdict ${alerta ? "alert" : "ok"}`}>

          <p className="verdict-kicker">{alerta ? "Requiere revisión" : "Sin alerta clara"}</p>

          <p className="verdict-title">

            {alerta

              ? `Revisar frase ${top1.sid + 1}`

              : "Ninguna frase supera el umbral de 0.50"}

          </p>

          <ScoreBar value={top1.score_localizacion} />

          <p className="hint">

            Score de localización {fmt(top1.score_localizacion)} · umbral 0.50

          </p>

        </div>

      ) : (

        <div className="banner warn">No se detectaron frases. Escribe enunciados separados por puntos.</div>

      )}



      {top1 && (

        <article className={`sentence ${alerta ? "alert" : ""}`}>

          <header>

            <span>Frase {top1.sid + 1}</span>

            <span className={`pill ${alerta ? "danger" : "ok"}`}>

              {alerta ? "Probable inconsistencia" : "Sin inconsistencia aparente"}

            </span>

          </header>

          <p>{top1.oracion}</p>

        </article>

      )}



      <div className="metrics">

        <div>

          <span>Frases</span>

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



      <div className="table-head-row">

        <h3 className="table-title">

          {verTodas ? "Detalle por frase" : "Frases a revisar"}

        </h3>

        {!verTodas && alertas.length > 0 && (

          <p className="hint table-subtitle">

            {alertas.length} de {totalFrases} frases superan el umbral de revisión.

          </p>

        )}

        {oraciones.length > 0 && (

          <button

            type="button"

            className="table-toggle-link"

            onClick={() => setVerTodas((v) => !v)}

          >

            {verTodas

              ? `Mostrar solo inconsistencias (${alertas.length})`

              : `Mostrar todas las frases (${oraciones.length})`}

          </button>

        )}

      </div>



      {!verTodas && alertas.length === 0 ? (

        <p className="hint table-empty">

          Ninguna frase supera el umbral de revisión (0,50).

        </p>

      ) : (

        <div className="table-wrap">

          <table>

            <thead>

              <tr>

                <th>#</th>

                <th>Frase</th>

                <th>

                  <InfoTip

                    label="TF-IDF"

                    tip="Comparador entrenado con historias donde ya se conocían errores. Busca frases con un patrón parecido al de una inconsistencia documentada."

                  />

                </th>

                <th>

                  <InfoTip

                    label="LLM"

                    tip="Modelo de lenguaje que lee la frase en contexto de toda la nota y evalúa si contradice lateralidad, sexo, alergias o edad."

                  />

                </th>

                <th>

                  <InfoTip

                    label="RAG"

                    tip="Igual que LLM, pero consulta guías clínicas (GPC) como referencia adicional."

                  />

                </th>

                <th>

                  <InfoTip

                    label="Loc."

                    tip="Puntuación combinada (0–1) que indica qué tan prioritario es revisar la frase. Por encima de 0,50 se marca para revisión."

                  />

                </th>

                <th>Motivo</th>

              </tr>

            </thead>

            <tbody>

              {filas.map((o) => (

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

                  <td className="motivo-cell">

                    {o.alerta ? explicarInconsistencia(o, brazosEfectivos) : "—"}

                  </td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

      )}

    </>

  );

}


