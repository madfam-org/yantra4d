# Full-Stack Headed Audit: Landing + Studio + API

**Date**: 2026-02-13
**Environment**: macOS Darwin 22.6.0, OpenSCAD v2021.01, Python 3.13, Node 22
**Auditor**: Claude Opus 4.6 (headed Playwright MCP)

---

## Summary

| Area | Result | Notes |
|------|--------|-------|
| **API Health** | PASS | All endpoints respond correctly |
| **API Rendering** | PASS | SSE streaming + sync render work (torus-knot, maze, julia-vase) |
| **API Multi-project** | PASS | 19 projects discovered and accessible |
| **API Error handling** | PASS | 404 for invalid slugs, 400 for missing fields |
| **Studio Initial Load** | PASS | Header, mode tabs, sliders, 3D viewer with grid/axes |
| **Studio Project Switching** | PASS | Dropdown selector works, manifests load, controls update |
| **Studio Parameter Controls** | PASS | Click-to-edit, slider, presets, Reset to Defaults |
| **Studio Rendering** | PASS | Auto-render, SSE progress, STL displayed in Three.js |
| **Studio Undo/Redo** | PASS | Undo reverts, Redo restores, buttons enable/disable correctly |
| **Studio Camera Views** | PASS | Isometric, Top, Front, Right all switch correctly |
| **Studio Theme** | PASS | Light → dark → system cycle, dark class toggled on `<html>` |
| **Studio Language** | PASS | 6 languages (EN, ES, PT, FR, DE, ZH), all UI text changes |
| **Studio Share** | PASS | "Link copied!" toast, URL with `?p=` param |
| **Studio Responsive** | PASS | Mobile layout collapses sidebar, shows viewer with hamburger |
| **Studio Print Estimate** | PASS | Time/weight/filament/cost overlay after render |
| **Studio Projects View** | **FIXED** | Was crashing — i18n object rendered as React child |
| **Studio Projects → Studio nav** | BUG | Clicking card navigates URL but doesn't switch project |
| **Landing Initial Load** | PASS | All sections render: Hero, Gallery, Features, Demo, Footer |
| **Landing i18n** | PASS | Spanish default, English at `/en/`, language switcher works |
| **Landing Responsive** | PASS | Mobile layout with hamburger, stacked CTAs |
| **Landing Gallery** | PASS | 20 projects with category tabs (7 categories) |
| **Landing Interactive Demo** | PASS | Iframe embed with 10 project tabs |
| **Production Build (Studio)** | PASS | 15.3s build, vendor chunks split correctly |
| **Production Build (Landing)** | PASS | 2.86s build, 2 pages (es + en) |
| **Production Backend (gunicorn)** | PASS | 2 workers, health + render both succeed |
| **Unit Tests (Studio)** | PASS | 570 tests / 66 files |
| **Unit Tests (Backend)** | PASS | 394 tests (2 skipped) |

---

## Bugs Found & Fixed

### 1. ProjectsView crash — i18n object rendered as React child (FIXED)

**File**: `apps/studio/src/components/project/ProjectsView.jsx`
**Severity**: Critical — Projects gallery completely broken
**Root cause**: `/api/admin/projects` returns `description` as `{en, es, ...}` objects. ProjectsView rendered them directly as React children.
**Fix**: Added `loc()` helper to extract current language string from i18n objects. Applied to description rendering (line 168) and search filter (line 63).

### 2. Verify script path wrong (FIXED)

**File**: `apps/api/config.py:87`
**Severity**: Medium — verification endpoint returned "file not found"
**Root cause**: `_default_verify` used `parent` (repo root) instead of `self.BASE_DIR` (apps/api/).
**Fix**: Changed `parent / "tests" / "verify_design.py"` → `self.BASE_DIR / "tests" / "verify_design.py"`.

### 3. dev.sh hardcodes OpenSCAD Snapshot path (FIXED)

**File**: `scripts/dev.sh:12`
**Severity**: Low — dev server fails to start if Snapshot not installed
**Root cause**: Hardcoded `/Applications/OpenSCAD-Snapshot.app/Contents/MacOS/OpenSCAD`
**Fix**: Auto-detect — prefer Snapshot, fall back to stable release.

### 4. ProjectsView → Studio navigation doesn't switch project (NOT FIXED)

**Severity**: Medium — UX issue
**Repro**: Navigate to `#/projects` → click a project card → URL updates to `#/julia-vase` but project selector stays on previous project and controls don't update.
**Root cause**: Hash-based navigation from ProjectsView card links doesn't trigger project switch in ManifestProvider. The dropdown selector works because it calls `setProject()` directly.

### 5. Julia Vase slider values all show 100 (NOT FIXED)

**Severity**: Low — cosmetic
**Repro**: Switch to Julia Vase project → all parameter values display "100" regardless of actual defaults. ARIA labels all say "Height".
**Root cause**: Likely manifest parameter structure issue — needs investigation.

### 6. Gridfinity render fails with OpenSCAD v2021.01 (KNOWN)

**Severity**: N/A — expected
**Detail**: Gridfinity Extended uses syntax requiring OpenSCAD Snapshot (2024+). The `dev.sh` comment documents this.

### 7. Verify thin-wall check fails — missing `rtree` module (NOT FIXED)

**Severity**: Low — optional dependency
**Detail**: `verify_design.py` thin-wall check requires `rtree` package (not in requirements.txt). Geometry checks (watertight, body count) work fine.

---

## Screenshots

| Screenshot | Description |
|-----------|-------------|
| `studio-initial-load.png` | Studio with Gridfinity (render failed — expected) |
| `studio-torus-knot-rendered.png` | Torus Knot rendered with print estimate |
| `studio-maze-rendered.png` | Maze coaster rendered with BOM |
| `studio-maze-top-view.png` | Top camera view of maze |
| `studio-dark-theme-actual.png` | Dark theme applied |
| `studio-projects-view-crash.png` | Projects view crash (before fix) |
| `studio-projects-view-fixed.png` | Projects view working (after fix) |
| `studio-mobile-responsive.png` | Mobile layout — Julia Vase |
| `landing-initial-load.png` | Full landing page (dark, Spanish) |
| `landing-mobile-responsive.png` | Mobile landing hero |

---

## Environment Setup Notes

1. **Git submodules must be initialized**: `git submodule update --init --recursive` — without this, most projects fail to render (missing BOSL2, dotSCAD, etc.)
2. **Python venv**: `apps/api/.venv` not committed — create with `python3 -m venv .venv && pip install -r requirements.txt`
3. **pytest**: Not in requirements.txt — install separately: `pip install pytest pytest-cov`
4. **OpenSCAD**: v2021.01 (stable) works for most projects. Gridfinity requires Snapshot.
5. **AUTH_ENABLED=false**: Required for local dev without Janua auth server.

---

## Test Results

### Studio Unit Tests
```
66 test files — 570 passed — 39.25s
```

### Backend Tests
```
394 passed, 2 skipped — 12.76s
```

### Production Builds
```
Studio: ✓ built in 15.34s (vendor-three 722KB, vendor-react 193KB, index 378KB)
Landing: ✓ built in 2.86s (2 pages — /index.html, /en/index.html)
Backend (gunicorn): ✓ 2 workers, health + render pass
```
