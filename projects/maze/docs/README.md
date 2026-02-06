# Maze Generator

Maze generator for coasters, cubes, and cylinders

*Generador de laberintos para posavasos, cubos y cilindros*

**Version**: 0.1.0  
**Slug**: `maze`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `coaster` | Coaster | `yantra4d_maze_coaster.scad` | coaster |
| `cube` | Cube | `yantra4d_maze_cube.scad` | cube |
| `cylinder` | Cylinder | `yantra4d_maze_cylinder.scad` | cylinder |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `rows` | slider | 10 | 5–30 | Number of maze rows |
| `cols` | slider | 10 | 5–30 | Number of maze columns |
| `cell_size` | slider | 5 | 3–10 (step 0.5) | Size of each maze cell |
| `wall_thickness` | slider | 1.2 | 0.8–3 (step 0.2) | Thickness of maze walls |
| `wall_height` | slider | 3 | 1–10 (step 0.5) | Height of maze walls |
| `base_thickness` | slider | 2 | 1–5 (step 0.5) | Thickness of the base plate |
| `seed` | slider | 123 | 1–9999 | Seed for maze generation |
| `diameter` | slider | 100 | 50–150 (step 5) | Diameter of coaster or cylinder |

## Presets

- **Simple Coaster Maze**
  `rows`=8, `cols`=8, `cell_size`=5, `diameter`=100, `wall_thickness`=1.2
- **Challenging Cube**
  `rows`=15, `cols`=15, `cell_size`=4, `wall_height`=5, `wall_thickness`=1.2
- **Cylinder Puzzle**
  `rows`=12, `cols`=12, `diameter`=80, `wall_height`=4, `wall_thickness`=1
- **Mini Coaster**
  `rows`=6, `cols`=6, `cell_size`=4, `diameter`=70, `wall_height`=2, `wall_thickness`=1
- **Expert Cube**
  `rows`=25, `cols`=25, `cell_size`=3, `wall_height`=4, `wall_thickness`=0.8
- **Decorative Cylinder**
  `rows`=8, `cols`=20, `diameter`=100, `wall_height`=6, `cell_size`=6, `wall_thickness`=1.5
- **Kids Maze**
  `rows`=5, `cols`=5, `cell_size`=8, `diameter`=100, `wall_height`=5, `wall_thickness`=2

## Parts

| ID | Label | Default Color |
|---|---|---|
| `coaster` | Coaster | `#e74c3c` |
| `cube` | Cube | `#9b59b6` |
| `cylinder` | Cylinder | `#1abc9c` |

## Constraints

- `wall_thickness >= 0.8` — Minimum 0.8mm thickness for FDM printing (error)
- `base_thickness >= 1` — Base too thin for stable printing (error)
- `rows * cols <= 500` — Very complex maze, rendering may be slow (warning)
- `cell_size >= wall_thickness * 2` — Cell must be at least twice the wall thickness (error)

## Assembly Steps

1. **Print the maze**
   Flat side down, 0.2mm layers, 20% infill
2. **Clean the piece**
   Remove supports if any. Verify the ball fits through corridors
3. **Add the steel ball**
   Place the ball at the maze entrance
   Hardware: steel_ball

## Bill of Materials

| Item | Quantity | Unit |
|---|---|---|
| 3mm steel ball (to solve the maze) | 1 | pcs |
| Adhesive felt pads (for coaster) | 1 | sheet |

## Render Estimates

- **base_time**: 6
- **per_unit**: 1
- **per_part**: 8
- **fn_factor**: 32
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
