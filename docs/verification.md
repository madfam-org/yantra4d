# Verification Suite Documentation

The project maintains a rigorous quality assurance process using the config-driven verification engine `tests/verify_design.py`.

The verification engine uses `trimesh` to analyze exported STL geometry. Checks are organized into **manufacturing stages** (`geometry`, `printability`, `assembly_fit`), configurable per **mode** and per **part** from `project.json`.

For Hyperobjects, an additional **Geometric Parity** check is enforced via `scripts/verify_parity.py` to ensure identical output across OpenSCAD and CadQuery engines.

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
- For Hyperobjects, the `scripts/verify_parity.py` logic is invoked periodically. It supports:
    - **AABB Alignment**: Exact matching of bounding box extents.
    - **Relative Volume Tolerance**: Allows up to 2% difference for complex kerneled meshes (CSG vs B-Rep).
    - **Hausdorff Distance Proxy**: Allows up to 0.5mm divergence for tessellation noise.

## Web Interface Integration

The verification suite is invoked from the [Web Interface](./web_interface.md) via the "Run Verification Suite" button. The backend endpoint `POST /api/verify` accepts a `mode` field (e.g., `"unit"`, `"assembly"`, `"grid"`) and an optional `project` slug for multi-project routing.

The backend:
1. Loads the manifest for the project
2. Resolves the verification config for the mode via `get_verification_config()`
3. Applies per-part overrides via `resolve_part_config()`
4. Passes the resolved config as a JSON argument to the verification script
5. Parses structured JSON output for the API response

[Back to Index](./index.md)
