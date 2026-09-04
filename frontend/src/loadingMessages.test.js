import assert from "node:assert/strict";
import test from "node:test";

import { getLoadingMessage, getLoadingStep } from "./loadingMessages.js";

test("loading messages rotate every 8 seconds in real mode", () => {
  const m0 = getLoadingMessage(0, false);
  const m8 = getLoadingMessage(8, false);
  const m48 = getLoadingMessage(48, false);
  assert.notEqual(m0.title, m8.title);
  assert.match(m48.hint, /No cierre esta pestaña/i);
});

test("mock mode uses shorter message set", () => {
  const step = getLoadingStep(0, true);
  assert.equal(step.total, 2);
  assert.match(getLoadingMessage(0, true).hint, /demo/i);
});
