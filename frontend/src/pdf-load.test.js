import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const notaSource = readFileSync(new URL("./components/NotaInput.jsx", import.meta.url), "utf8");
const appSource = readFileSync(new URL("./App.jsx", import.meta.url), "utf8");
const clientSource = readFileSync(new URL("./api/client.js", import.meta.url), "utf8");
const stylesSource = readFileSync(new URL("./styles.css", import.meta.url), "utf8");

test("nota panel exposes a PDF document section", () => {
  assert.match(notaSource, /Documento PDF/);
  assert.match(notaSource, /type="file"/);
  assert.match(notaSource, /accept="application\/pdf,\.pdf"/);
  assert.match(notaSource, /onPdfFile/);
  assert.match(notaSource, /onPdfMuestra/);
  assert.match(notaSource, /muestrasPdf/);
  assert.match(notaSource, /salidas_buscable|buscable/);
  assert.match(notaSource, /pdfCargado/);
  assert.match(notaSource, /pdf-loaded/);
  assert.match(notaSource, /onPdfQuitar/);
  assert.match(notaSource, /Cambiar PDF/);
});

test("app wires PDF extraction into nota state", () => {
  assert.match(appSource, /extraerPdf/);
  assert.match(appSource, /listarMuestrasPdf/);
  assert.match(appSource, /setEjemploId\("pdf"\)/);
  assert.match(appSource, /handlePdfFile/);
  assert.match(appSource, /handlePdfQuitar/);
  assert.match(appSource, /setPdfCargado/);
});

test("client can list samples and extract PDF text", () => {
  assert.match(clientSource, /listarMuestrasPdf/);
  assert.match(clientSource, /\/muestras-pdf/);
  assert.match(clientSource, /\/extraer-pdf/);
  assert.match(clientSource, /form.append\("archivo"/);
});

test("loaded pdf badge sits beside the file picker", () => {
  assert.match(stylesSource, /\.pdf-loaded\s*\{/);
  assert.match(stylesSource, /\.pdf-loaded-name\s*\{[^}]*text-overflow:\s*ellipsis;/);
});

test("pdf samples stay collapsed and do not look like a loaded file", () => {
  assert.match(notaSource, /pdf-muestras/);
  assert.match(notaSource, /Muestras anonimizadas de demostración/);
  assert.match(appSource, /useState\("propia"\)/);
  assert.match(appSource, /useState\(""\)/);
});

test("pdf extraction highlights the document origin and keeps evolutions collapsed", () => {
  assert.match(notaSource, /intake-pdf \$\{pdfActivo \? "is-active"/);
  assert.match(notaSource, /expediente-extracting/);
  assert.match(notaSource, /evol-preview-wrap/);
  assert.match(notaSource, /<summary>\{pdfResumen\}<\/summary>/);
  assert.match(appSource, /setEjemploId\("pdf"\)/);
});
