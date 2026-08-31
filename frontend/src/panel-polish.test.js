import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const notaSource = readFileSync(new URL("./components/NotaInput.jsx", import.meta.url), "utf8");
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

test("empty guidance follows the 01 through 03 demo path", () => {
  assert.match(resultadosSource, /<b>01<\/b>[\s\S]*Elige/);
  assert.match(resultadosSource, /<b>02<\/b>[\s\S]*Analizar nota/);
  assert.match(resultadosSource, /<b>03<\/b>[\s\S]*validar/i);
});

test("active chips use a soft primary treatment", () => {
  assert.match(
    stylesSource,
    /\.chip\.active\s*\{[^}]*color-mix\(in srgb, var\(--color-primary\)/,
  );
});

test("tablet and mobile layouts expose a collapsed historial toggle", () => {
  assert.match(appSource, /aria-controls="historial-rail"/);
  assert.match(appSource, /aria-expanded=\{historialRailOpen\}/);
  assert.match(
    stylesSource,
    /@media \(max-width: 1023px\)[\s\S]*\.historial-rail:not\(\.is-open\)\s*\{[^}]*display:\s*none;/,
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
