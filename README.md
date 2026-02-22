# ⌬ Yantra4D: The Hyperobjects Commons

> **Manifest-driven parametric design for the decentralized manufacturing age.**

Yantra4D is not just a CAD tool; it is a **Poly-Kernel Engine**, a **Continuous SDF Geometry Compiler**, and a thriving **Hyperobjects Commons**. It bridges the mathematical precision of programmatic CAD with the accessibility of a visual, web-native storefront — and uniquely integrates **nanoscale material intelligence** and **interactive Digital Twin simulation** directly into the browser.

[![Astro](https://img.shields.io/badge/Docs-Starlight-blueviolet)](https://4d-docs.madfam.io)
[![License](https://img.shields.io/badge/License-AGPL%20v3-red.svg)](./LICENSE)
[![React](https://img.shields.io/badge/Studio-React%2019-61dafb)](https://4d-app.madfam.io)

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

### 🌡️ Interactive Digital Twin (4D Simulation)
Yantra4D is the first browser-native platform to simulate **temporal phasing (4D printing)**. Users can apply simulated energy to any hyperobject and watch the continuous SDF morph in real-time as it crosses material phase boundaries (glass transition, yield, melt). An intelligent **WASM Circuit Breaker** automatically routes computationally intensive renders to the Docker backend, keeping the UI perfectly fluid regardless of topological complexity.

---

## 🛠️ The Stack
- **CAD Engines**: Tri-kernel execution via [OpenSCAD](https://openscad.org/) (CSG), [CadQuery](https://cadquery.readthedocs.io/) (B-Rep), and a native **Implicit SDF Engine** (TPMS/Lattice).
- **The Studio**: React 19 + Three.js + Manifold-3d for blisteringly fast volumetric browser rendering.
- **The API**: Python Flask backend with Docker-orchestrated render clusters and slicer-grade physics estimation.
- **The Knowledge Base**: [4D Docs](https://4d-docs.madfam.io) — Powered by Astro Starlight.

---

## 📦 The Commons Catalog (36+ Projects)
From modular storage systems like **Gridfinity** to precision robotics like **SCARA Harmonic Drives**, the Commons provides a massive library of ready-to-print hyperobjects.

| Ecosystem | Description |
| :--- | :--- |
| **Gridfinity** | The world-standard modular storage system, optimized for WASM. |
| **Microscope Commons** | Standardized lab hardware including the **Slide-Holder** hyperobject. |
| **Fasteners** | Parametric bolts, nuts, and threads with exact B-Rep parity. |
| **Scara-Robotics** | High-precision parametric robotic limbs and reducers. |

---

## 📖 Deep Documentation
For peak Developer Experience and Agentic Discovery, consult our interconnected docs:

- [**Getting Started**](https://4d-docs.madfam.io/overview/getting-started/) — Launch your first project.
- [**Manifest Specs**](https://4d-docs.madfam.io/commons/manifest-specs/) — How to author a "Cartridge".
- [**Poly-Kernel Logic**](https://4d-docs.madfam.io/commons/poly-kernel/) — Understanding the dual SCAD/Python pipeline.
- [**LLM Context** (llms.txt)](./llms.txt) — Structured entry point for AI Agents.

---

## 🚀 Quick Start

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
