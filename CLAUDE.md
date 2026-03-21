# Yantra4D — Parametric 3D Print Design Platform

Multi-project manifest-driven Flask + React/Vite platform for parametric OpenSCAD models with 3D preview (wireframe/bounding-box), evolving into a **Hyperobjects Commons**.

> **For human developers**: See [`docs/guides/developer-onboarding.md`](docs/guides/developer-onboarding.md) for a concise quickstart guide.

## Architecture

```
projects/
  {slug}/project.json  (manifest — single source of truth per project)
  {slug}/*.scad        (OpenSCAD geometry)
  {slug}/exports/      (reference STL exports)
       │
       ├──► apps/api/      (Flask API, renders via OpenSCAD CLI)
       │        ├── routes/  render, verify, health, manifest, config, projects, onboard, editor, git_ops, github, ai, admin, download, bom, datasheet, analytics, user
       │        ├── services/  render_orchestrator, render_cache, render_gc, openscad, cadquery, implicit, scad_analyzer, manifest_generator, ai_provider, ai_configurator, ai_code_editor, ai_session, git_operations, github_import, github_token, tier_service, mqtt_telemetry, format_converter
       │        └── middleware/  auth (JWT + tier gating)
       │
       ├──► apps/studio/   (React 19 + Vite + Three.js + Shadcn UI)
       │        ├── contexts/  auth, project, system
       │        ├── hooks/     ai, editor, project, render, system
       │        ├── components/  Controls, Viewer, ProjectSelector, OnboardingWizard, ScadEditor, GitPanel, AiChatPanel, ForkDialog, BomPanel
       │        └── services/  renderService, verifyService, openscad-worker (WASM)
       │
       ├──► apps/landing/  (Astro + React islands — marketing site)
       │        ├── src/components/  Header, Hero, FeaturesGrid, ProjectGallery, ProjectCarousel3D, ProjectGalleryGrid
       │        └── public/  static assets
       │
       └──► apps/admin/   (React + Vite + Shadcn UI — admin dashboard)
                └── src/  project management, flags, analytics

libs/
  BOSL2/               (git submodule — BSD-2 — attachments, rounding, math)
  NopSCADlib/          (git submodule — GPL-3 — real-world hardware models)
  Round-Anything/      (git submodule — MIT — coordinate-based filleting)

packages/
  schemas/             (JSON Schema for project manifests)
  tokens/              (shared CSS custom properties — colors, spacing)
```

**Domains**: `yantra4d.com` (landing), `app.yantra4d.com` (studio), `api.yantra4d.com` (api), `admin.yantra4d.com` (admin)

## Critical File Map

| Path | Purpose | Modify? |
|------|---------|---------|
| `projects/{slug}/project.json` | Project manifest — modes, parts, parameters, estimates | **YES** |
| `projects/{slug}/*.scad` | OpenSCAD geometry source files | YES |
| `apps/api/app.py` | Flask entry point, CORS, static serving | RARELY |
| `apps/api/extensions.py` | Flask extensions (rate limiter) | RARELY |
| `apps/api/routes/engine/render.py` | Render endpoints (thin route layer — delegates to orchestrator) | RARELY |
| `apps/api/services/engine/render_orchestrator.py` | Render orchestration: engine selection, caching, format conversion | RARELY |
| `apps/api/services/engine/render_gc.py` | Background render artifact garbage collection (24h TTL) | RARELY |
| `apps/api/routes/verify.py` | STL verification endpoint | RARELY |
| `apps/studio/src/App.jsx` | Main shell, state management | RARELY |
| `apps/studio/src/components/Controls.jsx` | Data-driven param controls (reads manifest) | RARELY |
| `apps/studio/src/components/Viewer.jsx` | Three.js 3D STL viewer | RARELY |
| `apps/studio/src/contexts/project/ManifestProvider.jsx` | Fetches & provides manifest to app | RARELY |
| `apps/api/routes/projects.py` | Multi-project listing API | RARELY |
| `apps/api/routes/onboard.py` | Project onboarding API | RARELY |
| `apps/api/services/scad_analyzer.py` | SCAD file analysis engine | RARELY |
| `apps/api/services/manifest_generator.py` | Manifest scaffolding from SCAD analysis | RARELY |
| `apps/studio/src/components/ProjectSelector.jsx` | Project switcher dropdown | RARELY |
| `apps/studio/src/components/OnboardingWizard.jsx` | Web-based project onboarding wizard | RARELY |
| `apps/studio/src/components/export/ExportPanel.jsx` | Accordion-based export hub: geometry, images, documents, print estimate, share & archive | RARELY |
| `apps/studio/src/components/PrintEstimateOverlay.jsx` | Print time/filament/cost overlay | RARELY |
| `apps/studio/src/hooks/project/useShareableUrl.js` | Shareable URL generation (base64url params) | RARELY |
| `apps/studio/src/hooks/editor/useUndoRedo.js` | Parameter undo/redo history stack | RARELY |
| `apps/studio/src/lib/printEstimator.js` | Print estimation from STL geometry volume | RARELY |
| `apps/landing/src/pages/index.astro` | Landing page (composes all sections) | RARELY |
| `packages/tokens/colors.css` | Shared CSS custom properties (both apps import) | RARELY |
| `docs/strategy/competitive-landscape.md` | Competitive research & feature roadmap | YES |
| `libs/*` | Global OpenSCAD libraries (git submodules) | **NEVER** |
| `apps/studio/src/components/ui/*` | Shadcn primitives | **NEVER** |
| `scripts/cli/yantra4d-init` | CLI tool for onboarding external SCAD projects | RARELY |
| `scripts/prerender-carousel.sh` | Pre-render GLB models for landing carousel + auto-generate `manifest.json` | RARELY |
| `scripts/qa/i18n_audit.py` | i18n key parity checker + hardcoded string scanner | RARELY |
| `packages/schemas/project-manifest.schema.json` | JSON Schema for project.json | RARELY |
| `apps/api/tests/verify_design.py` | STL quality checker script | RARELY |
| `apps/api/pyproject.toml` | pytest + coverage config | RARELY |
| `apps/api/tiers.json` | Tier definitions (renders, exports, features per tier) | RARELY |
| `apps/api/middleware/auth.py` | JWT auth + tier gating middleware | RARELY |
| `apps/api/routes/ai.py` | AI chat SSE endpoints (session, chat-stream) | RARELY |
| `apps/api/routes/github.py` | GitHub validate, import, sync endpoints | RARELY |
| `apps/api/routes/git_ops.py` | Git status, diff, log, commit, push, pull, connect-remote | RARELY |
| `apps/api/routes/engine/analysis.py` | Geometry analysis endpoints (wall thickness, overhang angles) | RARELY |
| `apps/api/services/geometry/thickness_analyzer.py` | trimesh-based wall thickness computation | RARELY |
| `apps/api/services/geometry/overhang_analyzer.py` | trimesh-based overhang angle computation | RARELY |
| `apps/api/routes/editor.py` | SCAD file CRUD (list/read/write/create/delete) | RARELY |
| `apps/api/routes/admin.py` | Admin project listing and detail endpoints | RARELY |
| `apps/api/routes/download.py` | STL and SCAD file download endpoints | RARELY |
| `apps/api/routes/bom.py` | Bill of materials API (JSON/CSV) | RARELY |
| `apps/api/routes/datasheet.py` | Project datasheet generation (PDF/HTML) | RARELY |
| `apps/api/routes/analytics.py` | Usage analytics tracking and summaries | RARELY |
| `apps/api/routes/user.py` | User tier info and tier definitions | RARELY |
| `apps/api/services/ai_configurator.py` | NL → parameter change mapping | RARELY |
| `apps/api/services/ai_code_editor.py` | NL → SCAD code edit mapping | RARELY |
| `apps/api/services/github_import.py` | GitHub repo clone and project creation | RARELY |
| `apps/api/services/tier_service.py` | Tier lookup and feature gating | RARELY |
| `apps/studio/src/lib/billing.ts` | Dhanam checkout URL generation for tier upgrades | RARELY |
| `apps/studio/src/components/ui/UpgradeModal.tsx` | Tier upgrade modal (links to Dhanam checkout) | RARELY |
| `apps/studio/src/contexts/auth/AuthProvider.jsx` | JWT auth context + login/logout | RARELY |
| `apps/studio/src/contexts/auth/TierProvider.jsx` | User tier context + feature flags | RARELY |
| `apps/studio/src/components/AiChatPanel.jsx` | AI chat UI (configurator + code-editor modes) | RARELY |
| `apps/studio/src/components/GitPanel.jsx` | Git status, diff, commit, push/pull, version history UI | RARELY |
| `apps/studio/src/components/viewer/ClippingPlane.jsx` | Cross-section clipping plane overlay | RARELY |
| `apps/studio/src/components/viewer/MeasureTool.jsx` | Point-to-point raycaster measurement | RARELY |
| `apps/studio/src/components/viewer/ThicknessOverlay.jsx` | Wall thickness heatmap point cloud | RARELY |
| `apps/studio/src/components/viewer/OverhangOverlay.jsx` | Overhang angle colored point cloud | RARELY |
| `apps/studio/src/components/studio/ModelInfoPanel.jsx` | Model geometry stats (dimensions, volume, triangles) | RARELY |
| `apps/studio/src/components/studio/ShortcutHelpDialog.jsx` | Keyboard shortcut help overlay (? key) | RARELY |
| `apps/studio/src/hooks/system/useUnitSystem.js` | mm↔inches display conversion hook | RARELY |
| `apps/studio/src/components/editor/VersionHistory.jsx` | Git commit history browser | RARELY |
| `apps/studio/src/components/ScadEditor.jsx` | Monaco-based SCAD code editor | RARELY |
| `apps/studio/src/components/ForkDialog.jsx` | Fork-to-edit modal for built-in projects | RARELY |
| `audit/*.png` | Browser audit screenshots (mobile, tablet, landscape, desktop) | **NEVER** |
| `docs/audits/*.md` | Internal audits (codebase, usability, deployment) | YES |
| `llms.txt` | LLM-optimized project overview (llmstxt.org spec) | RARELY |
| `llms-full.txt` | Comprehensive LLM context (all docs inlined) | RARELY |
| `docs/*.md` | Deep-dive documentation | YES |

## Core Pattern: Manifest-Driven Design

`projects/{slug}/project.json` controls **everything**: modes, parts, parameters, UI controls, colors, estimates, and optional `hyperobject` metadata (CDG interfaces, domain, material awareness, societal benefit). To add features, **edit the manifest first** — the UI and backend read it dynamically.

**Rule**: Most new parameters or modes require **zero code changes** — only manifest edits.

**Fallback**: The studio embeds a fallback manifest (`src/config/fallback-manifest.json`) for offline/WASM-only mode. Keep it in sync after manifest changes.

## Common Workflows

### Multi-project setup
1. Projects live in `projects/` — each subdirectory with a `project.json` is auto-discovered
2. Set `PROJECTS_DIR` env var to override (default: `projects/` at repo root)
3. Without `PROJECTS_DIR` or `projects/`, falls back to single-project via `SCAD_DIR`

### Onboard an external SCAD project
```bash
tools/yantra4d-init ./path/to/scad-dir --slug my-project --install
```
Or use the web UI: upload `.scad` files → review analysis → edit manifest → save.

### Add a parameter
1. Add entry to `projects/{slug}/project.json` → `parameters[]` (set name, type, default, min/max, modes)
2. Use `$name` in relevant `.scad` files
3. Update `fallback-manifest.json` if deploying to Pages

### Add a mode
1. Add entry to `projects/{slug}/project.json` → `modes[]` (set slug, scad_file, parts, estimate)
2. Optionally add `part_quantities` map to the mode (maps part ID → quantity formula or constant; formulas can reference parameter IDs; parts not listed default to qty 1)
3. Create the `.scad` file in `projects/{slug}/`
4. Update `fallback-manifest.json`

### Classify a project as a Hyperobject
1. Add `hyperobject` block to `projects/{slug}/project.json` with `domain`, `cdg_interfaces[]`, `material_awareness`, `societal_benefit`, `commons_license`
2. Each `cdg_interfaces` entry declares: `id`, `label`, `geometry_type` (grid/rail/thread/socket/pocket/snap/bolt_pattern/profile/spline/surface/custom), `standard`, and `parameters[]` (referencing manifest param IDs)
3. Add `hyperobject` and `commons` to `project.tags`
4. Update `projects/{slug}/docs/README.md` with a Hyperobject Profile section
5. See `projects/microscope-slide-holder/project.json` for the reference implementation

### Add a new SCAD project
1. Create `projects/{slug}/project.json` following the manifest schema (see `docs/reference/manifest.md`)
2. Add `.scad` files to `projects/{slug}/`

### Run tests
```bash
# Studio (frontend)
cd apps/studio && npm test              # single run
cd apps/studio && npm run test:watch     # watch mode
cd apps/studio && npm run test:coverage  # with coverage thresholds

# Landing
cd apps/landing && npm run build         # static build check

# Backend
cd apps/api && pytest                 # all backend tests
cd apps/api && pytest --cov           # with coverage report
```

### Local dev
```bash
./scripts/dev.sh          # start backend + studio + landing
./scripts/dev-stop.sh     # stop all dev servers
```

### Docker
```bash
docker compose up --build   # start (backend + studio + landing)
docker compose down         # stop
```

### Verify design
POST `/api/verify` with `{mode}` — runs `apps/api/tests/verify_design.py` on rendered STLs.

## API Quick Reference

| Method | Endpoint | Payload | Use Case |
|--------|----------|---------|----------|
| GET | `/api/health` | — | Health check, OpenSCAD availability |
| GET | `/api/config` | — | Legacy config (delegates to manifest) |
| GET | `/api/manifest` | — | Fetch manifest (default project) |
| GET | `/api/projects` | — | List all projects (append `?stats=1` for analytics) |
| GET | `/api/projects/<slug>/manifest` | — | Fetch manifest for specific project |
| POST | `/api/projects/<slug>/fork` | — | Fork project to editable copy (pro+) |
| POST | `/api/projects/analyze` | multipart `.scad` files | Analyze SCAD files, return draft manifest |
| POST | `/api/projects/create` | multipart manifest + files | Create new project in PROJECTS_DIR |
| POST | `/api/estimate` | `{mode, parameters, project?}` | Estimate render time |
| POST | `/api/render` | `{mode, parameters, parts, export_format?, project?}` | Synchronous render (format validated per engine; STL auto-converts to GLB) |
| POST | `/api/render-stream` | `{mode, parameters, parts, export_format?, project?}` | SSE streaming render |
| POST | `/api/render-cancel` | — | Cancel active render |
| POST | `/api/verify` | `{mode, project?}` | Run STL quality checks |
| GET | `/api/projects/<slug>/files` | — | List SCAD files in project (pro+) |
| GET | `/api/projects/<slug>/files/<path>` | — | Read SCAD file content (pro+) |
| PUT | `/api/projects/<slug>/files/<path>` | `{content}` | Write SCAD file (pro+) |
| DELETE | `/api/projects/<slug>/files/<path>` | — | Delete SCAD file (pro+) |
| GET | `/api/projects/<slug>/git/status` | — | Git working tree status (pro+) |
| GET | `/api/projects/<slug>/git/diff` | — | Unified diff (pro+) |
| GET | `/api/projects/<slug>/git/log` | `?limit=20` | Recent commit history (pro+) |
| POST | `/api/projects/<slug>/git/commit` | `{message, files?}` | Stage and commit (pro+) |
| POST | `/api/projects/<slug>/git/push` | — | Push to origin (pro+) |
| POST | `/api/projects/<slug>/git/pull` | — | Pull from origin (pro+) |
| POST | `/api/projects/<slug>/git/connect-remote` | `{url}` | Set GitHub remote (pro+) |
| POST | `/api/github/validate` | `{url}` | Validate GitHub repo URL (pro+) |
| POST | `/api/github/import` | `{url, slug?, private?}` | Import GitHub repo as project (pro+) |
| POST | `/api/github/sync` | `{slug}` | Sync project with GitHub source (madfam) |
| POST | `/api/ai/session` | `{project, mode}` | Create AI chat session (basic+) |
| POST | `/api/ai/chat-stream` | `{session_id, message, current_params}` | SSE streaming AI chat (basic+/pro+) |
| GET | `/api/projects/<slug>/bom` | query params | Bill of materials as JSON/CSV |
| GET | `/api/projects/<slug>/datasheet` | `?format=pdf&lang=en` | Project datasheet (PDF/HTML) |
| GET | `/api/projects/<slug>/download/stl/<file>` | — | Download STL file |
| GET | `/api/projects/<slug>/download/scad/<file>` | — | Download SCAD source file |
| POST | `/api/analytics/track` | `{event, slug, ...}` | Record analytics event |
| GET | `/api/analytics/<slug>/summary` | `?days=30` | Aggregate analytics for project |
| GET | `/api/tiers` | — | Public tier definitions |
| GET | `/api/me` | — | Current user info and tier |
| GET | `/api/config/client` | — | Client platform branding config |
| GET | `/api/materials` | — | List material hyperobjects |
| GET | `/api/materials/<slug>` | — | Material manifest by slug |
| GET | `/api/projects/<slug>/meta` | — | Project meta.json file |
| GET | `/api/projects/<slug>/parts/<path>` | — | Serve pre-built STL part files |
| GET | `/api/projects/<slug>/assembly-steps` | — | Auto-generate assembly steps from BOSL2 |
| POST | `/api/projects/<slug>/assembly-steps/write` | `{merge?}` | Write generated assembly steps to manifest |
| PUT | `/api/projects/<slug>/manifest/assembly-steps` | `{assembly_steps}` | Update assembly steps in manifest |
| GET | `/api/projects/<slug>/storefront` | — | Storefront-safe manifest (stripped) |
| GET | `/api/projects/<slug>/share/<preset_id>` | — | Shareable preset configuration URL |
| GET | `/api/catalog/nopscadlib` | — | NopSCADlib catalog categories |
| GET | `/api/catalog/nopscadlib/<category>` | — | Components for catalog category |
| POST | `/api/projects/<slug>/git/render-head` | `{file}` | Render HEAD version of SCAD file (pro+) |
| POST | `/api/ai/synthesize` | `{prompt, ...}` | SSE streaming AI project synthesis (pro+) |
| POST | `/api/projects/<slug>/analyze/thickness` | `{sample_count?}` | Wall thickness analysis on latest render (pro+) |
| POST | `/api/projects/<slug>/analyze/overhang` | `{threshold_deg?, sample_count?}` | Overhang angle analysis on latest render (pro+) |
| GET | `/api/admin/projects` | — | Admin: all projects with metadata (admin) |
| GET | `/api/admin/projects/<slug>` | — | Admin: detailed project info (admin) |
| PATCH | `/api/admin/projects/<slug>/flags` | `{is_demo?, is_hyperobject?, unlisted?}` | Toggle project flags (admin) |

## Tiered Access Control

Access is gated by user tier. Tier definitions live in `apps/api/tiers.json`; enforcement is in `middleware/auth.py`.

| Tier | Server renders/hr | Projects | Export | GitHub | AI Config | AI Code | AI Req/hr |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| guest | 10 | 0 | STL | — | — | — | 0 |
| essentials | 30 | 5 | STL/3MF/OBJ | — | Yes | — | 20 |
| pro | 150 | unlimited | STL/3MF/OFF/STEP/GLB/GLTF/OBJ | import, editor, private | Yes | Yes | 100 |
| madfam | 500 | unlimited | STL/3MF/OFF/STEP/GLB/GLTF/OBJ | import, sync, editor, private | Yes | Yes | 300 |

> **Note**: WASM (browser) rendering is unlimited at all tiers. Server render limits apply only to `/api/render*` endpoints.

Key files: `apps/api/tiers.json`, `apps/api/middleware/auth.py`, `apps/api/services/tier_service.py`, `apps/studio/src/contexts/AuthProvider.jsx`, `apps/studio/src/contexts/TierProvider.jsx`.

**Note**: Set `AUTH_ENABLED=false` to bypass auth in development (all users get madfam tier).

**Billing**: Tier upgrades via external Dhanam platform (`apps/studio/src/lib/billing.ts` generates checkout URLs, `UpgradeModal.tsx` presents upgrade flow). Tier assignment handled by Dhanam webhooks to Janua auth — JWT `yantra4d_tier` claim drives backend gating.

## AI Features

Two AI-powered features use LLMs to assist with parametric design:

- **AI Configurator** (basic+): Chat-based parameter adjustment — describe what you want and the AI adjusts slider values. Lives in `AiChatPanel.jsx` (mode: configurator) + `services/ai_configurator.py`.
- **AI Code Editor** (pro+): Natural language SCAD editing — describe changes and the AI generates search/replace edits. Lives in `ScadEditor.jsx` + `services/ai_code_editor.py`.

Both stream responses via SSE. Env vars: `AI_PROVIDER` (anthropic|openai), `AI_API_KEY` (required), `AI_MODEL` (optional override). Sessions are in-memory, expire after 1 hour.

See [`docs/guides/ai-features.md`](docs/guides/ai-features.md) for full API reference and SSE event format.

## GitHub Integration

GitHub features are tier-gated:

| Endpoint | Method | Tier | Purpose |
|----------|--------|------|---------|
| `/api/github/validate` | POST | pro+ | Validate GitHub repo URL, detect SCAD files |
| `/api/github/import` | POST | pro+ | Clone repo as new project |
| `/api/github/sync` | POST | madfam | Sync imported project with upstream |
| `/api/projects/<slug>/git/*` | GET/POST | pro+ | Git status, diff, commit, push, pull, connect-remote |
| `/api/projects/<slug>/files/*` | GET/PUT/DELETE | pro+ | SCAD file CRUD with auto git-init |

Key files: `routes/github.py`, `routes/git_ops.py`, `routes/editor.py`, `services/github_import.py`, `services/github_token.py`, `services/git_operations.py`. Frontend: `GitPanel.jsx`, `ForkDialog.jsx`, `ScadEditor.jsx`.

## Code Conventions

| Area | Convention |
|------|-----------|
| Python | PEP 8, type hints, Flask blueprints |
| JS/JSX | ESLint, functional components, hooks, ES modules |
| Astro | `.astro` components, React islands via `client:visible` |
| OpenSCAD | `snake_case`, `render_mode` variable selects part |
| CSS | Tailwind utility classes, shared tokens from `packages/tokens/` |
| Tests | Co-located (`*.test.js`/`*.test.jsx`), Vitest + RTL |
| Linting | ESLint + jsx-a11y (studio), ruff (backend) |
| Naming | `camelCase` JS, `snake_case` Python/SCAD |

## Testing Standards

- **Studio unit**: Vitest + RTL, coverage thresholds (80% statements/lines, 80% branches, 80% functions), jest-axe accessibility audits
- **Studio E2E**: Playwright — 23 test suites in `apps/studio/e2e/tests/`, page object pattern, mock API via `api-mocker.js`. Suite `23-browser-audit/` (86 tests) runs against the real Docker backend with OpenSCAD — use `--project=audit`
- **Landing**: `npm run build` (Astro static build)
- **Backend**: pytest + pytest-cov, coverage threshold 80%, tests in `apps/api/tests/` directory
- **Pre-commit**: Husky runs `lint-staged` → ESLint fix + Vitest on changed files
- **CI**: `.github/workflows/ci.yml` — studio (lint+test+coverage), landing (build), backend (lint+test+coverage), manifest-sync
- **Deploy**: Enclii PaaS — auto-deploy on push to main (deploy.yml builds Docker images → GHCR → K8s via ArgoCD)
- **Accessibility**: `eslint-plugin-jsx-a11y` enforces a11y rules; jest-axe audits in component tests

## Known Gotchas

| Issue | Detail |
|-------|--------|
| Manifest sync | After editing `project.json`, update `fallback-manifest.json` for Pages mode |
| URL format | Path-based routing: `/project/slug/preset/mode`. Legacy hash URLs (`#/slug/preset/mode`) auto-redirect via pre-mount script in `main.jsx` |
| Shadcn UI | **Never** hand-edit `components/ui/*` — use shadcn CLI to regenerate |
| Verify false positives | Verification needs rendered STLs to exist first; render before verifying |
| Render timeouts | Complex grid renders (high rows×cols) can exceed default timeout; Docker uses 300s |
| Render cache | Two-level LRU: L1 in-memory (per-process, 1hr TTL, 200 max) + L2 Redis DB 2 (shared, 24hr TTL). Set `REDIS_URL` to enable L2; falls back gracefully to L1-only |
| Env vars | Backend reads `OPENSCAD_PATH`, `SCAD_DIR`, `VERIFY_SCRIPT` — set in Docker or `.env` |
| CORS origins | Backend restricts CORS via `CORS_ORIGINS` env var; add your domain when deploying |
| Global SCAD libs | `libs/` are git submodules — run `git submodule update --init --recursive` after clone |
| Client-side WASM | `openscad-worker.js` runs in a Web Worker; cannot access DOM |
| Backend outage resilience | `detectMode()` checks backend availability *before* `force_backend`/`API_BASE` preferences. If backend is down, WASM fallback activates automatically (except CadQuery projects). `isBackendAvailable()` uses TTL cache: 30s negative (retries), 5min positive. `renderParts()` catches network errors **and HTTP 429 rate limit responses** and retries with WASM. `detectMode()` also overrides `force_backend` when rate limit is exhausted and WASM is capable. ProjectsView shows Retry + Open Demo buttons on error. The fallback manifest omits `force_backend` so WASM works offline |
| Rate limiting | Backend endpoints are rate-limited via Flask-Limiter (`extensions.py`). Render: per-tier (see tier table above), Estimate: 200/hr, Verify: 50/hr. WASM renders are unlimited |
| CSP headers | Production nginx adds Content-Security-Policy; requires `wasm-unsafe-eval` for OpenSCAD WASM |
| Bundle splitting | Vite splits vendor chunks (react, three, r3f, radix-ui); `ProjectsView` and `OnboardingWizard` are lazy-loaded |
| Shareable URLs | `?p=` query param encodes non-default params as base64url JSON diff; shared links use path-based format `/project/slug/share/mode?p=...`. Legacy hash-based shared links auto-redirect via `main.jsx` |
| Undo/Redo | Cmd/Ctrl+Z and Cmd/Ctrl+Shift+Z for parameter undo/redo; 50-entry history stack. Any `setParams()` call with `history: true` (default) truncates the redo stack |
| Viewer shortcuts | `O` toggle orthographic camera, `C` toggle clipping plane, `M` toggle measure tool, `?` toggle keyboard shortcut help dialog, `[` toggle sidebar show/hide, `]` toggle console show/hide. Non-modifier keys, ignored when focus is on text inputs |
| AM viewer tools | Cross-section clipping (axis selector + position slider), point-to-point measurement (two-click raycaster), wall thickness heatmap (backend trimesh analysis, pro+), overhang angle visualization (backend face normal analysis, color ramp green→yellow→red, configurable threshold, pro+), exploded view (displacement slider, multi-part only), adjustable lighting (brightness + environment preset), model info panel (dimensions, volume, triangle count, part count), unit system toggle (mm↔inches, display-only conversion), version history browser (git log), keyboard shortcut help overlay (`?` key), resizable sidebar and console panels (desktop, drag handle + `[`/`]` keyboard shortcuts, sizes persisted to localStorage), parameter geometry preview (hover parameter controls to see directional arrows + range labels for dimensional params, amber glow on affected parts for all params; disabled during assembly/diff/loading; auto-infers axis from label or uses explicit `preview_hint` in manifest; cached geometry ghost overlay shows semi-transparent purple ghost meshes at min/max values when IDB-cached variants exist, with breathing animation respecting prefers-reduced-motion) |
| E2E test patterns | Use Playwright's `toHaveText`/`toBeEnabled` assertions instead of `waitForTimeout` + `textContent()`. Auto-render caches results — change a param to bust cache before testing slow/error mocks. `editSliderValue` commits via Enter key. Native `<input type="color">` cannot be programmatically set in Playwright. Landing E2E tests in `12-responsive/` require `LANDING_URL` env var (skipped otherwise). Browser audit tests in `23-browser-audit/` require Docker stack (`docker compose up`) with OpenSCAD — run via `npx playwright test --project=audit`; tests auto-skip via `skipIfNoBackend()` if Docker is down. Default browser projects (chromium/firefox/webkit) exclude the audit suite via `testIgnore` |
| Export formats | `export_format` validated per engine (OpenSCAD: stl/3mf/off native + obj/glb/gltf via trimesh conversion; CadQuery: stl/step/glb/gltf/3mf/obj/vrml/amf; Implicit: stl native + obj/glb/gltf/3mf/off via trimesh). Dual-engine fallback routes OpenSCAD/Implicit to CadQuery for STEP/GLB/GLTF when `cq_file` present. Static STL parts converted on-demand. All STL renders auto-convert to GLB for web delivery. Non-GLB downloads trigger a dedicated `renderParts()` call with `exportFormat` to generate the target format on-demand; the 3D viewer always displays GLB from auto-render cache. Format selector only visible when manifest declares `export_formats`. Format buttons use `flex-wrap` to prevent overflow on narrow screens with 7 formats |
| Print estimation | Overlay computes volume from Three.js geometry; estimates are heuristic approximations, not slicer-accurate |
| Shared tokens | Both apps import `packages/tokens/colors.css` — edit tokens there, not in individual app CSS |
| Embed mode | `?embed=true` hides studio header/banners for iframe embedding. Production nginx must allow `frame-ancestors` for embedding domains |
| Responsive hooks | `useIsMobile()` / `useIsTablet()` / `useIsDesktop()` / `useIsLandscape()` from `hooks/system/useMediaQuery.js`. Uses `window.matchMedia`; in tests, `setup.js` defaults to `matches: false` (desktop mode). Call `globalThis.__setMediaQuery(query, true)` to simulate mobile/tablet, `__resetMediaQueries()` to reset. Camera view buttons render as both `<select>` (mobile) and `<button>` (desktop) — use `getAllByText` in tests |
| Mobile layout | Studio mobile (<768px): header overflow DropdownMenu with 44px menu items, mobile "Projects" link in header, editor as bottom Sheet with drag handle indicator (landscape capped at 75dvh), AI dismiss backdrop with `landscape:top-10` + `landscape:max-h-[calc(100dvh-2.5rem)]`, console expand/collapse bar. `StudioSidebar` accepts a `variant` prop (`desktop`/`mobile`/undefined): `variant="desktop"` renders only the desktop panel, `variant="mobile"` renders only the mobile bar, undefined renders both (backward compat). Desktop layout in `App.jsx` uses `ResizablePanelGroup` (horizontal) wrapping sidebar + viewer; sidebar has a collapse button (`onCollapse` prop) and a floating expand button when collapsed. Mobile layout unchanged. Panel sizes persisted via `usePanelLayout` hook (localStorage, debounced). `overscroll-behavior: contain` on body prevents pull-to-refresh during 3D viewer interaction. All layout containers use `h-dvh` (not `h-screen`) to respect mobile dynamic browser chrome. "Powered by" byline uses `hidden xl:block` (1280px+, not `lg:`) to avoid header cramping at 1024px tablet landscape. StorefrontView and PresetGallery use Tailwind (not BEM) with responsive grid (`grid-cols-1 xs:2 sm:3`). SynthesisModal uses `p-4 sm:p-6` padding, `min-h-[100px] sm:min-h-[150px]` textarea. ForkDialog has `max-h-[90dvh] overflow-y-auto` for landscape phones. OnboardingWizard uses `p-4 sm:p-6`. EditStep mode inputs stack vertically on mobile (`flex-col sm:flex-row`); parameter table inputs use `min-h-[44px] md:min-h-0` with wider mobile widths (`w-20/w-18`). Sidebar action buttons use `grid-cols-2 sm:grid-cols-1 landscape:grid-cols-2` for mobile 2-col layout. Landing mobile: carousel at `h-[60vh]` with FOV reactive via matchMedia listener, ContactShadows skipped, dpr capped 1.5, carousel uses `landscape:h-[70vh]` with truncated project titles; carousel loads `manifest.json` (auto-generated by `prerender-carousel.sh`) to gate GLB fetches — only projects listed in the manifest attempt model loading (avoids 404 console noise). Landing ES and EN pages have content parity: Hero, ProjectGallery, BeforeAfter, ForMakers, ForCreators, HowItWorks, OpenSource, CallToAction (ES also has "Choose Your Adventure" cards). Landing header Escape key closes mobile menu; mobile menu uses `overflow-y-auto` with `mt-12 landscape:mt-8`. Hero uses `text-2xl xs:text-3xl` for 320px screens, `landscape:min-h-[80vh]` with landscape text scaling. Hero "Launch Studio" CTA has `min-h-[44px]`. Hero animations prefixed with `motion-safe:`. Landing `scroll-margin-top: 3.5rem` (reduced from 5rem). Landing concept pages use `pt-24 sm:pt-20` for notched devices, `py-12 sm:py-24 space-y-12 sm:space-y-24` for tighter mobile spacing. Landing sections (ProjectGallery, HowItWorks) use `py-16 sm:py-24` + `mb-8 sm:mb-12`. CallToAction uses `py-16 sm:py-24 px-4 sm:px-6` + `text-2xl xs:text-3xl sm:text-4xl`. OpenSource stats cards use `gap-3 sm:gap-6` + `px-4 sm:px-6 py-2 sm:py-3`. ProjectGalleryGrid card titles use `min-w-0` for truncation in flex; descriptions use `line-clamp-2`. Landing feature cards have `group-active:` touch feedback alongside hover. Admin sidebar slides in as mobile overlay with backdrop |
| Safe areas | Studio + Landing + Admin use `viewport-fit=cover` and `env(safe-area-inset-*)` CSS utilities (`pb-safe`, `pt-safe`, `px-safe`, `pl-safe`, `pr-safe`) for notched devices. Applied to: studio PrintEstimateOverlay (both inline and overlay variants), AI panel (`pr-safe` for landscape), StudioSidebar bottom sheet, admin sidebar (`pl-safe`), landing header, mobile menu, footer. Tailwind `xs: 360px` and `landscape` custom screen variants in all three app configs (studio, landing, admin) |
| Touch targets | All interactive elements enforce WCAG 2.5.8 minimum 44px touch targets on mobile/tablet via `min-h-[44px] min-w-[44px]`. Touch targets persist through `md:` (768px) breakpoint — `sm:` (640px) is too early for touch-primary small tablets. **IMPORTANT**: Do NOT combine explicit `h-X` with `min-h-[44px]` — in Tailwind, `h-7` (28px) overrides `min-height: 44px`. Use `min-h-[44px] md:h-X md:min-h-0` pattern instead. Inputs use `text-base` on mobile to prevent iOS Safari auto-zoom (global rule in `index.css` forces 16px on `select/input/textarea` below 768px); text size resets use `md:text-sm`/`md:text-xs` (not `sm:`). AI chat input uses `text-base md:text-xs` to prevent iOS zoom. SynthesisModal textarea uses `text-base md:text-sm`. Slider numeric inputs have `inputMode="decimal"` for mobile number pad. 3D viewer container has `touch-action: none` to prevent browser gesture conflicts with Three.js OrbitControls. Focus-visible rings are 3px/4px offset on coarse pointer devices. Onboarding wizard inputs (EditStep, UploadStep) enforce 44px touch targets and mobile-friendly padding; SaveStep buttons use `flex-wrap` + `min-h-[44px]`. PrintEstimateOverlay selects use `py-2 md:py-0.5` + `min-h-[44px] md:min-h-0`. ComponentPicker and grid preset buttons use `min-h-[44px] md:min-h-0` with `flex-wrap`. TpmsTopologyControl buttons enforce `min-h-[44px]`. EnergySliderControl range thumb enlarged to 44px via webkit/moz pseudo-element selectors; track uses `h-3 md:h-2` (12px on mobile). AuthButton OAuth dropdown items use `py-3 md:py-1.5` + `min-h-[44px] md:min-h-0`. GitPanel file checkboxes, diff summary, and 3D diff button use `min-h-[44px] md:min-h-0`. ColorGradientControl inputs use `h-11 md:h-8` + `min-h-[44px] md:min-h-0`. Controls color input uses `h-11 min-h-[44px]`. ProjectSelector uses `h-11 min-h-[44px] text-base md:text-sm`. StudioHeader "Projects" links use `min-h-[44px]`; share toast and language dropdown use `max-w-[calc(100vw-2rem)]` to prevent overflow; "Powered by" uses `text-xs` (WCAG AA minimum). App.jsx projects view icon buttons use `min-h-[44px] min-w-[44px]`. BomPanel rows use `py-2.5 md:py-1.5` with supplier links `flex md:inline-flex min-h-[44px] md:min-h-0` for full-width tap. ExportPanel accordion triggers, download buttons, and format buttons use `min-h-[44px]`/`min-w-[44px]`. ScadEditor file tree items, delete buttons (always visible on mobile), tab close buttons, new file button, and AI toggle use `min-h-[44px] md:min-h-0`. AiChatPanel buttons use `min-h-[44px] md:h-X md:min-h-0` pattern (not `h-X min-h-[44px]`). Landing CTA buttons use `min-h-[44px] inline-flex items-center justify-center`. Hero "Launch Studio" link uses `min-h-[44px]`. Landing footer links use `min-h-[44px] inline-flex items-center`. Landing carousel selects use `text-base md:text-sm` for iOS zoom prevention. Custom tooltip component supports touch devices via `onPointerDown` toggle with 2s auto-dismiss. Viewer GizmoHelper uses responsive margin (`[40,40]` mobile / `[60,60]` desktop); loading overlay text/progress bar responsive (`text-base sm:text-xl`, `w-32 sm:w-48`) |
| Scroll affordances | BomPanel and Controls presets show thin scrollbar on mobile via `.scrollbar-thin` utility (4px, themed). Desktop hides scrollbar on presets (`sm:no-scrollbar`). Gallery category buttons use horizontal `snap-x` scroll on mobile, `flex-wrap` on desktop |
| Admin responsive | AdminShell has collapsible sidebar: `w-48 lg:w-56`, fixed overlay on mobile (<md) with backdrop, relative layout on desktop. Hamburger toggle in mobile header. ProjectList uses stacked card view on mobile (`sm:hidden`), table on desktop (`hidden sm:block`) with `overflow-x-auto` and `min-w-[500px]` |

## Do NOT Edit

- `apps/studio/src/components/ui/*` — Shadcn managed
- `node_modules/`, `dist/` — generated artifacts
- `.github/workflows/*` — change only with explicit CI/CD intent

## Deployment

| Target | Method |
|--------|--------|
| Enclii PaaS | Auto-deploy on push to main — `yantra4d-landing` at yantra4d.com, `yantra4d-studio` at app.yantra4d.com, `yantra4d-backend` at api.yantra4d.com, `yantra4d-admin` at admin.yantra4d.com |
| Docker | `docker compose up` (backend + studio + landing + admin, local) |
| Local | Flask dev server (5000) + Vite dev server (5173) + Astro dev server (4321) + Admin dev server (5174) |

## Further Docs

- [`llms.txt`](llms.txt) — LLM-optimized project overview (llmstxt.org spec)
- [`llms-full.txt`](llms-full.txt) — Comprehensive LLM context (all docs inlined)
- [`docs/index.md`](docs/index.md) — Platform documentation hub
- [`docs/reference/manifest.md`](docs/reference/manifest.md) — Manifest schema and extension guide
- [`docs/architecture/web_interface.md`](docs/architecture/web_interface.md) — Full-stack architecture details
- [`docs/guides/ai-features.md`](docs/guides/ai-features.md) — AI Configurator and Code Editor
- [`docs/guides/verification.md`](docs/guides/verification.md) — STL quality verification system
- [`docs/guides/wasm-mode.md`](docs/guides/wasm-mode.md) — Client-side rendering fallback
- [`docs/guides/devx-guide.md`](docs/guides/devx-guide.md) — Onboarding external SCAD projects
- [`docs/guides/troubleshooting.md`](docs/guides/troubleshooting.md) — Common issues and solutions
- [`docs/audits/codebase-audit.md`](docs/audits/codebase-audit.md) — Full platform assessment
- [`docs/audits/usability-audit.md`](docs/audits/usability-audit.md) — Browser-based UX testing
- [`docs/audits/browser-audit-2026-03.md`](docs/audits/browser-audit-2026-03.md) — Responsive/mobile browser audit with screenshots
- [`docs/audits/full-stack-audit.md`](docs/audits/full-stack-audit.md) — Full-stack architecture audit
- [`docs/audits/enclii-verification-prompt.md`](docs/audits/enclii-verification-prompt.md) — Deployment verification steps
- [`docs/architecture/typescript-migration.md`](docs/architecture/typescript-migration.md) — Gradual TypeScript adoption strategy
- [`packages/sdk/README.md`](packages/sdk/README.md) — Headless SDK API documentation
Per-project docs live in `projects/{slug}/docs/`.
