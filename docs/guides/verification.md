# Verification Suite Documentation

The project maintains a rigorous quality assurance process using the config-driven verification engine `tests/verify_design.py`.

The verification engine uses `trimesh` to analyze exported STL geometry. Checks are organized into **manufacturing stages** (`geometry`, `printability`, `assembly_fit`), configurable per **mode** and per **part** from `project.json`.

## Two verification systems, and which one gates CI

This page documents `tests/verify_design.py`, the **in-repo, manifest-driven** suite invoked
by `POST /api/verify` and the Studio's "Run Verification Suite" button. It is not the gate a
cartridge has to clear to merge.

That gate is the **keystone**, `hyperobjects-spec`, consumed as a pinned external package by
the `spec-conformance` job in `.github/workflows/ci.yml` and by the nightly sweep in
`.github/workflows/spec-nightly.yml`. Both pin the **same commit**,
`3aa57133186573b26279417f8de59b6c47ed9027`, and deliberately never a floating tag: the bar
the platform clears must be the bar the commons cleared, so this pin tracks `SPEC_PIN` in
`solid-hyperobjects` / `soft-hyperobjects`. The keystone repo went public on 2026-09-05, so
fetching it needs no token.

What each lane runs:

| Lane | Command | Scope |
| :-- | :-- | :-- |
| `spec-conformance` (every PR) | `y4d-spec check projects/*/` | structural, whole commons |
| `spec-conformance` (every PR) | `y4d-spec check --render --parity -v <changed>` | real renders, **only the cartridges the PR touched** |
| `spec-nightly` | the same render sweep, chunked into groups | whole commons |
| `spec-conformance` | `scripts/qa/check_render_env.py` | the runner image's OpenSCAD must match `y4d_spec.render_environment` |

Per-PR renders are scoped to changed cartridges because a full sweep is hours at 15–25 s per
part; the nightly carries the rest and aggregates a completeness check plus a rows-based
verdict, turning a red sweep into **one** tracking issue rather than a per-cartridge storm.
`check_render_env.py` stands itself down with a one-line notice if the pinned spec predates
the `render_environment` module — but a module that is present and *broken* still fails the
job. Only a missing one is tolerated.

`--parity` asks the keystone to compare a cartridge's two kernels where it has both. The
keystone owns that policy object and its schema (`enabled`, `tolerance`, `reason`,
`placement`) — including the requirement that an exemption carry a written reason rather
than merely switching the check off. Because the schema lives in the keystone rather than in
`packages/schemas/`, this page does not restate its field semantics; read them at the pinned
commit. Two cartridges carry reasoned per-part exemptions today.

**Graph cartridges are outside all of this.** `y4d-spec` renders `.py`, `.cq` and `.scad`
only, so a `.graph.json` mode gets no render bar and no nightly row — see
[graph-cartridges.md](graph-cartridges.md#what-is-not-verified-yet). Closing that hole is
lane G-SPEC in [`ROADMAP.md`](../../ROADMAP.md#the-node-based-geometry-programme-waves-df-s).

## The in-repo suite

For Hyperobjects, an additional **Geometric Parity** check compares output across the OpenSCAD and CadQuery engines. The check CI enforces is `tests/scripts/geometric_regression.py` (the `test-geometric-parity` job). `scripts/qa/verify_parity.py` is a separate, local-only tool for the same comparison; no workflow runs it, and as of 2026-09-02 (after #115) it reports 18 of 28 comparable mode pairs passing — see [dual-engine.md](../architecture/dual-engine.md#the-geometric-parity-guarantee).

## Script: `tests/verify_design.py`

### Usage
```bash
# Verify with built-in defaults (backward compat)
python3 tests/verify_design.py path/to/model.stl

# Verify with explicit config (used by backend route)
python3 tests/verify_design.py path/to/model.stl '{"stages": {...}}'
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All checks passed |
| `1` | One or more checks failed |
| `2` | Usage error |

### Output Format

The script outputs human-readable lines followed by a `===JSON===` marker and structured JSON data:

```
--- geometry ---
[PASS] watertight: watertight
[PASS] body_count: 1 body
[PASS] dimensions: 20.0x20.0x19.8mm
[PASS] facet_count: 832 facets
--- printability ---
[PASS] thin_wall: min 1.2mm (threshold 0.8mm)
[PASS] overhang: max 38° (threshold 45°)
[PASS] min_feature_size: min 1.5mm (threshold 0.4mm)
===JSON===
{"passed": true, "failures": [], "stages": {...}}
```

The backend route parses everything after `===JSON===` for structured results; the human-readable part goes to `output` for UI display.

## Verification Stages

### `geometry` — Structural Integrity

| Check | Description | Config Keys |
|-------|-------------|-------------|
| `watertight` | Mesh is a closed manifold (no holes) | `enabled` |
| `body_count` | Mesh is a single continuous solid | `enabled`, `expected` (default: 1) |
| `dimensions` | Bounding box within expected range | `enabled`, `xy_tolerance_mm`, `z_ratio_min`, `z_ratio_max` |
| `facet_count` | Geometric complexity above threshold | `enabled`, `min_facets` (default: 400) |

### `printability` — FDM Manufacturability

| Check | Description | Config Keys |
|-------|-------------|-------------|
| `thin_wall` | No walls thinner than threshold | `enabled`, `min_thickness_mm` (default: 0.8) |
| `overhang` | No unsupported overhangs beyond angle | `enabled`, `max_angle_deg` (default: 45) |
| `min_feature_size` | No features smaller than nozzle can print | `enabled`, `min_size_mm` (default: 0.4) |

### `assembly_fit` — Assembly Validation

| Check | Description | Config Keys |
|-------|-------------|-------------|
| `collision` | Parts don't collide after assembly transform | `enabled`, `transform.rotate_x_deg`, `transform.rotate_z_deg` |

## Configuration

### Manifest Structure

Add a `verification` section to `project.json`:

```json
{
  "verification": {
    "stages": {
      "geometry": {
        "checks": {
          "watertight": { "enabled": true },
          "body_count": { "enabled": true, "expected": 1 },
          "dimensions": { "enabled": true, "xy_tolerance_mm": 0.5, "z_ratio_min": 0.9, "z_ratio_max": 1.1 },
          "facet_count": { "enabled": true, "min_facets": 400 }
        }
      },
      "printability": { ... },
      "assembly_fit": { ... }
    },
    "mode_overrides": {
      "unit": { "stages": ["geometry", "printability"] },
      "assembly": { "stages": ["geometry", "printability", "assembly_fit"] },
      "grid": {
        "stages": ["geometry", "printability"],
        "part_overrides": {
          "rods": { "geometry.facet_count": { "min_facets": 50 }, "geometry.dimensions": { "enabled": false } }
        }
      }
    }
  }
}
```

### Configuration Hierarchy

1. **`stages`**: Global check registry with default thresholds
2. **`mode_overrides.{mode}.stages`**: Which stages run for that mode (e.g., `unit` skips `assembly_fit`)
3. **`mode_overrides.{mode}.part_overrides`**: Per-part threshold tweaks using dot-notation keys (e.g., `geometry.facet_count`)

### Backward Compatibility

- If the `verification` section is missing from `project.json`, the script uses built-in defaults with all checks enabled.
- If the config JSON argument is omitted from the CLI, built-in defaults are used.
- For Hyperobjects, `scripts/qa/verify_parity.py` compares a mode's two kernel outputs. It is run by hand, not on a schedule and not by any workflow. It compares a mode only when both kernels really exist for it (a present `.scad` plus a present `.py`, declared or inferred from the `.scad` sibling), mirroring `generate_commons_catalog::_engine_support`; a CadQuery-only mode whose `scad_file` is a `.py` placeholder is skipped and counted apart from failures. For a comparable pair it decides parity as:
    - **AABB Alignment**: bounding-box extents must match within the tolerance. Hard.
    - **Relative Volume Tolerance**: up to 2% difference for complex kerneled meshes (CSG vs B-Rep). Hard.
    - **Hausdorff Distance Proxy**: up to 0.5mm divergence for tessellation noise. Reported as a warning only — it never changes the verdict.
    - A mode declaring no `cq_file` is skipped; a mode naming a file that is not on disk is a failure.
  Its decision logic is covered by `scripts/tests/test_verify_parity.py`, which runs in the `backend` job.

## Web Interface Integration

The verification suite is invoked from the [Web Interface](../architecture/web_interface.md) via the "Run Verification Suite" button. The backend endpoint `POST /api/verify` accepts a `mode` field (e.g., `"unit"`, `"assembly"`, `"grid"`) and an optional `project` slug for multi-project routing.

The backend:
1. Loads the manifest for the project
2. Resolves the verification config for the mode via `get_verification_config()`
3. Applies per-part overrides via `resolve_part_config()`
4. Passes the resolved config as a JSON argument to the verification script
5. Parses structured JSON output for the API response

[Back to Index](../index.md)
