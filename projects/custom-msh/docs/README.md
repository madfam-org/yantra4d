# Custom MSH (AOCL)

Custom substrate holder system for 1×1 inch substrates (AOCL) — holder, 10-slot rack, and 3-rack storage box

Official Visualizer and Configurator: Yantra4D

*Sistema portamuestras para sustratos de 1×1 pulgada (AOCL) — soporte individual, rack de 10 ranuras y caja para 3 racks

Visualizador y configurador oficial: Yantra4D*

**Version**: 2.0.0  
**Slug**: `custom-msh`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `holder` | Single Holder | `holder.scad` | holder_body |
| `rack` | 10-Slot Rack | `rack.scad` | rack |
| `box` | 3-Rack Box | `box.scad` | box_base, box_lid |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `substrate_size` | slider | 25.4 | 24.0–27.0 (step 0.1) | Square substrate side length. AOCL spec: 25.4 mm (1 inch) |
| `tolerance_xy` | slider | 0.4 | 0.1–0.8 (step 0.05) | Horizontal clearance added to pocket/slot openings for FDM shrinkage compensation |
| `tolerance_z` | slider | 0.2 | 0.05–0.5 (step 0.05) | Slot width clearance over substrate thickness (waviness + layer offset) |
| `wall_thickness` | slider | 2.0 | 1.2–4.0 (step 0.2) | Outer wall and pillar thickness |
| `label_area` | checkbox | Yes |  | Debossed recess for handwritten or adhesive label |
| `chamfer_pocket` | checkbox | Yes |  | 45° chamfer at pocket entry to guide substrate insertion |
| `num_slots` | slider | 10 | 5–15 | Number of substrate positions per rack. AOCL spec: 10 |
| `handle` | checkbox | Yes |  | Integrated handle arch for carrying the rack |
| `open_bottom` | checkbox | Yes |  | Open crossbar base (less material, easier cleaning) vs. solid floor |
| `drainage_angle` | slider | 5 | 0–15 | Slope for fluid runoff (0 = flat). Reserved for future use. |
| `numbering_start` | slider | 1 | 1–100 | First slot number engraved on the rack. Requires Quality ($fn) > 0. |
| `num_racks` | slider | 3 | 1–5 | How many racks the box accommodates. AOCL spec: 3 |
| `box_depth_target` | slider | 26.0 | 24.0–40.0 (step 0.5) | Outer box Z-height. AOCL spec: ~26 mm (~2.6 cm). Clamped to minimum rack height automatically. |
| `snap_lid` | checkbox | Yes |  | Generate snap-fit cantilever latch arms on lid (PLA-safe 15 mm arm) |
| `fn` | slider | 0 | 0–64 (step 8) | 0 = auto (fast draft); higher = more detail + slot numbers engraved, but slower render |

## Presets

- **AOCL Default (1"×1", 10 slots, 3 racks)**
  `substrate_size`=25.4, `num_slots`=10, `num_racks`=3, `tolerance_xy`=0.4, `tolerance_z`=0.2, `wall_thickness`=2.0, `label_area`=1, `snap_lid`=1, `handle`=1, `open_bottom`=1
- **Tight Tolerance (precision printer)**
  `substrate_size`=25.4, `tolerance_xy`=0.2, `tolerance_z`=0.1, `wall_thickness`=2.0
- **Loose Tolerance (easy extraction)**
  `substrate_size`=25.4, `tolerance_xy`=0.6, `tolerance_z`=0.3, `wall_thickness`=2.0

## Parts

| ID | Label | Default Color |
|---|---|---|
| `holder_body` | Holder Body | `#4a90d9` |
| `rack` | Rack | `#e5e7eb` |
| `box_base` | Box Base | `#4a90d9` |
| `box_lid` | Box Lid | `#6b7280` |

## Render Estimates

- **base_time**: 5
- **per_unit**: 1
- **per_part**: 8

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
