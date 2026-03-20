# Developer Onboarding Guide

Quick-start guide for new contributors to the Yantra4D platform.

> For the comprehensive machine-readable reference, see the project [CLAUDE.md](../../CLAUDE.md).

---

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Node.js | 20+ | `node -v` |
| Python | 3.12+ | `python3 --version` |
| OpenSCAD | Latest stable | `openscad --version` (must be on PATH) |
| Git | 2.x+ | `git --version` |
| Docker | 24+ (optional) | `docker --version` |

---

## Local Setup

```bash
# 1. Clone with submodules
git clone --recurse-submodules https://github.com/madfam/yantra4d.git
cd yantra4d

# If already cloned without submodules:
git submodule update --init --recursive

# 2. Install root dev dependencies (commitlint, husky)
npm install

# 3. Install frontend dependencies
cd apps/studio && npm install && cd ../..
cd apps/landing && npm install && cd ../..
cd apps/admin && npm install && cd ../..

# 4. Install backend dependencies
cd apps/api && pip install -r requirements.txt && cd ../..

# 5. Copy env template
cp .env.example .env
# Edit .env — for local dev, defaults are fine (AUTH_ENABLED=false)
```

### Docker (recommended for full stack)

```bash
docker compose -f docker-compose.dev.yml up --build
# Services: backend (5000), studio (5173), landing (4321), redis, mqtt-broker
# Admin: docker compose -f docker-compose.dev.yml --profile admin up
```

### Without Docker

```bash
./scripts/dev.sh          # Starts backend + studio + landing
./scripts/dev-stop.sh     # Stops all dev servers
```

| Service | Port | URL |
|---------|------|-----|
| Flask API | 5000 | http://localhost:5000/api/health |
| Studio (Vite) | 5173 | http://localhost:5173 |
| Landing (Astro) | 4321 | http://localhost:4321 |
| Admin | 5174 | http://localhost:5174 |

---

## Project Structure

```
yantra4d/
├── apps/
│   ├── api/          Flask backend (routes, services, middleware)
│   ├── studio/       React 19 + Vite + Three.js (main app)
│   ├── landing/      Astro + React islands (marketing site)
│   ├── admin/        React + Vite (admin dashboard)
│   └── docs/         Starlight documentation site
├── projects/         Parametric SCAD projects (each has project.json)
├── libs/             OpenSCAD libraries (git submodules — never edit)
├── packages/
│   ├── schemas/      JSON Schema for manifests
│   ├── sdk/          Headless SDK (@yantra4d/sdk)
│   └── tokens/       Shared CSS custom properties
├── scripts/          CLI tools, dev helpers, QA scripts
├── docs/             Architecture, guides, audits, strategy
└── k8s/              Kubernetes deployment configs
```

---

## Core Concept: Manifest-Driven Design

Everything revolves around `projects/{slug}/project.json`. This manifest defines modes, parts, parameters, UI controls, colors, estimates, BOM, and assembly steps. The UI and backend read it dynamically.

**Rule**: Most new parameters or modes require **zero code changes** — only manifest edits.

---

## Common Workflows

### Add a parameter to a project

1. Edit `projects/{slug}/project.json` → add to `parameters[]`
2. Use `$name` in the relevant `.scad` file
3. Update `apps/studio/src/config/fallback-manifest.json` if deploying to Pages

### Add a mode (render variant)

1. Edit `projects/{slug}/project.json` → add to `modes[]`
2. Create the `.scad` file in `projects/{slug}/`
3. Update fallback manifest

### Add a new project

1. Create `projects/{slug}/project.json` (see `docs/reference/manifest.md`)
2. Add `.scad` files to `projects/{slug}/`
3. Auto-discovered — no code changes needed

### Onboard an external SCAD project

```bash
scripts/cli/yantra4d-init ./path/to/scad-dir --slug my-project --install
```

Or use the web UI: upload `.scad` files → review analysis → edit manifest → save.

---

## Running Tests

```bash
# Studio (frontend) — 80% coverage threshold
cd apps/studio
npm test              # single run
npm run test:watch    # watch mode
npm run test:coverage # with coverage

# Landing — static build check
cd apps/landing && npm run build

# Backend — 80% coverage threshold
cd apps/api
pytest                # all tests
pytest --cov          # with coverage

# E2E (browser audit — requires Docker stack)
cd apps/studio
npx playwright test --project=audit
```

**Pre-commit hooks**: Husky runs `lint-staged` → ESLint fix + Vitest on changed files.

**Commit messages**: Must follow [Conventional Commits](https://www.conventionalcommits.org/):
```
type(scope): description

# Examples:
feat(studio): add exploded view slider
fix(api): handle missing SCAD file in render
docs(projects): update gridfinity manifest
```

Valid types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`
Valid scopes: `studio`, `api`, `landing`, `admin`, `docs`, `projects`, `libs`, `sdk`, `schemas`, `ci`, `docker`, `deps`

---

## Coding Conventions

| Area | Convention |
|------|-----------|
| Python | PEP 8, type hints, Flask blueprints, ruff linter |
| JS/JSX/TS | ESLint, functional components, hooks, ES modules |
| OpenSCAD | `snake_case`, `render_mode` variable selects part |
| CSS | Tailwind utility classes, shared tokens from `packages/tokens/` |
| Tests | Co-located (`*.test.js`/`*.test.jsx`), Vitest + RTL |
| Naming | `camelCase` JS, `snake_case` Python/SCAD |

---

## Troubleshooting

### OpenSCAD not found
```
Error: OpenSCAD executable not found
```
Ensure OpenSCAD is installed and on your PATH. Set `OPENSCAD_PATH` env var to override:
```bash
export OPENSCAD_PATH=/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD
```

### Render timeouts
Complex grid renders (high rows x cols) can exceed the default timeout. Docker uses 300s. For local dev, renders may fail on very complex configurations — simplify parameters.

### WASM fallback activates unexpectedly
The studio auto-detects backend availability. If the API is down, WASM fallback activates. Check:
```bash
curl http://localhost:5000/api/health
```

### Redis connection errors
Redis is optional for local dev. The render cache falls back to L1 in-memory only. For full functionality:
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### Submodule checkout issues
```bash
git submodule update --init --recursive
# If submodules are stuck:
git submodule foreach 'git checkout .'
git submodule update --init --recursive --force
```

### iOS Safari auto-zoom on inputs
All mobile inputs use `text-base` (16px) to prevent Safari auto-zoom. If adding new inputs, follow this pattern.

---

## Key Files Quick Reference

| What you're changing | Start here |
|---------------------|------------|
| Project parameters/modes | `projects/{slug}/project.json` |
| Backend route | `apps/api/routes/{domain}/` |
| Backend service | `apps/api/services/{domain}/` |
| React component | `apps/studio/src/components/` |
| React hook | `apps/studio/src/hooks/{domain}/` |
| API client call | `apps/studio/src/services/` |
| Tier/auth rules | `apps/api/tiers.json` + `middleware/auth.py` |
| Shared styles | `packages/tokens/colors.css` |
| Manifest schema | `packages/schemas/project-manifest.schema.json` |

---

## Further Reading

- [Manifest Schema Reference](../reference/manifest.md)
- [AI Features Guide](ai-features.md)
- [WASM Mode](wasm-mode.md)
- [Troubleshooting](troubleshooting.md)
- [Production Checklist](production-checklist.md)
