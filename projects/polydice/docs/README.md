# PolyDice Generator

Parametric polyhedral dice generator for tabletop and RPG gaming

*Generador parametrico de dados polihedricos para juegos de mesa y RPG*

**Version**: 1.0.0  
**Slug**: `polydice`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `d4` | D4 (Tetrahedron) | `die.scad` | d4 |
| `d6` | D6 (Cube) | `die.scad` | d6 |
| `d8` | D8 (Octahedron) | `die.scad` | d8 |
| `d12` | D12 (Dodecahedron) | `die.scad` | d12 |
| `d20` | D20 (Icosahedron) | `die.scad` | d20 |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `die_size` | slider | 20 | 10–40 | Overall die size in millimeters |
| `font_depth` | slider | 0.6 | 0.2–1.5 (step 0.1) | Engraving depth of the numbers |
| `font_size` | slider | 6 | 3–12 (step 0.5) | Size of the numbers on each face |
| `rounding_corner` | slider | 0 | 0–5 (step 0.5) | Corner rounding radius |
| `rounding_edge` | slider | 0 | 0–3 (step 0.5) | Edge rounding radius |
| `fn` | slider | 0 | 0–64 (step 8) | 0 = auto; higher = more detail but slower |
| `dice_gradient` | slider | 0 | 0–1 | Gradient colors for two-tone dice (requires multi-material printing) |

## Presets

- **Standard D20**
  `die_size`=20, `font_depth`=0.6, `font_size`=6, `rounding_corner`=0, `rounding_edge`=0
- **Large Rounded D6**
  `die_size`=30, `rounding_corner`=2
- **Mini D8**
  `die_size`=12, `font_size`=4

## Parts

| ID | Label | Default Color |
|---|---|---|
| `d4` | D4 | `#e74c3c` |
| `d6` | D6 | `#3498db` |
| `d8` | D8 | `#2ecc71` |
| `d12` | D12 | `#9b59b6` |
| `d20` | D20 | `#f39c12` |

## Render Estimates

- **base_time**: 5
- **per_unit**: 1
- **per_part**: 8
- **fn_factor**: 64
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
