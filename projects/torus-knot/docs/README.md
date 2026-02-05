# Torus Knot Sculpture

Generative torus knot sculptures using dotSCAD and BOSL2

*Esculturas de nudos toroidales generativas usando dotSCAD y BOSL2*

**Version**: 0.1.0  
**Slug**: `torus-knot`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `sculpture` | Sculpture | `qubic_torus_knot.scad` | knot |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `p` | slider | 2 | 1–7 | Number of times the knot winds around the torus hole |
| `q` | slider | 3 | 2–11 | Number of times the knot winds around the axis of rotation |
| `tube_radius` | slider | 4 | 1–12 (step 0.5) | Cross-section radius of the knot |
| `torus_radius` | slider | 30 | 15–60 (step 5) | Main radius of the torus defining the knot |
| `segments` | slider | 120 | 40–300 (step 10) | Curve smoothness — more segments = smoother but slower |
| `scale_factor` | slider | 1.0 | 0.5–2.0 (step 0.1) | Global scale factor |

## Presets

- **Trefoil**
  `p`=2, `q`=3, `tube_radius`=4, `torus_radius`=30, `segments`=120
- **Cinquefoil**
  `p`=2, `q`=5, `tube_radius`=3, `torus_radius`=35, `segments`=180
- **Solomon's Seal**
  `p`=2, `q`=7, `tube_radius`=2.5, `torus_radius`=40, `segments`=200
- **Figure Eight**
  `p`=3, `q`=5, `tube_radius`=3.5, `torus_radius`=30, `segments`=160
- **Thick Trefoil**
  `p`=2, `q`=3, `tube_radius`=8, `torus_radius`=40, `segments`=100

## Parts

| ID | Label | Default Color |
|---|---|---|
| `knot` | Knot | `#e74c3c` |

## Constraints

- `tube_radius >= 1.5` — Minimum tube radius for FDM printing (error)
- `tube_radius < torus_radius * 0.3` — Tube too thick for torus radius — may self-intersect (error)
- `segments >= 80` — Few segments may cause visible edges (warning)

## Assembly Steps

1. **Print the sculpture**
   Requires supports. 0.2mm layers, 15% infill. Orient to minimize supports
2. **Remove supports and sand**
   Sand support marks. 220 grit then 400 grit for smooth finish

## Render Estimates

- **base_time**: 15
- **per_unit**: 2
- **per_part**: 15
- **fn_factor**: 64
- **wasm_multiplier**: 6
- **warning_threshold_seconds**: 120

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
