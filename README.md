# Qubic — Parametric 3D Print Design Platform

A manifest-driven platform for parametric OpenSCAD models with a web-based 3D preview studio.

![Qubic](/docs/images/half_cube_iso.png)

Ships with 20 built-in projects including **tablaco** (interlocking cubes), **gridfinity** (modular storage), **ultimate-box**, **keyv2** (keycaps), **multiboard** (pegboard), **fasteners**, **gears**, **yapp-box**, **stemfie** (STEM kit), **polydice** (dice), **julia-vase** (fractal vases), **portacosas**, **voronoi** (organic patterns), **maze** (puzzle mazes), **relief** (text plaques & signs), **gear-reducer** (BOSL2 parametric gears), **torus-knot** (mathematical sculpture), **superformula** (generative vases), **spiral-planter** (archimedean planters), and **motor-mount** (NEMA stepper mounts). See [`projects/`](./projects/) for all projects or [`projects/tablaco/README.md`](./projects/tablaco/README.md) for the flagship project.

## Features
-   **Manifest-Driven**: The webapp is data-driven via `project.json` manifests. Swapping SCAD projects requires only a new manifest file.
-   **Multi-Project**: Serve and switch between multiple SCAD projects from a single instance.
-   **White-Label Studio**: Each project white-labels the studio header with its own name via `manifest.project.name`, with a "powered by Qubic" tagline.
    -   **Theme Toggle**: Light, Dark, and System (Auto) modes.
    -   **Bilingual UI**: Spanish (default) and English.
    -   **Export**: Download STL files and capture images (Iso, Top, Front, Right).
-   **Onboarding**: CLI tool and web wizard for onboarding external SCAD projects.

## Documentation

Platform documentation is available in the [`docs/`](./docs/index.md) directory:

-   [Verification Suite](./docs/verification.md) — Automated STL quality checks
-   [Web Interface](./docs/web_interface.md) — Full-stack architecture (Flask/React)
-   [Project Manifest](./docs/manifest.md) — Extensible manifest schema and how to add new projects
-   [Multi-Project Platform](./docs/multi-project.md) — Multi-project setup and configuration
-   [Developer Experience](./docs/devx-guide.md) — Onboarding external SCAD projects

Per-project docs live in `projects/{slug}/docs/`. See [`projects/tablaco/`](./projects/tablaco/README.md) for the flagship project, or browse all 20 built-in projects under [`projects/`](./projects/).

## Tech Stack
-   **CAD**: OpenSCAD
-   **Backend**: Python 3 (Flask + Blueprints, gunicorn)
-   **Frontend**: React (Vite), Tailwind CSS, Shadcn UI, Three.js
-   **Containerization**: Docker + docker-compose
-   **Testing**: Vitest + RTL (frontend), pytest (backend), jest-axe (a11y)
-   **Security**: Flask-Limiter (rate limiting), CSP headers (nginx)

## Project Structure

```
tablaco/
├── projects/
│   ├── tablaco/                 # Flagship project (interlocking cubes)
│   │   ├── *.scad               # OpenSCAD geometry files
│   │   ├── project.json         # Project manifest (modes, params, parts)
│   │   └── exports/models/      # Reference STL exports
│   ├── gridfinity/              # Modular storage bins
│   ├── polydice/                # Parametric dice set
│   ├── ultimate-box/            # Parametric box maker
│   └── ...                      # 20 built-in projects total
├── apps/
│   ├── api/                     # Flask API server
│   │   ├── app.py               # App factory + blueprint registration
│   │   ├── routes/              # API endpoints
│   │   ├── services/            # OpenSCAD, analyzer, manifest generator
│   │   └── tests/               # Backend tests (pytest)
│   ├── studio/                  # React SPA (parametric editor)
│   │   └── src/
│   │       ├── App.jsx          # Main app shell + state management
│   │       ├── components/      # Controls, Viewer, UI primitives
│   │       ├── contexts/        # Manifest, Language, Theme providers
│   │       └── config/          # Bundled fallback manifest
│   └── landing/                 # Astro marketing site
│       └── src/
│           ├── pages/           # index.astro
│           └── components/      # Header, Hero, DemoViewer (React island)
├── packages/
│   ├── schemas/                 # JSON Schema for project manifests
│   └── tokens/                  # Shared CSS custom properties
├── docs/                        # Platform documentation
└── docker-compose.yml
```

## Usage

### Prerequisites
-   OpenSCAD
-   Python 3.10+ (`pip install -r apps/api/requirements.txt`)
-   pytest (`pip install pytest pytest-cov` — for running backend tests)
-   Node.js (v18+)

### Quick Run
Generate the default model:
```bash
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD -o projects/tablaco/exports/models/half_cube.stl projects/tablaco/half_cube.scad
```

### Launching Qubic

#### Development
```bash
./scripts/dev.sh                  # start backend + frontend
./scripts/dev-stop.sh             # stop all dev servers
./scripts/dev.sh --frontend-only  # frontend only (WASM mode, no backend needed)
```
Open http://localhost:5173

#### Docker
```bash
docker compose up --build   # start
docker compose down         # stop
```
Open http://localhost:3000
