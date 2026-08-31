import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const stylesSource = readFileSync(new URL("./styles.css", import.meta.url), "utf8");

test("global interactive controls use a pointer cursor", () => {
  assert.match(
    stylesSource,
    /button,\s*\.chip,\s*\.historial-item,\s*\.mark-btn\s*\{[^}]*cursor:\s*pointer;/,
  );
});

test("keyboard focus uses the primary color with a visible offset", () => {
  assert.match(
    stylesSource,
    /:focus-visible\s*\{[^}]*outline:\s*2px solid var\(--color-primary\);[^}]*outline-offset:\s*2px;/,
  );
});
