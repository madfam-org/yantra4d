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
- **The Commons Is Consumed At A Pin — `projects/` Is One Submodule** — RFC 0038
  §9 "Topology P2". The 35 public satellite cartridge repos are absorbed into
  `madfam-org/solid-hyperobjects` with full history and archived, so `.gitmodules`
  goes from 43 entries to 9: six `libs/*`, one `projects` (the commons), and the
  two client-private cartridges, which move to their own root at
  `private-projects/` and keep `update = none`. The commons repo holds each
  cartridge at `<slug>/`, so `projects/<slug>` still resolves and no cartridge
  path in the platform changes.

  **Two cartridge roots.** `Config.PRIVATE_PROJECTS_DIR` (env-overridable) joins
  `CARTRIDGES_DIRS`, and `utils/project_resolver` gains the single ordered search
  every read path now goes through — `project_roots()`, `find_project_dir()`,
  `project_write_root()`. The public commons wins a slug collision; writes
  (onboarding, forking, GitHub import) always target the public root but check
  existence across both, so nothing can shadow a private slug. The
  path-traversal guard is written once and applies per root. Access control is
  unchanged and stays slug-based (`PROJECT_ACCESS_GRANTS`, docs/AUTH.md).

  **The engine fixture leaves the commons.** `cq-hyperobject-test` was never a
  Commons object — the catalog and licence audit always excluded it — but it sat
  in `projects/`, which is why the API served 501 projects over a 500-cartridge
  commons. It is vendored at `apps/api/tests/fixtures/cartridges/` from
  `madfam-org/cq-hyperobject-test@c970dbc`. **The API now serves 500, and 500 is
  also the commons count.**

  **Every submodule-aware gate re-based.** The "submodule-backed vs vendored"
  distinction (34 cartridges) no longer exists, and four gates would have gone
  silently green rather than failing: the #86 ratchet in `validate_manifests.py`
  is re-targeted to "the `projects` submodule is initialised and non-empty" (and
  cannot fail on the private mounts, which are out of its scope by
  construction); `generate-landing-projects.mjs` gates on the commons carrying at
  least one cartridge; `generate_commons_catalog.py` gives every cartridge one
  `clone` shape pointing at the commons repo, plus `source.repo`;
  `check_licenses.py` drops the "published as its own repo" severity;
  `derive_mating_candidates.py` now reads all 500 cartridges instead of skipping
  the 34 satellites for determinism (500 scanned / 0 out of scope, was 466).
  `value_extraction_audit.py`'s docstring claimed 35 submodule-backed cartridges
  where the truth was 34 and is now 0 — corrected (open item F5).

### Removed
- **The Satellite-Era Bump Machinery** — `update-submodules.yml` (weekly, bumped
  all 43 submodules), `bump-submodule.yml` (a `repository_dispatch` receiver
  that pushed straight to `main`, one per cartridge repo), `project-ci-reusable.yml`
  and `project-ci.yml` (which each cartridge repo called to fire that dispatch),
  and `scripts/propagate_ci.sh` / `scripts/ci/propagate_project_ci.{sh,py}`
  (which pushed a CI template into the `madfam-org/<slug>` repos). One commons
  repo means one pin, so all of it is replaced by a single scheduled
  `bump-commons-pin.yml` that opens a PR when `solid-hyperobjects` main moves.
  Issue #69's dormant 33-repo bump loop is retired by construction rather than
  fixed; its `DISPATCH_TOKEN` / org-toggle guard is carried over verbatim so the
  replacement fails loud, not silent.

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
- **Derived CDG Mating-Rule Candidates (PROPOSED)** — `scripts/qa/derive_mating_candidates.py`
  reads the CDG interfaces the cartridges already declare, derives the mating rules
  those declarations imply, scores each candidate against the author-written answer
  key, and proposes a ratification order. Output is
  `docs/interfaces/mating-candidates.json` plus the narrative in
  `docs/strategy/CDG-MATING-RULES-PROPOSAL.md`. Nothing is ratified by this: the
  document is explicitly **PROPOSED**, and the only thing CI enforces is that the
  derivation is not stale — `--check` runs in the `manifest-sync` job, so a manifest
  that changes what the interfaces imply cannot leave the proposal describing a
  commons that no longer exists.
- **Rasters for the 174 Cartridges That Had None** — every cartridge that shipped
  only the type-on-flat SVG placeholder now has a real thumbnail: 348 WEBP files
  (two sizes each), wearables first. `docs/strategy/TRIM-GLYPHS.md` lands with them —
  the notion→cartridge→parameter inventory behind Fashion Cabinet flats v2, mapping
  each garment notion to the cartridge that makes it and the parameter that sizes it.
  The landing gallery reads each card's raster from what is on disk, so
  `apps/landing/src/data/projects.ts` was regenerated in the same wave.
- **SIXTH-100 Strategy (proposed)** — `docs/strategy/SIXTH-100-STRATEGY.md` ranks
  candidates for cartridges 501–600 by leverage × demand, computed from
  `docs/commons-catalog.json` at 500 cartridges and from the Fashion Cabinet
  indexes. Proposed, not ratified: it commits nothing and nothing in CI enforces it.
- **Browser-First Render Placement** — The visitor's browser is now the DEFAULT
  place a render runs; the server is the exception. `decideRenderPlacement()`
  (`apps/studio/src/services/engine/renderPlacement.ts`) is a PURE function with
  an 11-rule precedence table: four HARD rules first (the MODE's engine is
  `cadquery`/`graph`/`implicit`, manifest `render.server_only`, a wasm bundle
  that is unavailable or names `unsupported`/`unresolved`, and an `export_format`
  the browser kernel cannot emit), then `?render=` /
  `VITE_RENDER_MODE`, the visitor's placement preference, capability tier, this
  session's browser failures for the slug, the estimate budget, the SOFT
  `force_backend` hint, and finally **browser**. The export-format rule is per
  REQUEST, not per cartridge, and it sits **above** `?render=wasm` and above the
  visitor's own preference: the worker writes one `/output.stl` and has no
  converter, so a placement choice cannot make the kernel emit STEP. `useRender`
  forwards the export panel's format on every render, so without that rule a
  cartridge set to `step` rendered STL in the browser and the download saved it
  as `.step` — and skipped both of #87's tier gates, which sit only on the
  server's generation and retrieval paths. A soft server decision flips
  back to the browser when `/api/health` says the server is unreachable; a hard
  one does not. Engine is resolved PER MODE by `effectiveModeEngine()`, mirroring
  `ProjectManifest.mode_engine()`, so the 8 dual-engine cartridges keep their
  OpenSCAD modes on the free path. New `RenderPlacementControl` in the sidebar
  shows the placement, the deciding rule, and an Auto/Browser/Server choice —
  and never shows a quota next to a browser render.
- **Device Capability Probe** — `services/engine/renderCapability.ts` classifies
  a device `capable | limited | incapable` from static signals (WebAssembly,
  SIMD via a 29-byte `i8x16.splat` module, `hardwareConcurrency`, `deviceMemory`,
  mobile, `crossOriginIsolated`, Save-Data / `prefers-reduced-data`) **plus** a
  one-shot micro-benchmark run in the worker, cached in `localStorage` under a
  versioned key and re-probed after 7 days. A signal the browser withholds reads
  as *unknown* and neither promotes nor demotes. A probe that could not run at
  all is trusted for 1 hour, not a week, so a CDN hiccup cannot pin a device to
  metered renders.
- **`GET /api/projects/<slug>/wasm-bundle`** — Hands the browser worker the whole
  filesystem for a cartridge in one response: the transitively resolved
  `include`/`use` closure (allowlisted to `projects/` and `libs/`), the fonts
  base64'd, and a `fonts.conf` generated by the same `fontconfig_xml()` the
  native renderer uses. Honest about its limits: `unsupported` (`import`,
  `surface`, `unresolved_includes`) and `unresolved` both mean a server render is
  required. Refusals: 400 `engine_not_wasm`, 403 `project_locked`, 404
  `project_not_found`, 413 `bundle_too_large` (24 MiB / 600 files). ETag'd and
  cacheable for public projects, `no-store` for private ones. Never rate limited
  beyond the app-wide default — every request it satisfies is a server render
  that never happens.
- **Manifest `render.*` keys** — `render.server_only` (boolean, the HARD server
  pin) and `render.browser_max_estimate_seconds` (number, a per-cartridge browser
  budget replacing the per-tier default of 45 s capable / 15 s limited), both
  added to `packages/schemas/project-manifest.schema.json`.
- **Render Artifacts Behind a Storage Abstraction (ADR-014)** — Finished renders
  now go through an `ArtifactStore` (`apps/api/services/storage/`) instead of
  straight to a shared directory, with two backends: `fs` (today's static
  directory, **the default**) and `s3` (any S3-compatible endpoint, path-style
  addressing, MinIO-compatible). The point is the coupling this removes: the
  render worker writes artifacts into `/app/backend/static` and the API serves
  them from that same path, so the two can only run in one pod sharing an
  `emptyDir`. Split them and every render succeeds and then 404s on download —
  quietly, with the cache recording the artifact as present. With
  `RENDER_ARTIFACT_STORE=s3` there is no shared filesystem to split.
  **Nothing changes by default.** Under `fs`, publishing an artifact that a
  render already wrote to its final path is an `os.path.samefile` no-op — no
  copy, same inode, same mtime, so a volume with a hard `sizeLimit` does not
  double and the GC's mtime ordering is untouched — and the read path stays on
  `send_from_directory`/`send_file`, so `ETag`, `Last-Modified`,
  `Content-Length`, conditional 304s and range requests are byte-for-byte what
  they were. `tests/e2e/test_artifact_store_serving.py` compares real responses
  against the pre-change Flask calls, header for header.
  URLs are unchanged on both backends (`/static/<slug>_preview_<hash>_<part>.<fmt>`),
  which is what keeps #78's private-project gate and the download route's access
  checks applying with no change — both parse the artifact *name*. Object-store
  artifacts are **streamed through the API**, never redirected to a bucket URL,
  so those gates run on every request; there is deliberately no presigned-URL
  path in the S3 backend. Credentials come from the standard `AWS_*` environment
  variables only and are never held on a config object. `s3` **fails closed and
  loud at startup** (`HeadBucket`) in both the API and the worker rather than
  accepting renders it cannot serve back. The render cache now records store
  **keys** rather than absolute paths and validates entries with
  `ArtifactStore.exists`, so a key missing from the store is simply a cache miss
  — which is what makes flipping the flag safe in both directions, rollback
  included. `/api/health` reports the store kind (kind only: the endpoint and
  bucket stay out of an unauthenticated response). k8s manifests carry the
  settings on both containers with the endpoint and credentials as `optional:
  true` Secret references, so the pod starts without them; the bucket is
  provisioned by the operator through Enclii.
  The **read** side goes through the store too, which is what makes the flag
  actually flippable: the render GC lists and deletes through it (so age expiry
  works against a bucket instead of sweeping an empty scratch directory and
  leaving every artifact in place forever); the three routes that each globbed
  the static directory for "the latest render" — wall-thickness and overhang
  analysis, the FEA stress overlay, the Cotiza quote — share one store lookup;
  and the verifier and printer upload, which need a real file rather than a
  stream, get one from `local_artifact()` — the artifact's own path under `fs`,
  a temporary download removed afterwards under `s3`. The streamed read path
  answers `Range` (206 with `Content-Range`, 416 when unsatisfiable, `If-Range`
  honoured) and `If-None-Match`/`If-Modified-Since` (304), with ranges pushed
  down to the bucket rather than sliced in the API pod. `/static` is now served
  by a single store-backed rule on both backends — Flask's built-in `static`
  endpoint shadowed the app's own view and is no longer registered — so the two
  backends send identical headers, `Cache-Control: no-cache` included, and a
  private project's artifact is `private, no-store` with no validator reaching
  an unentitled caller either way. See
  [`docs/operations/render-artifact-storage.md`](docs/operations/render-artifact-storage.md)
  for the operator flip runbook and the rollback (flip the flag back).
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

### Security
- **Render Cancellation Is Scoped to the Caller's Own Jobs** — the render
  WebSocket channel's `cancel` action called a cancel-everything orchestrator alias
  with no auth, no scope check and no rate limit, so any anonymous client could
  kill every in-flight render on the single backend replica. `cancel` is now always
  refused on the socket and the alias is deleted. `POST /api/render-cancel` is the
  supported path and it is a **capability**: it cancels only the `request_id` /
  `job_ids` the caller was handed on its own render stream. `{"all": true}` still
  reaches `cancel_all_renders()` but sits behind `require_role("admin")`. An empty
  body is refused with 400 `cancel_target_required` rather than silently meaning
  "everything".
- **Every WebSocket Channel Authorises the Read** — #83 gave the WebSocket module
  an identity but left the two broadcast channels anonymous-readable, on the
  reasoning that a read-only stream discloses nothing. It does:
  `/api/ws/printer/<id>` forwards the same shop-floor status that
  `GET /api/printers/<id>/status` serves behind `@require_tier("pro")`, so
  connecting to the socket instead of calling the route skipped the tier gate
  entirely; `/api/ws/telemetry/<slug>` streams live sensor data for one project,
  including cartridges listed in `PRIVATE_PROJECTS`, which no HTTP route serves at
  all. The matrix is now `render` anonymous (ping/pong; `cancel` refused to
  everyone), `printer` at the `pro` tier its HTTP twin requires, and `telemetry`
  signed-in **plus** the private-project gate — resolved through
  `project_access.project_view_denied_reason`, a response-free sibling of
  `check_project_access`, so the HTTP and WS answers cannot drift. A refused reader
  gets one `error` frame and is closed before any payload, before the MQTT queue is
  read, and without occupying a per-IP connection slot. `AUTH_ENABLED=false`
  short-circuits both gates exactly as `@require_tier` does. Anonymous gained no
  capability; two channels lost capabilities they should never have had.
- **Export-Format Downloads Are Gated at Retrieval, Not Only at Generation** — the
  tier check sat on the render that produces a file and not on the route that hands
  it over, so a guest who knew a `step`/`glb` filename got a 200.
  `export_format_allowed(effective_tier(), fmt)` now runs on the download route
  after the access-control check; `scad` stays source-gated, and a missing
  premium-tier artifact answers 403 rather than 404 so the refusal does not depend
  on whether the file happens to exist. `effective_tier()` and
  `export_format_denied_response()` moved to `middleware/auth.py` so the
  render-time and download-time gates share one binding instead of two that can
  drift.
- **Stale JWKS Is Served While a Refresh Is Failing** — `PyJWKClient` is now the
  fetcher only; `middleware/auth.py` owns a stale-while-revalidate cache: fresh →
  serve, expired → refresh and on failure warn, mark stale and keep serving,
  unknown `kid` → one refresh, stale past the ceiling or never fetched → fail
  closed. Single-flighted with backoff. New settings `JWKS_CACHE_LIFESPAN`,
  `JWKS_STALE_MAX_AGE`, `JWKS_REFRESH_BACKOFF`. A Janua blip no longer logs
  everyone out of a running deployment, and an indefinitely unreachable issuer
  still fails closed rather than trusting an ancient key set forever.
- **The Legacy Manifest, Config, Estimate and AI-Session Routes Answer the
  Private-Project Gate** — the private-project check landed on the current routes
  but the older single-project aliases still served a private cartridge's manifest,
  its config, its estimate and an AI session against it. All four now go through
  the same `can_view_project` path as everything else.
- **A Missing Project's 404 Names the Slug, Not the Filesystem** —
  `manifest.py::load_manifest` interpolated the resolved manifest path into its
  error, and every manifest route answers a missing project with
  `{"error": str(e)}`. Because `_resolve_project_dir` falls back to
  `Config.SCAD_DIR` for a slug it cannot resolve, the body disclosed the
  deployment's absolute filesystem path *and* the name of the single-project
  default — in production, `gridfinity`. The message now names the requested slug
  and nothing else; the path is still logged at ERROR, which is the useful half.

### Changed
- **Pushes Are Classified Too — the Deploy's Digest Bump No Longer Reruns the
  Full Matrix** — the `changes` job classified pull requests only, so merging a
  PR ran the whole matrix for the merge commit and then ran it *again* for the
  `deploy(yantra4d): update digests` push that `deploy.yml` makes straight
  afterwards — a push that writes only `k8s/production/kustomization.yaml`, a
  file no job in `ci.yml` reads. That path is now negated in the filter and the
  job classifies `push` events as well: a pull request is diffed through the
  REST API against its base, a push with git against `github.event.before`,
  which is why the job gained a push-only `fetch-depth: 0` checkout and a
  "Resolve the push base" guard. It still fails **closed** — an all-zero
  `before` (new branch, first push), a `before` no longer reachable after a
  force push, an empty filter output, or any other event classifies as code —
  and `scripts/tests/test_ci_changes_classification.py` executes the job's own
  shell to pin exactly that. `deploy.yml` already excluded the kustomization
  from its own triggers for the same reason; this is the other half of the rule.
- **The Registry Login Is a Script, Pinned by Its Own Test** — the retry loop
  #107 introduced was inline YAML duplicated across eight steps in `deploy.yml`'s
  four build jobs, so nothing could run it outside a deploy and its backoff was
  only ever exercised by a real GHCR outage. It is now
  `scripts/ci/registry_login.sh`, called from a `run:` step, and
  `scripts/ci/tests/test_registry_login.sh` covers it in the `ci-scripts` job:
  the suite stubs `docker` and `sleep` on `PATH`, so no registry is contacted and
  the 10/20/30/40 s backoff is asserted as recorded data rather than waited out.
  The script also exits 2 immediately when a credential arrives empty — an unset
  `secrets.*` reaches a step as an empty string, which `set -u` cannot catch.
- **Unit Tests for the QA Lanes That Had None, and a Pinned `ruff`** — eight of
  the `scripts/qa` gates were enforcing the commons in CI while being covered by
  nothing themselves, which is the same "green for the wrong reason" failure
  they exist to catch; `scripts/tests/` now carries suites for the licence,
  OpenAPI, sandbox-sync, compliance, catalog-generation, graph-catalog, i18n and
  fallback-manifest checks. Two of them cannot live only in
  `manifest-validation`, because that job installs neither PyYAML and
  openapi-spec-validator nor trimesh and numpy and the modules would silently
  skip: `test_check_openapi.py` runs again in `openapi-validation` and
  `test_verify_parity.py` in `backend`, where the dependencies already exist.
  `ruff` was installed unpinned, so the rule set CI enforced was whatever ruff
  had released by the time the job started; it is now `0.16.5` in both `ci.yml`
  and `apps/api/requirements-dev.txt`, with `scripts/tests/test_ruff_pin.py`
  failing if the two ever disagree. `apps/api/pyproject.toml` pins the rules; the
  version pins the engine that reads them.
- **`verify_parity` Compares Real Dual-Engine Pairs and Survives a Sandbox
  Rejection** — it resolved a mode's OpenSCAD source from `scad_file` and handed
  that path to OpenSCAD, but CadQuery-only cartridges point `scad_file` at their
  own `.py` as a placeholder, so OpenSCAD was being asked to parse Python and
  every pair "failed". Candidate selection now mirrors
  `generate_commons_catalog::_engine_support`: a real `.scad` plus a real `.py`,
  a placeholder `scad_file` is skipped rather than rendered, a declared-but-absent
  file fails and an inferred-absent sibling skips. A CadQuery sandbox rejection
  (`SystemExit`) no longer kills the whole audit. Measured on the real
  dual-engine set it went from "everything fails" to 10 of 29 pairs passing —
  which is why the docs now call the Geometric Parity Guarantee an **intent**
  rather than an enforced invariant. It is still not a CI lane and wiring it in
  would fail the build on day one.
- **Ten Parity-Fixed Cartridges Pinned; `dual_engine` 22 → 21** — the parity
  triage fixed real geometry defects on both kernels across ten cartridges
  (blind holes, a rail channel cut outside its body, a hollowed housing, doubled
  hook widths, unfilleted pockets, inverted miters, wrong manifest defaults);
  each fix merged in its own cartridge repository and is pinned here at that
  repository's `main`. `implicit-lattice-hyperobject` stopped claiming an
  OpenSCAD kernel it never implemented, so `counts.dual_engine` goes 22 → 21 and
  `counts` OpenSCAD-declaring goes 32 → 31 in `docs/commons-catalog.json`,
  `COMMONS.md`, `README.md` and the value-extraction audit. The studio's offline
  fallback manifest was resynced from the pinned gridfinity manifest (five
  presets `cup_scad` → `cup`). Re-measured, `verify_parity` reports **18 of 28**
  comparable pairs passing, up from 10 of 29.
- **State-Aware E2E Waits Instead of Absent-Button Waits** — webkit shard timing
  flakes on the shared pool came from specs waiting on buttons that are unmounted
  for the whole of a render, or sleeping on mocks. The studio sidebar root now
  publishes `data-render-state="rendering|idle"`, derived from the `loading` flag
  that already renders Processing.../Cancel, so it introduces no state of its
  own; the page object waits on that reported state (`waitForRenderOutput`,
  `waitForRenderState`, `cancelRenderAndWaitForIdle`, held routes) and
  `editSliderValue` converges on the value the app actually commits — clamped,
  step-rounded, display-rounded, with the inches path mirrored — under a shared
  phase budget inside the 60 s test timeout. No test was skipped, disabled or
  weakened.
- **Registry Logins Retry With Backoff Instead of Dying On One Timeout** —
  `docker/login-action@v3` has no retry of its own, so a single transient network
  failure at login killed a whole build job, and because *Commit Image Digests*
  needs all four builds it killed the deploy. Deploy run 33633417615 was lost that
  way twice on 2026-09-02, both times on `net/http: TLS handshake timeout` reaching
  GHCR, while the other build jobs logged in to the same registry seconds later.
  Both logins in all four build jobs are now a `run:` step keeping the exact
  credentials the action used: the password goes in on stdin under `set +x` so
  nothing is echoed, and the login is retried five times with a 10/20/30/40 s
  backoff before the job fails with a message naming the registry. A matching
  `docker logout` runs in an `if: always()` step, mirroring what the action did in
  its post step.
- **CI Bounds `apt-get` and the Cache Restore, Lints `apps/worker`, and Stops
  Cancelled Runs Holding the Concurrency Group** — four unrelated ways CI was
  spending the shared pool badly, all observed on 2026-09-02. (1) An unreachable
  `git-core` PPA hung an e2e shard for 28 minutes until the job timeout, so every
  `apt-get` is now bounded (`timeout 300`, `Acquire::http/https::Timeout=30`,
  `Acquire::Retries=3`) with the offending source removed first. (2) A studio
  npm-cache restore stalled at 87 % for the full `SEGMENT_DOWNLOAD_TIMEOUT_MINS`
  default of ten minutes when a fresh `npm ci` takes twenty seconds; the workflow
  now sets it to `"2"`, turning a stalled restore into a cheap miss. (3)
  `apps/worker` — the process every render actually executes on — was linted by
  nothing, because `backend`'s `ruff check .` runs under
  `working-directory: apps/api` and no other job installs ruff; it now runs
  `ruff check --config apps/api/pyproject.toml apps/worker`, pointing at the API's
  own config rather than copying the rule set into a second file that can drift.
  (4) The `always()` aggregators (`ci-success`, `e2e-report`) still queued on a run
  the concurrency group had cancelled, holding the group while the superseding head
  waited; both now use `!cancelled()`, which reports exactly the same thing for
  every run that was not cancelled. The checkout-heavy budgets were widened to
  match what those checkouts actually cost: `manifest-validation` and
  `metadata-consistency` to 10 minutes, `studio` to 20.
- **Deploys Diff Against the Last SUCCESSFUL Deploy** — deploy change detection
  compared against the newest push, and `deploy.yml`'s concurrency group is serial,
  so GitHub keeps only ONE pending run per group and a third push REPLACES the
  queued second one. The replaced run never executes and its commits are never
  examined by any path filter: on 2026-09-02 merges #541 → #542 → #543 landed back
  to back, the surviving run saw only #543 (backend-only), and the Studio image
  #542 needed was never built. `scripts/ci/last_successful_deploy_sha.sh` now
  resolves the head SHA of the last successful deploy and hands it to
  `dorny/paths-filter` as the base, so a dropped run is harmless — the next run
  still sees every path that changed since the last shipped commit. Every non-zero
  exit means *build every service*; an unresolved base is never read as "nothing
  changed". Pinned against recorded API fixtures by
  `scripts/ci/tests/test_last_successful_deploy_sha.sh` in the `ci-scripts` job,
  which runs on docs-only pull requests too because it guards the machinery that
  skipping relies on. Single-service rollouts are health-checked rather than
  assumed.
- **Quality Ratchets: Uninitialised Submodules Fail, i18n Parity Is Gated, the axe
  Gate Widens to Serious** — three checks that could pass for the wrong reason.
  `scripts/qa/validate_manifests.py` now treats a `projects/<slug>` submodule that
  checked out empty as a FAILURE rather than a skip, and the local escape hatch
  `--allow-uninitialised-submodules` is never set in CI — a partial checkout must
  not be able to pass the job whose whole point is judging the commons. Locale key
  parity became a hard gate in its own `i18n-audit` job (a missing key ships
  untranslated UI), with the hardcoded-string count ratcheted against
  `scripts/qa/i18n_baseline.json` so the existing backlog does not block unrelated
  work but adding to it does. The accessibility gate widened from `critical` to
  `serious`, and the #59 click workaround was retired.
- **CI Skips the Browser Matrix on Documentation-Only PRs** — every job in
  `ci.yml` ran on every pull request, so a README-only change queued the full
  ten-shard Playwright matrix — ten jobs with a 30 minute cap each — on the same
  shared self-hosted pool a production deploy waits in. A new `changes` job now
  classifies each pull request first: **docs-only** (every changed file is a
  `*.md`, or under `docs/`, `apps/docs/`, `runbooks/`, or `.github/*.md`) skips
  the browser matrix and its report, the studio, landing and admin builds, the
  backend suite and the geometric parity check; **anything else is code** and
  runs exactly what it ran before. A pull request touching documentation *and*
  code is code, and (until #113 below) a push to `main` always ran everything.
  The classification
  uses `dorny/paths-filter` pinned to a commit, with
  `predicate-quantifier: every` so a file counts as code unless every
  documentation pattern excludes it, and the decision step fails closed: only a
  filter that ran and answered exactly `false` skips anything. No test was
  skipped, disabled or quarantined — the suite a code change runs is unchanged.
- **`ci-success` Can Now Actually Fail** — the single required check depended on
  nine jobs with the default `if: success()`, which meant a dependency that was
  skipped *or failed* left `ci-success` itself skipped, and a skipped required
  check is treated as passing. It now runs unconditionally and inspects
  every dependency's result: `failure` or `cancelled` anywhere fails it,
  `skipped` counts as passing. (The condition shipped as `if: always()` and was
  narrowed to `if: ${{ !cancelled() }}` in #106 — see *CI Stops Cancelled Runs
  Holding the Concurrency Group* below — which changes nothing about what it
  reports and stops a cancelled run's aggregator queueing on the pool.) `cancelled` matters because of the per-PR
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
- **The Landing Gallery Under-Reported the Commons and Listed a Private Cartridge**
  — `apps/landing/src/data/projects.ts` is generated from the manifests and
  committed, and nothing checked it. It had drifted to 328 entries against a
  501-cartridge commons, because the generator needs every submodule present and,
  run in a checkout without them, silently emitted the shorter list and overwrote
  the good one — no lane could see it, since the `landing` CI job checks out no
  submodules and the deploy's Build Landing job did not either. It also carried
  `tablaco`, a client-private cartridge the API has hidden from `/api/projects`
  since access control landed, with its description and a link to a Studio page
  that refuses to load. The generator now skips private cartridges on both signals
  the backend uses (`access_control.view == "private"` and the `PRIVATE_PROJECTS`
  env var, with the built-in list a floor rather than a default an empty variable
  can clear), refuses to write when a public `projects/*` submodule has no manifest
  on disk (exit 2) unless `--allow-partial`, and grew a `--check` that reports
  drift and an incomplete checkout as distinct, named failures. `--check` blocks a
  stale commit in `manifest-validation`, the only job whose checkout is complete
  enough to judge the file, and `build-landing` now regenerates at deploy so the
  shipped gallery is correct by construction. Regenerated: **328 → 501 entries**,
  `tablaco` removed. `project.unlisted` is untouched — unlisted means "not in API
  listings but reachable by URL", which is not private.
- **Active Render Jobs Have a Lease, So the Count Stays Truthful** —
  `yantra_render_active_jobs` was a plain Redis set with no expiry: the worker adds
  a job at start and removes it at finish, both in code that only runs if it
  reaches its `finally`, which a pod roll, an OOM kill or a node eviction never
  does. `/api/health` then reported `active jobs 1` against `queue depth 0`
  forever — observed in production across five samples and two rollouts, the count
  surviving the very restarts that should have cleared it. The fix is a lease, not
  a bigger cleanup: `yantra_render_job_meta:<job_id>` already carries a TTL and is
  already written and deleted alongside every set mutation, so it is exactly the
  expiring per-job key the set lacked. `prune_active_jobs()` drops members whose
  lease is gone or stamped longer ago than any real render can run, the worker
  renews the lease of everything it holds on each heartbeat tick, and
  `reconcile_active_jobs()` runs once at worker start before the first `blpop` so
  health is truthful immediately after a rollout. Redis failures degrade to "leave
  it alone": a blip never sweeps live work, and an unreadable set reports
  `active_jobs: null` rather than `0`.
- **The Studio Cancels the Render a Page Abandons** — nightly run #171 made ~95
  navigations in 40 minutes and produced ZERO `render-cancel` calls, so every
  abandoned render ran to completion against the single render worker while a live
  user's render queued behind it — starvation, not waste. `useRender` now keeps the
  cancellable identity of the render in flight (learned from `/api/render-stream`'s
  `job` event) and cancels it on `pagehide` and on unmount: `pagehide` rather than
  `beforeunload`, which does not fire for a page entering the back/forward cache
  and is unreliable on mobile Safari, with the unmount cleanup covering an in-app
  route change where no page event fires at all. The send is synchronous —
  `navigator.sendBeacon` first, then `fetch(..., {keepalive: true})` — and the
  identity is *taken*, not read, so a cancel cannot fire twice or land on a render
  that already finished. A new render also cancels the one it supersedes, so
  dragging a slider no longer leaves a trail of abandoned renders in front of the
  work the user is waiting for. `POST /api/render-cancel` parses its body as JSON
  regardless of Content-Type, because a beacon's type is whatever Blob it carries;
  every field is validated exactly as before and `{"all": true}` over a beacon is
  still refused by the same admin gate.
- **The Nightly Browser Audit Reconciled With the Shipped Product** — the first
  real results of the nightly (runs #166–#174) were four failures, and every one
  was drift between the suite and what the cartridges and the product actually
  ship: `gridfinity` is named "Gridfinity" with five modes, `custom-msh` gained
  `multi_rack`, a language-toggle click could never land because the Long Render
  Warning's Radix overlay was over it, and `locator('canvas').first()` resolved to
  a hidden canvas in the second layout tree. No product code needed fixing. The
  harness also gained the two things it was missing: `HARNESS_TIER`, so an
  auth-disabled harness can be gated as a real tier (auth-off alone does not unlock
  CadQuery, and an unknown value is dropped with a log line, silently running the
  job as `guest`), and a queue drain between spec groups so one group's abandoned
  work cannot starve the next. The drain posted an empty body to
  `POST /api/render-cancel`, which since #83 answers that with 400
  `cancel_target_required`; it now sends `{"all": true}`, the one form that still
  reaches `cancel_all_renders()`.
- **The Active Preset Is Matched Among the Ones the Mode Offers** — applying a
  preset in `custom-msh`'s assembly mode appeared to do nothing: no button ever
  highlighted, so nothing told the user the preset had landed. `Controls` derives
  the active preset by matching the current params against preset values — which is
  right, because the highlight then drops the moment a value is edited — but it
  searched the WHOLE preset list and took the first full match. Preset value sets
  overlap heavily, so a preset belonging to a *different* mode can win: after
  applying `assembly_rack_slides`, `custom-msh`'s earlier-declared `default_holder`
  is still fully satisfied, and it is not rendered in assembly mode at all
  (`visible_in_modes: ["holder"]`), so the active id pointed at a button that does
  not exist and all three visible ones stayed grey. It now searches
  `visiblePresets`, the list actually rendered. Not `custom-msh`-specific: any
  cartridge whose presets share a common parameter core hits this, and the
  earlier-declared mode always won.
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
- **`project.force_backend` demoted to a SOFT hint** — 490 of the 501 cartridges
  in the commons set the flag, and among the OpenSCAD ones it almost always
  encoded "WASM cannot load our BOSL2 include or our font" — a client limitation
  the wasm-bundle contract now closes, not a property of the model. It no longer
  pins anything: it wins only on a device measured as `limited`, and it never
  disables the browser fallback after an HTTP 429 or a server outage. Authors who
  genuinely need a server pin write `render.server_only: true`.
- **Browser worker reads the wasm bundle, not `/scad/<file>`** — The old fetch
  could never work in production: nginx's `try_files … /index.html` answers
  `/scad/anything` with the SPA's own HTML at **200 OK**, so the worker wrote a
  page of `<!doctype html>` into its virtual filesystem as SCAD; it fetched only
  the entry file, so `include <../../libs/BOSL2/std.scad>` had nothing to
  resolve; and it mounted no fonts, so `text()` silently rendered nothing at exit
  code 0. The worker now mounts the bundle at `/projects/<slug>/…`, `/libs/…` and
  `/fonts/…` with `OPENSCADPATH` and `FONTCONFIG_FILE` set in Emscripten's
  `preRun`. A `/scad/` fallback survives **dev builds only**, refuses a body
  beginning with `<!doctype`, and warns that it carries no libraries or fonts.
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
