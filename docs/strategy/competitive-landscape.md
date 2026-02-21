# Competitive Landscape Research & Improvement Roadmap

> **Date**: 2026-01-31
> **Purpose**: Market research benchmarking for Yantra4D's strategic positioning

---

## Landscape Summary

18+ open-source projects researched across 8 categories. Key competitors:

| Project | Type | Strengths vs Yantra4D | Weaknesses vs Yantra4D |
|---------|------|---------------------|----------------------|
| **OpenSCAD Playground** | Official WASM editor | Monaco editor, large community | Code-centric, not for end-users |
| **OpenJSCAD** | JS CAD framework | Native JS, modular, no OpenSCAD dep | Not a platform, dev-focused |
| **JSketcher** | Constraint-based modeler | Feature history, sketch+extrude | Different paradigm entirely |
| **Manifold CAD** | Modern WASM kernel | Fast geometry kernel, growing | Low-level, not a configurator |
| **NopSCADlib** | OpenSCAD framework | BOM generation, assembly docs, parts library | Not web-based, code-driven |
| **CadQuery/build123d** | Python CAD | Powerful parametric scripting | No web UI at all |
| **FreeCAD/SolveSpace** | Desktop CAD | Professional-grade features | Desktop-only, heavyweight |

**Yantra4D's unique position**: The only manifest-driven, end-user configurator platform with dual rendering, integrated verification, and multi-project management. No competitor combines "zero-code project onboarding" with "web-based 3D preview."

---

## Features to NOT Adopt

| Feature | Why Not |
|---------|---------|
| Code editor (Monaco) | Contradicts configurator identity. Users don't write code. |
| Constraint-based sketch modeling | Different paradigm; requires building a geometry engine. |
| STEP/IGES import | Professional exchange formats irrelevant to configurator users. |
| Standard parts library | Code-level OpenSCAD library. BOM covers the user need. |
| Real-time collaborative editing | Premature. Shareable links cover 80% of need at 5% cost. |
| Python/JS scripting | Code-centric. Fragments platform identity. |

---

## Roadmap

### Phase 1: Quick Wins (Implemented)

**1.1 Shareable Configuration Links** — Priority: highest
- Encodes full parameter state in URL query params (base64url-compressed diff against defaults)
- Users share exact configurations via link — no competitor has this
- Implementation: `useShareableUrl.js` hook, `App.jsx` integration, share button in header

**1.2 Parameter Undo/Redo**
- Simple history stack on params state with Cmd+Z / Cmd+Shift+Z
- Pure frontend, no manifest changes needed
- Implementation: `useUndoRedo.js` hook, wired into `App.jsx`

**1.3 Multi-Format Export (3MF, OBJ)**
- Backend: OpenSCAD CLI `--export-format` support; format param on render route
- Frontend: format selector in ExportPanel
- New `export_formats` array in manifest schema

**1.4 Print-Time & Filament Estimation**
- Computes STL volume from Three.js geometry using signed tetrahedra method
- Material profiles (PLA, PETG, ABS, TPU) with slicer heuristics
- Overlay component on viewer with material/infill selectors
- Implementation: `printEstimator.js`, `PrintEstimateOverlay.jsx`

### Phase 2: Medium-Term

**2.1 Bill of Materials (BOM)** ✅ Implemented
- Manifest-driven BOM (better than NopSCADlib's code-derived approach — editable by non-programmers)
- `bom.hardware[]` with `quantity_formula` evaluated via `expr-eval` against current params
- `BomPanel` component renders table with computed quantities, units, and optional supplier links
- Live in portacosas and gridfinity projects

**2.2 Assembly Instructions View** ✅ Implemented
- Step-by-step guide with 3D part highlighting per step
- `assembly_steps[]` manifest array with `visible_parts`, `highlight_parts`, camera positions
- Live in gridfinity project (3-step baseplate → bins → assembly flow)

**2.3 Project Gallery**
- Card-based layout with thumbnails, tags, difficulty for project discovery
- New manifest fields: `project.thumbnail`, `project.tags[]`, `project.difficulty`

**2.4 Cross-Parameter Validation** ✅ Implemented
- Manifest-driven constraint rules: `{ rule, message, severity, applies_to }`
- `useConstraints` hook evaluates rules via `expr-eval`, returns violations indexed by param
- Supports `warning` and `error` severities; `error` blocks render
- Live in portacosas and gridfinity projects

### Phase 3: Long-Term

**3.1 Visual Parameter Explorer (Comparison Mode)**
- Side-by-side render of 2-4 parameter variations — no competitor has this
- Batch rendering + split-view layout

**3.2 Auto-Generated Project Datasheets**
- One-click PDF/HTML combining manifest data, renders, BOM, assembly steps

**3.3 Plugin System for Custom Controls** ✅ Partially Implemented
- Extend parameter types beyond slider/checkbox/text with custom widgets
- Dynamic component loading from manifest `widget` field
- `color-gradient` widget implemented (dual color picker with gradient preview, live in polydice project)

---

## Priority Matrix

| Feature | Value | Effort | Strategic Fit | Score |
|---------|-------|--------|--------------|-------|
| Shareable Links | 9 | 2 | 10 | **27** |
| Undo/Redo | 8 | 2 | 7 | **23** |
| Multi-Format Export | 8 | 3 | 7 | **22** |
| BOM Generation | 8 | 5 | 9 | **22** |
| Print Estimation | 7 | 4 | 9 | **20** |
| Param Validation | 7 | 4 | 8 | **19** |
| Assembly Instructions | 7 | 5 | 8 | **18** |
| Project Gallery | 7 | 5 | 7 | **17** |
| Comparison Mode | 8 | 8 | 9 | **15** |
| Datasheet Generation | 6 | 5 | 8 | **15** |
| Plugin System | 6 | 8 | 7 | **11** |

*(Score = Value + Strategic Fit - Effort)*

---

## Schema Evolution (All Backward-Compatible)

**Phase 1**: `export_formats[]`, `print_estimation{}`
**Phase 2**: `bom{}` ✅, `assembly_steps[]` ✅, `constraints[]` ✅, `parameter_groups[]` ✅, `grid_presets{}` ✅, `viewer{}` ✅, `project.thumbnail`, `project.tags[]`
**Phase 3**: parameter `widget` field for custom controls

All additions are optional — existing projects continue to work unchanged.

---

## Category Analysis Detail

### Web-Based Parametric Platforms
- **OpenSCAD Playground**: Browser-based WASM OpenSCAD with Monaco editor. Strong developer tool but no configurator UX. No manifest system, no presets, no multi-project.
- **CadhubCommunity (deprecated)**: Attempted social CAD but discontinued. Validates that community features alone aren't enough — need solid core UX first.

### JavaScript/WASM CAD Frameworks
- **OpenJSCAD**: Modular JS CAD framework. Powerful but requires coding. No end-user configurator layer.
- **Manifold**: Fast C++ geometry kernel compiled to WASM. Could be a future rendering backend alternative to OpenSCAD for simple operations.

### Desktop Parametric CAD
- **FreeCAD**: Full-featured open-source CAD. Heavyweight, requires installation. Web frontend (FreeCAD.web) is experimental.
- **SolveSpace**: Lightweight constraint solver. Desktop-only. Different target audience.

### OpenSCAD Ecosystem
- **NopSCADlib**: Comprehensive OpenSCAD library with BOM generation and assembly documentation. Inspiration for our BOM feature — but code-driven, not manifest-driven.
- **BOSL2**: OpenSCAD standard library. Useful for SCAD authors, not for end-user configurators.

### Print-Adjacent Tools
- **PrusaSlicer/Cura**: Print estimation algorithms are the gold standard. Our heuristic estimator approximates their approach for quick feedback without requiring actual slicing.
- **Printables/Thingiverse**: Gallery and sharing platforms. Their configurator features (Thingiverse Customizer) are deprecated/broken — opportunity for Yantra4D.

---

## Key Takeaway

Yantra4D occupies a genuinely unique niche: **manifest-driven parametric configurator for end-users**. The competitive moat is the combination of:
1. Zero-code project onboarding (manifest + SCAD = working configurator)
2. Dual rendering (backend + WASM fallback)
3. Integrated verification pipeline
4. Multi-project management

No single competitor addresses all four. The roadmap strengthens each pillar while adding differentiating features (shareable links, print estimation, BOM) that competitors lack entirely.
