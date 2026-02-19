# Parametric Gear Reducer

Parametric gear reducer with BOSL2 — configurable ratio, motor size, and shaft diameter

*Reductor de engranajes parametrico con BOSL2 — ratio configurable, tamano de motor y diametro de eje*

**Version**: 0.1.0  
**Slug**: `gear-reducer`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `assembly` | Full Assembly | `gear_reducer.scad` | housing_bottom, housing_top, input_gear, output_gear, shaft |
| `housing` | Housing | `housing.scad` | housing_bottom, housing_top |
| `gears` | Gear Set | `gear_set.scad` | input_gear, output_gear |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `input_teeth` | slider | 12 | 8–30 | Number of teeth on the input (pinion) gear |
| `output_teeth` | slider | 36 | 16–80 | Number of teeth on the output gear |
| `module_size` | slider | 1.5 | 1–3 (step 0.25) | Gear module — controls tooth size |
| `gear_thickness` | slider | 8 | 4–20 | Thickness of the gears |
| `shaft_diameter` | slider | 5 | 3–10 (step 0.5) | Output shaft diameter |
| `bore_diameter` | slider | 5 | 3–10 (step 0.5) | Center bore diameter of the gear |
| `wall_thickness` | slider | 3 | 2–6 (step 0.5) | Thickness of the housing walls |
| `pressure_angle` | slider | 20 | 14–25 | Pressure angle of tooth profile |
| `fn` | slider | 0 | 0–64 (step 8) | 0 = auto; higher = more detail but slower |

## Presets

- **NEMA 17 — 3:1**
  `input_teeth`=12, `output_teeth`=36, `module_size`=1.5, `gear_thickness`=8, `shaft_diameter`=5, `bore_diameter`=5, `wall_thickness`=3
- **NEMA 17 — 4:1**
  `input_teeth`=10, `output_teeth`=40, `module_size`=1.5, `gear_thickness`=10, `shaft_diameter`=5, `bore_diameter`=5, `wall_thickness`=3
- **NEMA 23 — 5:1**
  `input_teeth`=10, `output_teeth`=50, `module_size`=2, `gear_thickness`=12, `shaft_diameter`=6.35, `bore_diameter`=6.35, `wall_thickness`=4
- **Compact 2:1**
  `input_teeth`=15, `output_teeth`=30, `module_size`=1, `gear_thickness`=6, `shaft_diameter`=5, `bore_diameter`=5, `wall_thickness`=2.5
- **Heavy Duty 6:1**
  `input_teeth`=10, `output_teeth`=60, `module_size`=2.5, `gear_thickness`=15, `shaft_diameter`=8, `bore_diameter`=8, `wall_thickness`=5

## Parts

| ID | Label | Default Color |
|---|---|---|
| `housing_bottom` | Housing Bottom | `#2c3e50` |
| `housing_top` | Housing Top | `#34495e` |
| `input_gear` | Input Gear | `#e74c3c` |
| `output_gear` | Output Gear | `#f39c12` |
| `shaft` | Shaft | `#95a5a6` |

## Constraints

- `output_teeth > input_teeth` — Output gear must have more teeth than input for reduction (error)
- `input_teeth >= 8` — Minimum 8 teeth to avoid undercutting (error)
- `bore_diameter < input_teeth * module_size * 0.4` — Bore too large for the pinion (error)
- `wall_thickness >= 2` — Minimum housing thickness for FDM printing (error)
- `output_teeth * module_size <= 150` — Output gear may exceed print bed size (warning)

## Assembly Steps

1. **Print the bottom housing**
   0.2mm layers, 40% infill for rigidity. Supports in bearing cavities
2. **Print the gears**
   0.16mm layers for tooth precision. 60% infill. PETG or ABS recommended
3. **Insert the bearings**
   Press-fit the 608ZZ bearings into housing cavities
   Hardware: bearing_608
4. **Mount gears on shafts**
   Apply grease to teeth before mounting
   Hardware: grease
5. **Attach top housing**
   Align guide posts and press down
6. **Secure with bolts**
   Insert 4 M3x20 bolts and tighten nuts
   Hardware: m3_bolt, m3_nut

## Bill of Materials

| Item | Quantity | Unit |
|---|---|---|
| 608ZZ Bearing (8x22x7mm) | 2 | pcs |
| M3x20mm Bolt | 4 | pcs |
| M3 Nut | 4 | pcs |
| Gear grease (optional) | 1 | tube |

## Render Estimates

- **base_time**: 10
- **per_unit**: 3
- **per_part**: 12
- **fn_factor**: 64
- **wasm_multiplier**: 5
- **warning_threshold_seconds**: 120

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
