# Fastener Generator

Parametric bolts and nuts with real threads

Official Visualizer and Configurator: Yantra4D

*Tornillos y tuercas paramétricas con roscas reales

Visualizador y configurador oficial: Yantra4D*

**Version**: 1.0.0  
**Slug**: `fasteners`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `` | Bolt | `bolt.scad` | bolt |
| `` | Nut | `nut.scad` | nut |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `diameter` | slider | 5 | 2–20 (step 0.5) | Nominal thread diameter |
| `length` | slider | 20 | 5–80 | Bolt shaft length excluding head |
| `pitch` | slider | 0.8 | 0.25–3 (step 0.05) | Distance between thread crests |
| `head_style_id` | slider | 0 | 0–2 | Bolt head shape |
| `head_diameter` | slider | 0 | 0–30 (step 0.5) | Override head diameter (0=auto) |
| `head_height` | slider | 0 | 0–15 (step 0.5) | Override head height (0=auto) |
| `nut_style_id` | slider | 0 | 0–2 | Nut shape |
| `width` | slider | 0 | 0–30 (step 0.5) | Override nut width (0=auto) |
| `height` | slider | 0 | 0–15 (step 0.5) | Override nut height (0=auto) |
| `thread_enabled` | checkbox | Yes |  | Generate real threads (slower) |
| `fn` | slider | 0 | 0–64 (step 8) | Circle smoothness (0=auto) |

## Presets

- **M3 Socket 20mm**
  `diameter`=3, `length`=20, `pitch`=0.5, `head_style_id`=1
- **M5 Hex 25mm**
  `diameter`=5, `length`=25, `pitch`=0.8, `head_style_id`=0
- **M8 Button 30mm**
  `diameter`=8, `length`=30, `pitch`=1.25, `head_style_id`=2

## Parts

| ID | Label | Default Color |
|---|---|---|
| `` | Bolt | `` |
| `` | Nut | `` |

## Constraints

- `` — Pitch must be less than diameter (error)
- `` — Length should be at least 1x diameter (warning)

## Render Estimates

- **base_time**: 8
- **per_unit**: 2
- **per_part**: 10
- **fn_factor**: 64
- **wasm_multiplier**: 4
- **warning_threshold_seconds**: 90

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
