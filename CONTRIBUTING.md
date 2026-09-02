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
git clone --recurse-submodules https://github.com/madfam-org/yantra4d.git
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

### What CI runs on your PR

`.github/workflows/ci.yml` classifies your PR before it schedules anything. The
`changes` job asks one question: is every changed file documentation?

- **Documentation** means any `*.md`, plus `docs/**`, `apps/docs/**`,
  `runbooks/**` and `.github/*.md`.
- **Docs-only PR** — the ten-shard Playwright browser matrix, the studio,
  landing and admin builds, the backend test suite and the geometric parity
  check are all skipped. The manifest, spec-conformance, metadata/licence,
  OpenAPI, i18n and `ci-scripts` checks still run, because those are what a
  documentation change can actually break — and `ci-scripts` guards the deploy
  change-detection resolver that the skipping itself relies on.
- **Anything else is a code PR** and runs the full matrix. A PR that touches
  documentation *and* code is a code PR — there is no way to opt a code change
  out of the matrix, and that is deliberate.
- **Pushes to `main`** always run everything, whatever they touch.

`ci-success` is the single required check. It runs even when jobs ahead of it
were skipped or failed (`if: ${{ !cancelled() }}`), and it fails if any job it
depends on reported `failure` or `cancelled`; a job skipped by the path filter
counts as passed. So a green `ci-success` on a docs-only PR means "nothing that
could break was skipped", not "the tests were turned off". The one run it does
not report on is a run the concurrency group cancelled, which is the point — a
superseded run must not queue an aggregator on the shared pool while the head
that replaced it waits.

If you are surprised that your PR skipped the browser matrix, open the `changes`
job's summary — it says which way it classified the PR and why.

## Do NOT Edit

- `apps/studio/src/components/ui/*` — Shadcn UI managed components (use shadcn CLI to regenerate)
- `libs/*` — Git submodules (BOSL2, NopSCADlib, Round-Anything, threads-scad, MCAD, dotSCAD)
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
- **Excluded submodules**: the client-private `projects/tablaco` and `projects/tablaco-v2` carry `update = none` in `.gitmodules` and are excluded from automated updates (managed separately via their own deployment pipeline). The other 35 `projects/*` submodules are public. `git submodule update` honours `update = none`, so never add `--checkout` — that overrides it and tries to clone the private repos, which a normal contributor cannot read

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
