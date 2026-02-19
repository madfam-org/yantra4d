# Parametric Gears

Involute spur and herringbone gears powered by MCAD

Official Visualizer and Configurator: Yantra4D

*Engranajes rectos y de espiga con perfil involuto impulsados por MCAD

Visualizador y configurador oficial: Yantra4D*

**Version**: 1.0.0  
**Slug**: `gears`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `spur_gear` | Spur Gear | `spur_gear.scad` | spur_gear |
| `herringbone_gear` | Herringbone Gear | `herringbone_gear.scad` | herringbone_gear |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `teeth_count` | slider | 20 | 8–80 | Number of teeth on the gear |
| `module_size` | slider | 2 | 0.5–5 (step 0.25) | Gear module — pitch diameter = module x teeth |
| `pressure_angle` | slider | 20 | 14–25 | Tooth profile angle — 20° is standard, 14.5° for legacy gears |
| `thickness` | slider | 5 | 2–30 | Face width of the gear |
| `bore_diameter` | slider | 5 | 0–20 (step 0.5) | Central shaft bore diameter — 0 for solid center |
| `helical_angle` | slider | 30 | 10–60 (step 5) | Helix angle for the herringbone pattern |
| `fn` | slider | 0 | 0–64 (step 8) | Curve resolution — 0 uses default (32) |

## Presets

- **Small Motor (20T)**
  `teeth_count`=20, `module_size`=1.5, `thickness`=5, `bore_diameter`=3
- **Large Drive (60T)**
  `teeth_count`=60, `module_size`=2, `thickness`=10, `bore_diameter`=8
- **Gear Pair 5:1 (50T)**
  `teeth_count`=50, `module_size`=1, `thickness`=8, `bore_diameter`=5

## Parts

| ID | Label | Default Color |
|---|---|---|
| `spur_gear` | Spur Gear | `#f59e0b` |
| `herringbone_gear` | Herringbone Gear | `#ef4444` |

## Constraints

- `` — Bore too large for pitch circle (warning)

## Render Estimates

- **base_time**: 6
- **per_unit**: 2
- **per_part**: 8
- **fn_factor**: 64
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
