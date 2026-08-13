# Yantra4D — Platform Documentation

Platform-level documentation for the Yantra4D parametric 3D print design platform.

## Documentation Index

### Architecture
-   [Architecture Audit](./architecture/architecture_audit.md): Deep dive into platform architecture and components.
-   [Database & Analytics](./architecture/database.md): SQLite/PostgreSQL, Alembic migrations, analytics schema.
-   [Engine architecture](./architecture/dual-engine.md): the four render kernels — OpenSCAD, CadQuery, implicit SDF, graph — and B-Rep export.
-   [Authoring graph cartridges](./guides/graph-cartridges.md): node graphs compiled to sandboxed CadQuery.
-   [Sim4D extraction record](./architecture/sim4d-extraction.md): what was taken from sim4d and what was left behind.
-   [Cross-ecosystem interventions](./operations/cross-ecosystem-interventions.md): what Yantra4D is owed from other platforms.
-   [TypeScript Migration](./architecture/typescript-migration.md): Gradual TS adoption — current progress, phase status, remaining work.
-   [Web Interface](./architecture/web_interface.md): Full-stack architecture (Flask/React), API reference, component structure.

### Guides
-   [Verification Suite](./guides/verification.md): Automated STL quality checks — watertightness, volume count, assembly fit.
-   [Developer Experience Guide](./guides/devx-guide.md): Onboarding external SCAD projects, CLI tool, and analyzer.
-   [WASM Mode](./guides/wasm-mode.md): Client-side rendering fallback — detection, architecture, limitations, browser support.
-   [Multi-Project Platform](./guides/multi-project.md): Multi-project setup, project switching, and Docker configuration.
-   [AI Features](./guides/ai-features.md): AI Configurator, Code Editor, and Synthesizer — setup, API reference, session management, tier access.
-   [Physics Simulation](./guides/physics-simulation.md): PPF Contact Solver pipeline (execution mocked), a labeled FEA stress proxy, heuristic topology optimization — architecture, REST API, local dev mock mode.
-   [Implicit SDF Engine](./guides/implicit-engine.md): TPMS lattice rendering, `engine: "implicit"` manifest usage, Digital Twin phase simulation.
-   [MQTT Telemetry](./guides/mqtt-telemetry.md): Real-time sensor data injection for 4D hyperobjects — MQTT client, parameter merging, SSE streaming.
-   [Rate Limiting](./guides/rate-limiting.md): Flask-Limiter, per-tier render limits, WASM fallback, production Redis setup.
-   [White-Labeling](./guides/white-labeling.md): Deploying branded instances — env vars, Docker Compose override, Kubernetes pattern, license key enforcement.
-   [Troubleshooting](./guides/troubleshooting.md): Common issues — render timeouts, CORS, Docker.

### Strategy & Planning
-   [Platform Manifesto](./strategy/MANIFESTO.md): Vision and philosophical hyperobject principles.
-   [Competitive Landscape](./strategy/competitive-landscape.md): Market research, competitor analysis, and feature context.
-   [Roadmap](../ROADMAP.md): Strategic features planned for future implementation.

### Reference
-   [Project Manifest](./reference/manifest.md): Extensible json schema, how the webapp is data-driven, and how to add new projects.
-   [OpenAPI Specification](./reference/openapi.yaml): Endpoint architecture and schema bounds.

### LLM Context

-   [llms.txt](../llms.txt): LLM-optimized project overview following [llmstxt.org](https://llmstxt.org/) spec.
-   [llms-full.txt](../llms-full.txt): Comprehensive single-file LLM context with all docs inlined.

### Internal Audits

-   [Codebase Audit](audits/codebase-audit.md): Full platform assessment — stability, coverage, architecture.
-   [Usability Audit](audits/usability-audit.md): Browser-based UX testing results.
-   [Production Verification](audits/enclii-verification-prompt.md): Deployment verification steps.

### Cartridge Projects

-   [Hyperobject Candidates](./cartridges/hyperobject_candidates.md): Three next-generation cartridge candidates leveraging the physics pipeline — Sentinel Gripper, Aegis Kinematic Fabric, Nautilus Continuum Spine.

### Per-Project Docs

Each project carries its own docs in `projects/{slug}/docs/`. The platform ships with 326 commons cartridges:
-   [Sentinel Gripper](../projects/sentinel-gripper-hyperobject/README.md) 🤖 — Crown demo: soft-robotics compliant gripper with PPF physics optimization
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

The platform has five layers:

1. **OpenSCAD Models** (`projects/{slug}/`) — Parametric geometry for previews and fast iteration.
2. **CadQuery Models** (`projects/{slug}/`) — Industrial-grade B-Rep mirrors for manufacturing export (STEP, GLB).
3. **Physics Engine** (`apps/api/services/simulation/`) — PPF Contact Solver integration for FEM stress simulation and generative topology optimization.
4. **Backend API** (`apps/api/`) — Flask server that invokes all four engines, runs verification, and queues background GPU tasks.
5. **Frontend SPA** (`apps/studio/`) — React app with Three.js viewer, kinematic timeline, and real-time physics heatmap.

All layers are connected through **project manifests** (`projects/{slug}/project.json`), which declare modes, parameters, parts, kinematics, physics targets, and labels. The backend's manifest registry discovers projects at startup; the frontend fetches the active project's manifest via `/api/projects/{slug}/manifest`. See [Project Manifest](./reference/manifest.md) and [Multi-Project Platform](./guides/multi-project.md) for details.
