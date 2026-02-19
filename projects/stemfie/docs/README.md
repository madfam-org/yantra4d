# STEMFIE

Modular construction system for education and prototyping

Official Visualizer and Configurator: Yantra4D

*Sistema de construccion modular para educacion y prototipado

Visualizador y configurador oficial: Yantra4D*

**Version**: 1.0.0  
**Slug**: `stemfie`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `beam` | Beam | `beam.scad` | beam |
| `brace` | Brace | `brace.scad` | brace |
| `fastener` | Fastener | `fastener.scad` | fastener |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `length_units` | slider | 4 | 1–20 | Length in block units (1 BU = 12.5 mm) |
| `width_units` | slider | 1 | 1–4 | Width in block units |
| `height_units` | slider | 1 | 1–4 | Height in block units |
| `holes_x` | checkbox | Yes |  | Enable holes along X axis |
| `holes_y` | checkbox | Yes |  | Enable holes along Y axis |
| `holes_z` | checkbox | Yes |  | Enable holes along Z axis |
| `arm_a_units` | slider | 3 | 1–10 | Length of first arm in block units |
| `arm_b_units` | slider | 3 | 1–10 | Length of second arm in block units |
| `thickness_units` | slider | 1 | 1–2 | Brace thickness multiplier (1 = 0.25 BU) |
| `holes_enabled` | checkbox | Yes |  | Enable connection holes in the brace |
| `fastener_type_id` | slider | 0 | 0–1 | 0 = Pin fastener, 1 = Shaft fastener |
| `fn` | slider | 0 | 0–64 (step 8) | 0 = auto; higher = more detail but slower |

## Presets

- **5-Unit Beam**
  `length_units`=5
- **90-Degree Brace**
  `arm_a_units`=3, `arm_b_units`=3
- **Standard Pin**
  `length_units`=2, `fastener_type_id`=0

## Parts

| ID | Label | Default Color |
|---|---|---|
| `beam` | Beam | `#4ade80` |
| `brace` | Brace | `#facc15` |
| `fastener` | Fastener | `#94a3b8` |

## Render Estimates

- **base_time**: 3
- **per_unit**: 1
- **per_part**: 5
- **fn_factor**: 32
- **wasm_multiplier**: 2
- **warning_threshold_seconds**: 30

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
