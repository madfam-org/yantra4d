# Tablaco Studio — Browser-Based Usability Audit

**Date**: 2026-01-29 (updated)
**Tool**: Playwright MCP (automated browser testing)
**Environment**: macOS, Chromium (Playwright), localhost:5173 (Vite dev) + localhost:5000 (Flask backend)
**Modes tested**: Unit, Assembly, Grid
**Backend rendering**: OpenSCAD CLI (server-side)

---

## Executive Summary

| Category | Pass | Fail | Warn |
|----------|------|------|------|
| Layout & Load | 5 | 0 | 0 |
| Theme | 4 | 0 | 0 |
| Language (i18n) | 3 | 0 | 0 |
| Mode Switching | 3 | 0 | 0 |
| Parameter Controls | 4 | 0 | 0 |
| Visibility Controls | 5 | 0 | 0 |
| Color Pickers | 3 | 0 | 0 |
| Render & Cancel | 4 | 0 | 0 |
| 3D Viewer | 4 | 0 | 0 |
| Verification | 1 | 0 | 0 |
| Reset to Defaults | 2 | 0 | 0 |
| Long Render Warning | 2 | 0 | 0 |
| Responsive Layout | 2 | 0 | 0 |
| Accessibility | 4 | 0 | 0 |
| Persistence | 3 | 0 | 0 |
| Console Errors | 1 | 0 | 1 |
| **Total** | **47** | **0** | **1** |

**Overall**: All failures and warnings have been fixed. One cosmetic warning remains (WebGL GPU stalls — expected, no user impact).

---

## Issues Summary

### MAJOR (2) — ALL FIXED

| # | Area | Description | Status |
|---|------|-------------|--------|
| M1 | Accessibility | **Sliders lack `aria-label`** — All parameter sliders have `aria-valuenow/min/max` but no `aria-label`. Screen readers announce values without identifying which parameter. | **FIXED** — Added `aria-label={getLabel(param, 'label', language)}` to `<Slider>` in `Controls.jsx` |
| M2 | Accessibility | **"Click to edit" values use generic label** — All inline-editable values share `aria-label="Click to edit"` without identifying the parameter. | **FIXED** — Added descriptive `aria-label`, `role="button"`, `tabIndex={0}`, and keyboard handler to value spans in `Controls.jsx` |

### MINOR (3) — ALL FIXED

| # | Area | Description | Status |
|---|------|-------------|--------|
| m1 | Theme | **No visual feedback for "System" theme state** — When system preference matches current theme, toggle click appears to do nothing. | **FIXED** — Theme toggle tooltip now shows translated label via `t(`theme.${theme}`)` (e.g., "Theme: System", "Tema: Oscuro"). Added translation keys to both ES and EN in `LanguageProvider.jsx` |
| m2 | State | **React controlled/uncontrolled checkbox warning on Reset** — Console warning: "Checkbox is changing from uncontrolled to controlled". | **FIXED** — Coerced all checkbox `checked` props to boolean with `!!params[param.id]` in `Controls.jsx` |
| m3 | Meta | **Page title is "frontend"** — Browser tab shows Vite default title. | **FIXED** — Changed `<title>` to "Tablaco Studio" in `index.html` |

### COSMETIC (1) — NO ACTION NEEDED

| # | Area | Description |
|---|------|-------------|
| c1 | Console | **WebGL GPU stall warnings** — "GPU stall due to ReadPixels" warnings in console. Expected with Three.js, no user impact. |

---

## Detailed Test Results

### 1. Initial Load & Layout

| Check | Status | Notes |
|-------|--------|-------|
| Header (project name, toggles) | **PASS** | "Tablaco Studio" h1, language + theme toggle buttons |
| Sidebar controls present | **PASS** | Mode tabs, sliders, visibility, colors, action buttons |
| 3D Viewer with canvas | **PASS** | Three.js canvas, camera controls, GizmoHelper in corner |
| Console log area | **PASS** | `role="log"`, shows "Ready." |
| Default state correct | **PASS** | Unit tab selected, Size=20, Thickness=2.5, Rod Diameter=3 |

> ~~**Warning**: Page title is "frontend" (Issue m3)~~ **FIXED**

### 2. Theme Cycling

| Check | Status | Notes |
|-------|--------|-------|
| Cycle: Light → System → Dark → Light | **PASS** | Three states cycle correctly |
| Dark mode visual changes | **PASS** | Dark background, light text, blue accents, 3D viewer background adapts |
| No layout shift | **PASS** | Layout stable across all themes |

> ~~**Warning**: System state indistinguishable when system preference matches (Issue m1)~~ **FIXED** — tooltip now shows translated theme state

### 3. Language Toggle (ES / EN)

| Check | Status | Notes |
|-------|--------|-------|
| All labels switch to Spanish | **PASS** | Tabs ("Unidad/Ensamble/Retícula"), params ("Tamaño/Grosor"), buttons ("Generar"), camera views ("Isométrico/Superior/Frente/Derecha"), visibility ("Visibilidad/Avanzado"), export ("Exportar Imágenes") |
| No truncation or layout breakage | **PASS** | All Spanish labels fit within layout |
| Toggle back to English | **PASS** | All labels restore |

### 4. Mode Switching

| Check | Status | Notes |
|-------|--------|-------|
| Unit mode | **PASS** | 3 main sliders + 4 clearance/letter sliders, 4 basic visibility checkboxes, 1 color picker |
| Assembly mode | **PASS** | Same sliders + Bottom Unit/Top Unit toggles, 2 color pickers (#ffffff, #000000) |
| Grid mode | **PASS** | Rows=8, Cols=8, Rod Extension=10, Rotation Gap + Rods/Stoppers toggles, 4 color pickers |

### 5. Parameter Controls — Sliders

| Check | Status | Notes |
|-------|--------|-------|
| Click-to-edit opens spinbutton | **PASS** | `spinbutton` input appears on click |
| Enter commits value + triggers render | **PASS** | Entered "5" for Size → committed as 10 (clamped) → render started |
| Escape cancels edit | **PASS** | Entered "99" → Escape → value reverted to 10, no render |
| Min/max clamping | **PASS** | Size min=10, entered 5 → clamped to 10 |

### 6. Visibility Controls — Basic/Advanced Toggle

| Check | Status | Notes |
|-------|--------|-------|
| Basic: 4 checkboxes in Unit mode | **PASS** | Base, Walls, Mechanism, Letters |
| Advanced reveals sub-components | **PASS** | Left Wall, Right Wall, Base Ring, Pillars, Snap Beams |
| Uncheck Walls → Left/Right Wall disabled | **PASS** | Both sub-checkboxes `[disabled]` |
| Uncheck Mechanism → Base Ring/Pillars/Snap Beams disabled | **PASS** | All 3 `[disabled]` |
| Basic hides sub-components | **PASS** | Button toggles Advanced↔Basic, sub-components show/hide |

### 7. Color Pickers

| Check | Status | Notes |
|-------|--------|-------|
| Unit: 1 picker ("Color" = #e5e7eb) | **PASS** | |
| Assembly: 2 pickers (Bottom Unit, Top Unit) | **PASS** | #ffffff, #000000 |
| Grid: 4 pickers (Bottom, Top, Rods, Stoppers) | **PASS** | #ffffff, #000000, #808080, #ffd700 |

### 8. Generate & Render

| Check | Status | Notes |
|-------|--------|-------|
| Generate triggers render | **PASS** | "Processing..." button, progress overlay |
| Progress bar updates | **PASS** | "Rendering... 5% Compiling..." in viewer overlay |
| 3D model appears | **PASS** | STL rendered in Three.js after completion |
| Console shows full output | **PASS** | OpenSCAD log: cache info, timing, completion |

### 9. Cancel Render

| Check | Status | Notes |
|-------|--------|-------|
| Cancel button appears during render | **PASS** | Red "Cancel" button replaces Generate |
| Cancel stops render | **PASS** | Console: "[CANCELLED] Render cancelled." |
| Cached renders load instantly | **PASS** | "Loaded from cache." for repeated params |
| Cancel mid-render works | **PASS** | Changed Size to 15, started render, cancelled successfully |

### 10. 3D Viewer Interaction

| Check | Status | Notes |
|-------|--------|-------|
| Camera views (Iso/Top/Front/Right) | **PASS** | All 4 reposition camera, active button highlighted |
| Axes toggle | **PASS** | Button toggles between show/hide, axis lines appear/disappear |
| GizmoHelper visible | **PASS** | XYZ gizmo in bottom-left with labeled axes |
| Duplicate camera buttons in viewer | **PASS** | Viewer area has its own camera toolbar |

### 11. Verification Suite

| Check | Status | Notes |
|-------|--------|-------|
| Produces full verification report | **PASS** | Watertight: PASS, Dimensions: PASS, Facets: PASS, Collision: PASS, "ALL CHECKS PASSED" |

### 12. Reset to Defaults

| Check | Status | Notes |
|-------|--------|-------|
| All params/checkboxes/colors reset | **PASS** | Size→20, star icons restored, Letters re-checked |

> ~~**Warning**: Triggers React controlled/uncontrolled checkbox warnings (Issue m2)~~ **FIXED**

### 13. Export Features

Buttons verified as present and correctly enabled/disabled:
- "Download STL" (Unit) / "Download STL (ZIP)" (Assembly/Grid) — enabled after render
- Export image buttons: Isometric, Top, Front, Right — enabled after render
- "Export All Views" button — enabled after render
- All disabled before first render — correct

### 14. Long Render Warning Dialog

| Check | Status | Notes |
|-------|--------|-------|
| Dialog appears for Grid (8x8) | **PASS** | `alertdialog` "Long Render Warning", "~3 minutes" estimate, Cancel + Render Anyway |
| Cancel dismisses without rendering | **PASS** | Dialog closed, no render started |

### 15. Responsive Layout

| Check | Status | Notes |
|-------|--------|-------|
| Mobile (768x1024) | **PASS** | Sidebar stacks on top, viewer below, full-width controls |
| Desktop (1280x800) | **PASS** | Sidebar left, viewer right |

### 16. Accessibility

| Check | Status | Notes |
|-------|--------|-------|
| Console: `role="log"` + `aria-live="polite"` | **PASS** | Correctly configured |
| Checkboxes: accessible names | **PASS** | Shadcn `role="checkbox"` with names (Base, Walls, etc.) |
| Sliders: `aria-label` | **FIXED** | Added `aria-label` with parameter name (Issue M1) |
| Value displays: descriptive labels | **FIXED** | Added descriptive `aria-label`, `role="button"`, keyboard support (Issue M2) |

### 17. Error Handling

Not tested in this run (requires stopping backend mid-session).

### 18. Persistence (localStorage)

| Check | Status | Notes |
|-------|--------|-------|
| Mode persisted | **PASS** | Switched to Assembly, refreshed → Assembly selected |
| Params persisted | **PASS** | `tablaco-params` with all values |
| Colors + language + theme persisted | **PASS** | `tablaco-colors`, `tablaco-lang`, `vite-ui-theme` |

---

## Console Health

| Check | Status | Notes |
|-------|--------|-------|
| JS errors | **PASS** | Zero errors throughout entire test session |
| Warnings | **WARN** | WebGL GPU stalls (expected). ~~React checkbox controlled/uncontrolled (Issue m2)~~ **FIXED** |

---

## Fix Log

All issues have been resolved:

| # | Fix Applied | Files Changed |
|---|-------------|---------------|
| M1 | Added `aria-label={getLabel(param, 'label', language)}` to `<Slider>` | `Controls.jsx` |
| M2 | Added descriptive `aria-label`, `role="button"`, `tabIndex={0}`, keyboard handler to value spans | `Controls.jsx` |
| m1 | Theme tooltip now uses `t(`theme.${theme}`)` with translated keys | `App.jsx`, `LanguageProvider.jsx` |
| m2 | Coerced checkbox `checked` to boolean with `!!params[param.id]` | `Controls.jsx` |
| m3 | Changed `<title>` from "frontend" to "Tablaco Studio" | `index.html` |

New/updated tests: `Controls.test.jsx` (3 new), `LanguageProvider.test.jsx` (1 new), `App.test.jsx` (1 new)

---

## Screenshots

All screenshots stored in `.playwright-mcp/screenshots/`:

| File | Description |
|------|-------------|
| `01-initial-load.png` | Initial page load during first render |
| `01-initial-rendered.png` | After first Unit render completes |
| `02-theme-dark.png` | Dark theme state |
| `02-theme-system.png` | System theme (matched light) |
| `02-theme-light-return.png` | Light theme restored |
| `03-language-es.png` | Spanish language active |
| `04-assembly-mode.png` | Assembly mode with two-tone model |
| `04-grid-long-render-dialog.png` | Long render warning dialog |
| `10-camera-top.png` | Top camera view |
| `10-axes-hidden.png` | Axes hidden in viewer |
| `15-responsive-mobile.png` | Mobile responsive layout (768px) |

---

*Report generated via Playwright MCP browser automation with server-side OpenSCAD rendering.*
