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
- [x] **P0.6 — CI Stability Remediation (2026-05-14):** Node 22 CI runtime, private submodule checkout credentials, backend migration drift repair, high-severity npm audit gates, Studio safe formula migration, and mobile responsive Playwright stabilization shipped in `2b0c397`.
- [ ] **P0.7 — Post-Push GitHub Actions Confirmation:** Verify all workflows on `main` pass after `2b0c397`.
- [ ] **P0.8 — Production Browser Stability Audit:** Validate `yantra4d.com`, `app.yantra4d.com`, `api.yantra4d.com`, and `admin.yantra4d.com` through browser-usable flows.
- [ ] **P0.9 — Tablaco End-to-End Render Stability:** Confirm Tablaco project discovery, manifest load, browser parameter updates, render, fallback, export, BOM, and quote handoff where enabled.
- [ ] **P1.6 — Full Playwright Audit Closure:** Run the broader production-like browser audit suite beyond the mobile responsive project.
- [ ] **P1.7 — Remaining Dependency Cleanup:** Safely resolve low/moderate Landing/Admin advisories through planned framework and dev-tool upgrades.
- [ ] **P1.8 — Auth-Enabled Production Smoke:** Validate tiers, CORS, Redis cache, database persistence, webhooks, and graceful render degradation with production-like settings.

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

> Local stability gates are green after commit `2b0c397`: high-severity npm audits passed for Studio, Landing, and Admin; Studio focused tests passed; backend migration drift and coverage passed; mobile responsive Playwright passed. Full production stability still requires post-push GitHub Actions confirmation and live browser validation of Yantra4D plus Tablaco.

---

### Sprint 12.5 — Quality Lock-In: 80% Coverage Foundation (Completed)
_Dependency: None._

Achieve a high-trust testing foundation across the fragmented monorepo to ensure future feature sprints (13-16) don't introduce regressions.

- [x] **Studio (Vitest) 80% Coverage:** Reach >80% coverage across all metrics (Statements, Branches, Functions, Lines) in `apps/studio`.
- [x] **API (Pytest) 80% Coverage:** Reach >80% coverage in `apps/api` with strict enforcement in the CI pipeline.
- [x] **Zero-Failure Verification:** Confirm all 600+ unit tests and 21+ E2E suites pass with absolute consistency.
- [x] **Branch Coverage Hardening:** Specifically target complex logic in `renderService.js`, `verifyService.js`, and the backend `openscad.py` engine.

---

### Sprint 13 — Per-Project CI & Federated Repo Health (Completed)
_Dependency: None._

Each of the 33 independent project repos now has its own CI to catch regressions independently of the yantra4d monorepo pipeline.

- [x] **GitHub Actions template:** Reusable `.github/workflows/project-ci-reusable.yml` (52 lines) — lint SCAD, validate `project.json` against schema, run compliance audit.
- [x] **Propagate to all 33 repos:** `scripts/ci/propagate_project_ci.sh` (185 lines) + `scripts/ci/propagate_project_ci.py` apply the CI template across all `madfam-org/<slug>` repositories.
- [x] **Submodule update automation:** `.github/workflows/project-ci.yml` triggers submodule SHA bump when a project repo's `main` branch passes CI.
- [x] **`tablaco` exclusion hardening:** `update = none` in `.gitmodules` confirmed — public clones skip the private repo.

---

### Sprint 14 — Parametric Assembly Animation (Completed)
_Dependency: None — Three.js viewer already in place._

The Yantra4D Studio animates parametric transitions between named states, producing in-browser assembly instruction animations.

- [x] **Manifest keyframes:** `animations[]` schema block with from-state params, to-state params, duration, easing, label.
- [x] **Three.js interpolation engine:** `apps/api/routes/projects/animations.py` (224 lines) — SSE streaming render with frame interpolation and easing functions (ease-in, ease-out, ease-in-out).
- [x] **Assembly sequence panel:** `AnimationPanel.jsx` — play/pause/scrub animation with flipbook playback. GIF/WebM export deferred to Phase 3A.
- [x] **Reference implementation:** Animation support across OpenSCAD, CadQuery, and Implicit engines.

---

### Sprint 15 — Printer Integration: OctoPrint & Moonraker (Completed)
_Dependency: None._

Users can send rendered geometry directly from the Yantra4D Studio to OctoPrint or Moonraker (Klipper) printers for direct manufacturing dispatch.

- [x] **Printer profile manifest:** `printers/example-printer.json` schema with connection type (octoprint/moonraker), endpoint URL, and machine metadata.
- [x] **Printer service clients:** `apps/api/services/integrations/octoprint.py` + `moonraker.py` (149 lines) — status polling, file upload, print dispatch, cancellation. Klipper state normalized to OctoPrint-style names.
- [x] **Print Panel UI:** `PrintPanel.jsx` — printer selection, live temperature gauges, status polling (5s), dispatch and cancel controls.
- [x] **Tier gating:** Printer dispatch gated at `pro+` via `@require_tier("pro")` in `apps/api/routes/integrations/printer.py`. MQTT telemetry bridge in `apps/api/services/core/mqtt_telemetry.py` (disabled by default, `MQTT_ENABLED=false`).

---

### Sprint 16 — BOM-to-Cart (ForgeSight Data Intelligence Platform Integration)
_Integration: **[ForgeSight Data Intelligence Platform](https://forgesight.quest)** — live at `api.forgesight.quest` (Starter tier: 10 calls/hr, benchmarks cached 1hr)._

The BOM API (`routes/bom.py`) and `BomPanel.jsx` already exist, and `supplier_url` is in the manifest schema. Sprint 16 adds the aggregation, pricing, and checkout layers powered by the ForgeSight Data Intelligence Platform.

- [x] **ForgeSight API client:** OAuth2 auth, benchmark pricing (`GET /api/v1/benchmarks`), 1hr cache, material category mapping (PLA/PETG/ABS/TPU/Resin/Nylon), graceful fallback to hardcoded defaults.
- [x] **Pricing endpoint:** `GET /api/pricing/benchmark?material=pla&region=CDMX` — returns p10/p50/p90 per-kg pricing from ForgeSight or hardcoded defaults. Public, rate-limited at 60/hr.
- [x] **Live pricing in print estimates:** PrintEstimateOverlay fetches ForgeSight benchmarks, displays cost range (low–high) with MXN/USD currency toggle and "Market pricing via ForgeSight" attribution.
- [x] **Cart aggregation endpoint:** `POST /api/projects/<slug>/bom/cart` — resolves BOM hardware items via ForgeSight, returns enriched BOM with pricing. Tier-gated at `pro+`.
- [ ] **BOM-to-Cart UI:** Studio panel extension — "Add all to cart" button, per-item supplier selection, estimated total cost.
- [ ] **Material hyperobject linking:** Auto-match `target_material` manifest param to ForgeSight material catalog entries for live `mat_shrinkage` / `mat_clearance` compensation values.
- [ ] **Tier gating refinement:** Cart export available at `basic+` tier; live pricing at `pro+`.

---

### Sprint 16.1 — Tablaco Verified Quote Relay (Selva -> Yantra4D -> Cotiza -> ForgeSight)
_Integration: Selva agent quote generation, Cotiza Studio tenant quote creation, and ForgeSight verified market data._

Yantra4D must act as a truthful project and geometry relay. It should not invent pricing truth, downgrade verified downstream results, or hide the reason a quote is not client-ready.

- [x] **Strict market verification propagation:** Forward `require_market_verified` as a top-level Cotiza request field for `/api/projects/<slug>/cotiza-quote-request`.
- [x] **Market context preservation:** Preserve Cotiza `market_verified`, `market_context`, `pricing_source`, `fallback_reason`, and `needs_review` in the Yantra4D response.
- [x] **Tablaco quote fixture:** Add a canonical `tablaco/unit` fixture with known parameters, geometry metadata, material, process, quantity, and currency.
- [ ] **Authenticated smoke path:** Verify pro-tier Selva/Janua credentials can render and request a Tablaco quote without bypassing tier policy.
- [x] **Fail-closed behavior:** If Cotiza or ForgeSight cannot verify market data while strict mode is requested, return a non-client-ready response with the blocking reason.
- [x] **Runbook coverage:** Document the live Tablaco quote flow and how Enclii verifies it without direct production container access.

---

### Sprint 16.2 — Platform Stability Closure: Browser, CI, and Production Confidence
_Dependency: Sprint 16.1 can proceed in parallel, but production stability claims depend on this closure sprint._

This sprint closes the gap between locally validated stability and production-grade confidence. The objective is not to add new surface area; it is to prove the existing Yantra4D platform and Tablaco experience are stable across CI, browser, backend, auth, and deployment boundaries.

- [x] **CI hotfix shipped:** Commit `2b0c397` removed the unsafe Studio formula dependency, hardened CI/runtime assumptions, repaired backend migration drift, and stabilized mobile responsive Playwright checks.
- [x] **High-severity npm gate:** Studio, Landing, and Admin pass `npm audit --audit-level=high`.
- [x] **Studio formula and constraint regression coverage:** `safeFormula`, BOM ternary formulas, and constraint paths have targeted tests.
- [x] **Studio CI typecheck contract:** CI now runs the stable TypeScript utility/type boundary through `tsconfig.ci.json`; strict TSX migration remains explicit backlog instead of blocking unrelated stability releases.
- [x] **Backend migration and coverage gate:** Isolated migration upgrade/check passes; backend coverage passes at 80.68%.
- [x] **Mobile responsive browser project:** Playwright mobile project passes with 22 passing tests and 2 intentional skips.
- [ ] **GitHub Actions post-push confirmation:** Verify all workflows are green on `main` for `2b0c397` or newer.
- [ ] **Live production browser audit:** Exercise `yantra4d.com`, `app.yantra4d.com`, `api.yantra4d.com`, and `admin.yantra4d.com` in desktop and mobile browsers.
- [ ] **Tablaco browser render proof:** Validate Tablaco loads from the browser, exposes expected controls, renders successfully, degrades cleanly on backend failure/rate limit, and exports usable artifacts.
- [ ] **Full E2E audit suite:** Run the real-backend/OpenSCAD Playwright audit project and capture screenshots/artifacts under `audit/` only when intentionally updating audit baselines.
- [ ] **Production-like backend smoke:** Validate Redis L2 render cache, auth-enabled tier behavior, database persistence, CORS origins, webhook HMAC rejection/acceptance, OpenSCAD availability, and render timeout handling.
- [ ] **Dependency modernization backlog:** Resolve remaining low/moderate advisories through deliberate Astro/Vitest/Vite upgrade work rather than force upgrades in hotfix mode.
- [ ] **Enclii-first operations runbook:** Document the production validation path through Enclii and record any missing adapters instead of normalizing raw infrastructure access.
- [ ] **Stability release note:** Publish a concise operator/developer note summarizing supported flows, known limitations, and rollback criteria.

Exit criteria:

- All GitHub Actions required checks are green on `main`.
- Live browser audit shows no blocking console errors, broken navigation, failed core API calls, or unusable responsive layouts.
- Tablaco browser path works end to end for the supported public/pro-tier flow.
- Backend production-like smoke covers auth, render, cache, persistence, and webhook boundaries.
- Remaining advisories are either resolved or explicitly accepted with owner, severity, and target sprint.

---

### Sprint 17 — Production Physics Readiness & Generative Optimization
_Integration: **[PPF Contact Solver](https://github.com/st-tech/ppf-contact-solver)** (SIGGRAPH Asia 2024)._

Transition the current mock simulation pipeline to full GPU-accelerated production readiness for compliant hyperobjects.

- [ ] **Infrastructure Provisioning:**
    - Deploy NVIDIA `g6.2xlarge` or `g6e.2xlarge` GPU instances with CUDA 12.8+.
    - Authenticate registry access to `ghcr.io/st-tech/ppf-contact-solver-compiled`.
    - Configure static storage (S3 or mounted volume) for persistent PLY frame sequences.
- [ ] **Backend Simulation Hardening:**
    - Replace mock `time.sleep` loops in `simulation_tasks.py` with real `subprocess` execution of generated PPF Python scripts.
    - Implement real-time STL path resolution in `script_generator.py` for concrete CAD-to-SOLVER mesh injection.
    - Migrate from background threads to Celery `@celery.task(queue="gpu_tasks")` for distributed job management.
- [ ] **Optimizer Physical Intelligence:**
    - Refactor `optimizer.py` to parse real `max-sigma` (Von Mises stress) values from PPF solver logs instead of heuristic mocks.
    - Implement generative feedback loop to apply optimized CAD parameters back to the active project state.
- [ ] **Frontend Kinematic Animator:**
    - Implement Three.js PLY binary parser in the Studio viewer.
    - Build `MorphTarget` animation engine to interpolate between 100+ physics frames.
    - Add Kinematic Timeline UI to allow users to scrub through the physics simulation sequence.
