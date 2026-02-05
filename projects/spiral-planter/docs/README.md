# Spiral Planter

Generative spiral planter with parametric drainage using dotSCAD

*Maceta espiral generativa con drenaje parametrico usando dotSCAD*

**Version**: 0.1.0  
**Slug**: `spiral-planter`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `planter` | Planter | `qubic_spiral_planter.scad` | planter, saucer |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `turns` | slider | 3 | 1–6 | Number of spiral turns |
| `spacing` | slider | 8 | 4–15 | Distance between spiral turns |
| `wall_thickness` | slider | 2 | 1.2–4 (step 0.2) | Thickness of the planter wall |
| `base_diameter` | slider | 60 | 30–150 (step 5) | Diameter of the planter base |
| `height` | slider | 80 | 40–200 (step 5) | Height of the planter |
| `drainage` | checkbox | Yes |  | Holes in the base for water drainage |
| `fn` | slider | 0 | 0–64 (step 8) | 0 = auto |

## Presets

- **Desktop**
  `turns`=3, `spacing`=8, `wall_thickness`=2, `base_diameter`=60, `height`=80, `drainage`=Yes
- **Hanging**
  `turns`=4, `spacing`=6, `wall_thickness`=2.5, `base_diameter`=50, `height`=100, `drainage`=Yes
- **Succulent**
  `turns`=2, `spacing`=10, `wall_thickness`=2, `base_diameter`=70, `height`=50, `drainage`=Yes
- **Herb Garden**
  `turns`=3, `spacing`=12, `wall_thickness`=3, `base_diameter`=100, `height`=120, `drainage`=Yes
- **Mini**
  `turns`=2, `spacing`=5, `wall_thickness`=1.5, `base_diameter`=40, `height`=50, `drainage`=No

## Parts

| ID | Label | Default Color |
|---|---|---|
| `planter` | Planter | `#27ae60` |
| `saucer` | Saucer | `#795548` |

## Constraints

- `wall_thickness >= 1.2` — Minimum 1.2mm thickness for FDM printing (error)
- `base_diameter >= 30` — Minimum diameter for stability (error)
- `height <= 200` — Heights over 200mm require a large printer (warning)

## Assembly Steps

1. **Print the planter**
   0.2mm layers, 20% infill. PETG recommended for water resistance
2. **Print the saucer**
   0.2mm layers, 20% infill
3. **Add drainage mesh**
   Place mesh over drainage holes to prevent soil from escaping
   Hardware: drainage_mesh
4. **Plant!**
   Add soil and your favorite plant

## Bill of Materials

| Item | Quantity | Unit |
|---|---|---|
| Drainage mesh (for holes) | 1 | pcs |
| Saucer felt (protects surfaces) | 1 | sheet |

## Render Estimates

- **base_time**: 8
- **per_unit**: 1.5
- **per_part**: 10
- **fn_factor**: 48
- **wasm_multiplier**: 4
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
