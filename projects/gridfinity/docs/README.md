# Gridfinity Extended

Modular storage system with bins, baseplates, and lids in the Gridfinity grid standard

Official Visualizer and Configurator: Yantra4D

*Sistema de almacenamiento modular con contenedores, placas base y tapas en el estándar Gridfinity

Visualizador y configurador oficial: Yantra4D*

**Version**: 1.0.0  
**Slug**: `gridfinity`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `cup` | Bin | `cup.scad` | cup |
| `baseplate` | Baseplate | `baseplate.scad` | baseplate |
| `lid` | Lid | `lid.scad` | lid |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `width_units` | slider | 2 | 1–6 | Grid units in X (multiples of 42mm) |
| `depth_units` | slider | 1 | 1–6 | Grid units in Y (multiples of 42mm) |
| `height_units` | slider | 3 | 1–10 | Height units (multiples of 7mm) |
| `cup_wall_thickness` | slider | 0 | 0–3 (step 0.2) | 0 = auto based on height |
| `cup_floor_thickness` | slider | 0.7 | 0.4–2 (step 0.1) | Minimum floor thickness above magnets |
| `vertical_chambers` | slider | 1 | 1–6 | Number of compartments along Y axis |
| `horizontal_chambers` | slider | 1 | 1–6 | Number of compartments along X axis |
| `lip_style_id` | slider | 0 | 0–3 | 0=normal, 1=reduced, 2=minimum, 3=none |
| `headroom` | slider | 0.8 | 0–2 (step 0.1) | Top undersizing for better stacking |
| `efficient_floor_id` | slider | 0 | 0–3 | 0=off, 1=on, 2=rounded, 3=smooth — saves 30-40% material |
| `fingerslide_enabled` | checkbox | No |  | Add front ramp for easy access |
| `label_enabled` | checkbox | No |  | Add label surface |
| `sliding_lid_enabled` | checkbox | No |  | Enable sliding lid support |
| `wallpattern_enabled` | checkbox | No |  | Enable decorative wall pattern |
| `wallpattern_style_id` | slider | 0 | 0–3 | 0=hexgrid, 1=grid, 2=voronoi, 3=brick |
| `tapered_corner_id` | slider | 0 | 0–2 | 0=none, 1=rounded, 2=chamfered |
| `tapered_corner_size` | slider | 10 | 5–20 | Corner taper radius/size |
| `enable_magnets` | checkbox | No |  | Add 6×2mm magnet cavities in corners |
| `enable_screws` | checkbox | No |  | Add M3×6 screw holes in corners |
| `bp_enable_magnets` | checkbox | No |  | Add magnet cavities in baseplate |
| `bp_enable_screws` | checkbox | No |  | Add screw holes in baseplate corners |
| `bp_corner_radius` | slider | 3.75 | 0–10 (step 0.25) | Baseplate corner radius |
| `bp_reduced_wall` | slider | -1 | -1–10 (step 0.5) | -1 = full height |
| `bp_reduced_wall_taper` | checkbox | No |  | Taper the reduced wall edge |
| `lid_include_magnets` | checkbox | Yes |  | Include magnet cavities in lid |
| `lid_efficient_floor` | slider | 0.7 | 0.4–2 (step 0.1) | Lid efficient floor thickness |
| `lid_type_id` | slider | 0 | 0–3 | 0=default, 1=flat, 2=halfpitch, 3=efficient |
| `fn` | slider | 0 | 0–64 (step 8) | 0 = auto; higher = more detail but slower |

## Presets

- **Small Parts Bin (2×1×3)**
  `width_units`=2, `depth_units`=1, `height_units`=3, `enable_magnets`=Yes, `fingerslide_enabled`=Yes
- **Battery Holder (3×2×3)**
  `width_units`=3, `depth_units`=2, `height_units`=3, `vertical_chambers`=3, `horizontal_chambers`=2, `label_enabled`=Yes
- **Tool Drawer (4×2×2)**
  `width_units`=4, `depth_units`=2, `height_units`=2, `horizontal_chambers`=4, `wallpattern_enabled`=Yes
- **Standard Baseplate (2×2)**
  `width_units`=2, `depth_units`=2, `bp_enable_magnets`=Yes
- **Standard Lid (2×1)**
  `width_units`=2, `depth_units`=1, `lid_include_magnets`=Yes
- **Screw Organizer (3×2×4)**
  `width_units`=3, `depth_units`=2, `height_units`=4, `vertical_chambers`=2, `horizontal_chambers`=3, `label_enabled`=Yes, `enable_magnets`=Yes
- **Pen Cup (1×1×6)**
  `width_units`=1, `depth_units`=1, `height_units`=6, `fingerslide_enabled`=No, `enable_magnets`=Yes

## Parts

| ID | Label | Default Color |
|---|---|---|
| `cup` | Bin | `#4a90d9` |
| `baseplate` | Baseplate | `#2d2d2d` |
| `lid` | Lid | `#6b7280` |

## Constraints

- `width_units * depth_units <= 24` — Max 24 grid cells (render timeout risk) (warning)
- `vertical_chambers * horizontal_chambers <= 12` — Max 12 compartments (warning)

## Assembly Steps

1. **Print the baseplate**
   Flat side down, 0.2mm layers, 20% infill
2. **Print the bins**
   Opening up, no supports needed for standard design
3. **Place bins on baseplate**
   Bins snap into the grid. Magnets are optional for extra hold.

## Bill of Materials

| Item | Quantity | Unit |
|---|---|---|
| N52 6×2mm Magnets | (enable_magnets ? 4 : 0) + (bp_enable_magnets ? 4 * width_units * depth_units : 0) + (lid_include_magnets ? 4 * width_units * depth_units : 0) | pcs |
| M3×6 Screws | (enable_screws ? 4 : 0) + (bp_enable_screws ? 4 : 0) | pcs |

## Render Estimates

- **base_time**: 8
- **per_unit**: 2
- **fn_factor**: 64
- **per_part**: 10
- **wasm_multiplier**: 4
- **warning_threshold_seconds**: 90

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
