# Tablaco Project Documentation

Welcome to the documentation for the Tablaco Interlocking Cube project.

## Documentation Index

-   [Mechanical Design](./mechanical_design.md): Parametric Half-Cube geometry, modules, clearance strategies, and grid assembly.
-   [Verification Suite](./verification.md): Automated STL quality checks — watertightness, volume count, assembly fit.
-   [Web Interface](./web_interface.md): Full-stack architecture (Flask/React), API reference, component structure.
-   [Project Manifest](./manifest.md): Extensible manifest schema, how the webapp is data-driven, and how to add new projects.
-   [Multi-Project Platform](./multi-project.md): Multi-project setup, project switching, and Docker configuration.
-   [Developer Experience Guide](./devx-guide.md): Onboarding external SCAD projects, CLI tool, and analyzer.

## Quick Start

### 1. Generating Models
```bash
# Standard Model
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD -o models/half_cube.stl projects/tablaco/half_cube.scad
```

### 2. Running Verification
```bash
python3 tests/verify_design.py
```

### 3. Launching Tablaco Studio
```bash
./scripts/dev.sh          # start backend + frontend
./scripts/dev-stop.sh     # stop all dev servers
```
Open http://localhost:5173

Or with Docker:
```bash
docker compose up --build   # start
docker compose down         # stop
```
Access: http://localhost:3000

## Architecture Overview

The project has three layers:

1. **OpenSCAD Models** (`projects/{slug}/`) — Parametric geometry definitions (e.g., `projects/tablaco/`)
2. **Backend API** (`web_interface/backend/`) — Flask server that invokes OpenSCAD and serves STL files
3. **Frontend SPA** (`web_interface/frontend/`) — React app with Three.js viewer

All three layers are connected through **project manifests** (`projects/{slug}/project.json`), which declare modes, parameters, parts, and labels. The backend's manifest registry discovers projects at startup; the frontend fetches the active project's manifest via `/api/projects/{slug}/manifest` (with a bundled fallback). See [Project Manifest](./manifest.md) and [Multi-Project Platform](./multi-project.md) for details.
