# Glia Diagnostic Tools

Open source stethoscope and otoscope medical hardware

**Slug**: `glia-diagnostic`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `stethoscope` | Stethoscope | `diagnostic.scad` | head |
| `otoscope` | Otoscope | `diagnostic.scad` | specula |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `diaphragm_size_mm` | number | 44 | 30–50 | diaphragm_size_mm |
| `speculum_size_mm` | number | 4 |  | speculum_size_mm |
| `render_mode` | number | 0 |  | render_mode |

## Parts

| ID | Label | Default Color |
|---|---|---|
| `head` | Head | `` |
| `specula` | Specula | `` |

## Render Estimates

- **base_time**: 5
- **per_unit**: 2
- **per_part**: 8
- **fn_factor**: 32
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
