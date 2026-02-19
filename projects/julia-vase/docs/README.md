# Julia Vase

Parametric twisted vase with sinusoidal profile modulation inspired by Julia set fractals

*Jarrón paramétrico con torsión y modulación sinusoidal inspirado en fractales de conjuntos de Julia*

**Version**: 1.0.0  
**Slug**: `julia-vase`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `vase` | Vase | `vase.scad` | vase |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `height` | slider | 150 | 50–300 (step 5) | Total vase height |
| `base_radius` | slider | 40 | 15–80 | Radius at the base of the vase |
| `twist_angle` | slider | 360 | 0–720 (step 15) | Total rotation angle from base to top |
| `wave_frequency` | slider | 5 | 1–12 | Number of wave lobes around perimeter |
| `wave_amplitude` | slider | 10 | 0–25 | Depth of wave modulation |
| `wall_thickness` | slider | 2 | 0.8–4 (step 0.2) | Vase wall thickness |
| `fn` | slider | 64 | 0–128 (step 8) | Angular resolution for curves |
| `resolution` | slider | 100 | 20–200 (step 10) | Number of vertical layers in the mesh |

## Presets

- **Smooth Cylinder**
  `twist_angle`=0, `wave_amplitude`=0
- **Twisted Spiral**
  `twist_angle`=360, `wave_amplitude`=5
- **Ripple Vase**
  `twist_angle`=90, `wave_frequency`=8, `wave_amplitude`=15
- **Fractal Complex**
  `twist_angle`=540, `wave_frequency`=6, `wave_amplitude`=12

## Parts

| ID | Label | Default Color |
|---|---|---|
| `vase` | Vase | `` |

## Constraints

- `` — Wall thickness must be at least 0.8mm for printability (error)
- `` — Wave amplitude should be less than 1/3 of base radius to avoid self-intersection (warning)

## Render Estimates

- **base_time**: 10
- **per_unit**: 2
- **per_part**: 10
- **fn_factor**: 128
- **wasm_multiplier**: 5
- **warning_threshold_seconds**: 120

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
