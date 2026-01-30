# Tablaco — Parametric 3D Print Design Studio

Manifest-driven Flask + React/Vite app for parametric OpenSCAD models with 3D preview.

## Architecture

```
scad/project.json (manifest — single source of truth)
       │
       ├──► web_interface/backend/  (Flask API, renders via OpenSCAD CLI)
       │        └── routes/  render, verify, health, manifest, config
       │
       └──► web_interface/frontend/ (React 19 + Vite + Three.js + Shadcn UI)
                ├── contexts/  ManifestProvider, Theme, Language
                ├── components/  Controls, Viewer, ConfirmRenderDialog
                └── services/  renderService, verifyService, openscad-worker (WASM)
```

## Critical File Map

| Path | Purpose | Modify? |
|------|---------|---------|
| `scad/project.json` | Project manifest — modes, parts, parameters, estimates | **YES** |
| `scad/*.scad` | OpenSCAD geometry source files | YES |
| `web_interface/backend/app.py` | Flask entry point, CORS, static serving | RARELY |
| `web_interface/backend/routes/render.py` | Render + estimate + cancel + SSE stream | RARELY |
| `web_interface/backend/routes/verify.py` | STL verification endpoint | RARELY |
| `web_interface/frontend/src/App.jsx` | Main shell, state management | RARELY |
| `web_interface/frontend/src/components/Controls.jsx` | Data-driven param controls (reads manifest) | RARELY |
| `web_interface/frontend/src/components/Viewer.jsx` | Three.js 3D STL viewer | RARELY |
| `web_interface/frontend/src/contexts/ManifestProvider.jsx` | Fetches & provides manifest to app | RARELY |
| `web_interface/frontend/src/components/ui/*` | Shadcn primitives | **NEVER** |
| `tests/verify_design.py` | STL quality checker script | RARELY |
| `docs/*.md` | Deep-dive documentation | YES |

## Core Pattern: Manifest-Driven Design

`scad/project.json` controls **everything**: modes, parts, parameters, UI controls, colors, and estimates. To add features, **edit the manifest first** — the UI and backend read it dynamically.

**Rule**: Most new parameters or modes require **zero code changes** — only manifest edits.

**Fallback**: The frontend embeds a fallback manifest (`src/config/fallback-manifest.json`) for offline/GitHub Pages mode. Keep it in sync after manifest changes.

## Common Workflows

### Add a parameter
1. Add entry to `scad/project.json` → `parameters[]` (set name, type, default, min/max, modes)
2. Use `$name` in relevant `.scad` files
3. Update `fallback-manifest.json` if deploying to Pages

### Add a mode
1. Add entry to `scad/project.json` → `modes[]` (set slug, scad_file, parts, estimate)
2. Create the `.scad` file in `scad/`
3. Update `fallback-manifest.json`

### Add a new SCAD project
1. Create new `scad/project.json` following the manifest schema (see `docs/manifest.md`)
2. Add `.scad` files to `scad/`

### Run tests
```bash
cd web_interface/frontend && npm test          # single run
cd web_interface/frontend && npm run test:watch # watch mode
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
| GET | `/api/manifest` | — | Fetch full project manifest |
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
| Naming | `camelCase` JS, `snake_case` Python/SCAD |

## Testing Standards

- **Pre-commit**: Husky runs `lint-staged` → ESLint fix + Vitest on changed files
- **CI**: `.github/workflows/ci.yml` — lint + test on push/PR to main (Node 20)
- **Deploy**: `.github/workflows/deploy.yml` — manual trigger, runs tests then builds to GitHub Pages

## Known Gotchas

| Issue | Detail |
|-------|--------|
| Manifest sync | After editing `project.json`, update `fallback-manifest.json` for Pages mode |
| Shadcn UI | **Never** hand-edit `components/ui/*` — use shadcn CLI to regenerate |
| Verify false positives | Verification needs rendered STLs to exist first; render before verifying |
| Render timeouts | Complex grid renders (high rows×cols) can exceed default timeout; Docker uses 300s |
| Env vars | Backend reads `OPENSCAD_PATH`, `SCAD_DIR`, `VERIFY_SCRIPT` — set in Docker or `.env` |
| CORS origins | Backend restricts CORS via `CORS_ORIGINS` env var; add your domain when deploying |
| Client-side WASM | `openscad-worker.js` runs in a Web Worker; cannot access DOM |

## Do NOT Edit

- `web_interface/frontend/src/components/ui/*` — Shadcn managed
- `node_modules/`, `dist/`, `models/` — generated artifacts
- `.github/workflows/*` — change only with explicit CI/CD intent

## Deployment

| Target | Method |
|--------|--------|
| Docker | `docker compose up` (backend + frontend) |
| GitHub Pages | Manual dispatch via `deploy.yml` (frontend-only, WASM rendering) |
| Local | Flask dev server + Vite dev server (see workflows above) |

## Further Docs

- [`docs/index.md`](docs/index.md) — Documentation hub
- [`docs/manifest.md`](docs/manifest.md) — Manifest schema and extension guide
- [`docs/web_interface.md`](docs/web_interface.md) — Full-stack architecture details
- [`docs/mechanical_design.md`](docs/mechanical_design.md) — OpenSCAD geometry and parameters
- [`docs/verification.md`](docs/verification.md) — STL quality verification system
