# Yantra4D — Parametric 3D Print Design Platform

Multi-project manifest-driven Flask + React/Vite platform for parametric OpenSCAD models with 3D preview.

## Architecture

```
projects/
  {slug}/project.json  (manifest — single source of truth per project)
  {slug}/*.scad        (OpenSCAD geometry)
  {slug}/exports/      (reference STL exports)
       │
       ├──► apps/api/      (Flask API, renders via OpenSCAD CLI)
       │        ├── routes/  render, verify, health, manifest, config, projects, onboard, editor, git_ops, github, ai, admin, download, bom, datasheet, analytics, user
       │        ├── services/  openscad, scad_analyzer, manifest_generator, ai_provider, ai_configurator, ai_code_editor, ai_session, git_operations, github_import, github_token, tier_service, render_cache, route_helpers
       │        └── middleware/  auth (JWT + tier gating)
       │
       ├──► apps/studio/   (React 19 + Vite + Three.js + Shadcn UI)
       │        ├── contexts/  ManifestProvider (multi-project), Theme, Language, Auth, Tier
       │        ├── components/  Controls, Viewer, ProjectSelector, OnboardingWizard, ScadEditor, GitPanel, AiChatPanel, ForkDialog, BomPanel
       │        └── services/  renderService, verifyService, openscad-worker (WASM)
       │
       └──► apps/landing/  (Astro + React islands — marketing site)
                ├── src/components/  Header, Hero, FeaturesGrid, LiveDemo, InteractiveShowcase
                └── public/  static assets

libs/
  BOSL2/               (git submodule — BSD-2 — attachments, rounding, math)
  NopSCADlib/          (git submodule — GPL-3 — real-world hardware models)
  Round-Anything/      (git submodule — MIT — coordinate-based filleting)

packages/
  schemas/             (JSON Schema for project manifests)
  tokens/              (shared CSS custom properties — colors, spacing)
```

**Domains**: `4d.madfam.io` (landing), `4d-app.madfam.io` (studio), `4d-api.madfam.io` (api)

## Critical File Map

| Path | Purpose | Modify? |
|------|---------|---------|
| `projects/{slug}/project.json` | Project manifest — modes, parts, parameters, estimates | **YES** |
| `projects/{slug}/*.scad` | OpenSCAD geometry source files | YES |
| `apps/api/app.py` | Flask entry point, CORS, static serving | RARELY |
| `apps/api/extensions.py` | Flask extensions (rate limiter) | RARELY |
| `apps/api/routes/render.py` | Render + estimate + cancel + SSE stream | RARELY |
| `apps/api/routes/verify.py` | STL verification endpoint | RARELY |
| `apps/studio/src/App.jsx` | Main shell, state management | RARELY |
| `apps/studio/src/components/Controls.jsx` | Data-driven param controls (reads manifest) | RARELY |
| `apps/studio/src/components/Viewer.jsx` | Three.js 3D STL viewer | RARELY |
| `apps/studio/src/contexts/ManifestProvider.jsx` | Fetches & provides manifest to app | RARELY |
| `apps/api/routes/projects.py` | Multi-project listing API | RARELY |
| `apps/api/routes/onboard.py` | Project onboarding API | RARELY |
| `apps/api/services/scad_analyzer.py` | SCAD file analysis engine | RARELY |
| `apps/api/services/manifest_generator.py` | Manifest scaffolding from SCAD analysis | RARELY |
| `apps/studio/src/components/ProjectSelector.jsx` | Project switcher dropdown | RARELY |
| `apps/studio/src/components/OnboardingWizard.jsx` | Web-based project onboarding wizard | RARELY |
| `apps/studio/src/components/ExportPanel.jsx` | Export controls with multi-format selector | RARELY |
| `apps/studio/src/components/PrintEstimateOverlay.jsx` | Print time/filament/cost overlay | RARELY |
| `apps/studio/src/hooks/useShareableUrl.js` | Shareable URL generation (base64url params) | RARELY |
| `apps/studio/src/hooks/useUndoRedo.js` | Parameter undo/redo history stack | RARELY |
| `apps/studio/src/lib/printEstimator.js` | Print estimation from STL geometry volume | RARELY |
| `apps/landing/src/pages/index.astro` | Landing page (composes all sections) | RARELY |
| `apps/landing/src/components/InteractiveShowcase.tsx` | React island — iframe embed of studio with project tabs | RARELY |
| `packages/tokens/colors.css` | Shared CSS custom properties (both apps import) | RARELY |
| `docs/competitive-landscape.md` | Competitive research & feature roadmap | YES |
| `libs/*` | Global OpenSCAD libraries (git submodules) | **NEVER** |
| `apps/studio/src/components/ui/*` | Shadcn primitives | **NEVER** |
| `tools/yantra4d-init` | CLI tool for onboarding external SCAD projects | RARELY |
| `packages/schemas/project-manifest.schema.json` | JSON Schema for project.json | RARELY |
| `apps/api/tests/verify_design.py` | STL quality checker script | RARELY |
| `apps/api/pyproject.toml` | pytest + coverage config | RARELY |
| `apps/api/tiers.json` | Tier definitions (renders, exports, features per tier) | RARELY |
| `apps/api/middleware/auth.py` | JWT auth + tier gating middleware | RARELY |
| `apps/api/routes/ai.py` | AI chat SSE endpoints (session, chat-stream) | RARELY |
| `apps/api/routes/github.py` | GitHub validate, import, sync endpoints | RARELY |
| `apps/api/routes/git_ops.py` | Git status, diff, commit, push, pull, connect-remote | RARELY |
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
| `apps/studio/src/contexts/AuthProvider.jsx` | JWT auth context + login/logout | RARELY |
| `apps/studio/src/contexts/TierProvider.jsx` | User tier context + feature flags | RARELY |
| `apps/studio/src/components/AiChatPanel.jsx` | AI chat UI (configurator + code-editor modes) | RARELY |
| `apps/studio/src/components/GitPanel.jsx` | Git status, diff, commit, push/pull UI | RARELY |
| `apps/studio/src/components/ScadEditor.jsx` | Monaco-based SCAD code editor | RARELY |
| `apps/studio/src/components/ForkDialog.jsx` | Fork-to-edit modal for built-in projects | RARELY |
| `claudedocs/*.md` | Internal audits (codebase, usability, deployment) | YES |
| `llms.txt` | LLM-optimized project overview (llmstxt.org spec) | RARELY |
| `llms-full.txt` | Comprehensive LLM context (all docs inlined) | RARELY |
| `docs/*.md` | Deep-dive documentation | YES |

## Core Pattern: Manifest-Driven Design

`projects/{slug}/project.json` controls **everything**: modes, parts, parameters, UI controls, colors, and estimates. To add features, **edit the manifest first** — the UI and backend read it dynamically.

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
2. Create the `.scad` file in `projects/{slug}/`
3. Update `fallback-manifest.json`

### Add a new SCAD project
1. Create `projects/{slug}/project.json` following the manifest schema (see `docs/manifest.md`)
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
| POST | `/api/render` | `{mode, parameters, parts, export_format?, project?}` | Synchronous render (stl/3mf/off) |
| POST | `/api/render-stream` | `{mode, parameters, parts, export_format?, project?}` | SSE streaming render |
| POST | `/api/render-cancel` | — | Cancel active render |
| POST | `/api/verify` | `{mode, project?}` | Run STL quality checks |
| GET | `/api/projects/<slug>/files` | — | List SCAD files in project (pro+) |
| GET | `/api/projects/<slug>/files/<path>` | — | Read SCAD file content (pro+) |
| PUT | `/api/projects/<slug>/files/<path>` | `{content}` | Write SCAD file (pro+) |
| DELETE | `/api/projects/<slug>/files/<path>` | — | Delete SCAD file (pro+) |
| GET | `/api/projects/<slug>/git/status` | — | Git working tree status (pro+) |
| GET | `/api/projects/<slug>/git/diff` | — | Unified diff (pro+) |
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
| GET | `/api/admin/projects` | — | Admin: all projects with metadata (admin) |
| GET | `/api/admin/projects/<slug>` | — | Admin: detailed project info (admin) |

## Tiered Access Control

Access is gated by user tier. Tier definitions live in `apps/api/tiers.json`; enforcement is in `middleware/auth.py`.

| Tier | Renders/hr | Projects | Export | GitHub | AI Config | AI Code | AI Req/hr |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| guest | 30 | 0 | STL | — | — | — | 0 |
| basic | 50 | 3 | STL | — | Yes | — | 30 |
| pro | 200 | unlimited | STL/3MF/OFF | import, editor, private | Yes | Yes | 100 |
| madfam | 500 | unlimited | STL/3MF/OFF | import, sync, editor, private | Yes | Yes | 300 |

Key files: `apps/api/tiers.json`, `apps/api/middleware/auth.py`, `apps/api/services/tier_service.py`, `apps/studio/src/contexts/AuthProvider.jsx`, `apps/studio/src/contexts/TierProvider.jsx`.

**Note**: Set `AUTH_ENABLED=false` to bypass auth in development (all users get madfam tier).

## AI Features

Two AI-powered features use LLMs to assist with parametric design:

- **AI Configurator** (basic+): Chat-based parameter adjustment — describe what you want and the AI adjusts slider values. Lives in `AiChatPanel.jsx` (mode: configurator) + `services/ai_configurator.py`.
- **AI Code Editor** (pro+): Natural language SCAD editing — describe changes and the AI generates search/replace edits. Lives in `ScadEditor.jsx` + `services/ai_code_editor.py`.

Both stream responses via SSE. Env vars: `AI_PROVIDER` (anthropic|openai), `AI_API_KEY` (required), `AI_MODEL` (optional override). Sessions are in-memory, expire after 1 hour.

See [`docs/ai-features.md`](docs/ai-features.md) for full API reference and SSE event format.

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

- **Studio**: Vitest + RTL, coverage thresholds (65% statements/lines, 55% branches, 60% functions), jest-axe accessibility audits
- **Landing**: `npm run build` (Astro static build)
- **Backend**: pytest + pytest-cov, coverage threshold 60%, tests in `apps/api/tests/` directory
- **Pre-commit**: Husky runs `lint-staged` → ESLint fix + Vitest on changed files
- **CI**: `.github/workflows/ci.yml` — studio (lint+test+coverage), landing (build), backend (lint+test+coverage), manifest-sync
- **Deploy**: Enclii PaaS — auto-deploy on push to main (`apps/api/enclii.yaml`, `apps/studio/enclii.yaml`, `apps/landing/enclii.yaml`)
- **Accessibility**: `eslint-plugin-jsx-a11y` enforces a11y rules; jest-axe audits in component tests

## Known Gotchas

| Issue | Detail |
|-------|--------|
| Manifest sync | After editing `project.json`, update `fallback-manifest.json` for Pages mode |
| URL format | Hash changed from `#/preset/mode` to `#/project/preset/mode` — old 2-segment format still supported |
| Shadcn UI | **Never** hand-edit `components/ui/*` — use shadcn CLI to regenerate |
| Verify false positives | Verification needs rendered STLs to exist first; render before verifying |
| Render timeouts | Complex grid renders (high rows×cols) can exceed default timeout; Docker uses 300s |
| Env vars | Backend reads `OPENSCAD_PATH`, `SCAD_DIR`, `VERIFY_SCRIPT` — set in Docker or `.env` |
| CORS origins | Backend restricts CORS via `CORS_ORIGINS` env var; add your domain when deploying |
| Global SCAD libs | `libs/` are git submodules — run `git submodule update --init --recursive` after clone |
| Client-side WASM | `openscad-worker.js` runs in a Web Worker; cannot access DOM |
| Rate limiting | Backend endpoints are rate-limited via Flask-Limiter (`extensions.py`). Render: 100/hr, Estimate: 200/hr, Verify: 50/hr |
| CSP headers | Production nginx adds Content-Security-Policy; requires `wasm-unsafe-eval` for OpenSCAD WASM |
| Bundle splitting | Vite splits vendor chunks (react, three, r3f, radix-ui); `ProjectsView` and `OnboardingWizard` are lazy-loaded |
| Shareable URLs | `?p=` query param encodes non-default params as base64url JSON diff; shared links restore params on load |
| Undo/Redo | Cmd/Ctrl+Z and Cmd/Ctrl+Shift+Z for parameter undo/redo; 50-entry history stack |
| Export formats | `export_format` in render payloads (stl/3mf/off); format selector only visible when manifest declares `export_formats` |
| Print estimation | Overlay computes volume from Three.js geometry; estimates are heuristic approximations, not slicer-accurate |
| Shared tokens | Both apps import `packages/tokens/colors.css` — edit tokens there, not in individual app CSS |
| Embed mode | `?embed=true` hides studio header/banners for iframe embedding; landing uses `InteractiveShowcase` to embed studio via iframe. Production nginx must allow `frame-ancestors` from `4d.madfam.io` |

## Do NOT Edit

- `apps/studio/src/components/ui/*` — Shadcn managed
- `node_modules/`, `dist/` — generated artifacts
- `.github/workflows/*` — change only with explicit CI/CD intent

## Deployment

| Target | Method |
|--------|--------|
| Enclii PaaS | Auto-deploy on push to main — `yantra4d-landing` at 4d.madfam.io, `yantra4d-studio` at 4d-app.madfam.io, `yantra4d-backend` at 4d-api.madfam.io |
| Docker | `docker compose up` (backend + studio + landing, local) |
| Local | Flask dev server (5000) + Vite dev server (5173) + Astro dev server (4321) |

## Further Docs

- [`llms.txt`](llms.txt) — LLM-optimized project overview (llmstxt.org spec)
- [`llms-full.txt`](llms-full.txt) — Comprehensive LLM context (all docs inlined)
- [`docs/index.md`](docs/index.md) — Platform documentation hub
- [`docs/manifest.md`](docs/manifest.md) — Manifest schema and extension guide
- [`docs/web_interface.md`](docs/web_interface.md) — Full-stack architecture details
- [`docs/ai-features.md`](docs/ai-features.md) — AI Configurator and Code Editor
- [`docs/verification.md`](docs/verification.md) — STL quality verification system
- [`docs/wasm-mode.md`](docs/wasm-mode.md) — Client-side rendering fallback
- [`docs/devx-guide.md`](docs/devx-guide.md) — Onboarding external SCAD projects
- [`docs/troubleshooting.md`](docs/troubleshooting.md) — Common issues and solutions
- [`claudedocs/codebase-audit.md`](claudedocs/codebase-audit.md) — Full platform assessment
- [`claudedocs/usability-audit.md`](claudedocs/usability-audit.md) — Browser-based UX testing
- [`claudedocs/enclii-verification-prompt.md`](claudedocs/enclii-verification-prompt.md) — Deployment verification steps
Per-project docs live in `projects/{slug}/docs/`.
