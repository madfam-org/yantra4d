# Microscope Slide Holder

Parametric microscope slide retention system — trays, boxes, staining racks, and archival cabinets

*Sistema paramétrico de retención de portaobjetos de microscopio — bandejas, cajas, bastidores de tinción y gabinetes archivadores*

**Version**: 2.0.0  
**Slug**: `slide-holder`  
**Difficulty**: intermediate

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `box` | Storage Box | `box.scad` | box_base, box_lid |
| `tray` | Horizontal Tray | `tray.scad` | tray |
| `staining_rack` | Staining Rack | `staining_rack.scad` | rack |
| `cabinet_drawer` | Cabinet Drawer | `cabinet_drawer.scad` | drawer, shell |

## Parameters

### Global (all modes)

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `slide_standard` | slider | 0 | 0–4 | 0=ISO 76×26, 1=US 76.2×25.4, 2=Petrographic 46×27, 3=Supa Mega 75×50, 4=Custom |
| `custom_slide_length` | slider | 76 | 40–100 (step 0.1) | Slide length when standard=Custom |
| `custom_slide_width` | slider | 26 | 15–55 (step 0.1) | Slide width when standard=Custom |
| `custom_slide_thickness` | slider | 1.0 | 0.5–2.0 (step 0.1) | Slide thickness when standard=Custom |
| `num_slots` | slider | 25 | 1–100 | Number of slide positions |
| `tolerance_xy` | slider | 0.4 | 0.1–1.0 (step 0.05) | XY clearance for FDM printing |
| `tolerance_z` | slider | 0.2 | 0.05–0.5 (step 0.05) | Z / thickness clearance |
| `wall_thickness` | slider | 2.0 | 1.2–4.0 (step 0.2) | Outer wall thickness |
| `label_area` | checkbox | true | — | Generate debossed label recess |
| `fn` | slider | 0 | 0–64 (step 8) | Quality ($fn), 0 = auto |

### Box (Class II)

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `rib_profile` | slider | 0 | 0–1 | 0=tapered, 1=rectangular |
| `rib_width` | slider | 1.5 | 0.8–3.0 (step 0.1) | Rib root width (mm) |
| `density` | slider | 1 | 0–3 | 0=archival (2.6mm), 1=working (3.5mm), 2=staining (5mm), 3=mailer (6mm) |
| `lid_latch` | slider | 0 | 0–2 | 0=snap-fit, 1=magnetic, 2=none |
| `stackable` | checkbox | true | — | Generate stacking lip + groove |
| `numbering_start` | slider | 1 | 0–999 | First slot number for debossed labels |

### Tray (Class I)

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `tray_columns` | slider | 5 | 1–10 | Columns of slide pockets |
| `tray_rows` | slider | 2 | 1–5 | Rows of slide pockets |
| `finger_notch` | checkbox | true | — | Cylindrical notch for easy slide removal |
| `anti_capillary` | checkbox | true | — | Floor rails to break vacuum seal |

### Staining Rack (Class III)

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `handle` | checkbox | true | — | Generate carrying handle |
| `drainage_angle` | slider | 5 | 0–15 | Drainage slope in degrees |
| `open_bottom` | checkbox | true | — | Crossbar floor (better fluid circulation) |

### Cabinet Drawer (Class IV)

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `rail_profile` | slider | 0 | 0–1 | 0=T-slot, 1=L-rail |
| `backstop` | checkbox | true | — | Flexible tab prevents full extraction |
| `drawers_per_shell` | slider | 5 | 1–10 | Drawer slots in shell |

## Presets

- **Standard 25-Place Box**: ISO, 25 slots, working density, snap-fit lid
- **100-Place Archival Box**: ISO, 100 slots, archival density, stackable
- **Petrographic Box (20)**: Petrographic slides, 20 slots
- **Drying Tray (5×2)**: ISO, 10 slides, anti-capillary ribs
- **20-Slide Staining Rack**: ISO, 20 slots, handle, 5° drainage
- **Compact 5-Slide Box**: US, 5 slots, non-stackable
- **Supa Mega Tray (2×2)**: Supa Mega slides, 4 positions
- **Cabinet Unit (5 drawers)**: ISO, 25 slots, T-slot rails

## Parts

| ID | Label | Default Color |
|---|---|---|
| `box_base` | Box Base | `#4a90d9` |
| `box_lid` | Box Lid | `#6b7280` |
| `tray` | Tray | `#4a90d9` |
| `rack` | Rack | `#e5e7eb` |
| `drawer` | Drawer | `#4a90d9` |
| `shell` | Shell | `#2d2d2d` |

## Constraints

- `num_slots >= 1` — At least 1 slide slot required (error)
- `custom_slide_thickness > 0` — Slide thickness must be positive (error)
- `custom_slide_length > custom_slide_width` — Length must exceed width (error)
- `wall_thickness >= 1.2` — Below 1.2mm may not print reliably (warning)
- `num_slots <= 50` — May exceed print bed width (warning)
- `tolerance_xy >= 0.2` — Below 0.2mm may cause insertion difficulty (warning)
- Supa Mega + archival density = very wide print bed needed (warning)

## Materials

| Material | Density (g/cm³) | Cost/kg | Recommended For |
|----------|:-:|:-:|---|
| PLA | 1.24 | $20 | Dry storage (tray, box) |
| PETG | 1.27 | $25 | General purpose, short-term staining |
| ABS/ASA | 1.04 | $22 | Archival, high-temp drying |
| Nylon (PA) | 1.14 | $40 | Heavy-duty staining, moving parts |

## Hyperobject Profile

> This project is classified as a **Bounded 4D Hyperobject** in the Yantra4D Commons.

| Field | Value |
|---|---|
| **Domain** | Medical |
| **License** | CERN-OHL-S-2.0 |
| **Material Awareness** | Tolerance-by-material ✅, Shrinkage compensation ✗, Recycled material ✗ |

### Common Denominator Geometry (CDG) Interfaces

| Interface | Type | Standard | Parameters |
|---|---|---|---|
| ISO 8037 Microscope Slide | pocket | ISO 8037-1:2003 | `slide_standard`, `custom_slide_length`, `custom_slide_width`, `custom_slide_thickness` |
| Retention Pitch System | rail | internal | `density`, `num_slots` |
| Stacking Lip/Groove | snap | internal | `stackable` |
| Snap-Fit Lid Latch | snap | internal | `lid_latch` |

### Societal Benefit

Enables laboratories and pathology departments to fabricate precision slide retention systems for histology, cytology, and archival workflows — independent of commercial supply chains.

## Engineering Reference

Design based on `docs/RESEARCH.pdf` (*Parametric Architectures for Microscope Slide Retention*) covering ISO 8037 slide standards, tolerance engineering, and retention class taxonomy.

---
*Generated from `project.json` v2.0.0 — Hyperobjects Commons*
