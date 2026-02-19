# Glia Diagnostic Tools

Open source stethoscope and otoscope medical hardware by the Glia Project

Official Visualizer and Configurator: Yantra4D

*Hardware médico de código abierto: estetoscopio y otoscopio del Proyecto Glia

Visualizador y configurador oficial: Yantra4D*

**Version**: 1.0.0  
**Slug**: `glia-diagnostic`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `stethoscope` | Stethoscope | `diagnostic.scad` | head |
| `otoscope` | Otoscope | `diagnostic.scad` | specula |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `diaphragm_size_mm` | slider | 44 | 30–50 | Diameter of the stethoscope diaphragm |
| `speculum_size_mm` | slider | 4 | 2.5–5 (step 0.5) | Tip diameter of the otoscope speculum (2.5, 3, 4, or 5 mm) |
| `fn` | slider | 0 | 0–64 (step 8) | fn |

## Parts

| ID | Label | Default Color |
|---|---|---|
| `head` | Head | `#e5e7eb` |
| `specula` | Specula | `#d1d5db` |

## Render Estimates

- **base_time**: 5
- **per_unit**: 2
- **per_part**: 8
- **fn_factor**: 32
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
