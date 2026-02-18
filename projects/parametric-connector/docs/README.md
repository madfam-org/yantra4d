# Parametric Pipe Connector

Universal connector system for PVC, Bamboo, and Wood Dowels

*Sistema de conectores universales para PVC, Bambú y Espigas de Madera*

**Version**: 1.0.0  
**Slug**: `parametric-connector`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `Standard` | Pipe Connector | `connector.scad` | connector_body |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `pipe_od_mm` | slider | 21.3 | 10–60 (step 0.1) | Outer diameter of the pipe/dowel |
| `connector_type` | select | elbow |  | connector_type |
| `wall_thickness_mm` | slider | 3 | 2–8 (step 0.5) | wall_thickness_mm |
| `insertion_depth_mm` | slider | 20 | 10–50 | insertion_depth_mm |
| `fn` | slider | 0 | 0–64 (step 8) | fn |

## Presets

- **1/2" PVC Elbow**
  `pipe_od_mm`=21.3, `connector_type`=elbow
- **3/4" PVC Tee**
  `pipe_od_mm`=26.7, `connector_type`=tee
- **Furniture 3-Way Corner (1")**
  `pipe_od_mm`=33.4, `connector_type`=3-way-corner

## Parts

| ID | Label | Default Color |
|---|---|---|
| `connector_body` | Connector Body | `#f97316` |

## Render Estimates

- **base_time**: 5
- **per_unit**: 2
- **per_part**: 8
- **fn_factor**: 32
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
