# KeyV2 Keycaps

Customizable mechanical keyboard keycaps with multiple profiles and stems

*Teclas personalizables para teclados mecánicos con múltiples perfiles y vástagos*

**Version**: 1.0.0  
**Slug**: `keyv2`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `keycap` | Keycap | `keycap.scad` | keycap |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `profile_id` | slider | 0 | 0–4 | Keycap profile family |
| `row_id` | slider | 1 | 1–4 | Sculpted row number (affects tilt) |
| `key_size_id` | slider | 0 | 0–3 | Keycap width in standard units |
| `stem_type_id` | slider | 0 | 0–2 | Switch stem type |
| `legend_enabled` | checkbox | No |  | Add text legend to keycap top |
| `legend_text` | text | A |  | Character or text for the legend |
| `font_size` | slider | 6 | 3–10 (step 0.5) | Legend font size in mm |
| `dish_depth` | slider | 1 | 0–3 (step 0.25) | Depth of the concave top dish |
| `wall_thickness` | slider | 3 | 1.5–5 (step 0.25) | Shell wall thickness |
| `keytop_thickness` | slider | 1 | 0.5–2 (step 0.25) | Thickness of keycap top surface |
| `stem_slop` | slider | 0.35 | 0.1–0.6 (step 0.05) | Extra clearance for stem fit |
| `fn` | slider | 0 | 0–64 (step 8) | Circle smoothness (0=auto) |

## Presets

- **Cherry Row 3 (1u)**
  `profile_id`=0, `row_id`=3, `key_size_id`=0
- **DSA Uniform**
  `profile_id`=1, `row_id`=1, `key_size_id`=0
- **SA Sculpted Row 3**
  `profile_id`=2, `row_id`=3, `key_size_id`=0

## Parts

| ID | Label | Default Color |
|---|---|---|
| `keycap` | Keycap | `#e879f9` |

## Render Estimates

- **base_time**: 5
- **per_unit**: 1
- **per_part**: 8
- **fn_factor**: 64
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 45

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
