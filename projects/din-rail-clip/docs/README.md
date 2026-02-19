# Heavy Duty DIN Rail Clip

Parametric mounting clip for TS35 DIN rails — industrial automation & electronics mounting

Official Visualizer and Configurator: Yantra4D

*Clip de montaje paramétrico para rieles DIN TS35 — automatización industrial y montaje de electrónica

Visualizador y configurador oficial: Yantra4D*

**Version**: 1.0.0  
**Slug**: `din-rail-clip`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `Standard` | Clip Body | `din_clip.scad` | clip_body |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `mount_width` | slider | 40 | 20–120 | mount_width |
| `bolt_spacing` | slider | 20 | 10–100 | bolt_spacing |
| `bolt_size` | slider | 1 | 0–2 | 0=M3, 1=M4, 2=M5 |
| `fn` | slider | 0 | 0–64 (step 8) | fn |

## Presets

- **Arduino Uno Mount**
  `mount_width`=54, `bolt_spacing`=40, `bolt_size`=1
- **Raspberry Pi Mount**
  `mount_width`=56, `bolt_spacing`=49, `bolt_size`=0
- **Relay Module (Small)**
  `mount_width`=30, `bolt_spacing`=20, `bolt_size`=1

## Parts

| ID | Label | Default Color |
|---|---|---|
| `clip_body` | Clip Body | `#2d2d2d` |

## Render Estimates

- **base_time**: 5
- **per_unit**: 2
- **per_part**: 8
- **fn_factor**: 32
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
