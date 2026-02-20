# Yantra4D — Parametric 3D Print Design Platform

A manifest-driven platform for parametric OpenSCAD models with a web-based 3D preview studio, evolving into a **Hyperobjects Commons**.

![Yantra4D](/docs/images/half_cube_iso.png)

Ships with 22 built-in projects including **gridfinity** (modular storage), **slide-holder** 🔷 (microscope slide retention — first hyperobject), **ultimate-box**, **keyv2** (keycaps), **multiboard** (pegboard), **fasteners**, **gears**, **yapp-box**, **stemfie** (STEM kit), **polydice** (dice), **julia-vase** (fractal vases), **portacosas**, **voronoi** (organic patterns), **maze** (puzzle mazes), **relief** (text plaques & signs), **gear-reducer** (BOSL2 parametric gears), **torus-knot** (mathematical sculpture), **superformula** (generative vases), **spiral-planter** (archimedean planters), **rugged-box** (hinged latching box), **motor-mount** (NEMA stepper mounts), and **scara-robotics** (precision SCARA robotics Harmonic Drive). See [`projects/`](./projects/) for all projects.

## Features
-   **Manifest-Driven**: The webapp is data-driven via `project.json` manifests. Swapping SCAD projects requires only a new manifest file.
-   **Multi-Project**: Serve and switch between multiple SCAD projects from a single instance.
-   **White-Label Studio**: Each project white-labels the studio header with its own name via `manifest.project.name`, with a "powered by Yantra4D" tagline.
    -   **Theme Toggle**: Light, Dark, and System (Auto) modes.
    -   **Bilingual UI**: Spanish (default) and English.
    -   **Export**: Download STL files and capture images (Iso, Top, Front, Right).
-   **AI-Assisted Design**: Natural language chat adjusts parameters (AI Configurator, basic+) or generates SCAD code edits (AI Code Editor, pro+).
-   **GitHub Integration**: Import repos, edit SCAD files in a Monaco editor, git status/diff/commit/push/pull.
-   **Tiered Access Control**: Four tiers (guest, basic, pro, madfam) gating export formats, project limits, GitHub, and AI features.
-   **SCAD Code Editor**: Monaco-based editor with file tree, syntax highlighting, tabs, auto-save, and auto-render.
-   **Onboarding**: CLI tool and web wizard for onboarding external SCAD projects.

## Documentation

Platform documentation is available in the [`docs/`](./docs/index.md) directory:

-   [Verification Suite](./docs/verification.md) — Automated STL quality checks
-   [Web Interface](./docs/web_interface.md) — Full-stack architecture (Flask/React)
-   [Project Manifest](./docs/manifest.md) — Extensible manifest schema and how to add new projects
-   [Multi-Project Platform](./docs/multi-project.md) — Multi-project setup and configuration
-   [Developer Experience](./docs/devx-guide.md) — Onboarding external SCAD projects
-   [AI Features](./docs/ai-features.md) — AI Configurator and Code Editor
-   [llms.txt](./llms.txt) — LLM-optimized project overview for AI agents

Per-project docs live in `projects/{slug}/docs/`. Browse all 21 built-in projects under [`projects/`](./projects/).

## Tech Stack
-   **CAD**: OpenSCAD
-   **Backend**: Python 3 (Flask + Blueprints, gunicorn)
-   **Frontend**: React (Vite), Tailwind CSS, Shadcn UI, Three.js
-   **Containerization**: Docker + docker-compose
-   **Testing**: Vitest + RTL (frontend), pytest (backend), jest-axe (a11y)
-   **Security**: Flask-Limiter (rate limiting), CSP headers (nginx)

## Project Structure

```
yantra4d/
├── projects/
│   ├── gridfinity/              # Flagship project (modular storage bins)
│   │   ├── *.scad               # OpenSCAD geometry files
│   │   ├── project.json         # Project manifest (modes, params, parts)
│   │   └── exports/models/      # Reference STL exports
│   ├── polydice/                # Parametric dice set
│   ├── ultimate-box/            # Parametric box maker
│   └── ...                      # 22 built-in projects total
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
│           └── components/      # Header, Hero, InteractiveShowcase (React island)
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
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD -o projects/gridfinity/exports/models/cup.stl projects/gridfinity/yantra4d_cup.scad
```

### Launching Yantra4D

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
