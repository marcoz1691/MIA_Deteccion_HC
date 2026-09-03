import assert from "node:assert/strict";
import test from "node:test";

import { groupHistorialByDate, previewNota } from "./historial.js";

test("historial preview skips evolution structural headers", () => {
  const raw =
    "--- EVOLUCIÓN 1 --- FECHA: 2026-07-06 HORA: 09:06 NOTAS DE EVOLUCIÓN: Paciente estable, sin dolor.";
  const preview = previewNota(raw);
  assert.equal(preview.includes("EVOLUCIÓN 1"), false);
  assert.equal(preview.includes("FECHA:"), false);
  assert.match(preview, /Paciente estable/);
});

test("historial groups chats like LibreChat by day", () => {
  const today = new Date();
  const yesterday = new Date(today.getTime() - 86_400_000);
  const older = new Date(today.getTime() - 20 * 86_400_000);
  const groups = groupHistorialByDate([
    { id: "1", ts: today.toISOString(), nota: "hoy" },
    { id: "2", ts: yesterday.toISOString(), nota: "ayer" },
    { id: "3", ts: older.toISOString(), nota: "antes" },
  ]);
  assert.deepEqual(
    groups.map((g) => g.label),
    ["Hoy", "Ayer", "Anteriores"],
  );
  assert.equal(groups[0].items[0].id, "1");
});
