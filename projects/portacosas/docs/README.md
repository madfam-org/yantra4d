# Portacosas

Modular desk organizer with snap-fit tray system

*Organizador de escritorio modular con sistema de bandejas a presión*

**Version**: 1.0.0  
**Slug**: `portacosas`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `unit` | Component | `desk_organizer.scad` | tray_base, pen_holder, phone_stand, card_slot, cable_clip, label_plate |
| `assembly` | Assembly | `assembly.scad` | tray_base, pen_holder, phone_stand, card_slot, cable_clip, label_plate |
| `grid` | Grid | `grid.scad` | tray_base |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `tray_width` | slider | 200 | 120–300 (step 5) | Total width of the base tray |
| `tray_depth` | slider | 120 | 60–200 (step 5) | Total depth of the base tray |
| `wall_height` | slider | 80 | 40–120 (step 5) | Maximum height of components |
| `wall_thickness` | slider | 2.0 | 1.0–4.0 (step 0.2) | Wall thickness of components |
| `pen_count` | slider | 5 | 3–8 | Number of pen holes |
| `pen_diameter` | slider | 12 | 8–20 | Diameter of each pen hole |
| `pen_style` | checkbox | No |  | Hexagonal holes instead of round |
| `phone_width` | slider | 75 | 60–90 | Width of the phone cradle |
| `phone_angle` | slider | 65 | 45–80 | Tilt angle of the phone stand |
| `charging_slot` | checkbox | Yes |  | Slot for charging cable pass-through |
| `card_width` | slider | 90 | 60–120 (step 5) | Width of the card slot |
| `card_depth` | slider | 60 | 30–80 (step 5) | Depth of the card slot |
| `card_angle` | slider | 10 | 5–20 | Tilt angle of the card holder |
| `clip_count` | slider | 2 | 1–4 | Number of cable clips |
| `clip_diameter` | slider | 6 | 4–10 | Inner diameter of cable clip |
| `label_text` | text | YANTRA4D |  | Custom text for the front label plate |
| `label_depth` | slider | 0.5 | 0.3–1.5 (step 0.1) | Depth of engraved text on label plate |
| `rows` | slider | 1 | 1–5 | Number of rows in the tray grid |
| `cols` | slider | 1 | 1–5 | Number of columns in the tray grid |

## Presets

- **Minimal**
  `tray_width`=140, `tray_depth`=80, `wall_height`=60, `wall_thickness`=2.0, `pen_count`=3, `pen_diameter`=12, `pen_style`=No, `phone_width`=75, `phone_angle`=65, `charging_slot`=No, `card_width`=90, `card_depth`=60, `card_angle`=10, `clip_count`=1, `clip_diameter`=6, `label_text`=YANTRA4D, `label_depth`=0.5
- **Office**
  `tray_width`=200, `tray_depth`=120, `wall_height`=80, `wall_thickness`=2.0, `pen_count`=5, `pen_diameter`=12, `pen_style`=No, `phone_width`=75, `phone_angle`=65, `charging_slot`=Yes, `card_width`=90, `card_depth`=60, `card_angle`=10, `clip_count`=2, `clip_diameter`=6, `label_text`=OFICINA, `label_depth`=0.5
- **Developer**
  `tray_width`=250, `tray_depth`=140, `wall_height`=80, `wall_thickness`=2.0, `pen_count`=4, `pen_diameter`=10, `pen_style`=No, `phone_width`=80, `phone_angle`=70, `charging_slot`=Yes, `card_width`=90, `card_depth`=60, `card_angle`=10, `clip_count`=4, `clip_diameter`=7, `label_text`=DEV, `label_depth`=0.5
- **Artist**
  `tray_width`=220, `tray_depth`=130, `wall_height`=90, `wall_thickness`=2.0, `pen_count`=8, `pen_diameter`=14, `pen_style`=Yes, `phone_width`=75, `phone_angle`=65, `charging_slot`=No, `card_width`=90, `card_depth`=60, `card_angle`=10, `clip_count`=2, `clip_diameter`=6, `label_text`=ARTE, `label_depth`=0.8
- **Compact**
  `tray_width`=160, `tray_depth`=100, `wall_height`=70, `wall_thickness`=2.0, `pen_count`=3, `pen_diameter`=12, `pen_style`=No, `phone_width`=70, `phone_angle`=60, `charging_slot`=Yes, `card_width`=80, `card_depth`=50, `card_angle`=10, `clip_count`=1, `clip_diameter`=5, `label_text`=YANTRA4D, `label_depth`=0.5

## Parts

| ID | Label | Default Color |
|---|---|---|
| `tray_base` | Tray Base | `#2d2d2d` |
| `pen_holder` | Pen Holder | `#3b82f6` |
| `phone_stand` | Phone Stand | `#2d2d2d` |
| `card_slot` | Card Slot | `#f59e0b` |
| `cable_clip` | Cable Clip | `#10b981` |
| `label_plate` | Label Plate | `#ffffff` |

## Constraints

- `wall_thickness >= 1.2` — Minimum thickness for FDM printing (error)
- `pen_diameter > wall_thickness * 2` — Pen must fit in the hole (error)
- `phone_angle >= 45` — Minimum stability angle (warning)
- `rows * cols <= 9` — Maximum 9 trays in grid (error)

## Assembly Steps

1. **Print the tray base**
   Flat side down, 0.2mm layers, 20% infill
2. **Print the pen holder**
   Supports needed if hex style
3. **Print the phone stand**
   Supports on charging slot
4. **Snap pen holder into tray**
   Align snap-fits and press firmly
5. **Snap phone stand into tray**
   Align snap-fits and press firmly
6. **Add rubber feet to bottom**
   Stick 4 feet on the bottom corners of the tray

## Bill of Materials

| Item | Quantity | Unit |
|---|---|---|
| Rubber feet | 4 * rows * cols | pcs |
| Adhesive pads | clip_count | pcs |
| Felt liner (optional) | 1 | sheet |

## Render Estimates

- **base_time**: 5
- **per_unit**: 2
- **fn_factor**: 48
- **per_part**: 6
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
