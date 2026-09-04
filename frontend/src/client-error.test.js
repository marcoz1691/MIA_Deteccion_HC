import assert from "node:assert/strict";
import test from "node:test";

import { mensajeErrorRed } from "./api/client.js";

test("Failed to fetch becomes a Spanish reconnect hint", () => {
  const msg = mensajeErrorRed(new TypeError("Failed to fetch"));
  assert.match(msg, /No se pudo conectar con la API/);
  assert.match(msg, /Analizar/);
});

test("other errors keep their message", () => {
  assert.equal(mensajeErrorRed(new Error("PDF ilegible")), "PDF ilegible");
});

test("healthCheck retries after a failed fetch", async () => {
  const originalFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    if (calls === 1) throw new TypeError("Failed to fetch");
    return {
      ok: true,
      json: async () => ({ status: "ok" }),
    };
  };
  try {
    const { healthCheck } = await import("./api/client.js");
    const data = await healthCheck({ retries: 1, delayMs: 1 });
    assert.equal(data.status, "ok");
    assert.equal(calls, 2);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
