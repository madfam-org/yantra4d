# Implicit SDF Engine Guide

This guide explains how to use Yantra4D's native **Implicit SDF (Signed Distance
Field) Engine** — the third kernel in the Tri-Kernel system, alongside OpenSCAD
and CadQuery.

---

## What Is the Implicit Engine?

The Implicit Engine generates **Triply Periodic Minimal Surface (TPMS)** lattice
structures using volumetric SDF mathematics rather than constructive solid geometry
or B-Rep modeling. It evaluates a continuous mathematical scalar field across a
3D spatial domain, then extracts the isosurface using Marching Cubes.

This produces geometries that:
- Are **topologically complex** (high surface area to volume ratio)
- Are **impossible to model in traditional CSG/B-Rep** without thousands of primitives
- Directly respond to **Material Hyperobject TDA parameters** (Euler characteristic
  drives frequency adaptation)
- Enable **Digital Twin phase simulation** where thermal energy morphs the lattice
  geometry in real time

---

## Supported TPMS Topologies

| Topology ID | Name | Mathematical Form |
|---|---|---|
| `0` (default) | **Gyroid** | sin(x)cos(y) + sin(y)cos(z) + sin(z)cos(x) = 0 |
| `1` | **Diamond** | sin(x)sin(y)sin(z) + sin(x)cos(y)cos(z) + cos(x)sin(y)cos(z) + cos(x)cos(y)sin(z) = 0 |
| `2` | **Schwarz-P** | cos(x) + cos(y) + cos(z) = 0 |

The topology is selected at runtime via the `topology_type` manifest parameter
(0, 1, or 2).

---

## `project.json` Configuration

### Minimal Example

```json
{
  "project": {
    "name": "Gyroid Lattice",
    "slug": "my-gyroid",
    "version": "1.0.0",
    "thumbnail": "thumb.png",
    "tags": ["lattice", "tpms", "hyperobject"],
    "difficulty": "advanced",
    "engine": "implicit",
    "hyperobject": {
      "is_hyperobject": true,
      "domain": "industrial",
      "implicit_field": {
        "topology": "gyroid",
        "base_frequency": 5.0,
        "resolution": 64,
        "size": 20.0
      }
    }
  },
  "modes": [...],
  "parameters": [...],
  "parts": [...]
}
```

### `hyperobject.implicit_field` Config Block

| Field | Type | Default | Description |
|---|---|---|---|
| `topology` | `string` | `"gyroid"` | Fallback topology name (overridden at runtime by `topology_type` param) |
| `base_frequency` | `number` | `5.0` | Base spatial frequency of the TPMS field (higher = finer lattice cells) |
| `resolution` | `integer` | `64` | Voxel resolution per dimension (64³ = ~262k voxels; 128³ = ~2M — CPU intensive) |
| `size` | `number` | `20.0` | Physical domain size in mm (applied symmetrically on all axes) |

> **Tip:** `"engine": "implicit"` and the presence of `implicit_field` are
> equivalent and both valid. When both exist, `"engine": "implicit"` takes
> priority.

---

## Runtime Parameters

These manifest `parameters` entries are consumed by the Implicit Engine at render
time:

| Parameter `id` | Type | Effect |
|---|---|---|
| `topology_type` | `select` (0/1/2) | Overrides field topology at runtime |
| `frequency` | `slider` | Overrides `base_frequency` |
| `simulated_energy` | `slider` | Drives Digital Twin phase simulation (see below) |

---

## Material Hyperobject Integration

When a `target_material` is selected by the user, the render pipeline injects
the following parameters from the material's `material.json` into the implicit
field evaluation:

| Injected Param | Source | Effect on Implicit Engine |
|---|---|---|
| `tda_euler_characteristic` | `material.tda.euler_characteristic` | Shifts spatial frequency: `frequency += abs(euler) / 100.0`. A highly porous material (e.g., Formlabs Clear with euler=-584) produces a significantly denser lattice. |
| `mat_shrinkage_x` | `material.am_compensations.shrinkage.x` | Scales the spatial domain size, compensating for material contraction |
| `thermo_glass_transition_temp` | `material.thermodynamics.glass_transition_temp` | Sets the Tg threshold for Digital Twin collapse (see below) |

---

## Digital Twin Phase Simulation

The Implicit Engine includes a real-time **thermodynamic phase simulation**.
When `simulated_energy` (in °C) exceeds `thermo_glass_transition_temp`:

1. The material is modeled as crossing its glass transition
2. The Z-axis of the SDF domain is scaled down by a `degradation_factor`:
   ```
   overage = simulated_energy - Tg
   degradation_factor = max(0.1, 1.0 - (overage × 0.05))
   ```
3. The resulting mesh is structurally **"sagged"** — compressed along Z as if
   under gravity past Tg

This allows the 3D viewer to visualize how a printed hyperobject would behave
under heat exposure, directly informing material selection decisions.

**Example:** A gyroid printed in PETG (Tg=80°C) with `simulated_energy=100` →
`degradation_factor = max(0.1, 1.0 - (20 × 0.05)) = 0.0` → capped at 0.1,
meaning significant structural collapse visible in the viewport.

---

## MQTT Telemetry Integration

In production deployments with physical hardware, `simulated_energy` and other
thermal parameters can be driven by live MQTT sensor data rather than manual
slider input. See [MQTT telemetry bridge](../architecture/dual-engine.md) for
setup details, or use
`scripts/dev/mock_telemetry_publisher.py` for local simulation.

---

## Resolution Guidelines

| Resolution | Voxels | Render Time (CPU) | Use Case |
|---|---|---|---|
| 32 | 32K | < 1s | Fast preview / dev iteration |
| 64 | 262K | 2–8s | Standard quality preview |
| 96 | 884K | 10–30s | High quality preview |
| 128 | 2.1M | 30–120s | Export quality (triggers Docker backend) |

> **WASM Circuit Breaker:** Resolutions > 64 will typically exceed the browser
> WASM timeout and automatically fall back to the Docker backend renderer.
