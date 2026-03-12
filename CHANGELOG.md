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
- **Per-Project CI Template** — `.github/workflows/project-ci.yml` template created and distributed via `propagate_ci.sh` to give all 33 federated project repositories their own independent CI pipelines.
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

### Security
- **Printer path traversal fix** — `_load_printer()` and `dispatch_print()` now
  use `safe_join_path()` to prevent directory traversal via crafted `printer_id`
  or `file_path` values.
- **Printer auth hardening** — All printer endpoints upgraded from `optional_auth`
  to `@require_tier("pro")`; added regex-based `printer_id` validation.
- **NPM token leak** — Removed `ENV NPM_MADFAM_TOKEN` from studio and admin
  Dockerfiles; token stays as build-time `ARG` only, not persisted in image layers.

### Changed
- **Gitmodules Configuration** — Appended `update = none` instruction to the `projects/tablaco` submodule to automatically exclude it from causing checkout failures during anonymous or unauthed public clones of the overarching application.
- **Project Manifest Schema** — `project.engine` enum extended to include
  `"implicit"` alongside `"openscad"` and `"cadquery"`.
- **CHANGELOG** — Retroactively versioned from `v0.1.0` through `v0.10.0`.
- **Billing tier rename** — `basic` tier renamed to `essentials` across tiers
  and UI; wired tier system to Dhanam billing platform.
- **Gunicorn workers** — Worker count now configurable via `WEB_CONCURRENCY`
  env var (default 4, was hardcoded 2).
- **CI audit enforcement** — Replaced `|| true` with `--audit-level=high` (npm)
  and `--severity high` (pip-audit) to fail CI on high-severity vulnerabilities.

### Fixed
- **Backend Render Cache Collisions** — `render.py` now secures `stl_prefix` file names by hashing the target SCAD parameters (`param_hash`). This perfectly resolves a severe race condition where rendering a sub-component inside a complex assembly mode overwrote the `.glb` cache file of the standalone single-component mode.
- **Frontend Mode Transitions** — `useProjectParams.js` now strictly strips out any URL state attributes that are explicitly restricted by a component's `visible_in_modes` manifest definition when transitioning between 3D UI states, comprehensively eliminating parameter ghosting.
- **JSON error handlers** — Added 405, 413, 429 error handlers to return JSON
  responses instead of Flask's default HTML error pages.
- **Animation tier gating** — Replaced proxy `cadquery_engine` feature check
  with dedicated `animation` flag in `tiers.json` (pro+ only).
- **MQTT default** — Changed `MQTT_ENABLED` default from `"true"` to `"false"`
  so the broker is opt-in rather than silently required.
- **force_deploy** — Consolidated path-filter and force logic into a single
  `decide` step in `deploy.yml` so the `force_deploy` input actually works.
- **Landing build-arg** — Added missing `PUBLIC_STUDIO_URL` to the build-landing
  CI job so the "Launch Studio" link resolves correctly in production.
- **Admin Dockerfile** — Added missing `VITE_JANUA_REDIRECT_URI` env var.
- **STL Download Delivers Corrupt GLB File** — `_post_render_convert` in
  `render_orchestrator.py` was unconditionally replacing the STL file URL with
  the GLB URL it creates for the 3D viewer, causing the "Download STL" button to
  deliver a misnamed GLB binary to the user (un-openable in any slicer). Fixed
  by separating the concerns: the render response now carries `url` (the actual
  requested format, e.g. `.stl`) and `viewer_url` (the GLB for the Three.js
  viewport). `renderService.ts` maps `viewer_url` into `url` for the viewer and
  stores the original format URL as `download_url`. `useProjectActions.js`
  `handleDownloadStl` now resolves the download URL via
  `part.download_url || part.url`. Covered by 2 new frontend tests and 6 new
  Python unit tests (`test_render_orchestrator.py`).
- **Stale Blob URL L1 cache bug** — `useRender.js` now exports `evictCache(key)` to purge a specific entry from the L1 in-memory render cache. `useProjectParams.js` calls `evictCache` inside the blob-revocation cleanup whenever a part's `blob:` URL is revoked. This prevents Three.js from receiving dead blob URLs on L1 cache hits after repeated parameter toggles, fixing the parameter toggle (e.g. "Carry Handle") breaking after ~3 cycles with `ERR_FILE_NOT_FOUND`.

### Infrastructure
- **K8s analytics PVC** — Added 1Gi `ReadWriteOnce` persistent volume for the
  analytics SQLite database; backend deployment mounts at `/app/backend/data`.
- **K8s secrets** — Added `AI_API_KEY` secret ref, explicit `MQTT_ENABLED=false`
  and `RATE_LIMIT_ENABLED=true` env vars to the backend deployment.
- **Docker healthchecks** — Added wget-based healthchecks to studio and admin
  services in `docker-compose.yml`.
- **Post-deploy verification** — `verify-deploy` job in `deploy.yml` checks
  production health endpoint after ArgoCD rollout.
- **Admin CI job** — Added lint, build, audit, and test pipeline for the admin
  app to `ci.yml`.
- **Janua auth gate** — Enabled Janua authentication in admin app production
  builds.

### Documentation
- **OpenAPI spec** — Added 15 previously undocumented endpoints: printer (4),
  animations (2), materials (2), storefront (2), catalog (2), assembly-steps (2),
  client config (1), admin flags PATCH (1).
- **CHANGELOG** — Retroactive entries for billing rename, admin app, responsive
  rounds, all Sprint 13–15 features.

### Testing
- **Printer route tests** — 13 test cases covering list, status, dispatch, cancel,
  path traversal prevention, and auth gating.
- **Animation route tests** — List, render SSE stream, error events, tier gating.
- **Animation utility tests** — Pure function tests for `_ease()` and
  `_interpolate_params()`.
- **Catalog route tests** — NopSCADlib category listing and component lookup.
- **Studio component tests** — AnimationPanel (8), PrintPanel (8),
  ReviewStep (7), SaveStep (9), UpgradeDialog (6), PresetGallery (7),
  CarouselUIOverlay (9), CarouselItem (4), ProjectCarousel3D (4).
- **Admin test bootstrap** — Vitest framework with 50% coverage thresholds;
  App and AuthGuard smoke tests.

### Known Tech Debt
- `--legacy-peer-deps` required in studio Dockerfile because `@janua/react-sdk`
  declares React 18 peer dependency. Will resolve when Janua publishes React 19
  peer support.
- Admin app: ESLint 8→9 and Vite 5→7 upgrades planned. React 18→19 deferred
  until `@janua/react-sdk` compatibility.

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
