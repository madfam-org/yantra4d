# Multiboard Wall Storage

Modular wall-mounted storage system with hexagonal peg pattern

*Sistema modular de almacenamiento de pared con patrón de pines hexagonales*

**Version**: 1.0.0  
**Slug**: `multiboard`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `tile` | Tile | `qubic_tile.scad` | tile |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `x_cells` | slider | 4 | 1–12 | Number of cells along the X axis |
| `y_cells` | slider | 4 | 1–12 | Number of cells along the Y axis |
| `cell_size` | slider | 25 | 20–35 | Center-to-center distance between pegs |
| `height` | slider | 6.4 | 4–10 (step 0.2) | Total board thickness including pegs |
| `fn` | slider | 0 | 0–64 (step 8) | Circle resolution — 0 uses default (32). Higher = smoother but slower |

## Presets

- **Small Panel (4x4)**
  `x_cells`=4, `y_cells`=4
- **Large Wall (8x6)**
  `x_cells`=8, `y_cells`=6
- **Tool Rack (10x3)**
  `x_cells`=10, `y_cells`=3

## Parts

| ID | Label | Default Color |
|---|---|---|
| `tile` | Tile | `#374151` |

## Constraints

- `` — Large panels render slowly (warning)

## Render Estimates

- **base_time**: 5
- **per_unit**: 1.5
- **per_part**: 8
- **fn_factor**: 64
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 90

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
