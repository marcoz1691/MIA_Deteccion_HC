import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const notaSource = readFileSync(new URL("./components/NotaInput.jsx", import.meta.url), "utf8");
const historialPanelSource = readFileSync(
  new URL("./components/HistorialPanel.jsx", import.meta.url),
  "utf8",
);
const resultadosSource = readFileSync(
  new URL("./components/ResultadosPanel.jsx", import.meta.url),
  "utf8",
);
const appSource = readFileSync(new URL("./App.jsx", import.meta.url), "utf8");
const stylesSource = readFileSync(new URL("./styles.css", import.meta.url), "utf8");

test("both analysis panels expose their loading state", () => {
  assert.match(notaSource, /<section[^>]+aria-busy=\{loading\}/);
  assert.match(resultadosSource, /<section[^>]+aria-busy=\{loading\}/);
});

test("alert results use the banner alert hierarchy", () => {
  assert.match(resultadosSource, /className=\{`banner verdict \$\{alerta \? "alert" : "ok"\}`\}/);
  assert.match(stylesSource, /\.banner\.alert[^}]*\{[^}]*border-left:/);
});

test("analyze action stays reachable without scrolling past the note", () => {
  assert.match(notaSource, /intake-sticky/);
  assert.match(stylesSource, /\.intake-sticky\s*\{[^}]*position:\s*sticky;/);
});

test("empty guidance follows the 01 through 03 demo path", () => {
  assert.match(resultadosSource, /<b>01<\/b>[\s\S]*historia clínica/);
  assert.match(resultadosSource, /<b>02<\/b>[\s\S]*Analizar historia clínica/);
  assert.match(resultadosSource, /<b>03<\/b>[\s\S]*criterio clínico/i);
});

test("active chips use a soft primary treatment", () => {
  assert.match(
    stylesSource,
    /\.chip\.active\s*\{[^}]*color-mix\(in srgb, var\(--color-primary\)/,
  );
});

test("historial rail can collapse and expand on all layouts", () => {
  assert.match(historialPanelSource, /aria-controls="historial-rail"/);
  assert.match(historialPanelSource, /aria-expanded=\{open\}/);
  assert.match(historialPanelSource, /historial-icon-btn/);
  assert.match(historialPanelSource, /Nueva revisión/);
  assert.match(historialPanelSource, /Buscar chats/);
  assert.match(
    stylesSource,
    /\.historial-slot:not\(\.is-open\)\s+\.historial-rail\s*\{[^}]*display:\s*none;/,
  );
});

test("light primary actions use an AA contrast background", () => {
  assert.match(stylesSource, /--color-cta:\s*#047857;/);
  assert.match(stylesSource, /\.primary-btn,[\s\S]*?\.cta\s*\{[^}]*background:\s*var\(--color-cta\);/);
});

test("reduced motion stops spinners and short control transitions", () => {
  assert.match(
    stylesSource,
    /@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.spinner\s*\{[^}]*animation:\s*none;/,
  );
  assert.match(
    stylesSource,
    /@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.chip,[\s\S]*?\.historial-item[^}]*\{[^}]*transition:\s*none;/,
  );
});

test("resultados panel filters alerts and shows info tips", () => {
  assert.match(resultadosSource, /oraciones\.filter\(\(o\) => o\.alerta\)/);
  assert.match(resultadosSource, /Frases a revisar/);
  assert.match(resultadosSource, /Expediente extenso/);
  assert.match(resultadosSource, /import InfoTip/);
  assert.match(resultadosSource, /import TrazabilidadDetalle/);
  assert.match(resultadosSource, /explicarInconsistencia/);
  assert.match(resultadosSource, /Motivo/);
  assert.match(resultadosSource, /Trazabilidad/);
  assert.match(stylesSource, /\.info-tip-popup/);
  assert.match(stylesSource, /\.shell-workspace \.workspace[\s\S]*flex-direction:\s*column/);
  assert.match(stylesSource, /\.shell-workspace \.workspace[\s\S]*align-items:\s*stretch/);
  assert.match(stylesSource, /\.shell-workspace \.card[\s\S]*width:\s*100%/);
});

test("historial restore maps pdf metadata", () => {
  assert.match(appSource, /pdfOrigen: pdfCargado\?\.nombre/);
  assert.match(appSource, /item\.pdfOrigen/);
  assert.match(appSource, /soloLectura: true/);
});
