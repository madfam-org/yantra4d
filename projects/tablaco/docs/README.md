# Tablaco Studio

Interlocking half-cube construction system with snap-fit mechanism and grid assembly

*Sistema de construcción de medio-cubos entrelazados con mecanismo de ensamble a presión y retícula*

**Version**: 1.0.0  
**Slug**: `tablaco`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `unit` | Unit | `half_cube.scad` | main |
| `assembly` | Assembly | `assembly.scad` | bottom, top |
| `grid` | Grid | `tablaco.scad` | bottom, top, rods, stoppers, tubing |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `size` | slider | 20.0 | 10–30 (step 0.5) | Width/height of each unit cube in millimeters |
| `thick` | slider | 2.5 | 0.6–4 (step 0.1) | Wall thickness of the cube |
| `rod_D` | slider | 3.0 | 1.0–4 (step 0.1) | Diameter of connecting rods |
| `clearance` | slider | 0.2 | 0.05–0.4 (step 0.05) | Radial clearance for rod bore — increase for looser fit |
| `fit_clear` | slider | 0 | 0–0.4 (step 0.05) | Gap between interlocking cube faces — currently zeroed out (kept for future use) |
| `show_base` | checkbox | Yes |  | Show or hide the base plate |
| `show_walls` | checkbox | Yes |  | Show or hide the side walls |
| `show_wall_left` | checkbox | Yes |  | Show or hide the left mitered wall |
| `show_wall_right` | checkbox | Yes |  | Show or hide the right mitered wall |
| `show_mech` | checkbox | Yes |  | Show or hide the interlocking mechanism |
| `show_mech_base_ring` | checkbox | Yes |  | Show or hide the mechanism base ring |
| `show_mech_pillars` | checkbox | Yes |  | Show or hide the dual-quadrant pillars |
| `show_mech_snap_beams` | checkbox | Yes |  | Show or hide the cantilever snap-fit beams |
| `show_letter` | checkbox | Yes |  | Show or hide embossed letters on walls |
| `show_bottom` | checkbox | Yes |  | Show or hide bottom half-cube units |
| `show_bottom_base` | checkbox | Yes |  | Show or hide bottom unit's base plate |
| `show_bottom_walls` | checkbox | Yes |  | Show or hide bottom unit's walls |
| `show_bottom_mech` | checkbox | Yes |  | Show or hide bottom unit's mechanism |
| `show_bottom_letter` | checkbox | Yes |  | Show or hide bottom unit's letters |
| `show_bottom_wall_left` | checkbox | Yes |  | Show or hide bottom unit's left wall |
| `show_bottom_wall_right` | checkbox | Yes |  | Show or hide bottom unit's right wall |
| `show_bottom_mech_base_ring` | checkbox | Yes |  | Show or hide bottom unit's mechanism base ring |
| `show_bottom_mech_pillars` | checkbox | Yes |  | Show or hide bottom unit's pillars |
| `show_bottom_mech_snap_beams` | checkbox | Yes |  | Show or hide bottom unit's snap beams |
| `show_top` | checkbox | Yes |  | Show or hide top half-cube units |
| `show_top_base` | checkbox | Yes |  | Show or hide top unit's base plate |
| `show_top_walls` | checkbox | Yes |  | Show or hide top unit's walls |
| `show_top_mech` | checkbox | Yes |  | Show or hide top unit's mechanism |
| `show_top_letter` | checkbox | Yes |  | Show or hide top unit's letters |
| `show_top_wall_left` | checkbox | Yes |  | Show or hide top unit's left wall |
| `show_top_wall_right` | checkbox | Yes |  | Show or hide top unit's right wall |
| `show_top_mech_base_ring` | checkbox | Yes |  | Show or hide top unit's mechanism base ring |
| `show_top_mech_pillars` | checkbox | Yes |  | Show or hide top unit's pillars |
| `show_top_mech_snap_beams` | checkbox | Yes |  | Show or hide top unit's snap beams |
| `show_rods` | checkbox | Yes |  | Show or hide connecting rods |
| `show_stoppers` | checkbox | Yes |  | Show or hide rod stoppers |
| `letter_bottom` | text | V |  | Character on bottom unit faces |
| `letter_top` | text | F |  | Character on top unit faces |
| `letter_emboss` | checkbox | No |  | Raised letters (on) or carved letters (off) |
| `letter_depth` | slider | 0.5 | 0.1–1.0 (step 0.1) | How deep letters are carved or how high they are embossed |
| `letter_size` | slider | 10 | 6–14 | Font size of embossed/carved letters on walls |
| `rows` | slider | 2 | 1–15 | Number of rows in the grid |
| `cols` | slider | 2 | 1–15 | Number of columns in the grid |
| `rod_extension` | slider | 10 | 0–20 | Rod length protruding beyond stoppers |
| `rotation_clearance` | slider | 2 | 0.5–3.5 (step 0.5) | Gap between cubes in grid — controls free rotation space |
| `tubing_H` | slider | 2 | 0.5–3.5 (step 0.5) | Height of tubing spacers between cubes |
| `tubing_wall` | slider | 1 | 0.5–2 (step 0.25) | Wall thickness of tubing spacers |
| `show_tubing` | checkbox | Yes |  | Show or hide tubing spacers |

## Presets

- **Standard (20mm)**
  `size`=20, `thick`=2.5, `rod_D`=3.0, `clearance`=0.2, `fit_clear`=0, `letter_depth`=0.5, `letter_size`=10, `rod_extension`=10, `rotation_clearance`=2, `tubing_H`=2, `tubing_wall`=1
- **Mini (5mm)**
  `size`=5, `thick`=0.8, `rod_D`=1.5, `clearance`=0.15, `fit_clear`=0, `letter_depth`=0.2, `letter_size`=2, `rod_extension`=2, `rotation_clearance`=0.5, `tubing_H`=1, `tubing_wall`=0.5

## Parts

| ID | Label | Default Color |
|---|---|---|
| `main` | Color | `#e5e7eb` |
| `bottom` | Bottom Unit | `#ffffff` |
| `top` | Top Unit | `#000000` |
| `rods` | Rods | `#808080` |
| `stoppers` | Stoppers | `#ffd700` |
| `tubing` | Tubing | `#ff8c00` |

## Assembly Steps

1. **Print bottom half**
   Flat side down, 0.2mm layers, 20% infill
2. **Print top half**
   Same settings. Snap mechanism needs supports.
3. **Snap together**
   Align tabs and press firmly until you hear a click.

## Render Estimates

- **base_time**: 5
- **per_unit**: 1.5
- **fn_factor**: 64
- **per_part**: 8
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
