# ⌬ Yantra4D: The Hyperobjects Commons

> **Manifest-driven parametric design for the decentralized manufacturing age.**

Yantra4D is not just a CAD tool; it is a **Poly-Kernel Engine**, a **Continuous SDF Geometry Compiler**, and a thriving **Hyperobjects Commons**. It bridges the mathematical precision of programmatic CAD with the accessibility of a visual, web-native storefront — integrating **material metadata** into the geometry pipeline, with **interactive Digital Twin simulation** in progress (see "Current status" below: parts of the simulation stack are heuristic or mocked today).

[![Astro](https://img.shields.io/badge/Docs-Starlight%20source-blueviolet)](apps/docs/)
[![License](https://img.shields.io/badge/License-AGPL%20v3-red.svg)](./LICENSE)
[![React](https://img.shields.io/badge/Studio-React%2019-61dafb)](https://app.yantra4d.com)

---

## 🛰️ The Vision: Hyperobjects & CDG
We are building the **Hyperobjects Commons** — a repository of "Bounded 4D Hyperobjects" designed for interoperability. By leveraging **Common Denominator Geometry (CDG)** interfaces (standardized snaps, threads, and joints), projects in the Yantra4D ecosystem can physically and mathematically interface with one another natively.

### 📼 Cartridge-Like Architecture
Every project in Yantra4D is a self-contained **"Cartridge"**. 
- **The Manifest**: A `project.json` file serves as the single source of truth, defining parameters, modes, and parts.
- **Poly-Kernel**: four kernels — high-performance OpenSCAD (CSG) for browser-side WASM reactivity, mathematically exact CadQuery (B-Rep) for engineering-grade STEP exports, a native Implicit SDF engine for lattices, and a node-graph engine that compiles graphs to sandboxed CadQuery.
- **Portability**: Drop a project folder into `projects/` and the platform instantly white-labels the UI to serve it.

### 🧠 Material Hyperobjects & Hyperawareness
Geometry is meaningless without material context. The Yantra4D Commons pioneers the integration of **Material Hyperobjects**—metadata modules (`/materials/`) capturing the Topological Data Analysis (TDA), spatial compensations, and semantic ontologies of physical AM substrates. By feeding this nanoscale intelligence directly into the geometric compiler, our additively manufacturable hyperobjects are imbued with **"hyperawareness"**, actively warping and adapting their dimensions to survive physical reality.

### 🌡️ Interactive Digital Twin (4D Simulation) — partially implemented / roadmap
The vision: apply simulated energy to any hyperobject and watch the continuous SDF morph in real-time as it crosses material phase boundaries (glass transition, yield, melt).

**What is real today (2026-07-04):** the Studio energy slider (`simulated_energy`) drives a thermodynamic-collapse heuristic in the implicit SDF engine (sag past glass-transition temperature), and the **WASM Circuit Breaker** genuinely routes complex renders from browser WASM to the server backend (`apps/studio/src/services/engine/renderService.ts`).

**What is mocked or heuristic today:** the "full physics simulation" pipeline (`POST /api/projects/:slug/simulate/physics`) generates a PPF solver script but never executes it — the background worker produces synthetic progress frames only (`apps/api/tasks/simulation_tasks.py`). The FEA stress endpoint returns a labeled geometry-derived **stress proxy**, not a structural solve. Real PPF/FEM execution on GPU nodes is **roadmap**. See the [Current status](#-current-status-2026-07-04) section.

---

## 🛠️ The Stack
- **CAD Engines**: Four-kernel execution via [OpenSCAD](https://openscad.org/) (CSG), [CadQuery](https://cadquery.readthedocs.io/) (B-Rep), a native **Implicit SDF Engine** (TPMS/Lattice), and a **Graph Engine** that transpiles `.graph.json` node graphs into sandboxed CadQuery (see [authoring guide](docs/guides/graph-cartridges.md)).
- **The Studio**: React 19 + Three.js + Manifold-3d for blisteringly fast volumetric browser rendering.
- **The API**: Python Flask backend with Docker-orchestrated render clusters and slicer-grade physics estimation.
- **The Knowledge Base**: [4D Docs source](apps/docs/) — Astro Starlight; the public docs site is not deployed yet (see "Deep Documentation" below).

---

## ✅ Current status (2026-07-04)

Honest, code-verified snapshot. **Working today:**

- **Interactive 3D preview** — Studio (React 19 + Three.js) renders projects live with parameter controls.
- **Dual rendering paths** — browser-side OpenSCAD **WASM** worker plus server-side native rendering, with automatic backend detection and a complexity **circuit breaker** that falls back between them.
- **STL / mesh export** — server render pipeline produces STL/GLB/3MF artifacts.
- **Geometry verification** — dedicated verify endpoint (`apps/api/routes/engine/verify.py`) and parity QA scripts (`scripts/qa/verify_parity.py`).
- **Cartridge project system** — `project.json` manifests, 326-cartridge CadQuery-first Commons catalog (including curated art/misc projects), admin app, Janua-authenticated admin flows.
- **Implicit SDF engine** — TPMS/lattice field generation, including the energy→sag "phase shift" heuristic behind the digital-twin slider.
- **Per-mode engine resolution** — a single cartridge can mix modes across kernels; the render engine is resolved per mode (`ManifestService.mode_engine`), so the flagship hyperobjects ship **dual-engine** (exact CadQuery B-Rep modes alongside their original OpenSCAD modes).

**Mocked or heuristic today (presented as roadmap, not shipped):**

- **PPF physics simulation** — the worker generates a solver script but does not execute it; progress and frames are synthetic (`apps/api/tasks/simulation_tasks.py`). No GPU execution path exists in this repo yet.
- **FEA stress heatmap** — a deterministic geometry-derived proxy (`schema_version: stress_proxy_v1`, `approximation: true`), not a structural solver.
- **Topology optimization** — a deterministic heuristic optimizer (`apps/api/services/simulation/optimizer.py` describes itself as the stand-in used "when full PDE-backed" solving is unavailable), not a real generative/PDE optimization.

---

## 📦 The Commons Catalog (CadQuery-first)

The Commons is a demand-grounded catalog of **Bounded 4D Hyperobjects**, authored
**CadQuery-first** (exact B-Rep, STEP export). Each `projects/<slug>/` is a
self-contained cartridge (`main.py` + `project.json` + docs); the flagship interfaces
are also published as independent `madfam-org` git submodules.

Counts below are generated from the manifests, not maintained by hand — see
[`docs/commons-catalog.json`](docs/commons-catalog.json):

<!-- BEGIN COMMONS_COUNTS -->

| | |
| :-- | --: |
| Cartridges | 340 |
| With declared CDG interfaces | 325 |
| Carrying an explicit license | 339 |
| Dual-engine (CadQuery B-Rep + OpenSCAD CSG) | 24 |
| Distinct external standards referenced | 209 |
| Licensed CERN-OHL-W-2.0 | 335 of 340 |

<!-- END COMMONS_COUNTS -->

### Licensing

Two licenses apply to this repository and they cover different things:

- **The platform** — everything outside `projects/` — is **AGPL-3.0** (see [LICENSE](./LICENSE)).
- **The cartridges** in `projects/` are hardware designs, licensed
  **CERN-OHL-W-2.0** (see the table above). Weakly reciprocal: modifications to a design
  must be shared, but a larger product incorporating one need not be.

A few cartridges differ because they derive from upstream work whose license
travels with it and cannot be relicensed:

| Cartridge | License | Upstream |
| :-- | :-- | :-- |
| `stemfie` | GPL-3.0-or-later | [stemfie.org](https://stemfie.org) |
| `keyv2` | GPL-3.0 | [rsheldiii/KeyV2](https://github.com/rsheldiii/KeyV2) |
| `multiboard` | **CC-BY-NC-SA-4.0** | Multiboard — **NonCommercial: you may not sell prints of this design** |
| `polydice` | BSD-2-Clause | PolyDiceGenerator, © 2020 charmaur |

If you build on those four you inherit their terms, not CERN-OHL-W-2.0 — and
`multiboard` in particular forbids commercial use, which CERN-OHL-W permits.
`rugged-box` is CERN-OHL-W-2.0 for its own wrappers but vendors upstream files
under CC BY-NC-SA 4.0; see its `NOTICE`.

Every cartridge's license is machine-readable in the catalog, and CI fails if a
declared license ever diverges from the one a cartridge actually ships, if a
manifest declares two conflicting licenses, or if an excluded cartridge appears
in the published catalog (`scripts/qa/check_licenses.py --strict-all`).

Two cartridges are deliberately **excluded** from the published Commons:
`tablaco` is a client engagement whose client retains all private rights, and
`cq-hyperobject-test` is an engine test fixture rather than a hyperobject.

**What is verified, precisely.** Every manifest is schema-validated in CI, and every
mode is geometrically distinct (each mode's `parts[]` id drives `target_part` dispatch).
Cross-kernel geometric parity and watertightness are enforced in CI for the cartridges
on the `VERIFIED_PARITY_PROJECTS` allowlist in
`apps/api/tests/scripts/geometric_regression.py`; for the rest, divergence is reported
but non-blocking, and each run prints how many cartridges were compared versus skipped.
Treat a green parity job as covering the allowlist, not the whole catalog.

**The first 100 — ordered by Common Denominator Geometry leverage:**

| Tier | Focus |
| :--- | :--- |
| 1 · Universal Interfaces | Gridfinity, VESA, ¼-20, GoPro, bottle thread, DIN clip, T-slot, gears, fasteners, box |
| 2 · Household Organization | dividers, pegboard/Multiboard, bins, hooks, shelf brackets |
| 3 · Kitchen / Bath / Utility | coasters, tube squeezers, jar racks, funnels, knobs |
| 4 · Mechanical & Kinematic | pulleys, bearings, gear trains, drag chain, springs, cams, lead-screw nuts |
| 5 · Fastening & Joining | connectors, snap-fits, dovetails, threaded bosses, ball-sockets |
| 6 · Electronics & Desk | enclosures, SBC cases, stands, risers, media caddies |
| 7 · Jigs & Fixtures | soft jaws, drill guides, gauges, templates, handwheels |
| 8 · Medical / Lab / Assistive | prosthetic sockets, slide holders, tube/pill racks, splints |
| 9 · Filtration / Water / Garden | Faircap filter, pipe/hose fittings, planters, drip fittings |
| 10 · Mobility / Automotive / EDC | Picatinny, bike/vent mounts, carabiners, keytags, French cleat |

**The second 100 — deeper cuts plus new domains** (mounting systems, drone/FPV,
automotive, kitchen, garden, workshop, electronics/maker, wearable/EDC, musical/studio,
sports, marine/RV, pet, generative art, safety).

**Dual-engine flagships** (CadQuery B-Rep modes + original OpenSCAD modes):
Gridfinity · Gears · Fasteners · DIN Rail Clip · Soft Jaw · Faircap Filter ·
Parametric Connector · Microscope Slide Holder · Prosthetic Socket — plus 14 more;
[`COMMONS.md`](./COMMONS.md) lists all 23.

> **Machine-readable catalog:** [`docs/commons-catalog.json`](docs/commons-catalog.json)
> — one entry per cartridge with its CDG interfaces, referenced standards, engines, and
> clone instructions. Human-readable index: [`COMMONS.md`](./COMMONS.md). Both are
> generated by `scripts/qa/generate_commons_catalog.py` and checked for staleness in CI.
>
> Note for agents: `llms.txt` and `llms-full.txt` are *not* the catalog. They are the
> org-wide agent operating contract, regenerated across every MADFAM repo by
> `internal-devops/scripts/sync-agent-docs.py`, which overwrites whatever is placed there.

---

## 📖 Deep Documentation
For peak Developer Experience and Agentic Discovery, consult our interconnected docs.

> **`docs.yantra4d.com` is not deployed yet** — the hostname does not resolve. The
> Starlight source below is complete and readable in-repo; the site build, ingress,
> and DNS record are still outstanding. Links point at the source until it is live.

- [**Getting Started**](apps/docs/src/content/docs/overview/getting-started.md) — Launch your first project.
- [**Manifest Specs**](apps/docs/src/content/docs/commons/manifest-specs.md) — How to author a "Cartridge".
- [**Poly-Kernel Logic**](apps/docs/src/content/docs/commons/poly-kernel.md) — Understanding the dual SCAD/Python pipeline.
- [**Hyperobjects Guide**](apps/docs/src/content/docs/commons/hyperobjects-guide.md) — CDG interfaces and the Commons model.
- [**Commons Catalog**](docs/commons-catalog.json) — Machine-readable entry point for AI agents.

---

## 🚀 Quick Start

### Clone (with all project submodules)
```bash
git clone --recurse-submodules https://github.com/madfam-org/yantra4d
```

### Development
```bash
./scripts/dev/dev.sh      # Full Stack (Backend + Studio + Landing)
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
