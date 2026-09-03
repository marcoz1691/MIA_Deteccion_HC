import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const notaSource = readFileSync(new URL("./components/NotaInput.jsx", import.meta.url), "utf8");

test("nota panel states MVP axes the model checks against the note", () => {
  assert.match(notaSource, /lateralidad/);
  assert.match(notaSource, /sexo/);
  assert.match(notaSource, /alergias/);
  assert.match(notaSource, /medicamentos/);
  assert.match(notaSource, /edad/);
  assert.match(notaSource, /umbral 0\.50/);
  assert.doesNotMatch(notaSource, /validarNota/);
});
