import assert from "node:assert/strict";
import { describe, it, beforeEach } from "node:test";
import {
  THEME_STORAGE_KEY,
  getStoredTheme,
  applyTheme,
  toggleTheme,
  createEggTracker,
  isThemeUnlocked,
  markThemeUnlocked,
  EGG_UNLOCK_STORAGE_KEY,
} from "./theme.js";

const memory = new Map();

beforeEach(() => {
  memory.clear();
  globalThis.localStorage = {
    getItem: (k) => (memory.has(k) ? memory.get(k) : null),
    setItem: (k, v) => memory.set(k, String(v)),
    removeItem: (k) => memory.delete(k),
  };
  globalThis.document = {
    documentElement: { setAttribute(name, value) { this[name] = value; }, getAttribute(name) { return this[name] ?? null; } },
  };
});

describe("theme", () => {
  it("defaults to light", () => {
    assert.equal(getStoredTheme(), "light");
  });

  it("applyTheme persists and sets data-theme", () => {
    applyTheme("dark");
    assert.equal(localStorage.getItem(THEME_STORAGE_KEY), "dark");
    assert.equal(document.documentElement.getAttribute("data-theme"), "dark");
  });

  it("toggleTheme flips light/dark", () => {
    applyTheme("light");
    assert.equal(toggleTheme(), "dark");
    assert.equal(toggleTheme(), "light");
  });

  it("egg tracker unlocks after 5 quick clicks", () => {
    const egg = createEggTracker({ clicksNeeded: 5, windowMs: 2000 });
    assert.equal(egg.registerClick(), false);
    assert.equal(egg.registerClick(), false);
    assert.equal(egg.registerClick(), false);
    assert.equal(egg.registerClick(), false);
    assert.equal(egg.registerClick(), true);
  });

  it("markThemeUnlocked persists", () => {
    assert.equal(isThemeUnlocked(), false);
    markThemeUnlocked();
    assert.equal(localStorage.getItem(EGG_UNLOCK_STORAGE_KEY), "1");
    assert.equal(isThemeUnlocked(), true);
  });
});
