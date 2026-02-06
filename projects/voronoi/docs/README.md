# Voronoi Generator

Voronoi pattern generator for coasters, vases, and lampshades

*Generador de patrones Voronoi para posavasos, jarrones y lamparas*

**Version**: 0.1.0  
**Slug**: `voronoi`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `coaster` | Coaster | `yantra4d_coaster.scad` | coaster |
| `vase` | Vase | `yantra4d_vase.scad` | vase |
| `lampshade` | Lampshade | `yantra4d_lampshade.scad` | lampshade |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `cell_count` | slider | 20 | 5–50 | Number of Voronoi cells |
| `size` | slider | 100 | 50–200 (step 5) | Outer diameter of the object |
| `thickness` | slider | 3 | 1–10 (step 0.5) | Base or wall thickness |
| `cell_wall` | slider | 2 | 0.5–5 (step 0.5) | Width of walls between cells |
| `seed` | slider | 42 | 1–999 | Seed for random pattern generation |
| `height` | slider | 120 | 50–250 (step 5) | Height of vase or lampshade |
| `fn` | slider | 0 | 0–64 (step 8) | 0 = auto; higher = more detail but slower |

## Presets

- **Simple Coaster**
  `cell_count`=15, `size`=100, `thickness`=3, `cell_wall`=2
- **Organic Vase**
  `cell_count`=30, `size`=80, `thickness`=2, `height`=150
- **Detailed Lampshade**
  `cell_count`=40, `size`=120, `thickness`=1.5, `height`=100
- **Dense Coaster**
  `cell_count`=40, `size`=90, `thickness`=4, `cell_wall`=1
- **Tall Vase**
  `cell_count`=25, `size`=60, `thickness`=2.5, `height`=250, `cell_wall`=1.5
- **Wide Lampshade**
  `cell_count`=50, `size`=200, `thickness`=1.5, `height`=80, `cell_wall`=1
- **Minimal Vase**
  `cell_count`=10, `size`=70, `thickness`=3, `height`=120, `cell_wall`=3

## Parts

| ID | Label | Default Color |
|---|---|---|
| `coaster` | Coaster | `#3498db` |
| `vase` | Vase | `#2ecc71` |
| `lampshade` | Lampshade | `#f39c12` |

## Constraints

- `thickness >= 1` — Minimum 1mm thickness for FDM printing (error)
- `cell_wall >= 0.8` — Cell wall too thin for printing (error)
- `cell_count <= 40 or size >= 80` — Many cells at small size may fail to print (warning)
- `height <= 200` — Heights over 200mm require a large printer (warning)

## Assembly Steps

1. **Print the main piece**
   Flat side down, 0.2mm layers, 15% infill. For lampshade use translucent material
2. **Remove supports and sand**
   Lightly sand cell walls with 220 grit sandpaper
3. **Install lighting (lampshade only)**
   Insert E27 socket or LED strip through the open base
   Hardware: led_strip, e27_socket
4. **Add felt pads (coaster)**
   Stick adhesive felt on the bottom to protect surfaces
   Hardware: felt_pads

## Bill of Materials

| Item | Quantity | Unit |
|---|---|---|
| LED strip (for lampshade) | 1 | pcs |
| E27 bulb socket (for lampshade) | 1 | pcs |
| Adhesive felt pads (for coaster) | 1 | sheet |

## Render Estimates

- **base_time**: 8
- **per_unit**: 0.5
- **per_part**: 10
- **fn_factor**: 48
- **wasm_multiplier**: 4
- **warning_threshold_seconds**: 90

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
