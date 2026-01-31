# Tablaco Studio — Parametric 3D Print Design Platform

A manifest-driven platform for parametric OpenSCAD models with a web-based 3D preview studio.

![Tablaco Studio](/docs/images/half_cube_iso.png)

Ships with the **tablaco** interlocking cube project. See [`projects/tablaco/README.md`](./projects/tablaco/README.md) for project-specific details.

## Features
-   **Manifest-Driven**: The webapp is data-driven via `project.json` manifests. Swapping SCAD projects requires only a new manifest file.
-   **Multi-Project**: Serve and switch between multiple SCAD projects from a single instance.
-   **Tablaco Studio**: A web-based interface for customization and visualization.
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

Per-project docs live in `projects/{slug}/docs/`. See [`projects/tablaco/`](./projects/tablaco/README.md) for the built-in project.

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
│   └── tablaco/                 # Default project (OpenSCAD source files)
│       ├── half_cube.scad       # Single half-cube unit
│       ├── assembly.scad        # Two-part assembly preview
│       ├── tablaco.scad         # Full grid assembly
│       ├── project.json         # Project manifest (modes, params, parts)
│       └── exports/models/      # Reference STL exports
├── web_interface/
│   ├── backend/                 # Flask API server
│   │   ├── app.py               # App factory + blueprint registration
│   │   ├── extensions.py        # Flask extensions (rate limiter)
│   │   ├── config.py            # Environment config (paths, server settings)
│   │   ├── manifest.py          # Project manifest loader + typed accessors
│   │   ├── routes/
│   │   │   ├── render.py        # /api/estimate, /api/render, /api/render-stream
│   │   │   ├── verify.py        # /api/verify
│   │   │   ├── health.py        # /api/health
│   │   │   ├── manifest_route.py # /api/manifest
│   │   │   └── config_route.py  # /api/config (legacy)
│   │   └── services/
│   │       └── openscad.py      # OpenSCAD subprocess wrapper
│   └── frontend/                # React SPA
│       └── src/
│           ├── App.jsx           # Main app shell + state management
│           ├── components/
│           │   ├── Controls.jsx  # Data-driven parameter controls
│           │   ├── Viewer.jsx    # Three.js 3D viewer
│           │   └── ui/           # Shadcn UI primitives
│           ├── contexts/
│           │   ├── ManifestProvider.jsx  # Manifest fetch + fallback
│           │   ├── LanguageProvider.jsx  # i18n (UI chrome strings)
│           │   └── ThemeProvider.jsx     # Light/Dark/System theme
│           └── config/
│               └── fallback-manifest.json  # Bundled manifest fallback
├── tests/
│   ├── verify_design.py         # STL verification script
│   ├── conftest.py              # Shared pytest fixtures
│   └── test_*.py                # Backend API + service tests
├── pyproject.toml              # pytest + coverage configuration
├── docs/                        # Project documentation
├── Dockerfile
└── docker-compose.yml
```

## Usage

### Prerequisites
-   OpenSCAD
-   Python 3.10+ (`pip install -r web_interface/backend/requirements.txt`)
-   pytest (`pip install pytest pytest-cov` — for running backend tests)
-   Node.js (v18+)

### Quick Run
Generate the default model:
```bash
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD -o projects/tablaco/exports/models/half_cube.stl projects/tablaco/half_cube.scad
```

### Launching Tablaco Studio

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
