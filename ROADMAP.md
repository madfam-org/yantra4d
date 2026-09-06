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

> _Status notes (2026-09-02) — nothing above is re-checked here; these only say what is now
> known about the items that stay open or whose checkmark needs a scope._
>
> - **P1.3 (WASM Fallback Testing)** stays checked, and as of
>   [#80](https://github.com/madfam-org/yantra4d/pull/80) (merged 2026-09-02) it is shipped
>   rather than merely tested. The `if (API_BASE) return 'backend'` pin inside `detectMode()`
>   is gone, so the heuristics below it are no longer dead code in production. The framing has
>   also inverted: the browser is now the **default** placement and the server is the
>   exception, decided by the pure 11-rule `decideRenderPlacement()` in
>   `apps/studio/src/services/engine/renderPlacement.ts`. "Fallback" is the wrong word for it
>   now — see [`docs/guides/wasm-mode.md`](docs/guides/wasm-mode.md).
> - **P1.6 (Full Playwright Audit Closure)** stays unchecked, but the harness is no longer the
>   blocker: since [#76](https://github.com/madfam-org/yantra4d/pull/76) (merged 2026-09-02)
>   the nightly `e2e-audit.yml` runs the `23-browser-audit` suite **without Docker** — backend,
>   Redis and the render worker start directly on the runner, the same shape as `ci.yml`'s e2e
>   job. The workflow's test step had been skipped on every run since 2026-03-21 because the
>   runner image has the docker CLI but not the Compose plugin. Run **#166** was the first to
>   execute the tests; [#96](https://github.com/madfam-org/yantra4d/pull/96) (merged
>   2026-09-02) reconciled runs #166–#174 — every failure was suite-vs-product drift, not a
>   product regression — and added the `HARNESS_TIER` knob the auth-off harness needs to render
>   CadQuery at all, plus a queue drain between groups.
>   [#98](https://github.com/madfam-org/yantra4d/pull/98) then fixed that drain to send the
>   `{ all: true }` body #83 requires. Closure still means a green audit run, which has not
>   happened yet.
> - **P0.7 / P0.8 / P0.9 / P1.7 / P1.8** are left unchecked and unchanged: no verification of
>   post-push workflow status, live production browser flows, the Tablaco end-to-end path, the
>   dependency backlog, or an auth-enabled production smoke was performed for this re-baseline.

---

## Completed Architecture Phases

### Phase 1: Fluid UI via Web Worker Geometry Processing
- [x] Web Worker Integration
- [x] Zero UI Freezing

### Phase 2: Hybrid Compute Architecture (WASM + Cloud Fallback)
- [x] WASM Execution
- [x] Intelligent Cloud Fallback

> _Scope note (updated 2026-09-02, after
> [#80](https://github.com/madfam-org/yantra4d/pull/80)):_ both boxes stay checked, and the
> production claim now matches the phase title — with one correction to the title itself. The
> cloud is not the fallback; the browser is the **default** and the server is the metered
> exception. `detectMode()`'s `if (API_BASE) return 'backend'` pin is gone, placement is
> decided per (device, cartridge) by the pure `decideRenderPlacement()` in
> `apps/studio/src/services/engine/renderPlacement.ts`, and a *soft* server decision falls
> back to the browser when the API is unreachable — the fallback runs in both directions now.

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
- [x] **100% Audit Passing:** Reaching zero violations across the whole cartridge estate
  (33 projects when this phase landed). `scripts/qa/compliance_audit.py --strict` now
  walks every directory under `projects/` and gates CI (`.github/workflows/ci.yml`), so
  the claim scales with the catalog instead of being pinned to a count.

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

### Phase 11 — Absolute Coherence Meta-Audit (Completed)
Holistic codebase audit ensuring absolute inner coherence between research documentation, backend engine logic, and frontend UI/UX presentation.

- [x] **Documentation & Research Congruency:** Synchronize `ROADMAP.md`, `README.md`, and manifest schemas with live codebase capabilities.
- [x] **Programmatic System Validation:** Extend `audit_compliance.py` to enforce thermodynamic, TDA, and semantic ontology manifest structures.
- [x] **Browser-Based E2E Verification:** Expand Playwright test suites to validate Digital Twin UI, WASM Circuit Breaker, and Undo/Redo state management.
- [x] **Structural Lock-In:** Achieve peak platform coherence with zero drift between documentation claims and programmatic reality.

> _Status note (2026-09-02):_ all four sub-items were checked; the phase header still read
> "In Progress". Marked complete. Coherence is a standing obligation rather than a phase —
> the drift this re-baseline removed (a 326-cartridge claim against a 500-cartridge catalog,
> a "33 repos" estate against 37 `projects/…` submodules) is the reason the counts in
> `README.md` and `COMMONS.md` are now generated from `docs/commons-catalog.json` rather
> than maintained by hand.

### Phase 12 — Federated Commons: Projects-as-Independent-Repos (Completed)
Decentralizing the Yantra4D Commons so every hyperobject project is a sovereign, fork-friendly GitHub repository — individually versionable, independently forkable, and importable as a git submodule.

- [x] **Independent GitHub Repositories:** The 33 hyperobject projects that existed when this phase landed were extracted from the monorepo and published as individual public repos under `madfam-org` (32 public, 1 private).
- [x] **CERN-OHL-W-2.0 Licensing:** Every project repo carries the CERN Open Hardware Licence Version 2 — Weakly Reciprocal. License text archived at `docs/licenses/CERN-OHL-W-2.0.txt`.
- [x] **Git Submodule Architecture:** The extracted projects are registered git submodules in `.gitmodules`, so `git clone --recurse-submodules` pulls them alongside the monorepo.
- [x] **Stub Eradication:** Orphaned `sdk-test` and `slide-holder` stub directories removed from the monorepo.
- [x] **LLM / Agentic Discovery:** `llms.txt` and `llms-full.txt` updated with the then-current 33-project catalog, GitHub URLs, submodule clone instructions, and CERN license references — enabling native LLM scraping and AI agent discoverability.
- [x] **Documentation Sync:** `README.md`, `llms.txt`, and `llms-full.txt` reflect the federated repo architecture with per-ecosystem project groupings and correct project count.

> _Estate re-baseline (2026-09-02):_ "all 33 projects" describes this phase as it landed, not
> the estate today, and federation turned out to be the flagship pattern rather than the
> default — and then RFC 0038 P2 ended it entirely. The Commons publishes
> **500 cartridges**
> (fact source: `docs/commons-catalog.json` → `counts.cartridges`; five slugs are reserved for
> clean-room re-creation under ADR-021), and every one of them now
> lives in ONE repo, `madfam-org/solid-hyperobjects`, which this platform consumes as a single
> pinned submodule at `projects/`
> (fact source: the `[submodule "projects"]` entry in `.gitmodules`). The 34 satellite cartridge
> repos that used to be separate `madfam-org` submodules were absorbed with full history and
> archived; there is no "submodule-backed vs in-repo" distinction left to draw. The two
> client-private cartridges are the only `projects/…`-era submodules that remain, and they moved
> out of the commons to `private-projects/`, still marked `update = none` so public clones skip
> them. New cartridges land in the commons repo.

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

Each federated project repo has its own CI to catch regressions independently of the yantra4d monorepo pipeline (33 repos when this sprint landed; 37 `projects/…` submodules today — see the estate re-baseline under Phase 12).

- [x] ~~**GitHub Actions template:** Reusable `.github/workflows/project-ci-reusable.yml`~~ — RETIRED by RFC 0038 P2. There are no federated cartridge repos left to give CI to; the commons repo has one CI lane of its own.
- [x] ~~**Propagate to the federated repos:** `scripts/ci/propagate_project_ci.{sh,py}`~~ — RETIRED with the above, along with `scripts/propagate_ci.sh`.
- [x] ~~**Submodule update automation:** `.github/workflows/project-ci.yml` + `bump-submodule.yml` + `update-submodules.yml`~~ — RETIRED and replaced by ONE `.github/workflows/bump-commons-pin.yml`, which opens a PR when `solid-hyperobjects` main moves ahead of the pin. Issue #69's dormant 33-repo bump loop is retired by construction.
- [x] **`tablaco` exclusion hardening:** `update = none` in `.gitmodules` confirmed — public clones skip the private repo.

---

### Sprint 14 — Parametric Assembly Animation (Completed)
_Dependency: None — Three.js viewer already in place._

The Yantra4D Studio animates parametric transitions between named states, producing in-browser assembly instruction animations.

- [x] **Manifest parameter states (not keyframes):** the `animations[]` schema block declares `from_state` and `to_state` parameter maps, a frame count (2–30), `duration_ms`, an easing curve and a label. An animation interpolates **parameter values** and re-renders the geometry per frame — numeric params linearly, non-numeric snapping at t ≥ 0.5 (`_interpolate_params` in `apps/api/routes/projects/animations.py`). There is no keyframe track and no transform interpolation; the word "keyframes" in this line was wrong from the start.
- [x] **Server-side interpolation engine:** `apps/api/routes/projects/animations.py` (234 lines) — SSE-streaming render of N interpolated frames with four easing curves (`linear`, `ease-in`, `ease-out`, `ease-in-out`). It is Python on the API, not Three.js: the parameters are interpolated server-side and each frame is a real engine render converted to GLB. Three.js only plays the resulting frames back.
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
- [ ] **Full E2E audit suite:** Run the real-backend/OpenSCAD Playwright audit project and capture screenshots/artifacts under `audit/` only when intentionally updating audit baselines. _(2026-09-02: the nightly `e2e-audit.yml` now executes this suite without Docker since #76; results are being reconciled under #79. Same item as P1.6 — see the status notes at the top of this file.)_
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

---

### Sprint 18 — CadQuery-First Commons Expansion (Completed — re-baselined at 500 on 2026-08-25)

Grew the Commons from the original catalog to **200 CadQuery-first hyperobjects** within this
sprint's own scope, authored dual-engine-ready, and added platform support for mixed-engine
cartridges. Expansion then continued past the sprint: the catalog reached **500** on
2026-08-25 (`9795f27` — "the closing six — 500", #67), and 500 is the number generated into
`README.md` and `COMMONS.md`. This sprint's title used to read "Expansion to 200"; 200 was a
target the catalog passed two and a half times over, so it survives only as the record of
what this sprint itself delivered.

Catalog shape at 500 (fact source: `docs/commons-catalog.json` → `counts`, and the
per-cartridge `engines` sets — a cartridge may declare more than one engine, so the engine
rows sum past 500; re-taken 2026-09-06, the numbers below had been left at a 495 shape):

| | |
| :-- | --: |
| Cartridges | 500 |
| Declaring CadQuery | 491 |
| Declaring OpenSCAD | 27 (20 of them alongside CadQuery) |
| Declaring Graph | 2 |
| Declaring Implicit | 1 |
| Flagged `dual_engine` | 20 |
| With declared CDG interfaces | 490 |
| Carrying an explicit `commons_license` | 500 |

The API serves 500 projects — the published cartridges, and only those. Since
RFC 0038 P2 the `cq-hyperobject-test` engine fixture is vendored under
`apps/api/tests/fixtures/cartridges/` instead of sitting in `projects/`, and the
client-private `tablaco` cartridges mount at `private-projects/` (served only to
authorized identities, and excluded from the catalog).

- [x] **Per-mode engine resolution:** `ManifestService.mode_engine(mode_id)` resolves the
  render engine per mode (explicit mode `engine` → `.py`/`.cq` inference → project engine;
  implicit projects stay implicit). Wired through `render_orchestrator`, animations, and
  git render-head. Optional `engine` field added to the mode schema. Covered by
  `tests/unit/test_manifest.py::TestModeEngine`.
- [x] **Dual-engine flagship re-authors:** the 9 highest-leverage OpenSCAD flagships
  (gridfinity, gears, fasteners, din-rail-clip, soft-jaw, faircap-filter,
  parametric-connector, microscope-slide-holder, prosthetic-socket) each gained exact
  CadQuery B-Rep modes alongside their original OpenSCAD modes, shipped to their
  `madfam-org` repos with submodule pointers bumped.
- [x] **First 100 (CDG-leverage order):** universal interfaces → household → mechanical →
  fastening → electronics → jigs → medical → water/garden → mobility/EDC.
- [x] **Second 100 (deeper + wider):** mounting systems, drone/FPV, automotive, kitchen,
  garden, workshop, electronics/maker, wearable/EDC, musical/studio, sports, marine/RV,
  pet, generative art, safety.
- [x] **Verification discipline:** every cartridge is self-contained (sandbox-safe `PARAM`
  idiom), watertight on every mode through the real render sandbox, and geometrically
  distinct per mode (mode/part-id alignment). A body-count check additionally rejects
  negative-volume / severed-body defects that watertightness alone misses.

**Next waves are RFC scale, not sprint scale.** 501–600 and anything past it is deliberately
not committed here. At 500 cartridges the binding constraints are domain selection,
CDG-interface leverage, licensing provenance, and the per-wave verification budget (real-sandbox
watertightness plus the body-count check on every mode) — each of which needs an RFC that names
the wave's domains and its verification cost before authoring starts. Until such an RFC lands,
the roadmap commitment stops at the 500 already in `docs/commons-catalog.json`.

---

## The Node-Based Geometry Programme (Waves D–F, S)

_Added 2026-09-06 (CDMX). Sourced from the read-only graph-engine audit
(`audit-graph-engine-2026-09-06.md`) and the method write-up
(`node-based-geometry-method-2026-09-06.md`), both under
`claudedocs/commons-p2-2026-09-04/`. The numbers below are the audit's, and the
"where we are" rows describe `origin/main` at `3c700d53` except where a landed
lane has updated them._

A hyperobject today is a **script** plus a manifest, and the script is opaque: the
platform can run it, verify its output and interpolate its parameters, but it cannot see
inside it. The node-based method makes the geometry a **graph** — a DAG (`.graph.json`)
of named operations with typed sockets — so the same document can be visualised
(every intermediate is addressable), built by composition instead of code, and
parametrised from the graph rather than from a hand-written parameter list.

**"Better than Grasshopper" is not "more components."** Grasshopper ships ~800 core
components; we need only the subset that expresses this catalogue. The bar is:
**verified** (every graph clears the same fail-closed bar the 500 scripts clear),
**parametric** (expressions, presets, constraints derived from node semantics),
**portable** (a manifest-bound, licensed, i18n'd document, not a `.gh` file), and
**dual-engine** where it matters. The one advantage Grasshopper does not have: **494
verified scripts to use as oracles.**

### Where we are (verified against `origin/main`, 2026-09-06)

| | |
| :-- | :-- |
| Engine | `apps/api/services/engine/graph_engine.py` transpiles `.graph.json` → sandboxed CadQuery. **19 node types** (3 solids, 3 profiles + extrude, 3 booleans, 3 transforms, 2 patterns, 4 finishing), cycle/socket/dangling-ref validation, tier-gated `pro+`, CI-enforced generated node catalog |
| Coverage | **2 of 500** cartridges are graphs (`flange-plate`, `spacer-block`), hand-authored as references |
| Expressibility | **134 / 494 (27 %)** mechanically expressible today; six more node types (revolve, loft, sweep, text, point array, free-form profile) reach **369 (75 %)**; seven more reach 390 (79 %); **104** need low-level `Solid`/`Wire`/`Face` (86) or `Assembly` (21) work and are not node-expressible without an escape hatch. The single biggest unlock is the free-form profile node — **218** cartridges use polyline/arc paths |
| Verification hole | the keystone is **blind to graphs**: `y4d-spec` renders `.py`/`.cq`/`.scad` only, so the two graph cartridges have no render bar, no watertight/body-count check and no nightly row |
| Studio | the graph view is **read-only** (`ScadEditor.tsx` Text/Graph toggle + validation panel); the mutation model exists, but no palette, drag-to-connect, parameter editing or save path calls it |
| Expressions | **landed (G-EXPR).** A node input is a literal, `{"param": id}`, or `{"expr": "width / 2 - wall"}` over manifest parameters — see `docs/guides/graph-cartridges.md`. _Drift ledger — G-EXPR, 2026-09-06. This row read "**none.** A node input is a literal or a bound manifest parameter, never `width / 2 - wall`", which was true of `origin/main` at `3c700d53` when the section was written and false the moment this lane landed. No gate covers this table; it is hand-written prose about the engine's capabilities._ |

### Wave D — foundation

_Exit criterion: the 2 graph cartridges have nightly rows, and a Tier-A cartridge authored
as a graph passes the same bar as its script. Effort ≈ 6 lanes._

- [ ] **G-SPEC:** teach `y4d-spec` the graph engine — `mode_sources()` recognises
  `.graph.json` and the renderer transpiles through the same `graph_engine` code (shared as
  a package or vendored with a pinned catalog), judged exactly like a script. **This comes
  first: until it exists, growing graph coverage grows _unverified_ surface.**
- [x] **G-EXPR:** `{"expr": "..."}` and `{"param": id}` socket inputs, on the same dialect
  the constraints use (`apps/studio/src/lib/safeFormula.ts`, ported to
  `apps/api/services/engine/graph_expr.py` and cross-validated against that file's own
  accept/reject vectors). Parsed at transpile time — an unknown identifier or a syntax
  error is a hard validation error — and emitted as arithmetic over the same `_param`
  probes a binding emits, so a derived dimension stays live at render time instead of
  freezing into a constant. Graph format `1.1`. Proof: `flange-plate`'s bolt spacing is now
  `{"expr": "360 / bolt_count"}` and its `bolt_spacing_deg` slider is gone; the STL is
  byte-identical at the defaults and matches, at `bolt_count: 8`, what the old graph
  produced only when the author *also* set the spacing to 45 by hand — leaving it at 60 had
  silently rendered the 6-bolt part.
- [ ] **G-LIST:** a `list`/`points` socket type plus range/series/repeat nodes —
  Grasshopper's data trees, deliberately scoped to one level.
- [ ] **G-NODES-1:** free-form profile path (line/arc/spline segments) — the 218-cartridge
  unlock — plus the point-array socket.
- [ ] **G-NODES-2:** loft, sweep, **bounded** revolve, and text with `fontPath`. Revolve
  needs a memory-bounded design: an unbounded revolve OOM-killed the render worker during
  bring-up, which is why it is absent today.
- [ ] **G-DEADPARAM:** keystone rule — a declared parameter must be referenced by every
  source that lists it. OpenSCAD silently accepts unknown `-D` parameters, so three manifest
  parameters were never consumed by their sources; a graph cannot have that bug (an unbound
  input is a validation error), but scripts need the rule.

### Wave E — authoring at scale

_Exit criterion: ≥ 50 % of the catalogue served from graphs, each with parity to the script
it retires. Effort ≈ 6–8 lanes (the twins are the long tail)._

- [ ] **G-SCAFFOLD:** script → graph skeleton generator (parameters bound, structure
  inferred from the operation trace, derived dimensions left as `expr` for the author to
  confirm) plus the per-cartridge readiness matrix in `docs/`. Depends on G-EXPR — a
  scaffolder without expressions produces frozen graphs. Fully automatic transpilation of a
  script's operation trace is **rejected**: it flattens every derived value into a constant
  and produces a graph nobody would maintain.
- [ ] **G-TWIN-A / G-TWIN-B:** golden-twin graphs for the 134 Tier-A cartridges, then
  Tier-B. **The golden-twin rule:** a graph authored for a cartridge that already has a
  script must agree with that script under `--parity` for every preset before the script is
  retired. This turns the existing scripts into the test oracle for the graphs.
- [ ] **G-SCRIPT-NODE:** an embedded-CadQuery escape hatch for the 104 low-level cartridges,
  staying inside the render sandbox. Grasshopper has one too.

### Wave F — the editor

_Exit criterion: a designer builds a new Tier-A hyperobject in the Studio without writing a
script, and it passes the bar. Effort ≈ 6 lanes. G-EDITOR can start after Wave D — it only
needs the schema stable._

- [ ] **G-EDITOR:** palette, drag-to-connect through the existing `connect()` (which already
  refuses type mismatches and cycles), node-parameter editing, node positions in `meta`, and
  a save path. React Flow is MIT and already a dependency.
- [ ] **G-PREVIEW:** per-node preview by rendering the sub-graph up to the selected node —
  the transpiler already emits in topological order, so cutting emission at node N is
  cheap, and the render queue already exists. Server round-trips first; OCCT-wasm only if
  the LGPL-2.1 source-availability ruling allows it in an AGPL-3.0 repo.
- [ ] **G-CLUSTERS:** sub-graphs as reusable nodes — the commons-lib idiom for graphs, and
  how BOSL2-style helpers become nodes.
- [ ] **G-PROMOTE:** a node input promotes itself to a manifest parameter (id, range,
  default, i18n label), so `parameters[]` is generated from the graph; `constraints[]`
  derived where node semantics imply them.

### Wave S — soft track (parallel)

_Exit criterion: a garment block authored as a graph drafts identically to its script.
Effort ≈ 4–6 lanes._

- [ ] **FC-GRAPH:** a 2D drafting vocabulary for fashion-cabinet — measurements →
  construction lines → curves → offsets/seam allowances → pieces, with `curve`/`piece`
  sockets.
- [ ] **FC-TWIN:** golden twins for the block cartridges, verified against the `fc` kernel's
  drafts.
- [ ] **FC-BRIDGE-NODES:** hardware bindings to solid cartridges as nodes, so the
  yantra4d ↔ FC bridge becomes graph-level.

### Sequencing and the decisions this programme assumes

**D before E** (a scaffolder without expressions produces frozen graphs); **E before F** for
coverage, though F's G-EDITOR can start after D. Four decisions gate the programme and are
taken as recommended unless an RFC overturns them:

1. **Graph is an authoring format verified through its transpiled output**, with the
   golden-twin rule — not a peer engine under the dual-engine rule.
2. **Coverage target** = every new cartridge in an expressible class, plus a Tier-A/B
   back-fill, with the script node for the remaining 104. "All 500" is not reachable without
   that escape hatch.
3. **Expressions first**, because they unlock the scaffolder and honest parametricity.
4. **OCCT-wasm** needs the LGPL ruling before per-node preview leaves the server.

Beyond the catalogue, the same document model carries analysis nodes (mass, centroid,
wall-thickness, overhang — already computed by the keystone's notes), solver/optimisation
nodes (natural on a dataflow, impossible on an opaque script), AI-assisted authoring (a graph
is exactly what an assistant can propose, explain node by node, and have verified by the same
bar), and the CDG standard itself, where a mating interface becomes a node with typed sockets
and "does A mate with B" becomes a graph-level check.
