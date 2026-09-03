# UI/UX Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the MIA · CITIMED React frontend into a 3-zone clinical workspace with light-slate modern default, dark-premium easter egg theme, and unchanged API contracts.

**Architecture:** Keep Vite + React 19 single-page `App.jsx`. Introduce a pure `theme.js` module (`data-theme` + `localStorage`), CSS variable dual themes in `styles.css`, and restructure layout to historial rail + note + hallazgo. Extract `HeaderBrand` for the 5-click easter egg. No backend changes.

**Tech Stack:** React 19, Vite 6, plain CSS (no Tailwind), Node built-in test runner (`node --test`) for theme helpers.

**Spec:** `docs/superpowers/specs/2026-08-25-ui-ux-redesign-design.md`

## Global Constraints

- Frontend-only; do not change `api/` contracts or payloads.
- Default theme is **light** slate (`#F4F6F8`); do not auto-apply OS dark preference.
- Dark theme only via easter egg (5 clicks on brand mark within ~2s) + optional header icon after unlock.
- No patient profiles, Exportar, Nueva nota, or other invented EHR chrome.
- No emoji icons; SVG or CSS shapes only.
- Preserve disclaimer copy intent (research prototype; no therapeutic decisions).
- Commits only when the user explicitly asks (omit commit steps during execution unless requested).

---

## File map

| File | Role |
|------|------|
| `frontend/src/theme.js` | Read/write theme, apply `data-theme`, egg counter helpers |
| `frontend/src/theme.test.js` | Node tests for theme helpers |
| `frontend/src/components/HeaderBrand.jsx` | Brand mark egg + disclaimer + status + post-unlock theme button |
| `frontend/src/components/ThemeToast.jsx` | Brief “Modo oscuro/claro” toast |
| `frontend/src/styles.css` | Dual-theme tokens + 3-zone layout + responsive |
| `frontend/src/App.jsx` | Shell layout wiring |
| `frontend/src/main.jsx` | Apply stored theme before paint |
| `frontend/src/components/NotaInput.jsx` | Visual classes only (props unchanged) |
| `frontend/src/components/ResultadosPanel.jsx` | Hallazgo focus styles / empty steps |
| `frontend/src/components/HistorialPanel.jsx` | Rail markup/classes |
| `.cursor/skills/ui-ux-pro-max/` | Optional skill install (Task 0) |

---

### Task 0: Install UI UX Pro Max skill (optional, once)

**Files:**
- Create: `.cursor/skills/ui-ux-pro-max/**` (via CLI)

**Interfaces:**
- Consumes: local CLI / npm `ui-ux-pro-max-cli`
- Produces: Cursor skill usable in later design queries (not required at runtime)

- [ ] **Step 1: Init skill in this repo**

```bash
cd "C:\Users\MarcoZurita\git\MIA_Deteccion_HC"
npx --yes ui-ux-pro-max-cli init --ai cursor
```

Expected: `.cursor/skills/ui-ux-pro-max/SKILL.md` exists.

- [ ] **Step 2: Verify Python available for search scripts**

```bash
python --version
```

Expected: Python 3.x. If missing, skip skill searches and continue; do not install Python via package managers for the user.

---

### Task 1: Theme module + tests

**Files:**
- Create: `frontend/src/theme.js`
- Create: `frontend/src/theme.test.js`
- Modify: `frontend/package.json` (add `"test": "node --test src/theme.test.js"`)

**Interfaces:**
- Consumes: `localStorage`, `document.documentElement`
- Produces:
  - `THEME_STORAGE_KEY = "mia-theme"`
  - `EGG_UNLOCK_STORAGE_KEY = "mia-theme-unlocked"`
  - `getStoredTheme(): "light" | "dark"` — defaults `"light"` if missing/invalid
  - `applyTheme(theme: "light" | "dark"): void` — sets `data-theme` on `<html>` and stores
  - `toggleTheme(): "light" | "dark"`
  - `isThemeUnlocked(): boolean`
  - `markThemeUnlocked(): void`
  - `createEggTracker({ clicksNeeded = 5, windowMs = 2000 } = {})` → `{ registerClick(): boolean }` where `true` means threshold reached (caller toggles + unlocks)

- [ ] **Step 1: Write failing tests**

Create `frontend/src/theme.test.js`:

```js
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
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd frontend
node --test src/theme.test.js
```

Expected: FAIL (module missing / exports missing).

- [ ] **Step 3: Implement `frontend/src/theme.js`**

```js
export const THEME_STORAGE_KEY = "mia-theme";
export const EGG_UNLOCK_STORAGE_KEY = "mia-theme-unlocked";

export function getStoredTheme() {
  const v = globalThis.localStorage?.getItem(THEME_STORAGE_KEY);
  return v === "dark" ? "dark" : "light";
}

export function applyTheme(theme) {
  const next = theme === "dark" ? "dark" : "light";
  globalThis.localStorage?.setItem(THEME_STORAGE_KEY, next);
  globalThis.document?.documentElement?.setAttribute("data-theme", next);
}

export function toggleTheme() {
  const next = getStoredTheme() === "dark" ? "light" : "dark";
  applyTheme(next);
  return next;
}

export function isThemeUnlocked() {
  return globalThis.localStorage?.getItem(EGG_UNLOCK_STORAGE_KEY) === "1";
}

export function markThemeUnlocked() {
  globalThis.localStorage?.setItem(EGG_UNLOCK_STORAGE_KEY, "1");
}

export function createEggTracker({ clicksNeeded = 5, windowMs = 2000 } = {}) {
  let count = 0;
  let windowStart = 0;
  return {
    registerClick(now = Date.now()) {
      if (!windowStart || now - windowStart > windowMs) {
        windowStart = now;
        count = 1;
        return false;
      }
      count += 1;
      if (count >= clicksNeeded) {
        count = 0;
        windowStart = 0;
        return true;
      }
      return false;
    },
  };
}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd frontend
node --test src/theme.test.js
```

Expected: all tests pass.

- [ ] **Step 5: Add npm script**

In `frontend/package.json` scripts:

```json
"test": "node --test src/theme.test.js"
```

Verify: `npm test` passes.

---

### Task 2: Apply theme before paint + CSS dual tokens

**Files:**
- Modify: `frontend/src/main.jsx`
- Modify: `frontend/src/styles.css` (token block at top; map legacy `--bg` etc. to new tokens)

**Interfaces:**
- Consumes: `getStoredTheme`, `applyTheme` from `theme.js`
- Produces: `<html data-theme="light|dark">` before React render; all UI colors via CSS variables

- [ ] **Step 1: Flash-free bootstrap in `main.jsx`**

```jsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { applyTheme, getStoredTheme } from "./theme";
import "./styles.css";

applyTheme(getStoredTheme());

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 2: Replace `:root` token block in `styles.css`**

At the top of `frontend/src/styles.css`, replace the Google Fonts import and `:root` variables with:

```css
@import url("https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&family=Noto+Sans:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap");

:root,
[data-theme="light"] {
  --color-primary: #0d9488;
  --color-accent: #059669;
  --color-background: #f4f6f8;
  --color-surface: #eef1f4;
  --color-card: #ffffff;
  --color-foreground: #0f172a;
  --color-muted-foreground: #64748b;
  --color-border: #e5e7eb;
  --color-destructive: #ef4444;
  --color-ok: #059669;
  --color-warn: #d97706;
  --radius: 12px;
  --shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
  --font: "Figtree", "Noto Sans", "Segoe UI", sans-serif;
  --font-body: "Noto Sans", "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, monospace;
  /* Legacy aliases used by existing rules */
  --bg: var(--color-background);
  --bg-elev: var(--color-card);
  --bg-soft: var(--color-surface);
  --line: var(--color-border);
  --line-strong: var(--color-border);
  --text: var(--color-foreground);
  --muted: var(--color-muted-foreground);
  --metal: var(--color-muted-foreground);
  --accent: var(--color-primary);
  --ok: var(--color-ok);
  --warn: var(--color-warn);
  --alert: var(--color-destructive);
  color: var(--color-foreground);
  background: var(--color-background);
  font-family: var(--font-body);
  line-height: 1.5;
}

[data-theme="dark"] {
  --color-primary: #2dd4bf;
  --color-accent: #10b981;
  --color-background: #0b0f14;
  --color-surface: #0f141b;
  --color-card: #12181f;
  --color-foreground: #e8eef2;
  --color-muted-foreground: #8b95a1;
  --color-border: rgba(255, 255, 255, 0.08);
  --color-destructive: #f87171;
  --color-ok: #34d399;
  --color-warn: #fbbf24;
  --shadow: 0 0 0 1px var(--color-border);
}

body {
  margin: 0;
  background: var(--color-background);
  color: var(--color-foreground);
  transition: background-color 200ms ease, color 200ms ease;
}

@media (prefers-reduced-motion: reduce) {
  body {
    transition: none;
  }
}
```

Remove the old Sora import and the heavy dark grid `body::before` pattern (or tone it down to a subtle dark-only glow). Keep class names (`.card`, `.chip`, `.primary-btn`, etc.) working via aliases.

- [ ] **Step 3: Restyle primary CTA to accent**

Ensure `.primary-btn` / analyze button uses `background: var(--color-accent)` and white/on-accent text with visible `:focus-visible` outline `2px solid var(--color-primary)`.

- [ ] **Step 4: Visual smoke**

```bash
cd frontend
npm run build
```

Expected: build succeeds. Manually open `npm run dev`, confirm light slate look (not old charcoal default).

---

### Task 3: HeaderBrand + ThemeToast + easter egg

**Files:**
- Create: `frontend/src/components/HeaderBrand.jsx`
- Create: `frontend/src/components/ThemeToast.jsx`
- Modify: `frontend/src/App.jsx` (use HeaderBrand; pass health/status props)

**Interfaces:**
- Consumes: `createEggTracker`, `toggleTheme`, `markThemeUnlocked`, `isThemeUnlocked`, `getStoredTheme`, `applyTheme`
- Produces:
  - `<HeaderBrand isDev backendOk healthReady health onThemeChange?: (theme) => void />`
  - Toast message for 1.5–2s after toggle

- [ ] **Step 1: Implement ThemeToast**

```jsx
// frontend/src/components/ThemeToast.jsx
export default function ThemeToast({ message }) {
  if (!message) return null;
  return (
    <div className="theme-toast" role="status" aria-live="polite">
      {message}
    </div>
  );
}
```

CSS (in `styles.css`):

```css
.theme-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 40;
  padding: 10px 16px;
  border-radius: 999px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow);
  color: var(--color-foreground);
  font-size: 0.85rem;
}
```

- [ ] **Step 2: Implement HeaderBrand with egg**

```jsx
import { useEffect, useRef, useState } from "react";
import {
  createEggTracker,
  getStoredTheme,
  isThemeUnlocked,
  markThemeUnlocked,
  toggleTheme,
} from "../theme";
import ThemeToast from "./ThemeToast";

export default function HeaderBrand({ isDev, backendOk, healthReady, health }) {
  const eggRef = useRef(createEggTracker());
  const [unlocked, setUnlocked] = useState(() => isThemeUnlocked());
  const [theme, setTheme] = useState(() => getStoredTheme());
  const [toast, setToast] = useState("");

  useEffect(() => {
    if (!toast) return undefined;
    const id = window.setTimeout(() => setToast(""), 1800);
    return () => window.clearTimeout(id);
  }, [toast]);

  function announce(next) {
    setTheme(next);
    setToast(next === "dark" ? "Modo oscuro" : "Modo claro");
  }

  function handleMarkClick() {
    if (eggRef.current.registerClick()) {
      markThemeUnlocked();
      setUnlocked(true);
      announce(toggleTheme());
    }
  }

  function handleExplicitToggle() {
    announce(toggleTheme());
  }

  return (
    <>
      <header className="topbar">
        <div className="brand">
          <button
            type="button"
            className="mark-btn"
            aria-label="MIA CITIMED"
            onClick={handleMarkClick}
          >
            <span className="mark" aria-hidden="true" />
          </button>
          <div>
            <p className="brand-kicker">MIA · CITIMED</p>
            <h1>Detección de inconsistencias</h1>
          </div>
        </div>
        <div className="topbar-meta">
          <p className="lede disclaimer-inline">
            Prototipo de investigación. No sustituye el criterio clínico.
          </p>
          {unlocked && (
            <button
              type="button"
              className="ghost-btn theme-toggle"
              onClick={handleExplicitToggle}
              aria-label={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
            >
              {theme === "dark" ? "Claro" : "Oscuro"}
            </button>
          )}
          {isDev && (
            <div className={`status ${backendOk ? "ok" : "down"}`}>
              <span className="dot" />
              {backendOk
                ? `Backend listo${health?.modelo_tfidf_disponible ? " · TF-IDF" : ""}${health?.llm_api_configurada ? " · OpenAI" : ""}`
                : healthReady
                  ? "Backend no disponible"
                  : "Conectando…"}
            </div>
          )}
        </div>
      </header>
      <ThemeToast message={toast} />
    </>
  );
}
```

Style `.mark-btn` as unstyled button (`border:0; background:transparent; cursor:pointer; padding:0`) wrapping existing `.mark`.

- [ ] **Step 3: Wire HeaderBrand in App.jsx**

Replace the existing `<header className="topbar">…</header>` block with:

```jsx
<HeaderBrand
  isDev={isDev}
  backendOk={backendOk}
  healthReady={healthReady}
  health={health}
/>
```

Remove the duplicate long disclaimer paragraph under shell **or** keep a shorter one — prefer single disclaimer in header per HeaderBrand (delete `.disclaimer` in shell if redundant).

- [ ] **Step 4: Manual test egg**

`npm run dev` → click mark 5× quickly → dark theme + toast; click again 5× or use “Claro/Oscuro” after unlock → toggles; reload → theme persists.

---

### Task 4: Three-zone layout (rail + note + hallazgo)

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/styles.css` (`.shell`, `.workspace`, `.historial`)
- Modify: `frontend/src/components/HistorialPanel.jsx` (rail classes only)

**Interfaces:**
- Consumes: existing panel props from App (unchanged API handlers)
- Produces: desktop grid `240px 1fr 1fr`; tablet/mobile breakpoints per spec

- [ ] **Step 1: Restructure App shell markup**

```jsx
<div className="app">
  <HeaderBrand ... />
  <div className="shell shell-workspace">
    <HistorialPanel
      className="historial-rail"
      items={historial}
      activeId={historialActivoId}
      error={historialError}
      onSelect={handleHistorialSelect}
      onRemove={handleHistorialRemove}
      onClear={handleHistorialClear}
    />
    <main className="workspace">
      <NotaInput ... />
      <ResultadosPanel ... />
    </main>
  </div>
</div>
```

If `HistorialPanel` does not accept `className`, add `className = ""` to its root `<section className={`card historial ${className}`}>`.

- [ ] **Step 2: CSS grid for shell**

```css
.shell-workspace {
  width: min(1440px, calc(100% - 32px));
  margin: 0 auto;
  padding: 20px 0 48px;
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
  flex: 1;
}

.shell-workspace .workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
  min-width: 0;
}

.historial-rail {
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 100px);
  overflow: auto;
}

@media (max-width: 1023px) {
  .shell-workspace {
    grid-template-columns: 1fr;
  }
  .shell-workspace .workspace {
    grid-template-columns: 1fr;
  }
  .historial-rail {
    position: static;
    max-height: none;
    order: 3;
  }
}
```

Place historial visually first on desktop (grid column 1). On mobile, `order: 3` so note → hallazgo → historial.

- [ ] **Step 3: Verify layout**

Resize to 1440 / 768 / 375 in browser. Confirm side-by-side note|hallazgo on desktop; stack on small screens.

---

### Task 5: Panel polish (Nota + Hallazgo)

**Files:**
- Modify: `frontend/src/components/NotaInput.jsx`
- Modify: `frontend/src/components/ResultadosPanel.jsx`
- Modify: `frontend/src/styles.css` (chips, empty steps, alert banner, scorebars)

**Interfaces:**
- Consumes: existing props (do not rename API fields)
- Produces: clearer empty-state steps; alert/OK banner hierarchy; `aria-busy` on analyzing container

- [ ] **Step 1: NotaInput — keep structure, tighten copy/classes**

Ensure:
- Eyebrow `Nota`, title `Historia clínica`
- Chips use `.chip` / `.chip.active` with primary soft fill
- Primary button class uses accent
- Wrapper has `aria-busy={loading}` on the section when loading

- [ ] **Step 2: ResultadosPanel empty steps**

Keep three steps; align numbering `01` `02` `03` with demo path (elige caso → analizar → validar). On success with `top1.alerta`, use `.banner.alert` with strong left border `var(--color-destructive)`.

- [ ] **Step 3: Loading skeleton**

Prefer stable `.loading` block with spinner (existing) + hint; add `aria-busy="true"` on section while `loading`.

- [ ] **Step 4: Manual demo path**

Pick Medicación → Analizar (mock) → confirm alert sentence is the visual focus without hunting.

---

### Task 6: Accessibility + reduced motion + final QA

**Files:**
- Modify: `frontend/src/styles.css` (focus-visible, cursor-pointer on buttons)
- Touch panels only if gaps found

**Interfaces:**
- Consumes: completed UI
- Produces: checklist sign-off against spec success criteria

- [ ] **Step 1: Global interactive affordances**

```css
button,
.chip,
.historial-item,
.mark-btn {
  cursor: pointer;
}

:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
```

- [ ] **Step 2: Run automated checks**

```bash
cd frontend
npm test
npm run build
```

Expected: tests pass; build OK.

- [ ] **Step 3: Manual QA checklist**

- [ ] Light default on fresh profile (clear `localStorage`)
- [ ] Egg: 5 clicks → dark + toast; persists on reload
- [ ] After unlock, Claro/Oscuro button works
- [ ] Demo &lt;2 min path works
- [ ] Historial select restores note+result
- [ ] Backend down disables analyze (dev)
- [ ] Keyboard: tab to mark, chips, analyze, historial items
- [ ] `prefers-reduced-motion`: no jarring transitions
- [ ] No purple gradients / no emoji icons / no invented EHR chrome

---

## Spec coverage self-review

| Spec requirement | Task |
|------------------|------|
| 3-zone workspace | Task 4 |
| Light slate tokens | Task 2 |
| Dark premium tokens | Task 2 |
| Easter egg 5× mark | Task 3 |
| localStorage theme | Task 1–3 |
| Post-unlock control | Task 3 |
| Header + disclaimer + status | Task 3 |
| Nota / Hallazgo / Historial | Task 4–5 |
| API unchanged | Global + all tasks |
| A11y focus / aria-busy / live | Task 5–6 |
| Responsive breakpoints | Task 4 |
| Pro Max skill install | Task 0 (optional) |
| No EHR invent | Global |

No TBD placeholders. Theme function names consistent across Tasks 1–3 (`toggleTheme`, `createEggTracker`, `markThemeUnlocked`).

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-25-ui-ux-redesign.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with checkpoints  

**Which approach?**
