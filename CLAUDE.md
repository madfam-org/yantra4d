# Qubic — Parametric 3D Print Design Platform

Multi-project manifest-driven Flask + React/Vite platform for parametric OpenSCAD models with 3D preview.

## Architecture

```
projects/
  {slug}/project.json  (manifest — single source of truth per project)
  {slug}/*.scad        (OpenSCAD geometry)
  {slug}/exports/      (reference STL exports)
       │
       ├──► apps/api/      (Flask API, renders via OpenSCAD CLI)
       │        ├── routes/  render, verify, health, manifest, config, projects, onboard
       │        └── services/  openscad, scad_analyzer, manifest_generator
       │
       ├──► apps/studio/   (React 19 + Vite + Three.js + Shadcn UI)
       │        ├── contexts/  ManifestProvider (multi-project), Theme, Language
       │        ├── components/  Controls, Viewer, ProjectSelector, OnboardingWizard
       │        └── services/  renderService, verifyService, openscad-worker (WASM)
       │
       └──► apps/landing/  (Astro + React islands — marketing site)
                ├── src/components/  Header, Hero, FeaturesGrid, LiveDemo, DemoViewer
                └── public/  static assets, pre-exported STL for demo

libs/
  BOSL2/               (git submodule — BSD-2 — attachments, rounding, math)
  NopSCADlib/          (git submodule — GPL-3 — real-world hardware models)
  Round-Anything/      (git submodule — MIT — coordinate-based filleting)

packages/
  schemas/             (JSON Schema for project manifests)
  tokens/              (shared CSS custom properties — colors, spacing)
```

**Domains**: `qubic.quest` (landing), `studio.qubic.quest` (studio), `api.qubic.quest` (api)

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
| `apps/landing/src/components/DemoViewer.tsx` | React island — Three.js STL viewer | RARELY |
| `packages/tokens/colors.css` | Shared CSS custom properties (both apps import) | RARELY |
| `docs/competitive-landscape.md` | Competitive research & feature roadmap | YES |
| `libs/*` | Global OpenSCAD libraries (git submodules) | **NEVER** |
| `apps/studio/src/components/ui/*` | Shadcn primitives | **NEVER** |
| `tools/qubic-init` | CLI tool for onboarding external SCAD projects | RARELY |
| `packages/schemas/project-manifest.schema.json` | JSON Schema for project.json | RARELY |
| `apps/api/tests/verify_design.py` | STL quality checker script | RARELY |
| `apps/api/pyproject.toml` | pytest + coverage config | RARELY |
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
tools/qubic-init ./path/to/scad-dir --slug my-project --install
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
| GET | `/api/projects` | — | List all available projects |
| GET | `/api/projects/<slug>/manifest` | — | Fetch manifest for specific project |
| POST | `/api/projects/analyze` | multipart `.scad` files | Analyze SCAD files, return draft manifest |
| POST | `/api/projects/create` | multipart manifest + files | Create new project in PROJECTS_DIR |
| GET | `/api/manifest` | — | Fetch full project manifest (default project) |
| GET | `/api/health` | — | Health check, OpenSCAD availability |
| POST | `/api/estimate` | `{mode, scad_file, parameters}` | Estimate render time |
| POST | `/api/render` | `{mode, scad_file, parameters, parts, export_format?}` | Synchronous render (stl/3mf/off) |
| POST | `/api/render-stream` | `{mode, scad_file, parameters, parts, export_format?}` | SSE streaming render (stl/3mf/off) |
| POST | `/api/render-cancel` | — | Cancel active render |
| POST | `/api/verify` | `{mode}` | Run STL quality checks |

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

## Do NOT Edit

- `apps/studio/src/components/ui/*` — Shadcn managed
- `node_modules/`, `dist/` — generated artifacts
- `.github/workflows/*` — change only with explicit CI/CD intent

## Deployment

| Target | Method |
|--------|--------|
| Enclii PaaS | Auto-deploy on push to main — `qubic-landing` at qubic.quest, `qubic-studio` at studio.qubic.quest, `qubic-backend` at api.qubic.quest |
| Docker | `docker compose up` (backend + studio + landing, local) |
| Local | Flask dev server (5000) + Vite dev server (5173) + Astro dev server (4321) |

## Further Docs

- [`docs/index.md`](docs/index.md) — Platform documentation hub
- [`docs/manifest.md`](docs/manifest.md) — Manifest schema and extension guide
- [`docs/web_interface.md`](docs/web_interface.md) — Full-stack architecture details
- [`docs/verification.md`](docs/verification.md) — STL quality verification system
- [`projects/tablaco/docs/mechanical_design.md`](projects/tablaco/docs/mechanical_design.md) — OpenSCAD geometry and parameters

Per-project docs live in `projects/{slug}/docs/`.
