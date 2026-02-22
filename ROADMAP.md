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

### Phase 9 — Ecosystem Standardization & Cartridge Compliance (In Progress)
The goal is to ensure all Yantra4D projects are fully self-contained, standardized "cartridges".

- [x] **Universal Compliance Tooling:** Implemented `scripts/audit_compliance.py`.
- [x] **Ecosystem Attribution:** Accredited Zack Freedman, Paulo Kiefe, Keep Making in manifests.
- [x] **Vendor Eradication:** Flattening `vendor/` folders into project roots.
- [x] **Cross-Project Dependency Resolution:** Eliminating unsafe parent-relative paths (`../`).
- [x] **100% Audit Passing:** Reaching zero violations across all 36+ projects.

### Phase 10 — Nanoscale Material Hyperobjects & Physical Intelligence (In Progress)
Treating additive manufacturing substrates as phased, nested hyperobjects to grant macroscopic geometries emergent "physical intelligence."

- [x] **Baseline Amorphous Core:** Establish `/materials/` directory, `material-manifest.schema.json`, and Poly-Kernel parameter injection (`mat_shrinkage`, `mat_clearance`) for basic behavioral compensation.
- [ ] **Topological Data Integration (TDA):** Extend material structures to accept subwavelength metrology data, linking Persistent Homology descriptions (PD1 Diagrams) of nanocrystalline structures and metamaterial networks.
- [ ] **Semantic Material Ontologies:** Align the Yantra4D API knowledge graph with ISO/ASTM 52900 terminology and Elementary Multiperspective Material Ontology (EMMO) frameworks.
- [ ] **Field-Driven Implicit Architecture:** Evolve the rendering engine beyond discrete B-reps to evaluate material parameters as continuous spatial fields, directly driving the generation of multi-level TPMS and gradient lattices.
- [ ] **Multiscale Digital Twin Visualization:** Enable the UI to simulate temporal phasing (4D printing) by calculating morphological shifts using the material's structural phase states and energy thresholds.

---

## Known Bottlenecks & UX Improvements (Backlog)
- **Slicer-Grade Estimations:** Replace bounding-box volume heuristics with true path-based cost/time/filament estimations.
- **Complex Render Stability:** Address browser WASM timeouts for highly complex models (e.g., dense grid arrays) to reduce reliance on the Docker backend fallback.
- **Robust State Management:** Refactor the Undo/Redo history stack to prevent truncation during parametric state updates.
- **Verification Accuracy:** Eliminate false positives in the geometric verification pipeline by decoupling checks from pre-rendered STLs.

## Future Expansion
- **Real-time Printing Integration:** OctoPrint/Mainsail hooks.
- **BOM-to-Cart:** Auto-generate hardware shopping carts.
- **Parametric Assembly Animation:** Live instruction animations.
- **Agentic Discovery:** Formalize `/llms.txt` specifications for native LLM scraping.
