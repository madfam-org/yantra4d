# Microscope Slide Holder

Parametric 3D-printable microscope slide holder rack

*Porta-laminillas parametrico para microscopio, imprimible en 3D*

**Version**: 0.1.0  
**Slug**: `slide-holder`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `holder` | Slide Holder | `yantra4d_slide_holder.scad` | holder |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `slides` | slider | 10 | 1–30 | Number of slide slots in the rack |
| `thickness` | slider | 1 | 0.5–3 (step 0.1) | Thickness of microscope slides (standard: 1mm) |
| `length` | slider | 76.2 | 50–100 (step 0.1) | Length of microscope slides (standard: 75–76.2mm) |
| `width` | slider | 25 | 15–35 (step 0.5) | Width of microscope slides (standard: 25–26mm) |
| `fn` | slider | 0 | 0–64 (step 8) | 0 = auto |

## Presets

- **Standard (10 slides)**
  `slides`=10, `thickness`=1, `length`=76.2, `width`=25
- **Compact (5 slides)**
  `slides`=5, `thickness`=1, `length`=76.2, `width`=25
- **Large (20 slides)**
  `slides`=20, `thickness`=1, `length`=76.2, `width`=25
- **Thick Slides (2mm)**
  `slides`=10, `thickness`=2, `length`=76.2, `width`=25
- **Half-Size (short slides)**
  `slides`=10, `thickness`=1, `length`=50, `width`=20

## Parts

| ID | Label | Default Color |
|---|---|---|
| `holder` | Slide Holder | `#4a90d9` |

## Constraints

- `slides >= 1` — At least 1 slide slot is required (error)
- `thickness > 0` — Thickness must be greater than 0 (error)
- `length > width` — Length must be greater than width (warning)
- `slides <= 25` — More than 25 slides may require a large print bed (warning)

## Assembly Steps

1. **Print the slide holder**
   0.2mm layers, 20–30% infill. PLA or PETG recommended
2. **Insert microscope slides**
   Slide microscope slides in from the top into the slots

## Render Estimates

- **base_time**: 3
- **per_unit**: 1
- **per_part**: 5
- **fn_factor**: 32
- **wasm_multiplier**: 2
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
