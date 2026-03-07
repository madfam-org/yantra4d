# Browser Audit — March 2026 (Round 2)

**Date**: 2026-03-06
**Method**: Playwright MCP browser automation against Docker stack
**Stack**: `docker compose up --build` (backend:5000, studio:3000, landing:4321, redis:6379)
**Auth**: Disabled (`AUTH_ENABLED=false` — madfam tier, all features unlocked)
**Branch**: `audit/round-2-remediation`
**Projects tested**: gridfinity, tablaco, custom-msh
**Viewports**: 1280x900, 1024x768, 768x1024, 375x812, 812x375

---

## Summary

| Severity | Count |
|----------|-------|
| **High** | 3 |
| **Medium** | 2 |
| **Low** | 1 |
| **Total** | **6** |

| Category | High | Medium | Low |
|----------|------|--------|-----|
| Responsive Layout | 1 | 0 | 0 |
| Render & Export | 1 | 1 | 0 |
| Export / Download | 1 | 0 | 0 |
| Navigation & Routing | 0 | 1 | 0 |
| i18n & Localization | 0 | 0 | 1 |

---

## Issues

### ISSUE-R2-1: Mobile controls completely inaccessible below 1024px (HIGH)

**Viewport**: 375x812, 768x1024, 812x375 (all viewports < 1024px)
**Projects**: ALL (gridfinity, tablaco, custom-msh)
**Category**: Responsive Layout

**Description**: The `StudioSidebar` component renders both a desktop sidebar (`hidden lg:flex`) and a mobile controls bar (`lg:hidden`) with a Sheet trigger (hamburger menu + mode tabs). However, in `App.jsx:202`, the `StudioSidebar` is wrapped in a parent container with `hidden lg:flex`:

```jsx
{/* App.jsx:202 */}
<div className="hidden lg:flex flex-col flex-1 min-w-[280px] ...">
  <StudioSidebar ... />
</div>
```

Since the parent is `hidden` below `lg` (1024px), the mobile bar inside `StudioSidebar` is **never visible** on mobile/tablet portrait. The hamburger button ("Open controls"), mode tabs (Bin/Baseplate/Lid), presets, and all sidebar content have zero dimensions in the DOM.

**Impact**: Mobile and tablet portrait users have **zero access** to:
- Parameter controls (sliders, checkboxes, text inputs)
- Mode switching (Bin/Baseplate/Lid, Unit/Assembly/Grid, etc.)
- Presets
- Export panel (all 7 format buttons)
- BOM panel
- Generate/Cancel buttons
- Compare mode
- All Design/View/BOM/Export tabs

The 3D viewer renders correctly, but users can only view the default model — they cannot customize, export, or interact with any controls.

**Fix**: Move the mobile bar rendering outside the `hidden lg:flex` parent, or restructure the layout so `StudioSidebar` is not wrapped in a desktop-only container. The `StudioSidebar` component already has correct responsive logic internally — only the parent wrapper in `App.jsx` is wrong.

**Screenshots**:
- `audit/G4-gridfinity-mobile-portrait-v2.png` — Gridfinity 375x812: 3D viewer only, no controls
- `audit/G5-gridfinity-tablet-portrait.png` — Gridfinity 768x1024: same issue
- `audit/G7-gridfinity-mobile-landscape.png` — Gridfinity 812x375: same issue
- `audit/T4-tablaco-mobile-portrait.png` — Tablaco 375x812: same issue
- `audit/M3-custom-msh-mobile-portrait.png` — Custom-MSH 375x812: same issue

---

### ISSUE-R2-2: custom-msh assembly mode — box_base and box_lid render failure (HIGH, PERSISTS)

**Viewport**: 1280x900 (desktop)
**Project**: custom-msh
**Category**: Render & Export

**Description**: In assembly mode, 2 of 4 parts fail to render:
- `rack` — renders OK
- `slides` — renders OK
- `box_base` — `[ERROR] box_base: Render failed with code 1`
- `box_lid` — `[ERROR] box_lid: Render failed with code 1`

This is the same as **ISSUE-1 from the March audit** (Round 1). The OpenSCAD process exits with code 1 for these two parts. Assembly mode shows only 2 of 4 expected parts.

**Screenshot**: `audit/M2-custom-msh-assembly-partial.png`

---

### ISSUE-R2-3: Export format selection is UI-only — downloads always serve cached GLB (HIGH)

**Viewport**: 1280x900 (desktop)
**Projects**: ALL (gridfinity, tablaco, custom-msh)
**Category**: Export / Download

**Description**: The ExportPanel displays all 7 format buttons (STL, 3MF, OFF, STEP, GLB, GLTF, OBJ) and the button label updates correctly when a format is selected. However, clicking "Download {format}" always downloads the cached GLB render file — the `export_format` parameter is **never sent** in the download request.

The download button fetches the pre-rendered GLB file regardless of format selection. Network inspection shows no `export_format` query parameter on the download URL. This means:
- STL download actually serves GLB
- STEP download actually serves GLB
- OBJ download actually serves GLB
- All 7 formats serve the same GLB file

The format selector is purely cosmetic with no functional effect on the downloaded file.

**Screenshot**: `audit/G2-gridfinity-export-7formats.png` — Shows all 7 format buttons visible

---

### ISSUE-R2-4: Preset "Standard Baseplate" does not auto-switch mode (MEDIUM)

**Viewport**: 1280x900 (desktop)
**Project**: gridfinity
**Category**: Navigation & Routing

**Description**: Clicking the "Standard Baseplate (2x2)" preset on the Cup mode page updates the URL to `/cup/baseplate_std` but does not switch the active mode from "Cup" to "Baseplate". The user remains on Cup mode with baseplate parameters applied, producing a confusing state where the mode tab says "Bin" but parameters belong to a baseplate preset. Same for "Standard Lid" preset — stays on Cup mode.

Expected behavior: presets that belong to a different mode should auto-switch the mode tab.

---

### ISSUE-R2-5: Model info dimensions do not update on mode switch without re-render (MEDIUM)

**Viewport**: 1280x900 (desktop)
**Project**: gridfinity
**Category**: Render & Export

**Description**: After switching modes (e.g., Cup to Baseplate), the Model Info panel retains stale dimensions from the previous mode's model until a new render completes. If the render is served from cache, the update is fast enough to be unnoticeable. But if there's a delay, stale data is displayed.

This was **ISSUE-3 from the March audit** — partially improved but still observable in slow-render scenarios.

---

### ISSUE-R2-6: Minor i18n inconsistency — "Open Studio" in carousel not translated (LOW)

**Viewport**: 375x812 (mobile landing)
**Project**: Landing page
**Category**: i18n & Localization

**Description**: The landing page defaults to Spanish. Most content is translated, but the 3D carousel's "Open Studio" CTA button text and "Hyperobject" badge remain in English. The gallery grid cards correctly show "Abrir en Studio" but the carousel overlay shows "Open Studio".

---

## Comparison with March Audit (Round 1)

| March Issue | March Severity | Round 2 Status | Notes |
|-------------|---------------|----------------|-------|
| ISSUE-1: custom-msh assembly render (box_base/box_lid) | High | **PERSISTS** (ISSUE-R2-2) | Still fails with code 1 |
| ISSUE-5: tablaco render failure | High | **RESOLVED** | Unit mode auto-render succeeds, all 3 modes work |
| ISSUE-3: stale model info on mode switch | Medium | **IMPROVED** (ISSUE-R2-5) | Less noticeable with cache, but still present |
| ISSUE-4: language not persistent across navigation | Medium | **RESOLVED** | Language persists across project switching |
| ISSUE-8: 13 missing GLB models on landing carousel | Medium | **RESOLVED** | `AVAILABLE_GLBS` allowlist prevents 404s; only 2 GLBs requested, both 200 OK |
| ISSUE-9: header cramped at 1024px tablet landscape | Medium | **RESOLVED** | "Powered by" uses `hidden xl:block`; header clean at 1024px |
| ISSUE-6/7: untranslated strings | Low | **MOSTLY RESOLVED** (ISSUE-R2-6) | Minor carousel text remains in English |

### New Issues Found

| New Issue | Severity | Category |
|-----------|----------|----------|
| ISSUE-R2-1: Mobile controls inaccessible below 1024px | High | Responsive Layout |
| ISSUE-R2-3: Export format selection non-functional | High | Export / Download |
| ISSUE-R2-4: Preset doesn't auto-switch mode | Medium | Navigation & Routing |

---

## Positive Findings

### Desktop (1280x900) — All 3 Projects
- 3D viewer renders correctly for gridfinity (Cup, Baseplate, Lid modes), tablaco (Unit, Assembly, Grid modes), custom-msh (Holder, Rack modes)
- Mode switching triggers auto-render with SSE streaming progress
- Cached renders load instantly on mode re-visit
- Camera views (Isometric, Top, Front, Right) work correctly
- Orthographic toggle works
- Model Info panel displays dimensions, volume, triangles, parts
- Print Estimate overlay shows material, infill, time, weight, filament, cost
- Parameter sliders, checkboxes, and text inputs are functional
- Presets update parameter values and trigger re-render (within same mode)
- Dark mode toggle works (system/light/dark cycling)
- Project navigation via ProjectSelector dropdown works across all 3 projects
- Console panel shows render progress and status messages
- BOM panel accessible on gridfinity (Documents tab)
- Export panel shows all 7 format buttons with correct labels
- Assembly steps visible for gridfinity and tablaco
- Undo/Redo (Cmd+Z / Cmd+Shift+Z) functional

### Tablet Landscape (1024x768)
- Desktop sidebar renders correctly at this breakpoint
- All controls, mode tabs, parameter sliders visible and functional
- Header not cramped (ISSUE-9 resolved)
- Print Estimate panel visible alongside console

### Landing Page (Desktop + Mobile)
- All sections render: Hero, Choose Your Path, Gallery, Before/After, For Makers, For Creators, How It Works, Open Source, CTA
- 3D carousel loads GLBs without 404s
- Gallery grid shows 14 projects with category filtering
- "Abrir Studio" CTA navigates to studio
- Mobile: hamburger menu works, Escape key closes it
- Mobile: hero text sizing correct, CTAs accessible
- Spanish/English content parity maintained
- Footer links accessible

---

## Audit Coverage

### Phases Completed
- [x] Phase 0: Stack setup + health verification
- [x] Phase 1A: Gridfinity desktop (modes, params, presets, export, BOM, assembly, viewer tools)
- [x] Phase 1B: Tablaco desktop (3 modes, params, assembly, grid render)
- [x] Phase 1C: Custom-MSH desktop (holder, rack, assembly failure)
- [x] Phase 2: Cross-project features (navigation, theme, language, undo/redo)
- [x] Phase 3-V1: Desktop 1280x900 (covered in Phase 1-2)
- [x] Phase 3-V2: Tablet landscape 1024x768
- [x] Phase 3-V3: Tablet portrait 768x1024
- [x] Phase 3-V4: Mobile portrait 375x812
- [x] Phase 3-V5: Mobile landscape 812x375
- [x] Phase 4A: Landing desktop
- [x] Phase 4B: Landing mobile
- [x] Phase 5: Findings report (this document)

### Phases Blocked by ISSUE-R2-1
Mobile/tablet portrait testing of parameter controls, export panel interaction, BOM, assembly steps, presets, and mode switching was **blocked** because the controls sidebar is completely inaccessible below 1024px. These features could only be verified at desktop (1280x900) and tablet landscape (1024x768).

---

## Screenshots Index

| File | Viewport | Description |
|------|----------|-------------|
| `audit/G1-gridfinity-initial-desktop.png` | 1280x900 | Gridfinity Cup mode initial load |
| `audit/G2-gridfinity-export-7formats.png` | 1280x900 | Export panel with 7 format buttons |
| `audit/G3-gridfinity-top-view.png` | 1280x900 | Top camera view |
| `audit/G4-gridfinity-mobile-portrait-v2.png` | 375x812 | Mobile: 3D viewer only, no controls |
| `audit/G5-gridfinity-tablet-portrait.png` | 768x1024 | Tablet portrait: no controls |
| `audit/G6-gridfinity-tablet-landscape.png` | 1024x768 | Tablet landscape: full sidebar visible |
| `audit/G7-gridfinity-mobile-landscape.png` | 812x375 | Mobile landscape: no controls |
| `audit/T1-tablaco-initial-desktop.png` | 1280x900 | Tablaco Unit mode render (ISSUE-5 resolved) |
| `audit/T2-tablaco-assembly-desktop.png` | 1280x900 | Tablaco Assembly mode (2 parts) |
| `audit/T3-tablaco-grid-desktop.png` | 1280x900 | Tablaco Grid mode (5 parts, 2x2) |
| `audit/T4-tablaco-mobile-portrait.png` | 375x812 | Tablaco mobile: no controls |
| `audit/M1-custom-msh-holder-desktop.png` | 1280x900 | Custom-MSH holder mode |
| `audit/M2-custom-msh-assembly-partial.png` | 1280x900 | Assembly: box_base/box_lid ERROR |
| `audit/M3-custom-msh-mobile-portrait.png` | 375x812 | Custom-MSH mobile: no controls |
| `audit/X1-dark-mode-custom-msh.png` | 1280x900 | Dark mode (system toggle) |
| `audit/X2-dark-mode-attempt2.png` | 1280x900 | Dark mode confirmed |
| `audit/L1-landing-desktop-hero.png` | 1280x900 | Landing hero (Spanish) |
| `audit/L2-landing-gallery-desktop.png` | 1280x900 | Landing gallery with 3D carousel |
| `audit/L3-landing-mobile-hero.png` | 375x812 | Landing mobile hero |
| `audit/L4-landing-mobile-menu.png` | 375x812 | Landing mobile menu open |

---

## Recommended Fix Priority

1. **ISSUE-R2-1** (High): Move `StudioSidebar` mobile bar outside `hidden lg:flex` parent in `App.jsx` — ~10 lines changed, unblocks entire mobile experience
2. **ISSUE-R2-3** (High): Wire `export_format` parameter through download request — ExportPanel format selection must pass format to API
3. **ISSUE-R2-2** (High, persists): Debug custom-msh `box_base.scad` / `box_lid.scad` OpenSCAD errors — likely SCAD syntax or module dependency issue
4. **ISSUE-R2-4** (Medium): Auto-switch mode when a preset targets a different mode
5. **ISSUE-R2-5** (Medium): Clear Model Info on mode switch before new render completes
6. **ISSUE-R2-6** (Low): Translate carousel "Open Studio" and "Hyperobject" badge to Spanish
