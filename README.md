# Tablaco: Parametric Interlocking Cube

A generative design project creating a 3-walled interlocking cube system optimized for FDM 3D printing.

![Tablaco Studio](/docs/images/half_cube_iso.png)

## Features
-   **Parametric**: Fully adjustable size, thickness, and clearance via OpenSCAD.
-   **Interlocking**: Two identical "Half-Cubes" snap together to form a solid void.
-   **Cantilever Snaps**: Integrated mechanism for secure, repeated assembly.
-   **Grid Assembly**: Generate arrays of cubes with configurable rows, columns, and connecting rods.
-   **Tablaco Studio**: A web-based interface for customization and visualization.
    -   **Three Modes**: Unit Design, Assembly Preview, and Grid Design.
    -   **Theme Toggle**: Light, Dark, and System (Auto) modes.
    -   **Bilingual UI**: Spanish (default) and English.
    -   **Export**: Download STL files and capture images (Iso, Top, Front, Right).
-   **Extensible Manifest Architecture**: The webapp is data-driven via a project manifest (`project.json`). Swapping SCAD projects requires only a new manifest file.

## Documentation

Full documentation is available in the [`docs/`](./docs/index.md) directory:

-   [Mechanical Design](./docs/mechanical_design.md) — OpenSCAD geometry, parameters, modules
-   [Verification Suite](./docs/verification.md) — Automated STL quality checks
-   [Web Interface](./docs/web_interface.md) — Full-stack architecture (Flask/React)
-   [Project Manifest](./docs/manifest.md) — Extensible manifest schema and how to add new projects

## Tech Stack
-   **CAD**: OpenSCAD
-   **Backend**: Python 3 (Flask + Blueprints, gunicorn)
-   **Frontend**: React (Vite), Tailwind CSS, Shadcn UI, Three.js
-   **Containerization**: Docker + docker-compose

## Project Structure

```
tablaco/
├── scad/                        # OpenSCAD source files
│   ├── half_cube.scad           # Single half-cube unit
│   ├── assembly.scad            # Two-part assembly preview
│   ├── tablaco.scad             # Full grid assembly
│   └── project.json             # Project manifest (modes, params, parts)
├── web_interface/
│   ├── backend/                 # Flask API server
│   │   ├── app.py               # App factory + blueprint registration
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
│   └── verify_design.py         # STL verification script
├── docs/                        # Project documentation
├── Dockerfile
└── docker-compose.yml
```

## Usage

### Prerequisites
-   OpenSCAD
-   Python 3.10+ (`pip install -r web_interface/backend/requirements.txt`)
-   Node.js (v18+)

### Quick Run
Generate the default model:
```bash
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD -o models/half_cube.stl scad/half_cube.scad
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
