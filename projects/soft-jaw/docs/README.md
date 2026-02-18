# Parametric Vise Soft Jaw

Custom soft jaws for Kurt and machine vises — parametric gripping surfaces

*Mordazas blandas personalizadas para tornillos Kurt y de máquina — superficies de agarre paramétricas*

**Version**: 1.0.0  
**Slug**: `soft-jaw`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `Standard` | Soft Jaw | `soft_jaw.scad` | jaw_body |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `vise_model` | slider | 0 | 0–2 | 0=Kurt DX6, 1=Orange Vise, 2=Tormach 5" |
| `jaw_width` | slider | 6 | 4–10 | Width of the jaw in inches |
| `jaw_height` | slider | 1.735 | 1.0–3.0 (step 0.125) | jaw_height |
| `jaw_thickness` | slider | 0.75 | 0.5–2.0 (step 0.125) | jaw_thickness |
| `face_pattern` | slider | 0 | 0–3 | 0=smooth, 1=prismatic (V-groove), 2=grid (knurled), 3=step (parallels) |
| `magnet_pockets` | checkbox | Yes |  | Pockets for 10x3mm magnets on back face |
| `fn` | slider | 0 | 0–64 (step 8) | fn |

## Presets

- **Kurt DX6 Prismatic (Round Stock)**
  `vise_model`=0, `face_pattern`=1, `jaw_width`=6
- **Kurt DX6 Smooth (Mar-free)**
  `vise_model`=0, `face_pattern`=0, `jaw_width`=6
- **Orange Vise 6" Grid**
  `vise_model`=1, `face_pattern`=2, `jaw_width`=6

## Parts

| ID | Label | Default Color |
|---|---|---|
| `jaw_body` | Jaw Body | `#a8a29e` |

## Render Estimates

- **base_time**: 5
- **per_unit**: 2
- **per_part**: 8
- **fn_factor**: 32
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
