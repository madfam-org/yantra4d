# YAPP Box Generator

Yet Another Parametric Projectbox — PCB enclosure with snap-fit lid

*Caja paramétrica para proyectos — carcasa para PCB con tapa a presión*

**Version**: 1.0.0  
**Slug**: `yapp-box`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `` | Base | `qubic_yapp_base.scad` | base |
| `` | Lid | `qubic_yapp_lid.scad` | lid |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `` | slider | 80 | 20–200 | Length of the PCB board |
| `` | slider | 50 | 15–150 | Width of the PCB board |
| `` | slider | 1.6 | 0.8–3.2 (step 0.1) | Thickness of the PCB |
| `` | slider | 3 | 1–10 (step 0.5) | Height of PCB standoffs from floor |
| `` | slider | 2 | 1.2–4 (step 0.2) | Enclosure wall thickness |
| `` | slider | 25 | 10–60 | Height of base enclosure walls |
| `` | slider | 15 | 5–40 | Height of lid walls |
| `` | slider | 3 | 0–8 (step 0.5) | Corner rounding radius |
| `` | slider | 2 | 0–10 (step 0.5) | Extra space in front of PCB |
| `` | slider | 2 | 0–10 (step 0.5) | Extra space behind PCB |
| `` | slider | 2 | 0–10 (step 0.5) | Extra space left of PCB |
| `` | slider | 2 | 0–10 (step 0.5) | Extra space right of PCB |
| `` | slider | 0 | 0–64 (step 8) | Circle smoothness (0=auto) |

## Presets

- **ESP32 Dev Board**
  `pcbLength`=56, `pcbWidth`=28, `baseWallHeight`=20, `lidWallHeight`=15, `standoffHeight`=3
- **Sensor Node**
  `pcbLength`=40, `pcbWidth`=25, `baseWallHeight`=15, `lidWallHeight`=10
- **Display Box**
  `pcbLength`=100, `pcbWidth`=60, `baseWallHeight`=30, `lidWallHeight`=20, `roundRadius`=5

## Parts

| ID | Label | Default Color |
|---|---|---|
| `base` | Base | `` |
| `lid` | Lid | `` |

## Assembly Steps

. ****
. ****
. ****
. ****

## Bill of Materials

| Item | Quantity | Unit |
|---|---|---|
|  | 4 |  |

## Render Estimates

- **base_time**: 8
- **per_unit**: 2
- **per_part**: 10
- **fn_factor**: 64
- **wasm_multiplier**: 4
- **warning_threshold_seconds**: 90

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
