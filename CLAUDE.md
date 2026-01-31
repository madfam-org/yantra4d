# Tablaco — Parametric 3D Print Design Studio

Multi-project manifest-driven Flask + React/Vite platform for parametric OpenSCAD models with 3D preview.

## Architecture

```
projects/
  {slug}/project.json  (manifest — single source of truth per project)
  {slug}/*.scad        (OpenSCAD geometry)
  {slug}/exports/      (reference STL exports)
       │
       ├──► web_interface/backend/  (Flask API, renders via OpenSCAD CLI)
       │        ├── routes/  render, verify, health, manifest, config, projects, onboard
       │        └── services/  openscad, scad_analyzer, manifest_generator
       │
       └──► web_interface/frontend/ (React 19 + Vite + Three.js + Shadcn UI)
                ├── contexts/  ManifestProvider (multi-project), Theme, Language
                ├── components/  Controls, Viewer, ProjectSelector, OnboardingWizard
                └── services/  renderService, verifyService, openscad-worker (WASM)
```

## Critical File Map

| Path | Purpose | Modify? |
|------|---------|---------|
| `projects/{slug}/project.json` | Project manifest — modes, parts, parameters, estimates | **YES** |
| `projects/{slug}/*.scad` | OpenSCAD geometry source files | YES |
| `web_interface/backend/app.py` | Flask entry point, CORS, static serving | RARELY |
| `web_interface/backend/extensions.py` | Flask extensions (rate limiter) | RARELY |
| `web_interface/backend/routes/render.py` | Render + estimate + cancel + SSE stream | RARELY |
| `web_interface/backend/routes/verify.py` | STL verification endpoint | RARELY |
| `web_interface/frontend/src/App.jsx` | Main shell, state management | RARELY |
| `web_interface/frontend/src/components/Controls.jsx` | Data-driven param controls (reads manifest) | RARELY |
| `web_interface/frontend/src/components/Viewer.jsx` | Three.js 3D STL viewer | RARELY |
| `web_interface/frontend/src/contexts/ManifestProvider.jsx` | Fetches & provides manifest to app | RARELY |
| `web_interface/backend/routes/projects.py` | Multi-project listing API | RARELY |
| `web_interface/backend/routes/onboard.py` | Project onboarding API | RARELY |
| `web_interface/backend/services/scad_analyzer.py` | SCAD file analysis engine | RARELY |
| `web_interface/backend/services/manifest_generator.py` | Manifest scaffolding from SCAD analysis | RARELY |
| `web_interface/frontend/src/components/ProjectSelector.jsx` | Project switcher dropdown | RARELY |
| `web_interface/frontend/src/components/OnboardingWizard.jsx` | Web-based project onboarding wizard | RARELY |
| `web_interface/frontend/src/components/ui/*` | Shadcn primitives | **NEVER** |
| `scripts/tablaco-init` | CLI tool for onboarding external SCAD projects | RARELY |
| `schemas/project-manifest.schema.json` | JSON Schema for project.json | RARELY |
| `tests/verify_design.py` | STL quality checker script | RARELY |
| `pyproject.toml` | pytest + coverage config | RARELY |
| `docs/*.md` | Deep-dive documentation | YES |

## Core Pattern: Manifest-Driven Design

`projects/{slug}/project.json` controls **everything**: modes, parts, parameters, UI controls, colors, and estimates. To add features, **edit the manifest first** — the UI and backend read it dynamically.

**Rule**: Most new parameters or modes require **zero code changes** — only manifest edits.

**Fallback**: The frontend embeds a fallback manifest (`src/config/fallback-manifest.json`) for offline/GitHub Pages mode. Keep it in sync after manifest changes.

## Common Workflows

### Multi-project setup
1. Projects live in `projects/` — each subdirectory with a `project.json` is auto-discovered
2. Set `PROJECTS_DIR` env var to override (default: `projects/` at repo root)
3. Without `PROJECTS_DIR` or `projects/`, falls back to single-project via `SCAD_DIR`

### Onboard an external SCAD project
```bash
scripts/tablaco-init ./path/to/scad-dir --slug my-project --install
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
# Frontend
cd web_interface/frontend && npm test              # single run
cd web_interface/frontend && npm run test:watch     # watch mode
cd web_interface/frontend && npm run test:coverage  # with coverage thresholds

# Backend
pytest                    # all backend tests (from repo root)
pytest --cov              # with coverage report
```

### Local dev
```bash
./scripts/dev.sh          # start backend + frontend
./scripts/dev-stop.sh     # stop all dev servers
```

### Docker
```bash
docker compose up --build   # start
docker compose down         # stop
```

### Verify design
POST `/api/verify` with `{mode}` — runs `tests/verify_design.py` on rendered STLs.

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
| POST | `/api/render` | `{mode, scad_file, parameters, parts}` | Synchronous STL render |
| POST | `/api/render-stream` | `{mode, scad_file, parameters, parts}` | SSE streaming render |
| POST | `/api/render-cancel` | — | Cancel active render |
| POST | `/api/verify` | `{mode}` | Run STL quality checks |

## Code Conventions

| Area | Convention |
|------|-----------|
| Python | PEP 8, type hints, Flask blueprints |
| JS/JSX | ESLint, functional components, hooks, ES modules |
| OpenSCAD | `snake_case`, `render_mode` variable selects part |
| CSS | Tailwind utility classes, Shadcn tokens |
| Tests | Co-located (`*.test.js`/`*.test.jsx`), Vitest + RTL |
| Linting | ESLint + jsx-a11y (frontend), ruff (backend) |
| Naming | `camelCase` JS, `snake_case` Python/SCAD |

## Testing Standards

- **Frontend**: Vitest + RTL, coverage thresholds (65% statements/lines, 55% branches, 60% functions), jest-axe accessibility audits
- **Backend**: pytest + pytest-cov, coverage threshold 60%, tests in `tests/` directory
- **Pre-commit**: Husky runs `lint-staged` → ESLint fix + Vitest on changed files
- **CI**: `.github/workflows/ci.yml` — lint + test + coverage + `npm audit` + `pip-audit` on push/PR to main
- **Deploy**: `.github/workflows/deploy.yml` — manual trigger, runs tests then builds to GitHub Pages
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
| Client-side WASM | `openscad-worker.js` runs in a Web Worker; cannot access DOM |
| Rate limiting | Backend endpoints are rate-limited via Flask-Limiter (`extensions.py`). Render: 100/hr, Estimate: 200/hr, Verify: 50/hr |
| CSP headers | Production nginx adds Content-Security-Policy; requires `wasm-unsafe-eval` for OpenSCAD WASM |
| Bundle splitting | Vite splits vendor chunks (react, three, r3f, radix-ui); `ProjectsView` and `OnboardingWizard` are lazy-loaded |

## Do NOT Edit

- `web_interface/frontend/src/components/ui/*` — Shadcn managed
- `node_modules/`, `dist/` — generated artifacts
- `.github/workflows/*` — change only with explicit CI/CD intent

## Deployment

| Target | Method |
|--------|--------|
| Docker | `docker compose up` (backend + frontend) |
| GitHub Pages | Manual dispatch via `deploy.yml` (frontend-only, WASM rendering) |
| Local | Flask dev server + Vite dev server (see workflows above) |

## Further Docs

- [`docs/index.md`](docs/index.md) — Platform documentation hub
- [`docs/manifest.md`](docs/manifest.md) — Manifest schema and extension guide
- [`docs/web_interface.md`](docs/web_interface.md) — Full-stack architecture details
- [`docs/verification.md`](docs/verification.md) — STL quality verification system
- [`projects/tablaco/docs/mechanical_design.md`](projects/tablaco/docs/mechanical_design.md) — OpenSCAD geometry and parameters

Per-project docs live in `projects/{slug}/docs/`.
