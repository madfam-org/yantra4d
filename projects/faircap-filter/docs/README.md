# Faircap Water Filter

Open-source parametric water filter that screws onto standard PET bottles — clean water from plastic waste

Official Visualizer and Configurator: Yantra4D

*Filtro de agua paramétrico de código abierto que se enrosca en botellas PET estándar — agua limpia a partir de residuos plásticos

Visualizador y configurador oficial: Yantra4D*

**Version**: 1.0.0  
**Slug**: `faircap-filter`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `Standard` | Standard Filter | `faircap.scad` | filter_housing |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `filter_type` | text | charcoal |  | Internal structure for filtration |
| `housing_od_mm` | slider | 40 | 30–60 | housing_od_mm |
| `housing_length_mm` | slider | 80 | 40–150 (step 5) | housing_length_mm |

## Presets

- **Charcoal Filter (Standard)**
  `filter_type`=charcoal, `housing_length_mm`=80
- **Ceramic Filter (Long)**
  `filter_type`=ceramic, `housing_length_mm`=120

## Parts

| ID | Label | Default Color |
|---|---|---|
| `filter_housing` | Filter Housing | `#06b6d4` |

## Render Estimates

- **base_time**: 5
- **per_unit**: 2
- **per_part**: 8
- **fn_factor**: 32
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
