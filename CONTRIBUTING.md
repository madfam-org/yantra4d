# Contributing to Yantra4D

Thanks for your interest in contributing to Yantra4D! This guide covers everything you need to get started.

## Prerequisites

- **Node.js** 20+
- **Python** 3.12+
- **OpenSCAD** (latest stable, must be on PATH)
- **Git** with submodule support

## Dev Setup

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/madfam/yantra4d.git
cd yantra4d

# If already cloned without submodules
git submodule update --init --recursive

# Install frontend dependencies
cd apps/studio && npm install && cd ../..
cd apps/landing && npm install && cd ../..

# Install backend dependencies
cd apps/api && pip install -r requirements.txt && cd ../..
```

## Running Dev Servers

```bash
# Start all servers (backend + studio + landing)
./scripts/dev.sh

# Stop all dev servers
./scripts/dev-stop.sh
```

Ports: Flask API (5000), Studio Vite (5173), Astro Landing (4321), Admin (5174).

## Testing

We enforce **80% coverage thresholds** on both studio and backend.

```bash
# Studio (frontend) — Vitest + React Testing Library
cd apps/studio && npm test              # single run
cd apps/studio && npm run test:watch    # watch mode
cd apps/studio && npm run test:coverage # with coverage

# Backend — pytest
cd apps/api && pytest                   # all tests
cd apps/api && pytest --cov             # with coverage

# Landing — build check
cd apps/landing && npm run build
```

All tests must pass before merging.

## Linting

```bash
# JavaScript/JSX — ESLint
cd apps/studio && npx eslint src/

# Python — ruff
cd apps/api && ruff check .
```

## Code Style

| Area | Convention |
|------|-----------|
| Python | PEP 8, type hints, Flask blueprints |
| JavaScript/JSX | ESLint, functional components, hooks, ES modules |
| OpenSCAD | `snake_case` variables, `render_mode` selects part |
| CSS | Tailwind utility classes, shared tokens from `packages/tokens/` |
| Naming | `camelCase` JS, `snake_case` Python/SCAD |

## Manifest-First Design

Most features require **zero code changes** — only edits to `projects/{slug}/project.json`. The UI and backend read manifests dynamically. Before writing code, check if a manifest edit solves your problem.

See `docs/reference/manifest.md` for the full manifest schema.

## PR Process

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```
2. **Make your changes** and ensure tests pass
3. **Commit with conventional commits**:
   ```
   type(scope): description
   ```
   Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

   Examples:
   ```
   feat(studio): add exploded view slider for multi-part models
   fix(api): handle missing SCAD file in render endpoint
   docs(manifest): document hyperobject CDG interfaces
   ```
4. **Push and open a PR** against `main`
5. CI runs lint, tests, and coverage checks — all must pass

## Do NOT Edit

- `apps/studio/src/components/ui/*` — Shadcn UI managed components (use shadcn CLI to regenerate)
- `libs/*` — Git submodules (BOSL2, NopSCADlib, Round-Anything)
- `node_modules/`, `dist/` — Generated artifacts
- `.github/workflows/*` — Only with explicit CI/CD intent

## Adding a New Project

1. Create `projects/{slug}/project.json` following the manifest schema
2. Add `.scad` files to `projects/{slug}/`
3. The project is auto-discovered — no code changes needed

## Submodule Management

OpenSCAD libraries in `libs/` and federated projects in `projects/` are git submodules.

- **Weekly auto-update**: The `update-submodules.yml` workflow updates all submodules weekly and creates a PR
- **Per-push auto-bump**: The `bump-submodule.yml` workflow bumps individual project submodules when their upstream repos push to main
- **Excluded submodules**: `tablaco` has `update = none` in `.gitmodules` and is excluded from automated updates (managed separately via its own deployment pipeline)

To manually update a specific submodule:
```bash
cd projects/my-project
git fetch origin
git checkout origin/main
cd ../..
git add projects/my-project
git commit -m "chore(deps): update my-project submodule"
```

## Questions?

Open a GitHub Issue for bugs, feature requests, or questions.
