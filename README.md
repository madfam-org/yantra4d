# ⌬ Yantra4D: The Hyperobjects Commons

> **Manifest-driven parametric design for the decentralized manufacturing age.**

Yantra4D is not just a CAD tool; it is a **Poly-Kernel Engine**, a **Continuous SDF Geometry Compiler**, and a thriving **Hyperobjects Commons**. It bridges the mathematical precision of programmatic CAD with the accessibility of a visual, web-native storefront — integrating **material metadata** into the geometry pipeline, with **interactive Digital Twin simulation** in progress (see "Current status" below: parts of the simulation stack are heuristic or mocked today).

[![Astro](https://img.shields.io/badge/Docs-Starlight-blueviolet)](https://docs.yantra4d.com)
[![License](https://img.shields.io/badge/License-AGPL%20v3-red.svg)](./LICENSE)
[![React](https://img.shields.io/badge/Studio-React%2019-61dafb)](https://app.yantra4d.com)

---

## 🛰️ The Vision: Hyperobjects & CDG
We are building the **Hyperobjects Commons** — a repository of "Bounded 4D Hyperobjects" designed for interoperability. By leveraging **Common Denominator Geometry (CDG)** interfaces (standardized snaps, threads, and joints), projects in the Yantra4D ecosystem can physically and mathematically interface with one another natively.

### 📼 Cartridge-Like Architecture
Every project in Yantra4D is a self-contained **"Cartridge"**. 
- **The Manifest**: A `project.json` file serves as the single source of truth, defining parameters, modes, and parts.
- **Poly-Kernel**: High-performance OpenSCAD (CSG) for browser-side WASM reactivity + mathematically exact CadQuery (B-Rep) for engineering-grade STEP exports.
- **Portability**: Drop a project folder into `projects/` and the platform instantly white-labels the UI to serve it.

### 🧠 Material Hyperobjects & Hyperawareness
Geometry is meaningless without material context. The Yantra4D Commons pioneers the integration of **Material Hyperobjects**—metadata modules (`/materials/`) capturing the Topological Data Analysis (TDA), spatial compensations, and semantic ontologies of physical AM substrates. By feeding this nanoscale intelligence directly into the geometric compiler, our additively manufacturable hyperobjects are imbued with **"hyperawareness"**, actively warping and adapting their dimensions to survive physical reality.

### 🌡️ Interactive Digital Twin (4D Simulation) — partially implemented / roadmap
The vision: apply simulated energy to any hyperobject and watch the continuous SDF morph in real-time as it crosses material phase boundaries (glass transition, yield, melt).

**What is real today (2026-07-04):** the Studio energy slider (`simulated_energy`) drives a thermodynamic-collapse heuristic in the implicit SDF engine (sag past glass-transition temperature), and the **WASM Circuit Breaker** genuinely routes complex renders from browser WASM to the server backend (`apps/studio/src/services/engine/renderService.ts`).

**What is mocked or heuristic today:** the "full physics simulation" pipeline (`POST /api/projects/:slug/simulate/physics`) generates a PPF solver script but never executes it — the background worker produces synthetic progress frames only (`apps/api/tasks/simulation_tasks.py`). The FEA stress endpoint returns a labeled geometry-derived **stress proxy**, not a structural solve. Real PPF/FEM execution on GPU nodes is **roadmap**. See the [Current status](#-current-status-2026-07-04) section.

---

## 🛠️ The Stack
- **CAD Engines**: Tri-kernel execution via [OpenSCAD](https://openscad.org/) (CSG), [CadQuery](https://cadquery.readthedocs.io/) (B-Rep), and a native **Implicit SDF Engine** (TPMS/Lattice).
- **The Studio**: React 19 + Three.js + Manifold-3d for blisteringly fast volumetric browser rendering.
- **The API**: Python Flask backend with Docker-orchestrated render clusters and slicer-grade physics estimation.
- **The Knowledge Base**: [4D Docs](https://docs.yantra4d.com) — Powered by Astro Starlight.

---

## ✅ Current status (2026-07-04)

Honest, code-verified snapshot. **Working today:**

- **Interactive 3D preview** — Studio (React 19 + Three.js) renders projects live with parameter controls.
- **Dual rendering paths** — browser-side OpenSCAD **WASM** worker plus server-side native rendering, with automatic backend detection and a complexity **circuit breaker** that falls back between them.
- **STL / mesh export** — server render pipeline produces STL/GLB/3MF artifacts.
- **Geometry verification** — dedicated verify endpoint (`apps/api/routes/engine/verify.py`) and parity QA scripts (`scripts/qa/verify_parity.py`).
- **Cartridge project system** — `project.json` manifests, 33 submodule projects, admin app, Janua-authenticated admin flows.
- **Implicit SDF engine** — TPMS/lattice field generation, including the energy→sag "phase shift" heuristic behind the digital-twin slider.

**Mocked or heuristic today (presented as roadmap, not shipped):**

- **PPF physics simulation** — the worker generates a solver script but does not execute it; progress and frames are synthetic (`apps/api/tasks/simulation_tasks.py`). No GPU execution path exists in this repo yet.
- **FEA stress heatmap** — a deterministic geometry-derived proxy (`schema_version: stress_proxy_v1`, `approximation: true`), not a structural solver.
- **Topology optimization** — a deterministic heuristic optimizer (`apps/api/services/simulation/optimizer.py` describes itself as the stand-in used "when full PDE-backed" solving is unavailable), not a real generative/PDE optimization.

---

## 📦 The Commons Catalog (33 Projects — each an independent GitHub repo)

All 33 projects are public repos under `madfam-org`, licensed **CERN-OHL-W-2.0**. Every `projects/<slug>/` is a git submodule.

| Ecosystem | Projects |
| :--- | :--- |
| **Storage & Enclosures** | Gridfinity · Multiboard · Rugged Box · Ultimate Box · YAPP Box · Portacosas |
| **Precision Robotics** | Chronos-SCARA (Harmonic Drive) · Motor Mount · Gear Reducer · Gears · Fasteners · Parametric Connector |
| **Generative Art** | Voronoi · Superformula · Torus Knot · Julia Vase · Maze · Spiral Planter · Relief |
| **Medical & Bio** | Microscope Slide Holder 🔷 · Microscope Slide Hyperobject 🔷 · Glia Diagnostic · Prosthetic Socket |
| **Hyperobjects** | Implicit Lattice (TPMS) · Extrusion · Framing · Custom MSH · Faircap Filter · DIN Rail Clip |
| **Input Devices** | KeyV2 Keycaps · Soft Jaw |
| **Construction** | STEMFIE · Tablaco (private) · PolyDice · CQ Hyperobject Test |

---

## 📖 Deep Documentation
For peak Developer Experience and Agentic Discovery, consult our interconnected docs:

- [**Getting Started**](https://docs.yantra4d.com/overview/getting-started/) — Launch your first project.
- [**Manifest Specs**](https://docs.yantra4d.com/commons/manifest-specs/) — How to author a "Cartridge".
- [**Poly-Kernel Logic**](https://docs.yantra4d.com/commons/poly-kernel/) — Understanding the dual SCAD/Python pipeline.
- [**LLM Context** (llms.txt)](./llms.txt) — Structured entry point for AI Agents.

---

## 🚀 Quick Start

### Clone (with all project submodules)
```bash
git clone --recurse-submodules https://github.com/madfam-org/yantra4d
```

### Development
```bash
./scripts/dev.sh          # Full Stack (Backend + Studio + Landing)
./scripts/dev-stop.sh     # Cleanup
```

### Docker (Production-Ready)
```bash
docker compose up --build
```
Open [localhost:3000](http://localhost:3000) to enter the Studio.

---

## 🤝 Community & License
Yantra4D is licensed under the **GNU Affero General Public License v3.0 (AGPLv3)**. Our hyperobjects are always released under the **CERN-OHL-W-2.0** (Weakly Reciprocal) open hardware license.

**Join the movement. Print the Hyperobjects.**
