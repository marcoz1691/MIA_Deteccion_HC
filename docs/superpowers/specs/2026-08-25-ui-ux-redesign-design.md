# Design: UI/UX Redesign — MIA Detección HC

**Date:** 2026-08-25  
**Status:** Approved  
**Scope:** Frontend redesign only (`frontend/`). No API contract changes.  
**Design intelligence:** [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (local repo + Cursor skill install).

## Context

MIA · CITIMED is a React (Vite) prototype that analyzes clinical notes for inconsistencies (TF-IDF · LLM · RAG) and persists results in SQLite via the existing API.

**Current UI:** Dark single-column/workspace layout with Nota, Resultados, and Historial stacked; Sora + IBM Plex Mono; metal/neutral palette.

**Goals (approved):**
- Full UX redesign (not polish-only).
- Primary audiences: **demo/presentation** and **clinician day-to-day**.
- Visual direction and layout pattern guided by UI UX Pro Max for healthcare / clinical SaaS, then adapted.

## Approach (selected)

**Enfoque 1 — Clinical workspace with demo impact**

One product shell: strong brand header + two-column note/finding workspace + collapsible historial rail. Demo clarity comes from guided empty state and prominent finding panel, not a separate wizard or dual-mode UI.

Rejected alternatives:
- Guided step wizard only — too much friction for daily clinical use.
- Dual Presentación/Clínico modes — doubles maintenance surface.

## Architecture

Single app shell (no new routes):

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER: MIA·CITIMED | short disclaimer | API status (dev) │
├──────────┬──────────────────────────────┬───────────────────┤
│ HISTORIAL│  NOTA CLÍNICA                │  HALLAZGO         │
│ (rail)   │  demo cases + textarea       │  alert / empty    │
│ collaps. │  advanced options (details)  │  sentence + scores│
│          │  [Analizar nota]             │  RAG evidence     │
└──────────┴──────────────────────────────┴───────────────────┘
```

### Responsive behavior

| Breakpoint | Layout |
|------------|--------|
| ≥1024px | 3 zones: rail ~240px \| note ~1fr \| finding ~1fr |
| Tablet | Historial collapsed to icons/drawer; note above finding |
| Mobile | Vertical stack: note → finding → historial |

### Constraints

- Technical controls (mock LLM, language) remain under “Opciones de análisis”.
- Finding panel is the visual focus after analysis (alert/OK state).
- Disclaimer remains visible (research prototype; not clinical decision substitute).

## Visual design system

Source: UI UX Pro Max `--design-system` for healthcare + medical SaaS, adapted after visual review.

**Style:** Modern Soft UI + Swiss Minimalism (healthtech SaaS 2025), not mint-pastel “hospital form”. Soft depth, not neumorphism.

**Themes (approved):**
- **Default — Light slate moderno (B):** cool slate page `#F4F6F8`, white cards, teal `#0D9488`, CTA emerald `#059669`. Better for clinical reading and projectors.
- **Easter egg — Dark premium (A):** charcoal `#0B0F14`, elevated cards `#12181F`, teal accent `#2DD4BF`, CTA `#10B981`, soft ambient teal glow. Feels more modern/demo-tech.

Default remains **light**. Dark is **not** a visible settings toggle in the main chrome; it is unlocked via easter egg (see below). Preference persists in `localStorage` once discovered.

### Easter egg — theme switch

| Rule | Detail |
|------|--------|
| Trigger | Click the brand diamond mark **5 times** within ~2s (or equivalent: 5 activations) |
| Effect | Toggle light ↔ dark; brief toast “Modo oscuro” / “Modo claro” (auto-dismiss) |
| Persist | `localStorage` key e.g. `mia-theme` = `light` \| `dark` |
| A11y | After unlock, optional subtle control may appear in header (sun/moon) so keyboard users are not trapped; until unlock, no discoverable theme button |
| Respect | If user has never set preference, do **not** auto-follow `prefers-color-scheme` for dark (avoids surprise); once set, honor stored value |

Reference mockups: `assets/mia-citimed-mockup-light-modern.png`, `assets/mia-citimed-mockup-dark-modern.png` (Cursor project assets; optional copy into repo `docs/` later).

### Color tokens — light (default)

| Role | Hex | CSS variable | Use |
|------|-----|--------------|-----|
| Primary | `#0D9488` | `--color-primary` | Brand, links, focus ring |
| Accent / CTA | `#059669` | `--color-accent` | Analizar button |
| Background | `#F4F6F8` | `--color-background` | Page |
| Surface | `#EEF1F4` | `--color-surface` | Shell |
| Card | `#FFFFFF` | `--color-card` | Panels |
| Foreground | `#0F172A` | `--color-foreground` | Body text |
| Muted | `#64748B` | `--color-muted-foreground` | Hints |
| Border | `#E5E7EB` | `--color-border` | Dividers |
| Destructive / Alert | `#EF4444` | `--color-destructive` | Alerta |
| OK | `#059669` | `--color-ok` | Sin alerta |
| Warn | `#D97706` | `--color-warn` | Notices / mock |

### Color tokens — dark (easter egg)

| Role | Hex | CSS variable (same names) | Use |
|------|-----|---------------------------|-----|
| Primary | `#2DD4BF` | `--color-primary` | Brand / focus |
| Accent / CTA | `#10B981` | `--color-accent` | Analizar |
| Background | `#0B0F14` | `--color-background` | Page (+ soft teal glow OK) |
| Surface | `#0F141B` | `--color-surface` | Shell |
| Card | `#12181F` | `--color-card` | Panels |
| Foreground | `#E8EEF2` | `--color-foreground` | Text |
| Muted | `#8B95A1` | `--color-muted-foreground` | Hints |
| Border | `rgba(255,255,255,0.08)` | `--color-border` | Hairlines |
| Destructive / Alert | `#F87171` | `--color-destructive` | Alerta |
| OK | `#34D399` | `--color-ok` | Sin alerta |
| Warn | `#FBBF24` | `--color-warn` | Notices |

Implementation: `data-theme="light"|"dark"` on `<html>` (or `#root`) swapping the same CSS variables.

### Typography

- Headings: **Figtree**
- Body: **Noto Sans**
- Mono (scores/IDs only): IBM Plex Mono (or current mono stack)

### Shape & motion

- Radius: 12–14px
- Shadow light: `0 2px 8px rgba(15, 23, 42, 0.06)`; dark: soft bloom / hairline only
- Transitions: 150–250ms (including theme crossfade)
- Respect `prefers-reduced-motion`

### Anti-patterns (do not ship)

- Mint pastel wash as default (`#F0FDFA` hospital look) — superseded by slate light
- Dark as the only/default theme
- Neon cyberpunk, purple AI gradients
- Emojis as icons (Lucide/Heroicons SVG)
- Visible “Dark mode” marketing toggle in the primary demo path (easter egg only; post-unlock control OK)

## Components

| Component | Responsibility |
|-----------|----------------|
| `HeaderBrand` | Mark (easter egg theme toggle) + MIA·CITIMED + title; disclaimer; status pill; optional sun/moon after unlock |
| `HistorialRail` | List (date, Alerta/OK pill, preview); select restores note+result; delete/clear; collapsible |
| `NotaWorkspace` | Demo case chips, textarea, char count, advanced details, primary CTA |
| `HallazgoPanel` | Empty (3 demo steps), loading skeleton + hint, result banner + sentence + scores + RAG, error banner |

### Interaction states

- **Nota:** idle · loading (`aria-busy`) · error inline; CTA disabled when empty or backend down
- **Hallazgo:** empty · loading · success (alert/ok) · error
- Micro-interactions: visible hover/focus on chips, buttons, rail items; no parallax or heavy stagger

### Out of scope

- Auth, new routes, analytics dashboard charts
- Full settings page / theme picker in main IA (easter egg + optional post-unlock icon only)
- Backend/API schema changes
- Invented EHR features (patient profiles, Exportar reporte, Nueva nota) — not in product

## Data flow

Unchanged API surface (`analizarNota`, `fetchHistorial`, delete/clear, `healthCheck`):

1. Dev: health → status + load historial
2. Edit note / pick example → clear active finding selection as today
3. Analyze → show result + refresh historial (`historial_id`)
4. Historial select → restore note + result (no re-LLM)
5. Delete / clear → API + UI sync

### Error matrix

| Case | UI |
|------|-----|
| Backend offline | CTA disabled + status pill |
| `/historial` 404 | Message in rail |
| Analysis failure | Banner in HallazgoPanel |
| Historial delete/clear failure | Banner in rail; list unchanged |

## Accessibility

- Associated labels; visible focus ring using primary
- `aria-live` on finding panel; `aria-busy` while analyzing
- Contrast ≥ 4.5:1 (light mode)
- `prefers-reduced-motion` respected
- Semantic buttons/nav; no clickable `div`s for primary actions

## Success criteria

1. **Demo (<2 min):** pick case → Analizar → alert sentence obvious without confusing scroll
2. **Clinical:** note and finding side-by-side; historial reachable in ≤1 click
3. **Compatibility:** same API contracts; frontend-only changes (CSS + React layout)
4. **Pro Max checklist:** no emoji icons, cursor-pointer on clickables, focus visible, responsive 375 / 768 / 1024 / 1440

## Implementation outline (for later plan)

1. Install UI UX Pro Max skill into this repo (`.cursor/skills/ui-ux-pro-max/`) for ongoing design queries
2. Optionally persist design system MASTER via Pro Max `--persist` under `design-system/`
3. Replace tokens in `frontend/src/styles.css` with light + dark variable sets (`data-theme`)
4. Add theme easter egg (5× click on brand mark) + `localStorage` + brief toast; optional header icon after unlock
5. Restructure `App.jsx` layout (rail + two columns)
6. Update `NotaInput`, `ResultadosPanel`, `HistorialPanel` for new structure/states
7. Manual pass: demo path, clinical path, light/dark, a11y smoke, responsive breakpoints

## Decisions log

| Decision | Choice |
|----------|--------|
| Scope | Full redesign (B) |
| Audience | Demo + clinician (A+B) |
| Visual | Pro Max healthcare/SaaS guidance (D) |
| Layout | Pro Max-adapted clinical workspace (D → Enfoque 1) |
| Theme | Light slate moderno default + dark premium easter egg (5× click mark) |
| Modes | Single UI (no dual Presentación/Clínico) |
| Backend | No contract changes |
| Visual refs | Light + dark modern mockups (v3 direction) |
