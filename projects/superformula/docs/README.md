# Superformula Vase

Generative vases based on mathematical superformulas using dotSCAD

*Jarrones generativos basados en superformulas matematicas usando dotSCAD*

**Version**: 0.1.0  
**Slug**: `superformula`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `vase` | Vase | `superformula.scad` | vase |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `m1` | slider | 5 | 1–20 | Number of lobes/points in the shape |
| `m2` | slider | 5 | 1–20 | Vertical symmetry of the shape |
| `n1` | slider | 2 | 0.1–10 (step 0.1) | Superformula N1 parameter — controls curvature |
| `n2` | slider | 7 | 0.1–20 (step 0.1) | Superformula N2 parameter |
| `n3` | slider | 7 | 0.1–20 (step 0.1) | Superformula N3 parameter |
| `height` | slider | 100 | 40–200 (step 5) | Height of the vase |
| `wall_thickness` | slider | 2 | 1–5 (step 0.5) | Vase wall thickness |
| `radius` | slider | 40 | 20–80 (step 5) | Base radius of the superformula |
| `fn` | slider | 0 | 0–64 (step 8) | 0 = auto |

## Presets

- **Starfish**
  `m1`=5, `m2`=5, `n1`=2, `n2`=7, `n3`=7, `height`=100, `wall_thickness`=2
- **Flower**
  `m1`=8, `m2`=8, `n1`=0.5, `n2`=0.5, `n3`=8, `height`=120, `wall_thickness`=2
- **Alien Egg**
  `m1`=3, `m2`=3, `n1`=4.5, `n2`=10, `n3`=10, `height`=80, `wall_thickness`=2.5
- **Sea Urchin**
  `m1`=12, `m2`=12, `n1`=1, `n2`=1, `n3`=1, `height`=60, `wall_thickness`=1.5
- **Organic Blob**
  `m1`=6, `m2`=6, `n1`=1, `n2`=3, `n3`=5, `height`=90, `wall_thickness`=2

## Parts

| ID | Label | Default Color |
|---|---|---|
| `vase` | Vase | `#9b59b6` |

## Constraints

- `wall_thickness >= 1` — Minimum 1mm wall thickness for FDM (error)
- `height >= 40` — Minimum height for stability (warning)

## Assembly Steps

1. **Print the vase**
   Vase (spiralize) mode recommended in slicer. 0.2mm layers
2. **Sand and seal (optional)**
   For water use, seal interior with epoxy resin

## Render Estimates

- **base_time**: 12
- **per_unit**: 2
- **per_part**: 12
- **fn_factor**: 64
- **wasm_multiplier**: 5
- **warning_threshold_seconds**: 90

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
