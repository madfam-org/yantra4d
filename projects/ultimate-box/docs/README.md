# Ultimate Box Maker

Parametric electronics enclosure with ventilation, PCB standoffs, and snap-fit lid

*Carcasa paramétrica para electrónica con ventilación, soportes para PCB y tapa a presión*

**Version**: 1.0.0  
**Slug**: `ultimate-box`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `` | Enclosure | `yantra4d_box.scad` | enclosure |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `` | slider | 80 | 30–200 | Internal length of the box |
| `` | slider | 60 | 30–150 | Internal width of the box |
| `` | slider | 30 | 15–100 | Internal height of the box |
| `` | slider | 2.8 | 1.5–5 (step 0.1) | Thickness of enclosure walls |
| `` | slider | 2 | 0–10 (step 0.5) | Fillet radius for box corners |
| `` | checkbox | Yes |  | Enable rounded corners on the box |
| `` | checkbox | Yes |  | Add ventilation slots to walls |
| `` | slider | 1.7 | 0.5–3 (step 0.1) | Width of each ventilation slot |
| `` | checkbox | No |  | Add mounting standoffs for a PCB |
| `` | slider | 0 | 0–4 | Style of case feet (0=none) |
| `` | slider | 2.2606 | 1.5–4 (step 0.1) | Diameter of screw holes for lid |
| `` | slider | 0 | 0–64 (step 8) | Circle smoothness (0=auto) |

## Presets

- **Arduino Uno**
  `box_length`=80, `box_width`=60, `box_height`=30, `pcb_standoffs`=Yes
- **Raspberry Pi**
  `box_length`=90, `box_width`=65, `box_height`=35, `ventilation`=Yes, `case_feet_id`=2
- **Generic Small**
  `box_length`=50, `box_width`=40, `box_height`=20

## Parts

| ID | Label | Default Color |
|---|---|---|
| `enclosure` | Enclosure | `#6366f1` |

## Bill of Materials

| Item | Quantity | Unit |
|---|---|---|
|  |  |  |
|  |  |  |

## Render Estimates

- **base_time**: 8
- **per_unit**: 2
- **per_part**: 12
- **fn_factor**: 64
- **wasm_multiplier**: 4
- **warning_threshold_seconds**: 90

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
