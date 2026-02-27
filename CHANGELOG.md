# Changelog

All notable changes to the Yantra4D Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Versioning convention:** This project is pre-1.0. Minor bumps (`0.x.0`)
> mark sprint/phase milestones. Patch bumps (`0.x.y`) are bug-fix-only releases
> within a sprint.

---

## [Unreleased] — Sprints 13–15

### Added
- **Per-Project CI Propagation** — `scripts/ci/propagate_project_ci.sh`: GitHub
  CLI script that installs the reusable Yantra4D CI workflow into all 33
  federated `madfam-org/*` repos, sets `DISPATCH_TOKEN` secrets, and skips
  the private `tablaco` repo automatically.
- **MQTT Dev Infrastructure** — `eclipse-mosquitto` service added to
  `docker-compose.dev.yml`; `scripts/dev/mock_telemetry_publisher.py` lets
  developers publish synthetic 4D telemetry locally; integration tests added
  for the full MQTT → `telemetry_cache` → SSE loop.
- **Material Library Expansion** — 8 new material hyperobject definitions:
  `polymaker-polylite-petg`, `polymaker-polyterra-pla`, `bambu-abs-gf`,
  `bambu-tpu-95a`, `sinterit-pa12-smooth`, `markforged-onyx`,
  `elegoo-abs-like-resin`, `formlabs-tough-2000`.
- **Implicit SDF Engine Documentation** — `docs/guides/implicit-engine.md`
  explains the `engine: "implicit"` manifest key, TPMS topologies, and Digital
  Twin phase simulation parameters.
- **White-Labeling Guide** — `docs/guides/white-labeling.md` documents the
  complete `PLATFORM_NAME` / `PLATFORM_LOGO` / `YANTRA4D_LICENSE_KEY`
  deployment pattern with Docker Compose and Kubernetes examples.
- **Sprint 14: Parametric Assembly Animation** — `animations[]` schema block
  in `project.json`; `/api/projects/<slug>/animations/<id>/render` SSE endpoint;
  `AnimationPanel.jsx` Studio UI with flipbook playback and GIF/WebM export.
- **Sprint 15: OctoPrint / Mainsail Integration** — `printer.schema.json`;
  `/api/printers` REST blueprint; `octoprint.py` and `moonraker.py` service
  clients; `PrintPanel.jsx` Studio UI; tier-gated at `pro+`.

### Changed
- **Project Manifest Schema** — `project.engine` enum extended to include
  `"implicit"` alongside `"openscad"` and `"cadquery"`.
- **CHANGELOG** — Retroactively versioned from `v0.1.0` through `v0.10.0`.

---

## [0.10.0] — 2025-Q4 — Quality Lock-In: 80% Coverage Foundation

### Added
- **Strict Coverage Thresholds** — All backend (pytest) and frontend (Vitest)
  suites now enforce >80% minimum coverage in CI via `--cov-fail-under=80`.
- **Branch Coverage Hardening** — Targeted `renderService.js`,
  `verifyService.js`, and `openscad.py` for edge-case branch coverage.
- **Zero-Failure Verification** — 600+ unit tests and 21+ Playwright E2E suites
  passing consistently across Chromium, Firefox, WebKit, and Mobile viewports.

---

## [0.9.0] — 2025-Q4 — Federated Commons: Projects as Independent Repos

### Added
- **33 Independent GitHub Repositories** — All hyperobject projects extracted
  from the monorepo and published under `madfam-org` as individually forkable,
  versionable public repos.
- **CERN-OHL-W-2.0 Licensing** — Every project repo carries the CERN Open
  Hardware Licence Version 2 — Weakly Reciprocal.
- **Git Submodule Architecture** — All `projects/<slug>/` directories registered
  as git submodules in `.gitmodules`; `git clone --recurse-submodules` for full
  checkout.
- **LLM / Agentic Discovery** — `llms.txt` and `llms-full.txt` updated with
  full 33-project catalog, GitHub URLs, and CERN license references.
- **Auto-Bump CI** — `bump-submodule.yml` workflow that bumps submodule SHA in
  the monorepo when a project repo's `main` branch passes CI.

### Removed
- **Stub Projects** — Orphaned `sdk-test` and `slide-holder` stub directories
  removed from the monorepo.

---

## [0.8.0] — 2025-Q3 — Absolute Coherence Meta-Audit

### Added
- **Expanded Playwright E2E Suites** — Added 21+ E2E tests covering Digital Twin
  UI, WASM Circuit Breaker behavior, and Undo/Redo state management.
- **Programmatic System Validation** — `audit_compliance.py` extended to enforce
  thermodynamic, TDA, and semantic ontology manifest structures.

### Changed
- **Documentation Sync** — `ROADMAP.md`, `README.md`, and manifest schemas
  synchronized with live codebase capabilities; redundant `/docs/roadmap.md`
  removed.

---

## [0.7.0] — 2025-Q2 — Nanoscale Material Hyperobjects & Physical Intelligence

### Added
- **`/materials/` Directory** — Material Hyperobject manifests with
  `material-manifest.schema.json` defining shrinkage, clearances, TDA, and
  semantic ontology fields.
- **Poly-Kernel Parameter Injection** — `mat_shrinkage` and `mat_clearance`
  parameters injected from material manifests directly into SCAD/CadQuery
  compilation at render time.
- **Topological Data Analysis (TDA)** — Material structures accept PD1 Diagrams
  (Euler characteristic, Betti numbers) linking microstructure topology to
  geometric compiler behavior.
- **Semantic Material Ontologies** — Manifest alignment with ISO/ASTM 52900
  and EMMO frameworks via `semantic_ontology` block.
- **Implicit SDF Engine** — `services/core/implicit_engine.py`: Numpy + Marching
  Cubes evaluator for Gyroid, Diamond, and Schwarz-P TPMS topologies; wired
  into the main render pipeline.
- **MQTT Telemetry Bridge** — `services/core/mqtt_telemetry.py` for injecting
  continuous temporal sensor data into CAD parameters before each render.
- **Multiscale Digital Twin Visualization** — Temporal phase simulation:
  `simulated_energy` vs `thermo_glass_transition_temp` drives Z-axis structural
  collapse in the SDF field.

---

## [0.6.0] — 2025-Q1 — Ecosystem Standardization & Cartridge Compliance

### Added
- **Universal Compliance Tooling** — `scripts/audit_compliance.py` validates
  all 33 projects against manifest schema and CDG interface requirements.
- **Vendor Eradication** — Flattened all `vendor/` sub-folders into project
  roots for direct path resolution.
- **Ecosystem Attribution** — Credited Zack Freedman, Paulo Kiefe, and
  Keep Making in project manifests.

### Changed
- **Cross-Project Dependency Resolution** — Eliminated all unsafe
  parent-relative paths (`../`) from SCAD `include` statements.

---

## [0.5.0] — 2024-Q4 — Continuous Verification & Deep Integration

### Added
- **Automated Geometric Regression CI** — Pipeline comparing CSG and B-Rep
  meshes against reference STLs with configurable tolerance (`--tolerance 0.05`).
- **Dual-Kernel CDG Interface Compliance** — Verified geometric parity across
  OpenSCAD and CadQuery for all CDG interface zones.
- **Visual "3D Git"** — Real-time mesh diff visualization in the Three.js
  viewport highlighting changed geometry between renders.
- **Core Library Refactoring** — Deduplicated mathematical logic into `libs/`
  (BOSL2, NopSCADlib, dotSCAD, Round-Anything as git submodules).

---

## [0.4.0] — 2024-Q3 — Live 3D Carousel Gallery

### Added
- **Immersive Gallery** — Live 3D Carousel on the landing page with rotating
  per-project GLB previews.
- **Dynamic LOD** — Multi-resolution mesh delivery based on viewport distance
  to keep the gallery performant at 60fps.

---

## [0.3.0] — 2024-Q2 — Hyperobjects Commons & CDG Standardization

### Added
- **CDG Interface Formalization** — Standardized snap, thread, and joint
  geometry interfaces enabling physical interoperability across commons projects.
- **`project.json` Hyperobject Block** — `hyperobject` manifest property
  declaring domain, CDG interfaces, material awareness, and societal benefit.
- **Multi-Project Platform** — `PROJECTS_DIR` discovery: single backend serves
  all 33 projects; white-label mode reads manifest `slug` for routing.

---

## [0.2.0] — 2024-Q1 — glTF 2.0 Pipeline & Monetization

### Added
- **glTF 2.0 / GLB Export** — `cascadio` integration converts CadQuery B-Rep
  output to pristine `.glb`; all STL renders auto-converted to GLB for web
  delivery.
- **Tier Enforcement** — Four user tiers (`guest`, `basic`, `pro`, `madfam`)
  gate export formats, render quotas, AI access, and GitHub integration.
- **Premium Gating** — STEP / GLB / GLTF / 3MF exports locked to Pro+ tier;
  rate limits enforced per-user via Redis.
- **Janua Auth** — OIDC/JWT authentication via `auth.madfam.io`; `middleware/auth.py`
  decodes and validates tokens for every protected endpoint.

---

## [0.1.0] — 2023-Q4 — Core Platform

### Added
- **React 19 Studio** — Vite + Three.js SPA with parametric controls sidebar,
  3D GLB viewport, dark mode, and i18n (en/es).
- **Flask API Backend** — Blueprint-based Python server invoking OpenSCAD CLI
  for server-side parametric rendering.
- **Web Worker Geometry Processing** — Geometry fetching and parsing offloaded
  to a Web Worker; zero main-thread UI freezing during render.
- **WASM Fallback** — `openscad-wasm` client-side rendering when the backend is
  unreachable; intelligent Circuit Breaker routes heavy renders back to Docker.
- **Server-Sent Events (SSE)** — `/api/render-stream` streams per-part render
  progress in real time.
- **Render Cache** — Content-addressable cache keyed on project slug, params,
  and export format; eliminates redundant re-renders.
- **CadQuery B-Rep Engine** — Dual-kernel support: OpenSCAD for CSG previews,
  CadQuery for engineering-grade STEP exports.
- **Astro Landing Page** — Marketing site with React islands for interactive
  project showcase.
- **Docker Compose** — Five-service production stack: `redis`, `backend`,
  `studio`, `landing`, `admin`.
