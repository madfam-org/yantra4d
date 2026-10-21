# Physics Simulation — PPF Contact Solver Integration

> [!IMPORTANT]
> **Current status (2026-10-07): no physics solver ships with this repo.**
> `POST /api/projects/:slug/simulate/physics` answers **501** with
> `error_code: "physics_solver_unavailable"` and creates no job until a solver
> backend is registered with `configure_physics_solver`
> (`apps/api/tasks/simulation_tasks.py`). The PPF script generator is real; it
> builds the input such a backend would run. The stress endpoint is a labeled
> geometry-derived estimate (`method: "geometry_proxy"`, `approximation: true`,
> `stress_proxy_v1`), not a finite-element solve. The optimize endpoint is a
> deterministic heuristic (`method: "heuristic"`, `approximation: true`). Real
> PPF/FEM execution on GPU nodes is **roadmap**.

Yantra4D includes a physics simulation pipeline designed around the **PPF Contact Solver** (`st-tech/ppf-contact-solver`, SIGGRAPH Asia 2024). The target capability is penetration-free FEM contact simulation for compliant mechanism hyperobjects.

## Overview

| Feature | Endpoint | Tier Required |
|---------|----------|---------------|
| **Stress estimate** (geometry proxy, not FEA) | `POST /api/projects/:slug/simulate/stress` | pro+ |
| **Physics simulation** (PPF; 501 until a solver is registered) | `POST /api/projects/:slug/simulate/physics` | pro+ |
| **Parameter estimate** (heuristic, not topology optimization) | `POST /api/projects/:slug/simulate/optimize` | pro+ |

---

## Architecture

The simulation pipeline uses a **decoupled background worker** pattern, keeping the API non-blocking. **No solver backend ships with the repo.** Until one is registered, the physics endpoint answers 501 and creates no job. A registered backend receives the generated PPF script and the part count and returns the frames it computed; the job reports exactly those frames.

```
Studio frontend
    │  POST /simulate/physics
    │    no solver registered → 501 physics_solver_unavailable, no job
    │    solver registered    → 202 { job_id }
    │
Yantra4D API
    │  queue_simulation() → background thread
    │
Background Worker
    │  generates the PPF Python script via script_generator.py
    │  calls the registered solver backend with the script and part count
    │  stores the frames the solver returned
    │
Studio polls GET /simulate/physics/:job_id
    │  status queued → running → success | failed
    │  physicsFrames → WebGL morph targets (roadmap)
```

---

## Services

### `apps/api/services/simulation/script_generator.py`

Translates a Yantra4D `project.json` payload (parts + kinematics) into an executable Python script using the `ppf-contact-solver` native SDK:

| Input | Output |
|-------|--------|
| `parts[]` | `app.asset.add.tri()` mesh loads |
| `kinematics.pinned == true` | `obj.pin()` boundary conditions |
| `kinematics.flex_modulus` | `obj.param.set("strain-limit", X)` |

### `apps/api/services/simulation/optimizer.py`

Implements `TopologyOptimizer`, a deterministic heuristic. Over N generations it moves one numeric parameter (it prefers names containing `thickness`, e.g. `blade_thickness`) toward a target inside inferred bounds. The score it reports comes from that rule, not from a computed stress; no solver runs. It is meant to be replaced by a solver-backed objective (see `ROADMAP.md`, Sprint 17).

### `apps/api/tasks/simulation_tasks.py`

Background task runner (background threads; a Celery GPU queue is roadmap). `configure_physics_solver(solver)` registers the backend that executes PPF scripts: a callable `(script: str, part_count: int) -> list` that returns the frames it computed. `configure_physics_solver(None)` removes it, and `physics_solver_available()` reports whether one is registered. Without a backend, `queue_simulation()` raises `PhysicsSolverUnavailable` and the route answers 501. Per-job state in `_JOB_STORE`:

```python
{
    "status": "queued" | "running" | "success" | "failed",
    "progress": 0.0 | 100.0,  # 100 on success; the solver reports no intermediate progress
    "frames": [...],          # exactly what the solver returned (e.g. PLY frame refs)
    "frames_generated": int,
    "metadata": {"parts": int, "script_signature": str},
    "error": None | str
}
```

### `apps/api/tasks/optimization_tasks.py`

Background task runner for the heuristic parameter estimate. Runs 15 generations and logs one line per generation (`Gen 05 | blade_thickness=2.6 -> heuristic score 31.996 (best 29.638)`). Every job carries `method: "heuristic"` and `approximation: true`. On success it writes `best_params` to the job store for the Studio to apply.

---

## REST API Reference

### Start Physics Simulation

```
POST /api/projects/:slug/simulate/physics
Authorization: Bearer <token>   (pro tier required)
Content-Type: application/json

{
  "parts": [{ "id": "housing" }, { "id": "flexure" }],
  "kinematics": {
    "housing": { "pinned": true },
    "flexure": { "pinned": false, "flex_modulus": 90 }
  }
}
```

**Response** `501 Not Implemented` when no solver backend is registered (the default). The check runs before the payload is read, and no job is created:
```json
{
  "status": "error",
  "error": "Physics simulation is not available: no physics solver is configured on this server.",
  "error_code": "physics_solver_unavailable"
}
```

**Response** `202 Accepted` when a solver backend is registered (`400` if `parts` or `kinematics` is missing):
```json
{ "status": "success", "message": "Physics simulation queued.", "job_id": "uuid" }
```

### Poll Physics Status

```
GET /api/projects/:slug/simulate/physics/:job_id
```

**Response**:
```json
{
  "status": "running",
  "progress": 47.0,
  "frames": [],
  "error": null
}
```

On `status == "success"`, `frames` holds exactly the frames the solver returned and `frames_generated` their count. Without a solver no job exists, so this route answers `404`.

### Start Parameter Estimate (heuristic)

```
POST /api/projects/:slug/simulate/optimize
Content-Type: application/json

{ "params": { "blade_thickness": 2.0, "finger_length": 65 } }
```

**Response** `202 Accepted`:
```json
{ "status": "success", "job_id": "uuid", "method": "heuristic", "approximation": true }
```

### Poll Parameter Estimate Status

```
GET /api/projects/:slug/simulate/optimize/:job_id
```

**Response**:
```json
{
  "status": "running",
  "method": "heuristic",
  "approximation": true,
  "progress": 33.3,
  "best_params": null,
  "logs": ["Gen 05 | blade_thickness=2.6 -> heuristic score 31.996 (best 29.638)"],
  "current_score": 31.996,
  "current_sigma": 31.996,
  "error": null
}
```

`current_sigma` is a deprecated alias of `current_score`, kept for one release; both hold a heuristic score, not a stress. On `status == "success"`, `best_params` holds the parameters the heuristic settled on: an estimate, not an optimized design. The Studio applies them with `setParams(best_params)` and regenerates the model; the change can be undone.

### Stress Estimate

```
POST /api/projects/:slug/simulate/stress
Content-Type: application/json

{ "force_x": 0.0, "force_y": -50.0, "force_z": 0.0 }
```

**Response** `200` (`409` when the project has no rendered mesh; fields inside `simulation` other than `summary` are left out here):
```json
{
  "status": "success",
  "method": "geometry_proxy",
  "approximation": true,
  "project": "slug",
  "mesh_file": "<file>",
  "simulation": { "summary": { "schema_version": "stress_proxy_v1", "approximation": true } },
  "force_vector": { "x": 0.0, "y": -50.0, "z": 0.0 }
}
```

The stress field is computed from the mesh geometry and the force vector. It is an estimate, not a finite-element solve.

---

## Frontend Integration

State is managed in `ProjectProvider.tsx`:

| State Variable | Type | Description |
|---|---|---|
| `physicsJobId` | `string \| null` | Active simulation job ID |
| `physicsProgress` | `number` | 0–100 completion percentage |
| `physicsFrames` | `boolean[] \| null` | Frames of a finished job |
| `physicsUnavailable` | `boolean` | `true` once the API answered `physics_solver_unavailable`; the physics button stays disabled and shows the reason |
| `stressData` | `object \| null` | The stress estimate shown as a heatmap |
| `optimizationJobId` | `string \| null` | Active parameter estimate job ID |
| `optimizationProgress` | `number` | 0–100 completion percentage |
| `optimizationLogs` | `string[]` | Live generation log lines |

Handlers: `handleRunPhysics()`, `handleRunFEA()` (the stress estimate; the name predates the relabel) and `handleOptimizeTopology()` (the heuristic parameter estimate). The Studio labels the stress map and the parameter search as estimates in all six locales (`sim.*` keys).

Polling interval: **1500ms** via `setInterval` / `useEffect` cleanup.

---

## Local Development Notes

> [!TIP]
> No solver ships with the repo, so locally the physics endpoint answers 501 and the Studio disables the physics button with the reason. The backend tests register a stand-in solver (`apps/api/tests/unit/test_simulation_tasks.py`, `apps/api/tests/unit/test_simulate_routes.py`) to exercise the job and polling path. Never register a stand-in in a deployed environment: it would report frames that no solver computed.

Moving the worker to a Celery GPU queue is roadmap (`ROADMAP.md`, Sprint 17).

---

## Production Deployment (roadmap — not yet wired up)

The steps below describe the intended GPU deployment. The repo does not contain a solver backend yet; one would be registered with `configure_physics_solver` (see the status note at the top).

Provision an NVIDIA instance (e.g. `g6.2xlarge`) and install:
```bash
pip install ppf-contact-solver  # requires CUDA 12.8+
```

The `script_generator.py` output is a self-contained Python script using:
```python
from frontend import App
app = App.create("session_name")
```

PPF exports frame sequences as `.ply` files. In production, these are uploaded to S3/CDN and referenced in the `frames` array as signed URLs.

---

## See Also

- [PPF Contact Solver GitHub](https://github.com/st-tech/ppf-contact-solver)
- [Sentinel Gripper Hyperobject](../../projects/sentinel-gripper-hyperobject/README.md) — Crown Demo
- [Cartridge Candidates](../cartridges/hyperobject_candidates.md) — Future roadmap
