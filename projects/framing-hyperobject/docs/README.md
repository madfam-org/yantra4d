# Framing Hyperobject

Parametric framing and containment systems (Hyperobject)

Official Visualizer and Configurator: Yantra4D

*Sistemas paramétricos de enmarcado y contención (Hiperobjeto)

Visualizador y configurador oficial: Yantra4D*

**Version**: 1.0.0  
**Slug**: `framing-hyperobject`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `frame` | Frame Assembly | `framing.scad` | frame_assembly, back_panel, glazing |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `width` | slider | 200 | 50–1000 | width |
| `height` | slider | 250 | 50–1000 | height |
| `depth` | slider | 20 | 10–100 | depth |
| `profile_style` | select | ogee |  | profile_style |
| `mounting_style` | select | none |  | mounting_style |
| `container_type` | select | none |  | container_type |
| `mat_width` | slider | 50 | 0–200 | mat_width |
| `glazing_thickness` | slider | 2 | 1–6 (step 0.5) | glazing_thickness |

## Parts

| ID | Label | Default Color |
|---|---|---|
| `frame_assembly` | Frame | `#8b4513` |
| `back_panel` | Backing | `#f5deb3` |
| `glazing` | Glazing | `#add8e6` |

## Render Estimates

- **base_time**: 5
- **per_unit**: 1
- **per_part**: 8

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
