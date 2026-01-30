# Tablaco Studio — Usability Audit Report

**Date**: 2026-01-29
**Mode**: Frontend-only (WASM/fallback manifest)
**Browser**: Chromium (Playwright MCP)
**Viewports tested**: Desktop 1280x800, Tablet 768x1024, Tablet landscape 1024x768, Mobile 375x812

---

## Executive Summary

| Category | Pass | Fail | Warn |
|----------|------|------|------|
| Functionality | 14 | 0 | 2 |
| Accessibility | 5 | 1 | 1 |
| Responsiveness | 3 | 0 | 2 |
| Usability | 8 | 0 | 3 |
| Performance | 3 | 0 | 0 |
| **Total** | **33** | **1** | **8** |

Overall: The application is functional and well-built. One major accessibility gap (slider labels) and several minor UX polish items.

---

## Issues by Severity

### MAJOR (2)

| # | Area | Description | Steps to Reproduce |
|---|------|-------------|-------------------|
| M1 | Accessibility | **Sliders lack `aria-label`** — All 3 parameter sliders (Size, Thickness, Rod Diameter) have no accessible name. Screen readers cannot identify which parameter a slider controls. | Inspect any slider element; `aria-label` is `null`. |
| M2 | UX/State | **Confirm dialog re-triggers with "~0 seconds" estimate** — After canceling the Grid mode confirm dialog, it immediately reappears with an estimate of "~0 seconds". Requires a second Cancel click to dismiss. | Switch to Grid tab → Cancel dialog → dialog reappears with "~0 seconds". |

### MINOR (6)

| # | Area | Description |
|---|------|-------------|
| m1 | UX | **Escape key does not close the confirm render dialog.** Must use Cancel button. Expected: Escape dismisses dialog per standard dialog behavior. |
| m2 | i18n | **3D viewer camera buttons not translated.** Viewport overlay buttons (Iso/Top/Front/Right) remain in English when language is set to Spanish. The sidebar export buttons correctly translate. |
| m3 | Console | **Cryptic error numbers in WASM render console.** After renders, messages like "Error: 1124712" appear in the console log. These are WASM memory addresses, not meaningful to users. |
| m4 | UX | **No feedback when all visibility checkboxes are unchecked.** User gets no message that nothing will render. The render appears to silently complete. |
| m5 | Mobile | **No visual scroll affordance on mobile sidebar.** On 375px viewport, the sidebar is scrollable (action buttons below fold) but there is no scrollbar or visual hint that more content exists below. |
| m6 | Meta | **Page title is "frontend" instead of "Tablaco Studio".** The `<title>` tag in `index.html` was not updated from the Vite default. |

### COSMETIC (3)

| # | Area | Description |
|---|------|-------------|
| c1 | Theme | **Near-white color swatch low contrast in dark mode.** The default color `#e5e7eb` is barely distinguishable from the dark sidebar background. Border helps but contrast is low. |
| c2 | Layout | **"Right" camera button clipped at 1024px width.** In tablet landscape (1024x768), the viewport camera toolbar's rightmost button is partially cut off. |
| c3 | i18n | **Console log messages remain in English.** Render messages ("Generating (unit)...", "Generated STL.") are not translated. Acceptable for a developer-facing log but inconsistent with full i18n. |

---

## Functional Test Results

### Mode Switching
- Unit tab: 3 sliders (Size, Thickness, Rod Diameter), 3 visibility checkboxes, 1 color picker — **PASS**
- Assembly tab: Same 3 sliders, 3 checkboxes, 2 color pickers (Bottom Unit, Top Unit) — **PASS**
- Grid tab: 3 different sliders (Rows, Cols, Rod Extension), 0 checkboxes, 4 color pickers — **PASS**
- Keyboard shortcut Cmd+1 switches to Unit — **PASS**
- Mode switch triggers auto-render with confirm dialog for slow modes — **PASS**

### Inline Number Editing
- Click on value opens `spinbutton` input — **PASS**
- Type new value + Enter commits and triggers render — **PASS**
- Escape cancels edit, reverts to previous value, no render triggered — **PASS**

### Reset to Defaults
- Modified Size (25) reverts to default (20) — **PASS**
- Star icons reappear after reset — **PASS**
- Colors reset to manifest defaults — **PASS**

### Render Workflow
- Auto-render triggers on load (WASM mode) — **PASS**
- Render overlay shows progress bar, percentage, phase text — **PASS**
- Confirm dialog appears for slow renders with time estimate — **PASS**
- Cancel button dismisses dialog — **PASS**

### Theme Toggle
- Light → Dark → System cycle — **PASS**
- Dark theme: sidebar dark, 3D viewer dark background, model white, sliders blue — **PASS**
- Theme persists in localStorage (`vite-ui-theme`) — **PASS**

### Language Toggle
- EN → ES toggle translates: tabs, parameter labels, button labels, section headers, visibility labels, export buttons — **PASS**
- Language persists in localStorage (`tablaco-lang`) — **PASS**

### State Persistence
- All params, colors, mode, theme, language stored in localStorage — **PASS**
- Page reload restores full state — **PASS**

---

## Accessibility (WCAG 2.1 AA)

### Passing
| Criterion | Status |
|-----------|--------|
| Console: `role="log"`, `aria-live="polite"`, `aria-label` | PASS |
| Tabs: `role="tab"`, `aria-selected` | PASS |
| Checkboxes: accessible names via label association | PASS |
| Images/icons: properly handled (alt or aria-hidden) | PASS |
| Sliders: `aria-valuenow`, `aria-valuemin`, `aria-valuemax` present | PASS |

### Failing
| Criterion | Status | Issue |
|-----------|--------|-------|
| Sliders: `aria-label` for accessible name | **FAIL** | M1 — no `aria-label` on any slider |
| Dialog: Escape key dismissal | WARN | m1 — `alertdialog` not closed by Escape |

### Recommendations
- Add `aria-label` to each slider matching the parameter name (e.g., `aria-label="Size (mm)"`)
- Add `onKeyDown` handler for Escape on the confirm dialog (or use Radix `AlertDialog` with proper dismiss behavior)

---

## Responsive Design

| Viewport | Layout | Status |
|----------|--------|--------|
| Desktop 1280x800 | Side-by-side (sidebar left, viewer right) | PASS |
| Tablet landscape 1024x768 | Side-by-side (triggers at `lg` breakpoint) | PASS (minor clipping c2) |
| Tablet portrait 768x1024 | Stacked (sidebar top, viewer bottom) | PASS |
| Mobile 375x812 | Stacked, sidebar scrollable | PASS (no scroll hint m5) |

---

## Performance Benchmarks

| Metric | Value | Rating |
|--------|-------|--------|
| DOM Content Loaded | 946ms | Good (dev build) |
| Full Page Load | 950ms | Good |
| First Contentful Paint | 1444ms | Acceptable |
| JS Heap (idle after render) | 39MB / 64MB | Normal for WASM + Three.js |
| Unit render time (WASM) | ~4.8s | Acceptable for client-side |

---

## Prioritized Fix Recommendations

1. **M1 — Add `aria-label` to sliders** (Accessibility, quick fix)
   - File: `web_interface/frontend/src/components/Controls.jsx`
   - Add `aria-label={param.label}` to each `<Slider>` component

2. **M2 — Fix confirm dialog re-trigger on cancel** (UX bug)
   - File: likely in render trigger logic / mode-switch handler
   - Debounce or guard against re-triggering dialog when canceling

3. **m1 — Add Escape key handler to confirm dialog** (Accessibility)
   - Use Radix `AlertDialog` built-in dismiss or add `onEscapeKeyDown`

4. **m6 — Fix page title** (Quick fix)
   - File: `web_interface/frontend/index.html` — change `<title>` to "Tablaco Studio"

5. **m2 — Translate 3D viewer camera buttons** (i18n)
   - File: `web_interface/frontend/src/components/Viewer.jsx`

6. **m3 — Suppress or format WASM error numbers in console** (UX polish)

7. **m4 — Add "No parts selected" message when all visibility unchecked** (UX)

8. **m5 — Add scroll indicator on mobile sidebar** (UX)

---

*Report generated via Playwright MCP browser automation.*
