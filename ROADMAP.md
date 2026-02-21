# Yantra4D Platform Roadmap

This roadmap outlines the strategic path towards a world-class hyperobject commons library, configurator, and visualizer, based on the findings from our [Architecture Audit](./docs/architecture/architecture_audit.md).

> **Strategy**: Reach platform stability first (P0 → P1), then expand the Hyperobjects Commons with new projects.

---

## Stability First: P0 & P1 Priorities

Before expanding with new features or new hyperobject projects, the platform must be stable, well-tested, and fully documented.

### P0 — Critical (Blockers)
- [x] **P0.1 — Wire E2E Tests into CI**: Playwright E2E test suites integrated into `.github/workflows/ci.yml`.
- [x] **P0.2 — Resolve Stub Projects**: All 28 active projects now pass `scripts/validate_manifests.py`.

### P1 — High Priority (Pre-Expansion)
- [x] **P1.1 — Complete Project Gallery**: All 36 active projects now have `thumbnail`, `tags`, and `difficulty` fields.
- [x] **P1.2 — Per-Project Documentation**: All 36 active projects now have `docs/README.md`, auto-generated.
- [x] **P1.3 — WASM Fallback Testing**: `wasm-fallback.spec.js` added.
- [x] **P1.4 — Rate Limiter Backend**: Redis integrated.
- [x] **P1.5 — Hyperobjects Commons Phase 2 (UI)**: Landing page and studio updated with CDG badges.

---

## Completed Architecture Phases

### Phase 1: Fluid UI via Web Worker Geometry Processing
- [x] **Web Worker Integration:** Moved STL geometry parsing (`STLLoader`) entirely off the main thread.
- [x] **Asynchronous Loader Hook:** Implemented `useWorkerLoader` to drop into the React Three Fiber viewer.
- [x] **Zero UI Freezing:** Eliminated browser jitter during complex, high-poly geometry ingestion.
- [x] **Schema Validation:** Standardized all hyperobject ontology definitions (`project.json`).

### Phase 2: Hybrid Compute Architecture (WASM + Cloud Fallback)
- [x] **WASM Execution:** Core CAD engine compiled to WebAssembly for zero-latency generation.
- [x] **Intelligent Cloud Fallback:** Dynamic detection of hardware limitations with routing to backend clusters.

### Phase 4: glTF 2.0 Viewport Transmission
- [x] **Format Upgrade:** Deprecated STL for active viewport transmission in favor of high-fidelity `glTF`/`GLB`.
- [x] **Rich Assemblies:** Enabled hierarchical structures and material properties.

### Phase 5: Monetization & Computational Tiering
- [x] **Tier Enforcements:** Defined usage boundaries (Free, Pro, MadFam).
- [x] **Premium Gating:** Cloud rendering and CadQuery exports gated behind tiers.

### Phase 6: The Hyperobjects Commons & CDG Standardization
- [x] **CDG Interface Formalization:** Integrated Common Denominator Geometry interfaces into the manifest.
- [x] **Unified Geometry:** Localized shared primitives (e.g. microscope slides).

### Phase 7: Live 3D Carousel Gallery
- [x] **Immersive Browsing:** Replaced the flat grid with an interactive 3D carousel.
- [x] **Dynamic LOD:** Smooth transition between optimized thumbnails and live 3D hyperobjects.

---

## Phase 3 — Platform Expansion (Post-Stability)

### 3.1 — Product Configurator Storefront Mode
- [x] "Customer view" layout that hides developer UI.
- [x] Datasheet PDF generation from manifest + rendered STL thumbnail.
- [x] Storefront landing page per project (public URL, product description, preset gallery).

### 3.2 — BOSL2 Attachment-Aware Auto-Assembly
- [x] Extend `scad_analyzer.py` to parse `attach()`.
- [x] Topological sort → ordered assembly sequence.

### 3.3 — NopSCADlib Component Catalog Widget
- [x] Parse NopSCADlib catalog metadata.
- [x] New widget type in `Controls.jsx`: visual grid of hardware components.
- [x] Selection updates dependent parameters.

### 3.4 — MCAD to BOSL2 Gear Migration
- [x] Replace MCAD `involute_gears` with BOSL2 `gears.scad` across existing projects.

### 3.5 — Hyperobjects Commons Rollout
- [x] Transform designated projects into standardized Hyperobjects with CDG interfaces. *(Note: 13 out of 13 declared Hyperprojects migrated to native Phase 3.5 BOSL2).*

### 3.6 — Dual-Engine Architecture & B-Rep Geometry (CadQuery)
- [x] Expand Yantra4D's geometric engine to natively support CadQuery.

### 3.7 — Hyperobject SDK Cartridges & Telemetry
- [x] Construct `mqtt_telemetry.py` to stream live external data architectures directly into procedural CadQuery param loops.

### 3.8 — Technical Health & Engineering
- [ ] Refactor core project geometry to reduce duplication.
- [x] Implement memory optimizations for WASM rendering.
- [x] Optimize the Docker rendering pipeline.

### 3.9 — Visual "3D Git" & Decentralized Ecosystem
- [ ] **Visual Version Control (3D Diffing):** Implement a Three.js-based visual diffing tool.
- [ ] **Decentralized Instancing:** Enhance the CLI and multi-project tools to allow independent creators to easily spin up their own white-labeled Yantra4D nodes.

### 3.10 — Reliability & Documentation
- [x] **4D Docs Application:** Deployed an Astro Starlight `apps/docs` portal at `4d-docs.madfam.io` for "peak devX".
- [x] **Agentic Discovery:** Formalized `/llms.txt` specifications for native LLM scraping.
- [x] **Landing Page Island Tests:** Implement Vitest component testing for React islands.
- [x] **Feature Documentation:** Author strict user guides for "invisible" platform mechanics.
- [x] **E2E CI Integration Validation:** Ensure the recently integrated Playwright E2E suites successfully block regressions.

---

## Phase 4 — New Hyperobject Projects (Post-Stability)

### 4.1 — `framing-hyperobject` — The Containing Frames Hyperobject
- [x] Implement the `framing-hyperobject` parametric SCAD design incorporating `rabbet`, `seg_channel`, `snap_profile`, `vesa_pattern`, `french_cleat`, and `standoff_bore` CDG interfaces.

---

## Phase 5 — Full Poly-Kernel Implementation & Strict Compliance (Completed)

This phase focuses on reaching 100% architectural parity across the entire Hyperobject Commons, ensuring every project is a "first-class citizen" in both OpenSCAD and CadQuery kernels.

### 5.1 — Strict Schema Compliance
- [x] **Enforce strict manifest rules:** Re-enable mandatory `cq_file` and `estimate_constants` requirements in the core JSON Schema.
- [x] **Hyperobject Integrity:** Formalize that `is_hyperobject: true` is invalid without a geometrically parity-matched CadQuery definition.

### 5.2 — Geometric Parity Authoring
- [x] **Poly-Kernel Implementations:** Authored CadQuery (`.py`) B-Rep equivalents for all 36 projects in the commons that were SCAD-only.
- [x] **Commons Validation:** Verified that `scripts/validate_manifests.py` organically passes at 100% ecosystem compliance.

---

## Phase 6 — Continuous Verification & Deep Integration (Next Priorities)

To solidify our status as an elite Hyperobjects Commons platform, the immediate next focus must turn toward mathematical verification, deduplication, and collaborative viewing.

### Priority 1: 6.1 — Automated Geometric Regression Testing
- [ ] Build a CI pipeline testing script to dynamically generate meshes via both CSG (OpenSCAD) and B-Rep (CadQuery) algorithms.
- [ ] Conduct volumetric and bounding-box analysis to guarantee the Python output mathematically matches the original SCAD geometry.

### Priority 2: 6.2 — Core Library Geometry Refactoring (Tech Debt)
- [ ] Eliminate fragmented mathematical logic across the 36 projects. 
- [ ] Centralize reusable constructs (threads, snaps, specific module functions) deeply into Yantra4D's integrated `libs/` namespace.

### Priority 3: 6.3 — Dual-Kernel CDG Interface Compliance
- [ ] Explicitly verify that the 6 required Common Denominator Geometry (CDG) interfaces (e.g. `rabbet`, `french_cleat`) physically slice flawless bounds natively across BOTH kernels.

### Priority 4: 6.4 — Visual "3D Git" Implementation
- [ ] Connect the Monaco editor's GitHub tracking into the Three.js viewport.
- [ ] Visualize geometrical additions (green) and deletions (red) directly on the realtime 3D mesh.

