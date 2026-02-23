# Yantra4D Platform Roadmap

This roadmap outlines the strategic path towards a world-class hyperobject commons library, configurator, and visualizer.

---

## Stability First: P0 & P1 Priorities
- [x] **P0.1 — Wire E2E Tests into CI**
- [x] **P0.2 — Resolve Stub Projects**
- [x] **P1.1 — Complete Project Gallery**
- [x] **P1.2 — Per-Project Documentation**
- [x] **P1.3 — WASM Fallback Testing**
- [x] **P1.4 — Rate Limiter Backend**
- [x] **P1.5 — Hyperobjects Commons Phase 2 (UI)**

---

## Completed Architecture Phases

### Phase 1: Fluid UI via Web Worker Geometry Processing
- [x] Web Worker Integration
- [x] Zero UI Freezing

### Phase 2: Hybrid Compute Architecture (WASM + Cloud Fallback)
- [x] WASM Execution
- [x] Intelligent Cloud Fallback

### Phase 4: glTF 2.0 Viewport Transmission
- [x] Format Upgrade (STL → glTF/GLB)
- [x] Rich Assemblies

### Phase 5: Monetization & Computational Tiering
- [x] Tier Enforcements
- [x] Premium Gating

### Phase 6: The Hyperobjects Commons & CDG Standardization
- [x] CDG Interface Formalization
- [x] Unified Geometry

### Phase 7: Live 3D Carousel Gallery
- [x] Immersive Browsing
- [x] Dynamic LOD

---

## Technical Expansion Phases

### Phase 8 — Continuous Verification & Deep Integration (Completed)
- [x] **Automated Geometric Regression Testing:** Build CI pipeline to match CSG & B-Rep meshes.
- [x] **Core Library Geometry Refactoring:** Deduplicate mathematical logic into `libs/`.
- [x] **Dual-Kernel CDG Interface Compliance:** Verify parity across OpenSCAD and CadQuery.
- [x] **Visual "3D Git" Implementation:** Real-time mesh diffing in the viewport.

### Phase 9 — Ecosystem Standardization & Cartridge Compliance (Completed)
The goal is to ensure all Yantra4D projects are fully self-contained, standardized "cartridges".

- [x] **Universal Compliance Tooling:** Implemented `scripts/audit_compliance.py`.
- [x] **Ecosystem Attribution:** Accredited Zack Freedman, Paulo Kiefe, Keep Making in manifests.
- [x] **Vendor Eradication:** Flattening `vendor/` folders into project roots.
- [x] **Cross-Project Dependency Resolution:** Eliminating unsafe parent-relative paths (`../`).
- [x] **100% Audit Passing:** Reaching zero violations across all 33 projects.

### Phase 10 — Nanoscale Material Hyperobjects & Physical Intelligence (Completed)
Treating additive manufacturing substrates as phased, nested hyperobjects to grant macroscopic geometries emergent "physical intelligence."

- [x] **Baseline Amorphous Core:** Establish `/materials/` directory, `material-manifest.schema.json`, and Poly-Kernel parameter injection (`mat_shrinkage`, `mat_clearance`) for basic behavioral compensation.
- [x] **Topological Data Integration (TDA):** Extend material structures to accept subwavelength metrology data, linking Persistent Homology descriptions (PD1 Diagrams) of nanocrystalline structures and metamaterial networks.
- [x] **Semantic Material Ontologies:** Align the Yantra4D API knowledge graph with ISO/ASTM 52900 terminology and Elementary Multiperspective Material Ontology (EMMO) frameworks.
- [x] **Field-Driven Implicit Architecture:** Evolve the rendering engine beyond discrete B-reps to evaluate material parameters as continuous spatial fields, directly driving the generation of multi-level TPMS and gradient lattices.
- [x] **Multiscale Digital Twin Visualization:** Enable the UI to simulate temporal phasing (4D printing) by calculating morphological shifts using the material's structural phase states and energy thresholds.

---

## Known Bottlenecks & UX Improvements (Resolved)
- [x] **Slicer-Grade Estimations:** Replace bounding-box volume heuristics with true path-based cost/time/filament estimations.
- [x] **Complex Render Stability:** Address browser WASM timeouts for highly complex models (e.g., dense grid arrays) to reduce reliance on the Docker backend fallback.
- [x] **Robust State Management:** Refactor the Undo/Redo history stack to prevent truncation during parametric state updates.
- [x] **Verification Accuracy:** Eliminate false positives in the geometric verification pipeline by decoupling checks from pre-rendered STLs.

---

### Phase 11 — Absolute Coherence Meta-Audit (In Progress)
Holistic codebase audit ensuring absolute inner coherence between research documentation, backend engine logic, and frontend UI/UX presentation.

- [x] **Documentation & Research Congruency:** Synchronize `ROADMAP.md`, `README.md`, and manifest schemas with live codebase capabilities.
- [x] **Programmatic System Validation:** Extend `audit_compliance.py` to enforce thermodynamic, TDA, and semantic ontology manifest structures.
- [x] **Browser-Based E2E Verification:** Expand Playwright test suites to validate Digital Twin UI, WASM Circuit Breaker, and Undo/Redo state management.
- [x] **Structural Lock-In:** Achieve peak platform coherence with zero drift between documentation claims and programmatic reality.

### Phase 12 — Federated Commons: Projects-as-Independent-Repos (Completed)
Decentralizing the Yantra4D Commons so every hyperobject project is a sovereign, fork-friendly GitHub repository — individually versionable, independently forkable, and importable as a git submodule.

- [x] **Independent GitHub Repositories:** All 33 hyperobject projects extracted from the monorepo and published as individual public repos under `madfam-org` (32 public, 1 private).
- [x] **CERN-OHL-W-2.0 Licensing:** Every project repo carries the CERN Open Hardware Licence Version 2 — Weakly Reciprocal. License text archived at `docs/licenses/CERN-OHL-W-2.0.txt`.
- [x] **Git Submodule Architecture:** All `projects/<slug>/` directories are now registered git submodules in `.gitmodules`, enabling `git clone --recurse-submodules` for full checkout.
- [x] **Stub Eradication:** Orphaned `sdk-test` and `slide-holder` stub directories removed from the monorepo.
- [x] **LLM / Agentic Discovery:** `llms.txt` and `llms-full.txt` updated with full 33-project catalog, GitHub URLs, submodule clone instructions, and CERN license references — enabling native LLM scraping and AI agent discoverability.
- [x] **Documentation Sync:** `README.md`, `llms.txt`, and `llms-full.txt` reflect the federated repo architecture with per-ecosystem project groupings and correct project count.

---

## Upcoming Sprints

> Platform stability is confirmed (588 Studio unit tests passing, 33/33 compliance audit clean, CI green). The following sprints are sequenced for maximum architectural leverage.

---

### Sprint 12.5 — Quality Lock-In: 80% Coverage Foundation (Completed)
_Dependency: None._

Achieve a high-trust testing foundation across the fragmented monorepo to ensure future feature sprints (13-16) don't introduce regressions.

- [x] **Studio (Vitest) 80% Coverage:** Reach >80% coverage across all metrics (Statements, Branches, Functions, Lines) in `apps/studio`.
- [x] **API (Pytest) 80% Coverage:** Reach >80% coverage in `apps/api` with strict enforcement in the CI pipeline.
- [x] **Zero-Failure Verification:** Confirm all 600+ unit tests and 21+ E2E suites pass with absolute consistency.
- [x] **Branch Coverage Hardening:** Specifically target complex logic in `renderService.js`, `verifyService.js`, and the backend `openscad.py` engine.

---

### Sprint 13 — Per-Project CI & Federated Repo Health
_Dependency: None — can start immediately._

Each of the 33 independent project repos now needs its own CI to catch regressions independently of the yantra4d monorepo pipeline.

- [ ] **GitHub Actions template:** Create a reusable `.github/workflows/project-ci.yml` workflow (lint SCAD, validate `project.json` against schema, run `audit_compliance.py` for the single project).
- [ ] **Propagate to all 33 repos:** Script to apply the CI template across all `madfam-org/<slug>` repositories via GitHub CLI.
- [ ] **Submodule update automation:** GitHub Action in yantra4d that auto-bumps submodule SHA refs when a project repo's `main` branch passes CI.
- [ ] **`tablaco` exclusion hardening:** Confirm `update = none` in `.gitmodules` propagates correctly so public clones never block on the private repo.

---

### Sprint 14 — Parametric Assembly Animation
_Dependency: None — Three.js viewer already in place._

Enable the Yantra4D Studio to animate parametric transitions between two named states (e.g., "collapsed → expanded", "open → closed"), producing in-browser assembly instruction animations.

- [ ] **Manifest keyframes:** Extend `project.json` schema with an `animations[]` block (from-state params, to-state params, duration, easing, label).
- [ ] **Three.js interpolation engine:** STL-to-STL morph via `THREE.BufferGeometry` lerp, or render N keyframes and play as a flipbook.
- [ ] **Assembly sequence panel:** UI panel to play/pause/scrub animation, export as GIF or WebM.
- [ ] **Reference implementation:** Add animation manifest to `gridfinity` (baseplate → cup assembly sequence).

---

### Sprint 15 — Real-time Printing Integration (OctoPrint / Mainsail)
_Dependency: None — new subsystem from scratch._

Allow users to send a rendered STL directly from the Yantra4D Studio to a connected 3D printer via OctoPrint REST API or Mainsail/Moonraker WebSocket.

- [ ] **Printer profile manifest:** New `/printers/` directory with `printer.json` files (API endpoint, auth token, bed dimensions, nozzle diameter).
- [ ] **OctoPrint REST client:** Backend service (`services/integrations/octoprint.py`) — upload STL, start print, poll status.
- [ ] **Moonraker/Klipper WebSocket client:** Alternative for Mainsail users.
- [ ] **Print Queue UI:** Studio panel for printer selection, print status, temperature graphs.
- [ ] **Tier gating:** Print dispatch available at `pro+` tier only.

---

### Sprint 16 — BOM-to-Cart (ForgeSight Integration)
_Dependency: **[ForgeSight](https://github.com/madfam-org/forgesight) platform must be production-ready.**_

> [!IMPORTANT]
> This sprint is explicitly blocked on the ForgeSight platform reaching production stability. ForgeSight is the commercial and industry data layer for Yantra4D — it provides real-time pricing, supplier availability, materials data, and consumables intelligence. Do not begin this sprint until ForgeSight's API is stable and versioned.

The BOM API (`routes/bom.py`) and `BomPanel.jsx` already exist, and `supplier_url` is in the manifest schema. Sprint 16 adds the aggregation, pricing, and checkout layers powered by ForgeSight.

- [ ] **ForgeSight API client:** Backend service (`services/integrations/forgesight.py`) — query materials pricing, supplier stock, lead times.
- [ ] **Cart aggregation endpoint:** `POST /api/projects/<slug>/bom/cart` — resolves BOM hardware items against ForgeSight catalog, returns cart with live pricing.
- [ ] **BOM-to-Cart UI:** Studio panel extension — "Add all to cart" button, per-item supplier selection, estimated total cost.
- [ ] **Material hyperobject linking:** Auto-match `target_material` manifest param to ForgeSight material catalog entries for live `mat_shrinkage` / `mat_clearance` compensation values.
- [ ] **Tier gating:** Cart export available at `basic+` tier; live pricing at `pro+`.
