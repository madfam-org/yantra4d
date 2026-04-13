# Physics Simulation — PPF Contact Solver Integration

Yantra4D includes a physics simulation pipeline backed by the **PPF Contact Solver** (`st-tech/ppf-contact-solver`, SIGGRAPH Asia 2024). This enables penetration-free FEM contact simulation for compliant mechanism hyperobjects.

## Overview

| Feature | Endpoint | Tier Required |
|---------|----------|---------------|
| **FEA Stress Heatmap** (heuristic) | `POST /api/projects/:slug/simulate/stress` | pro+ |
| **Full Physics Simulation** (PPF FEM) | `POST /api/projects/:slug/simulate/physics` | pro+ |
| **AI Topology Optimization** | `POST /api/projects/:slug/simulate/optimize` | pro+ |

---

## Architecture

The simulation pipeline uses a **decoupled background worker** pattern, keeping the API non-blocking. On MacOS / local dev, the CUDA dependency is absent so the pipeline runs a **mock mode** that exercises the full data pipeline with synthetic frames. On a GPU-provisioned node (e.g. AWS `g6.2xlarge` with NVIDIA CUDA 12.8+), the real PPF solver executes.

```
Studio frontend
    │  POST /simulate/physics   (returns job_id)
    │
Yantra4D API
    │  queue_simulation() → background thread / Celery GPU queue
    │
Background Worker
    │  generates PPF Python script via script_generator.py
    │  executes via subprocess (or mock on CPU nodes)
    │  exports frames to static storage
    │
Studio polls GET /simulate/physics/:job_id
    │  progress 0→100 %
    │  physicsFrames → WebGL morph targets
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

Implements `TopologyOptimizer` — a heuristic gradient descent engine that sweeps target parameters (e.g. `blade_thickness`) through N generations, evaluating synthetic Von Mises stress at each iteration. Designed to be replaced with a real PPF surrogate model on GPU nodes.

### `apps/api/tasks/simulation_tasks.py`

Background task runner (threading-based locally; swap to `@celery.task(queue="gpu_tasks")` in production). Manages `_JOB_STORE` with per-job state:

```python
{
    "status": "queued" | "running" | "success" | "failed",
    "progress": 0.0–100.0,
    "frames": [...],  # boolean array (real PLY frame refs in production)
    "error": None | str
}
```

### `apps/api/tasks/optimization_tasks.py`

Background task runner for the topology optimizer. Runs 15 generations by default, emitting live logs on each generation. On success, writes `best_params` back to the job store for the frontend to apply.

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

**Response** `202 Accepted`:
```json
{ "status": "success", "job_id": "uuid" }
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

On `status == "success"`, `frames` is a 100-element array.

### Start Topology Optimization

```
POST /api/projects/:slug/simulate/optimize
Content-Type: application/json

{ "params": { "blade_thickness": 2.0, "finger_length": 65 } }
```

**Response** `202 Accepted`:
```json
{ "status": "success", "job_id": "uuid" }
```

### Poll Optimization Status

```
GET /api/projects/:slug/simulate/optimize/:job_id
```

**Response**:
```json
{
  "status": "running",
  "progress": 33.3,
  "best_params": null,
  "logs": ["Gen 05 | Sigma: 67.3 | Best: 64.1"],
  "error": null
}
```

On `status == "success"`, `best_params` contains the optimized parameter dictionary. The Studio automatically calls `setParams(best_params)` and re-generates the model.

---

## Frontend Integration

State is managed in `ProjectProvider.tsx`:

| State Variable | Type | Description |
|---|---|---|
| `physicsJobId` | `string \| null` | Active simulation job ID |
| `physicsProgress` | `number` | 0–100 completion percentage |
| `physicsFrames` | `boolean[] \| null` | Resolved frame array post-simulation |
| `optimizationJobId` | `string \| null` | Active optimization job ID |
| `optimizationProgress` | `number` | 0–100 completion percentage |
| `optimizationLogs` | `string[]` | Live generation log lines |

Handlers: `handleRunPhysics()`, `handleOptimizeTopology()`.

Polling interval: **1500ms** via `setInterval` / `useEffect` cleanup.

---

## Local Development Notes

> [!TIP]
> On macOS without NVIDIA CUDA, the simulation worker runs in **mock mode** automatically. The pipeline still exercises the full HTTP→Context→Polling loop — only the PPF computation itself is synthetic. This makes frontend development fully possible without GPU hardware.

To switch to real GPU execution, replace the `thread.start()` call in `simulation_tasks.py` with:
```python
@celery.task(queue='gpu_tasks')
def run_simulation_task(job_id, slug, script):
    _run_worker_simulation(job_id, slug, script)
```
And set `CELERY_BROKER_URL` + `CELERY_RESULT_BACKEND` in `.env`.

---

## Production Deployment

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
