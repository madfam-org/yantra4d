# Yantra4D — Platform Documentation

Platform-level documentation for the Yantra4D parametric 3D print design platform.

## Documentation Index

-   [Verification Suite](./verification.md): Automated STL quality checks — watertightness, volume count, assembly fit.
-   [Web Interface](./web_interface.md): Full-stack architecture (Flask/React), API reference, component structure.
-   [Project Manifest](./manifest.md): Extensible manifest schema, how the webapp is data-driven, and how to add new projects.
-   [Multi-Project Platform](./multi-project.md): Multi-project setup, project switching, and Docker configuration.
-   [Developer Experience Guide](./devx-guide.md): Onboarding external SCAD projects, CLI tool, and analyzer.
-   [WASM Mode](./wasm-mode.md): Client-side rendering fallback — detection, architecture, limitations, browser support.
-   [Dual-Engine Architecture](./dual-engine.md): Benefits of OpenSCAD + CadQuery parity and B-Rep export.
-   [AI Features](./ai-features.md): AI Configurator and Code Editor — setup, API reference, tier access.
-   [Troubleshooting](./troubleshooting.md): Common issues — render timeouts, CORS, git submodules, Docker env vars.
-   [Competitive Landscape](./competitive-landscape.md): Market research, competitor analysis, and feature roadmap.
-   [Roadmap](./roadmap.md): Strategic features planned for future implementation.

### LLM Context

-   [llms.txt](../llms.txt): LLM-optimized project overview following [llmstxt.org](https://llmstxt.org/) spec.
-   [llms-full.txt](../llms-full.txt): Comprehensive single-file LLM context with all docs inlined.

### Internal Audits

-   [Codebase Audit](../claudedocs/codebase-audit.md): Full platform assessment — stability, coverage, architecture.
-   [Usability Audit](../claudedocs/usability-audit.md): Browser-based UX testing results.
-   [Production Verification](../claudedocs/enclii-verification-prompt.md): Deployment verification steps.

### Per-Project Docs

Each project carries its own docs in `projects/{slug}/docs/`. The platform ships with 21 built-in projects:
-   [Gridfinity](../projects/gridfinity/) — Modular storage bins (flagship)
-   [Microscope Slide Holder](../projects/microscope-slide-holder/) 🔷 — Microscope slide retention (first hyperobject)
-   [Polydice](../projects/polydice/) — Parametric dice set
-   Browse all projects under [`projects/`](../projects/)

## Quick Start

### 1. Running Verification
```bash
python3 tests/verify_design.py
```

### 3. Launching Yantra4D
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

The project has four layers:

1. **OpenSCAD Models** (`projects/{slug}/`) — Parametric geometry definitions for web previews.
2. **CadQuery Models** (`projects/{slug}/`) — Industrial-grade B-Rep mirrors for manufacturing.
3. **Backend API** (`apps/api/`) — Flask server that invokes both engines and runs verification.
4. **Frontend SPA** (`apps/studio/`) — React app with Three.js viewer.

All three layers are connected through **project manifests** (`projects/{slug}/project.json`), which declare modes, parameters, parts, and labels. The backend's manifest registry discovers projects at startup; the frontend fetches the active project's manifest via `/api/projects/{slug}/manifest` (with a bundled fallback). See [Project Manifest](./manifest.md) and [Multi-Project Platform](./multi-project.md) for details.
