# Changelog

All notable changes to the Yantra4D Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Versioning convention:** This project is pre-1.0. Minor bumps (`0.x.0`)
> mark sprint/phase milestones. Patch bumps (`0.x.y`) are bug-fix-only releases
> within a sprint.

---

## [Unreleased] — Sprints 13–15

### Changed
- **Top Tier Renamed `madfam` → `premium`, With a Permanent Alias** — ADR-006
  Decision 4: a company name was doing duty as a tier name on a MADFAM product,
  and `premium` is already dhanam's top tier. The ladder is now
  `guest | essentials | pro | premium`, and `premium` is the key in
  `apps/api/tiers.json`, the top of `TIER_HIERARCHY`, and what every output
  emits — `/api/me` (`tier` and `entitlement.resolved_tier`), `/api/tiers`, the
  `X-RateLimit-Tier` header, and the 403 upsell copy.

  **The alias guarantee: `madfam` is accepted forever, on every input path.**
  This is not a deprecation window with an end date. Janua's machine-token claim
  builder still synthesises the literal `yantra4d_tier: "madfam"` for any client
  holding a `yantra4d:`-namespaced scope, and an operator's `TIER_OVERRIDES`
  Secret may still say `madfam` — so the alias is load-bearing in production
  today. A token, a `TIER_OVERRIDES` value, or a `has_tier()` argument carrying
  the old name resolves to `premium` and seats exactly the same entitlements:
  unlimited renders, unlimited AI requests, GitHub sync, every export format,
  and access to private projects. **No Kubernetes Secret needs rotating and no
  consumer needs to re-mint anything.** Removing the alias would silently
  downgrade live callers to `essentials` (`resolve_tier` fails closed), so
  `LEGACY_TIER_MAP` is treated as permanent contract, pinned by tests.

  Aliases resolve in one place, `_normalize_tier`, which is the funnel
  `resolve_tier` and the config parser both go through — no call site knows an
  alias exists. The deprecation note is logged **once per process per alias**
  rather than once per request, because the alias sits on the hot path.

  The local-dev unlock is named by constant, not by string. `effective_tier()`
  (`middleware/auth.py`), which the render-time and download-time export-format
  gates share, returns `TOP_TIER` when auth is off and Flask debug is on. The
  literal it replaced would have survived the rename without a red test — the
  gates normalise their argument — while going out verbatim as
  `X-RateLimit-Tier` and ranking as guest in every hierarchy comparison.

  Studio: one helper (`src/lib/tiers.ts` — `tierAtLeast`, `normalizeTier`,
  `TOP_TIER`) now owns every tier comparison that used to be a hard-coded
  string, so a cached `/api/me` still reporting `madfam` grants what `premium`
  grants instead of gating a paying user out. Tier display names are i18n keys
  (`tier.name_*`) in all six locales, and the cloud-render upsell string is no
  longer hard-coded English. The unlimited rate-limit display from #78 is
  unchanged.

  **Deliberately unchanged: the checkout SKU.** `plan=yantra4d_madfam` still
  goes to dhanam. The SKU slug lives in tulana's catalog, not in this repo, and
  is a different namespace from the tier name; `billing.ts` now maps tier to
  plan id through an explicit table rather than deriving one from the other
  (ADR-006 Decision 5 — writing a plan id into the claim seats a paying
  customer in `essentials` with no error anywhere).

### Added
- **Value-Extraction Audit re-measured against the 500-cartridge commons** —
  `docs/strategy/VALUE-EXTRACTION-AUDIT.md` was the last document reasoning in
  `x/326` ratios, a denominator that stopped existing when the commons reached
  500. The 2026-08 findings are preserved verbatim as a dated point-in-time
  record; a new dated 2026-09 section re-measures every one of them. New
  `scripts/qa/value_extraction_audit.py` recomputes each ratio from
  `projects/*/project.json`, `docs/commons-catalog.json`, the studio locale
  files and the CDG family taxonomy in `apps/api` (stdlib only), prints a
  metric/numerator/denominator/ratio/delta table, and offers `--json`,
  `--write` (regenerate the table the document embeds) and `--cohorts` (split
  the commons into the 324 cartridges present at the audit commit and the 176
  added since). Recomputing the 2026-08 rows over that first cohort returns the
  published figures exactly — 300 `engine: cadquery`, 287 with constraints, 310
  with `material_awareness`, 294/30/16 material flags — which is what makes the
  delta column a comparison rather than two unrelated measurements. Figures the
  audit stated that are judgement, frontend import-graph reachability, or
  another QA lane's output are listed as not-recomputable rather than
  approximated with a proxy. Before measuring anything the script asserts the
  on-disk cartridge count against the catalog's `counts.cartridges`: 34
  cartridges are submodules and *every* dual-engine cartridge is one of them, so
  an uninitialised checkout would under-count silently and still print a
  plausible table. `--check` runs as one self-contained step in the existing
  `manifest-validation` CI job, and `scripts/tests/test_value_extraction_audit.py`
  adds 30 tests. What the re-measurement found: constraint coverage down 8.0 pp
  (64.2% on new cartridges vs 88.6% on audit-era ones), quadrilingual
  (de/fr/pt/zh) coverage down 6.6 pp as new keys landed untranslated, the public
  landing gallery stalled at 326 of 500 cartridges, `recycled_material_toggle`
  up from 16 to 98, and the Fashion Cabinet bridge surfaced as 72 wearables /
  49 flange interfaces / 53 bridge READMEs, none of which existed in 2026-08.
- **Fashion Cabinet consumers back-edge (blocking)** — The hardware bridge now
  pins in both directions. Fashion Cabinet vendors a slice of our commons
  catalog and resolves its `hardware_ref` notions against it, so its CI has
  always known when we moved; ours knew nothing, and renaming a parameter here
  went red days later in someone else's repo. Their published
  `yantra4d-consumers.json` (contract `yantra4d_consumers_v1`) is now vendored
  at `docs/interfaces/fashion-cabinet-consumers.snapshot.json`, commit-pinned to
  the fashion-cabinet commit it came from, and
  `scripts/qa/refresh_fc_consumers.py --check` resolves every linked claim in it
  against our own manifests — 87 cartridges consumed, 299 linked consumers, 960
  parameter references. Blocking in the `manifest-validation` CI job: rename a
  parameter a garment drives and the failure names the garment, the cartridge
  and the parameter, in the pull request that makes the change. Unlinked claims
  (their `wanted` list — `hammer-loop` is a solid a garment is waiting on) are
  reported and never enforced. Offline, stdlib-only, no timestamps; `--check`
  also rejects a hand-edited snapshot, and `--check-upstream` (network, not in
  CI) reports drift against the pin. Docs:
  `docs/reference/fashion-cabinet-consumers.md`.
- **Multi-Rack Mode (custom-msh)** — New 6th mode producing 2–5 contiguous
  staining racks joined front-to-back (Y-axis, default) or side-by-side (X-axis).
  Y-axis stacking: racks share diamond grid junction guards at Y boundaries,
  solid end walls at front/back, handle walls on left/right spanning full depth.
  X-axis stacking: racks share solid handle walls (with carry handle) at
  junctions, continuous diamond grid guards on front/back. New `multi_stack_y`
  checkbox (default ON) toggles stacking direction. `multi_rack.scad` refactored
  with axis-aware geometry: `handle_wall()`, `plain_end_wall()`,
  `junction_guard_xz()`, `continuous_side_guards()`, parameterized segment
  positioning. `multi_num_racks` parameter (slider 2–5), preset, and
  `multi_rack_body` part (render_mode 5). 1494/1494 studio tests passing.

### Changed
- **CI Skips the Browser Matrix on Documentation-Only PRs** — every job in
  `ci.yml` ran on every pull request, so a README-only change queued the full
  ten-shard Playwright matrix — ten jobs with a 30 minute cap each — on the same
  shared self-hosted pool a production deploy waits in. A new `changes` job now
  classifies each pull request first: **docs-only** (every changed file is a
  `*.md`, or under `docs/`, `apps/docs/`, `runbooks/`, or `.github/*.md`) skips
  the browser matrix and its report, the studio, landing and admin builds, the
  backend suite and the geometric parity check; **anything else is code** and
  runs exactly what it ran before. A pull request touching documentation *and*
  code is code, and a push to `main` always runs everything. The classification
  uses `dorny/paths-filter` pinned to a commit, with
  `predicate-quantifier: every` so a file counts as code unless every
  documentation pattern excludes it, and the decision step fails closed: only a
  filter that ran and answered exactly `false` skips anything. No test was
  skipped, disabled or quarantined — the suite a code change runs is unchanged.
- **`ci-success` Can Now Actually Fail** — the single required check depended on
  nine jobs with the default `if: success()`, which meant a dependency that was
  skipped *or failed* left `ci-success` itself skipped, and a skipped required
  check is treated as passing. It now runs with `if: always()` and inspects
  every dependency's result: `failure` or `cancelled` anywhere fails it,
  `skipped` counts as passing. `cancelled` matters because of the per-PR
  concurrency group added in #84 — a superseded run must not report green.
  `manifest-sync` and `spec-conformance` were added to its `needs`: both already
  ran on every pull request and spec-conformance documents itself as blocking,
  but neither was wired into the one required check, so neither could block a
  merge.
- **Deploy Jobs Take Their Runner From a Repository Variable** — all eight jobs
  in `deploy.yml` were hard-pinned to the shared pool, so a production deploy
  queued behind whatever pull request CI happened to be running: deploy #540's
  Build Studio sat queued from 04:01Z past 04:30Z behind roughly a hundred PR
  shard jobs, and deploy #542 waited behind #540 in the serial deploy
  concurrency group. Each job now resolves
  `${{ vars.DEPLOY_RUNNER_LABEL != '' && vars.DEPLOY_RUNNER_LABEL || 'madfam-runners-blue' }}`,
  the operator-override form ADR-010 already permits, so deploys can be moved to
  a dedicated runner set by setting one repository variable. Unset, the
  expression resolves to the shared pool and behaviour is byte-for-byte what it
  was. Both arms are MADFAM-operated runners; no GitHub-hosted fallback was
  introduced.

### Fixed
- **Auto-Generate No Longer Opens a Blocking Modal** — The studio renders on
  load and after every parameter change (the debounced effect in
  `useProjectParams.ts`), and `useRender` answered an over-threshold estimate
  the same way no matter who asked: it opened "⚠️ Long Render Warning", a Radix
  alertdialog over a pointer-blocking overlay. gridfinity's cadquery `bin`
  default estimates ~2 minutes against a 60s threshold, so every visit to
  `/project/gridfinity` put up a modal the visitor never asked for and froze the
  UI until they answered it — and cancelling left the empty viewer a skipped
  render produces anyway. `handleGenerate` now takes a third argument,
  `GenerateOptions.automatic`, and **only** the debounced effect passes it; the
  Generate button, Force re-render, Ctrl+Enter, the editor's save-and-render,
  the storefront and the optimizer follow-up keep today's behaviour, modal
  included. An automatic render over the threshold renders nothing and opens
  nothing: it raises a non-blocking `toast.auto_render_skipped` notice on one
  fixed toast id (so a run of slider edits replaces the notice rather than
  stacking it), records `pendingEstimate`, and waits for an explicit Generate.
  Under the threshold an automatic render is untouched. New locale key across
  all six locales (337 keys, parity OK). 11 files, 6 new tests.
- **Download Must Match Viewport (ISSUE-R2-3 follow-up)** — `handleDownloadStl`
  always triggered a fresh backend re-render for non-GLB formats, which could
  produce geometry that didn't match the 3D viewport due to param drift (e.g.,
  `assembly_level` leaking from mode defaults). The viewer's initial render
  already produces both `download_url` (STL) and `url` (GLB), so the re-render
  was redundant. Fixed in three layers: (1) `useProjectActions` checks whether
  viewer parts already have files in the requested format before re-rendering,
  with `pickUrl` helper that selects the URL matching the requested extension;
  (2) `renderCache.ts` now stores the download-format blob (STL) alongside the
  viewer blob (GLB) in IndexedDB, so `download_url` survives L2 cache
  round-trips; (3) `useRender.js` L2 restore path creates `download_url` blob
  URL from the cached download blob. 4 files, 10 new tests, 1489/1489 passing.
- **STL Export Downloads GLB Instead of STL (ISSUE-R2-3)** — Clicking "Download
  STL" served a GLB file due to three interacting bugs: (1) `renderService.ts`
  only set `download_url` when `viewer_url` was present — on cache hits it was
  `undefined`, falling back to the GLB viewer URL; (2) `downloadFile()` used
  `<a download>` which browsers ignore for cross-origin URLs, so the server's
  GLB filename overrode the code-specified `.stl` name; (3) the archive download
  used `part.url` (GLB) instead of `part.download_url` (requested format). Fixed
  by always setting `download_url`, fetching as blob before downloading (cross-
  origin safe), and preferring `download_url` in the archive handler. 4 files,
  4 new tests, 1480/1480 passing.
- **Sidebar Responsiveness (Horizontal Scrollbar)** — The left-hand configuration
  sidebar forced a 352px minimum width (`min-w-[22rem]` + `min-w-[280px]`),
  overriding the ResizablePanel's percentage-based sizing and producing a
  horizontal scrollbar at default 25% width (~320px). Replaced fixed min-widths
  with `min-w-0`, removed `shrink-0`, added `overflow-x-hidden` as defense-in-depth.
  Tightened slider value display (`w-16` → `w-14`), BOM Qty columns (`w-16` → `w-12`),
  and preset container (`max-w-full`). 4 files, 1 new test.
- **Resizable Panels v4 Migration (Crushed Sidebar + Broken Layout)** — After
  the v2→v4 component rename fix (Session 104), the studio layout was broken on
  desktop: sidebar crushed to ~40px, vertical viewer/console split rendered
  side-by-side instead of stacked. Root cause: `react-resizable-panels` v4.7.3
  renamed `direction` → `orientation`, `onLayout` → `onLayoutChanged` (with
  `{[panelId]: number}` signature instead of `number[]`), and removed
  `data-panel-group-direction` data attributes used by CSS selectors. Fixed in 4
  files: `resizable.jsx` (prop-based orientation logic replacing dead data-attr
  selectors), `App.jsx` and `StudioMainView.jsx` (`direction` → `orientation`,
  `onLayout` → `onLayoutChanged`, panel `id` props), `usePanelLayout.js` (bounds
  clamping for corrupted localStorage from the broken layout period). 8 new tests.

### Performance
- **Studio Mounts One Layout Tree, Not Two** — `App.jsx` rendered a desktop tree
  (`hidden lg:flex`) and a mobile tree (`lg:hidden`) at the same time, and the
  `StudioMainView` inside each of them did the same again, handing the identical
  viewer content to both halves. A page load therefore mounted four `<Viewer>`s
  — four `<canvas>` elements and four WebGL render loops — and three of them sat
  inside a `display:none` subtree, spending exactly the client GPU and memory
  the product wants for the model the visitor is looking at. Both files now pick
  the tree with `useIsDesktop()` (`min-width: 1024px`, Tailwind's `lg` — the
  same width the classes already used, so the JS decision and the CSS can never
  disagree); the classes stay, now redundant rather than load-bearing. Behaviour
  is unchanged at every width. Three consequences worth knowing: `viewerRef`
  used to be claimed by whichever `<Viewer>` mounted last (the hidden mobile
  one) and now points at the visible viewer; `#main-content` is in the DOM once,
  so the skip link no longer lands on a hidden element on a phone; and crossing
  1024px remounts the tree, so the viewer re-creates its canvas while params,
  parts and render results — owned by `ProjectProvider` above it — survive
  untouched. 4 files, 8 new tests.

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
- **Mode Switch Discards User Params (Rack → Assembly)** — When switching from
  `rack`, `base`, or `lid` to `assembly`, the studio applied a fallback assembly
  preset that blindly overwrote all shared params (`num_slots`, `handle`,
  `num_racks`, `wall_thickness`, etc.) back to their preset defaults. Fixed in
  `setMode` (`useProjectParams.js`): the fallback preset is now merged
  selectively — only params the user has NOT explicitly changed from their
  manifest default are taken from the preset; user-modified values are carried
  forward. System-group params (`assembly_level`) are always taken from the
  preset since they control mode-specific rendering behavior. Covered by 4 new
  tests in `useProjectParams.test.js`.
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
