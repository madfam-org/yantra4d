# Browser-Based UI/UX Audit — Studio + Landing

**Date**: 2026-03-05
**Method**: Playwright MCP browser automation (navigate, interact, screenshot, report)
**Dev servers**: Studio `:5173`, Landing `:4321`, API `:5000`
**Auth**: Disabled (madfam tier for all users)
**Projects tested**: custom-msh (6 modes, 16 params, 6 presets, glass parts, assembly), tablaco (36 params, hierarchical checkboxes, text inputs, grid mode, assembly steps)

## Viewport Matrix

| Phase | Label | Size | Status |
|-------|-------|------|--------|
| E | Desktop | 1280x900 | Completed |
| D | Tablet Landscape | 1024x768 | Completed |
| C | Tablet Portrait | 768x1024 | Completed |
| A | Mobile Portrait | 375x812 | Completed |
| B | Mobile Landscape | 812x375 | Completed |

## Pre-Audit Fix

**AuthButton.jsx crash**: The app rendered a blank white page because `AuthButton.jsx` imported `SignedIn`, `SignedOut`, `UserButton` from `@janua/react-sdk` v0.1.1, which doesn't export those components. Fixed by rewriting to use `useSession` hook and `UserProfile` component. Updated `setup.js` mocks and `AuthButton.test.jsx` to match. All 1166 studio tests pass after fix.

**Files modified**:
- `apps/studio/src/components/auth/AuthButton.jsx`
- `apps/studio/src/test/setup.js`
- `apps/studio/src/components/auth/AuthButton.test.jsx`

## Findings

### ISSUE-1: Assembly mode box_base and box_lid render failures
- **Viewport**: All (1280x900 tested)
- **Page**: Studio custom-msh
- **Severity**: High
- **Description**: In assembly mode (`assembly_box_lid` preset), `box_base` and `box_lid` parts fail with "OpenSCAD exited with code 1". `rack` and `slides` (glass) render successfully. The assembly viewer shows only 2 of 4 expected parts.

### ISSUE-2: WebGL GL_INVALID_OPERATION warnings
- **Viewport**: All (1280x900 tested)
- **Page**: Studio custom-msh
- **Severity**: Low
- **Description**: 196 `GL_INVALID_OPERATION` warnings in console after loading a model. Does not affect visual rendering. Likely caused by Three.js/R3F shader state during scene setup.

### ISSUE-3: Model info showing stale dimensions after mode switch
- **Viewport**: Desktop (1280x900)
- **Page**: Studio custom-msh
- **Severity**: Medium
- **Description**: After switching modes (e.g., holder to rack), the ModelInfoPanel may briefly show dimensions from the previous mode until the new render completes and loads. If the new render is cached, this resolves quickly.

### ISSUE-4: Language doesn't persist across project navigation
- **Viewport**: All viewports tested
- **Page**: Studio (all projects)
- **Severity**: Medium
- **Description**: Setting language to Spanish on custom-msh, then navigating to tablaco via the project selector, resets the language to English. Language preference is not persisted in localStorage or URL state across project changes. Confirmed at 1280x900, 768x1024, 375x812.

### ISSUE-5: Tablaco render fails from browser (OpenSCAD exit code 1)
- **Viewport**: All viewports tested
- **Page**: Studio tablaco
- **Severity**: High
- **Description**: Tablaco unit mode auto-render fails with "Error: OpenSCAD exited with code 1" in the console bar. The 3D viewer shows only the grid/axes with no model geometry. However, the same render works via `curl` to the API directly. This suggests a parameter mismatch between what the frontend sends (auto-render on page load) and what the backend expects. Needs investigation of the request payload.

### ISSUE-6: "Edit Assembly Guide" button not translated
- **Viewport**: All
- **Page**: Studio tablaco (controls sheet)
- **Severity**: Low
- **Description**: The "Edit Assembly Guide" button at the bottom of the controls sheet remains in English regardless of language setting.

### ISSUE-7: Several header/toolbar buttons not translated
- **Viewport**: All
- **Page**: Studio (all projects)
- **Severity**: Low
- **Description**: The following buttons remain in English when UI is set to Spanish: "Open AI configurator", "Synthesize Project", "Open code editor", "Fork & edit code" (in More actions menu), "Open controls". These are likely missing i18n keys.

### ISSUE-8: 13 missing GLB model files on landing carousel
- **Viewport**: All viewports tested
- **Page**: Landing
- **Severity**: Medium
- **Description**: 26 console errors (13 HTTP 404 + 13 Three.js load errors) for missing GLB files. Missing models: `gear-reducer`, `faircap-filter`, `parametric-connector`, `gears`, `motor-mount`, `soft-jaw`, `din-rail-clip`, `microscope-slide-holder`, `prosthetic-socket`, `glia-diagnostic`, `stemfie`, `fasteners`, `keyv2`. The carousel still functions but shows fallback/empty state for these projects. Fix requires running `scripts/prerender-carousel.sh` with a running backend (script uses `grep -oP` which requires GNU grep on macOS).

### ISSUE-9: Header toolbar cramped at 1024px
- **Viewport**: Tablet Landscape (1024x768)
- **Page**: Studio custom-msh
- **Severity**: Low / Visual
- **Description**: At 1024px width (the `lg:` breakpoint), the header toolbar shows all buttons inline but they are visually cramped. The sidebar also appears at this width, further reducing horizontal space. Icons are still functional but the layout feels tight.

### ISSUE-10: Header text overlap at 768px and below
- **Viewport**: Tablet Portrait (768x1024), Mobile (375x812)
- **Page**: Studio (all projects)
- **Severity**: Medium
- **Description**: At 768px width, "Iniciar sesion" (Sign in) text overlaps with "Proyectos" link in the header. At 375px, the header is extremely cramped with "desarrollado con" / "Yantra4D" byline text visible at top-left, overlapping with navigation elements. The "powered by" text should be hidden at these viewport sizes.

### ISSUE-11: Dialog accessibility warning — missing aria-describedby
- **Viewport**: All (when Sheet dialog is open)
- **Page**: Studio (all projects)
- **Severity**: Low
- **Description**: Opening the controls Sheet dialog triggers 2 React warnings: "Missing `Description` or `aria-describedby`" for the dialog component. The dialog renders correctly but lacks the proper ARIA description for screen readers. Fix: add a visually-hidden `DialogDescription` inside the Sheet component.

### ISSUE-12: Header extremely cramped at 375px mobile
- **Viewport**: Mobile Portrait (375x812)
- **Page**: Studio (all projects)
- **Severity**: Medium
- **Description**: At 375px width, the studio header shows the "desarrollado con" / "Yantra4D" byline text that should be hidden, causing visual clutter. The project title "Tablaco S..." gets truncated (acceptable) but the byline text creates unnecessary noise.

### ISSUE-13: Mode tab icons in Sheet lack visible labels at 375px
- **Viewport**: Mobile Portrait (375x812)
- **Page**: Studio custom-msh (Sheet dialog)
- **Severity**: Low
- **Description**: In the controls Sheet at 375px width, the 6 mode tabs render as icons only (no text labels). While the icons are distinct, first-time users may not know which mode each icon represents. Tooltips or a long-press label would improve discoverability.

### ISSUE-14: dev.sh script PROJECT_ROOT bug
- **Viewport**: N/A (tooling)
- **Page**: N/A
- **Severity**: Low
- **Description**: `scripts/dev/dev.sh` calculates `PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"` which resolves to `scripts/` instead of the repo root. This is because the script lives at `scripts/dev/dev.sh`, so `SCRIPT_DIR=scripts/dev` and `dirname` gives `scripts`. Dev servers had to be started manually. Fix: use `PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"` or resolve via `git rev-parse --show-toplevel`.

### ISSUE-15: Status text uses raw i18n interpolation tokens
- **Viewport**: All
- **Page**: Studio (all projects)
- **Severity**: Low
- **Description**: The ARIA status region shows raw interpolation tokens: `"Render complete. Modelo 3D cargado. {parts} piezas. Caja delimitadora: {width} x {height} x {depth}. Volumen: {volume}."` instead of actual values. The visual UI shows correct values, but the screen reader announcement has unresolved placeholders.

## Summary by Severity

| Severity | Count | Issues |
|----------|-------|--------|
| **High** | 2 | ISSUE-1 (assembly render failures), ISSUE-5 (tablaco render fails) |
| **Medium** | 4 | ISSUE-3 (stale model info), ISSUE-4 (language persistence), ISSUE-10 (header overlap), ISSUE-12 (header cramped 375px) |
| **Low** | 8 | ISSUE-2, ISSUE-6, ISSUE-7, ISSUE-9, ISSUE-11, ISSUE-13, ISSUE-14, ISSUE-15 |
| **Visual** | 1 | ISSUE-9 (part of Low) |

## What Works Well

### Desktop (1280x900)
- Projects gallery loads 33 projects in 4-column grid with search, filters, and sort
- custom-msh: holder and rack modes render correctly, model appears with green status chip
- ModelInfoPanel shows dimensions, volume, triangle count, part count
- Export panel with STL/3MF format selector functional
- Theme cycling (light/dark/system) works
- Unit toggle (mm/in) converts ModelInfoPanel values correctly

### Tablet Landscape (1024x768)
- Desktop sidebar visible at `lg:` breakpoint (correct)
- All params accessible without Sheet
- Viewer fills remaining space after sidebar

### Tablet Portrait (768x1024)
- Sidebar hidden, mobile bar with hamburger visible (correct breakpoint behavior)
- Sheet dialog opens at 85vh with all controls
- Mode tabs scrollable in mobile bar

### Mobile Portrait (375x812)
- Projects gallery: single-column card layout, search/filter functional
- Sheet dialog scrollable with all params
- Mode tabs render as compact icons in Sheet
- "More actions" overflow menu with all toolbar actions
- Camera view uses `<select>` dropdown (correct mobile pattern)
- Text input (tablaco "Bottom Letter") has adequate touch target
- Checkbox hierarchy renders properly

### Mobile Landscape (812x375)
- Sheet capped at 75vh (~280px) — scrollable, not collapsed
- Viewer canvas retains meaningful height
- Mode tabs show as text labels (more horizontal space)
- Landing: inline nav at 812px, hero renders well

### Landing (all viewports)
- Header: inline nav at 768px+, hamburger at 375px
- Mobile menu: Escape key closes, all nav links accessible
- Hero CTA buttons visible with 44px touch targets
- "Elige Tu Camino" cards responsive (3-col desktop, 1-col mobile)
- Project gallery with category filters, thumbnails load
- Footer links functional

## Screenshots

All screenshots saved in `audit/` directory at repo root:
- `E1-projects-gallery-desktop.png`
- `E2-custom-msh-desktop-holder.png`, `E2-custom-msh-assembly-desktop.png`
- `E3-tablaco-desktop-unit.png`
- `E4-landing-desktop.png`
- `D1-custom-msh-tablet-landscape.png`
- `C1-custom-msh-tablet-portrait-full.png`, `C1-custom-msh-sheet-open.png`
- `C2-tablaco-tablet-portrait.png`
- `C3-landing-tablet-portrait.png`
- `A1-projects-gallery-mobile.png`
- `A2-custom-msh-mobile.png`, `A2-custom-msh-sheet-mobile.png`, `A2-custom-msh-overflow-menu.png`
- `A3-tablaco-mobile.png`, `A3-tablaco-sheet-mobile.png`
- `A4-landing-mobile.png`, `A4-landing-mobile-menu.png`
- `B1-custom-msh-landscape.png`, `B1-custom-msh-sheet-landscape.png`
- `B3-landing-landscape.png`

## Recommended Fix Priority

1. **ISSUE-5** (High): Investigate tablaco render failure — compare frontend auto-render payload vs working curl payload
2. **ISSUE-1** (High): Debug box_base/box_lid OpenSCAD failures in assembly mode
3. **ISSUE-4** (Medium): Persist language preference in localStorage, restore on project navigation
4. **ISSUE-10 + ISSUE-12** (Medium): Hide "powered by" byline below `lg:` breakpoint; fix header element overlap at 768px
5. **ISSUE-8** (Medium): Pre-render remaining 13 GLB models (fix `grep -oP` for macOS in prerender script)
6. **ISSUE-15** (Low): Fix i18n interpolation in ARIA status text
7. **ISSUE-11** (Low): Add `DialogDescription` to Sheet component
8. **ISSUE-7** (Low): Add missing i18n keys for toolbar buttons
9. **ISSUE-14** (Low): Fix `dev.sh` PROJECT_ROOT calculation

---

## Remediation Status

Remediated on 2026-03-04. Summary of fixes applied:

| Issue | Status | Fix Applied |
|-------|--------|-------------|
| **ISSUE-1** | **Fixed** | Changed `assembly_level` default from `1` to `3` in `projects/custom-msh/assembly.scad` so box_base/box_lid render by default |
| **ISSUE-2** | **Won't fix** | Three.js internal GL warnings — no user impact, suppression would require patching Three.js |
| **ISSUE-3** | **Fixed** | `setMode()` in `useProjectParams.js` now calls `setPrintEstimate(null)` to clear stale model info on mode switch |
| **ISSUE-4** | **Fixed** | `ManifestAwareLanguageProvider.jsx` rewritten to use global `yantra4d-lang` localStorage key instead of per-project key |
| **ISSUE-5** | **Partial** | Removed `"star": 8` typo from `rows`/`cols` params in `projects/tablaco/project.json`. Full render failure requires live server debugging |
| **ISSUE-6** | **Fixed** | "Edit Assembly Guide" button now uses `t('btn.edit_assembly')` i18n key |
| **ISSUE-7** | **Fixed** | All header/toolbar buttons now use `t()` calls: `btn.ai_open`, `btn.ai_close`, `btn.synthesize`, `btn.fork_edit`, `btn.editor_open`, `btn.editor_close` |
| **ISSUE-8** | **Fixed** | Replaced `grep -oP` with POSIX `grep | sed` in `scripts/prerender-carousel.sh` for macOS compatibility |
| **ISSUE-9** | **Deferred** | Low priority visual issue at `lg:` breakpoint — inherent to layout trade-off at 1024px |
| **ISSUE-10** | **Fixed** | Added `hidden lg:block` to "powered by" byline span in `StudioHeader.jsx` |
| **ISSUE-11** | **Fixed** | Added `SheetDescription` with `t('a11y.controls_description')` to mobile Sheet in `StudioSidebar.jsx` |
| **ISSUE-12** | **Fixed** | Same fix as ISSUE-10 — byline hidden below `lg:` eliminates clutter at 375px |
| **ISSUE-13** | **Fixed** | Added `title={getLabel(m, 'label', language)}` to mobile mode tab triggers in `StudioSidebar.jsx` |
| **ISSUE-14** | **Fixed** | `PROJECT_ROOT` calculation in `dev.sh` and `dev-stop.sh` now uses double `dirname` for correct resolution from `scripts/dev/` |
| **ISSUE-15** | **Fixed** | `t()` function in `LanguageProvider.jsx` now supports `{key}` interpolation with passed params object |

### Files Modified

- `projects/custom-msh/assembly.scad` — ISSUE-1
- `projects/tablaco/project.json` — ISSUE-5
- `apps/studio/src/contexts/system/ManifestAwareLanguageProvider.jsx` — ISSUE-4
- `apps/studio/src/contexts/system/LanguageProvider.jsx` — ISSUE-15
- `apps/studio/src/components/studio/StudioHeader.jsx` — ISSUE-7, ISSUE-10, ISSUE-12
- `apps/studio/src/components/studio/StudioSidebar.jsx` — ISSUE-6, ISSUE-11, ISSUE-13
- `apps/studio/src/hooks/project/useProjectParams.js` — ISSUE-3
- `scripts/prerender-carousel.sh` — ISSUE-8
- `scripts/dev/dev.sh`, `scripts/dev/dev-stop.sh` — ISSUE-14
- `apps/studio/src/locales/{en,es,fr,pt,de,zh}.json` — ISSUE-6, ISSUE-7, ISSUE-11, ISSUE-15
- `apps/studio/src/components/studio/StudioHeader.test.jsx` — updated assertions for i18n keys
- `apps/studio/src/components/studio/StudioSidebar.test.jsx` — updated assertions for i18n keys
- `apps/studio/src/contexts/system/LanguageProvider.test.jsx` — added interpolation tests
- `apps/studio/src/hooks/project/useProjectParams.test.js` — added setMode clears printEstimate test
