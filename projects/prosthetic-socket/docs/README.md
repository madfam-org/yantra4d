# Parametric Prosthetic Socket

Customizable socket for lower-limb prosthetics — Voronoi patterns for breathability and light weight

*Socket personalizable para prótesis de miembro inferior — patrones Voronoi para transpirabilidad y ligereza*

**Version**: 1.0.0  
**Slug**: `prosthetic-socket`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `transtibial_socket` | Transtibial Socket | `socket.scad` | socket_shell |
| `transfemoral_socket` | Transfemoral Socket | `socket.scad` | socket_shell |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `amputation_level` | slider | 0 | 0–1 | 0=Below Knee (Transtibial), 1=Above Knee (Transfemoral) |
| `circumference_top` | slider | 350 | 200–600 (step 10) | Proximal circumference of the residual limb |
| `circumference_bottom` | slider | 250 | 150–500 (step 10) | Distal circumference of the residual limb |
| `length` | slider | 300 | 150–500 (step 10) | length |
| `voronoi_density` | slider | 10 | 5–20 | Higher = more, smaller holes; Lower = fewer, larger holes |
| `wall_thickness` | slider | 4 | 3–8 (step 0.5) | wall_thickness |
| `fn` | slider | 0 | 0–64 (step 8) | fn |

## Presets

- **Child Below-Knee (Small)**
  `amputation_level`=0, `circumference_top`=280, `circumference_bottom`=200, `length`=200
- **Adult Below-Knee (Medium)**
  `amputation_level`=0, `circumference_top`=350, `circumference_bottom`=250, `length`=300
- **Adult Above-Knee (Large)**
  `amputation_level`=1, `circumference_top`=450, `circumference_bottom`=350, `length`=400

## Parts

| ID | Label | Default Color |
|---|---|---|
| `socket_shell` | Socket Shell | `#fcd34d` |

## Render Estimates

- **base_time**: 5
- **per_unit**: 2
- **per_part**: 8
- **fn_factor**: 32
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
