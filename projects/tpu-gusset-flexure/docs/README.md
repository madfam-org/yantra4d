# TPU Gusset Flexure

A **print-in-place stretch gusset** — generated with **CadQuery** (B-Rep). The
additive-manufacturing insert Fashion Cabinet's `printed-gusset-flexure` notion
describes and bridges to **here**. A diamond gusset (the four-point insert sewn into an
underarm, crotch, or side vent for range of motion) printed as a thin TPU panel cut with
a **slit lattice**, so it stretches biaxially where a woven gusset only eases on the
bias.

Part of the AM-fashion capsule. One material identity, **Bambu TPU 95A**. Official
visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Stretch Gusset** | `gusset` | The full diamond with the slit lattice. |
| **Slit Swatch** | `swatch` | A small square of the slit pattern. |
| **Plain Diamond** | `solid` | No slits, to compare stretch. |

## Parameters

| Parameter | Default | Notes |
| :--- | :--- | :--- |
| `diag_w` | 70 mm | Width diagonal of the diamond. |
| `diag_h` | 90 mm | Height diagonal of the diamond. |
| `wall` | 1.4 mm | Thinner = more stretch. |
| `slit_rows` / `slit_cols` | 5 / 4 | Slit lattice density. |
| `slit_len` | 9 mm | Slit length; longer = more stretch, less coverage. |

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:** Sewn Gusset Edge (`flange` — `diag_w`, `diag_h`, `wall`) and
  Slit-Lattice Stretch Cell (`snap` — `slit_rows`, `slit_cols`, `slit_len`, `wall`).

## Fabrication notes

The diamond is an extruded rhombus (straight segments — no arcs); the slit lattice is a
grid of short through-slots that sit inside the outline and leave ligaments, so the panel
stays one watertight solid and stretches at the slits. Print thin in TPU; run the swatch
first and lengthen the slits (or thin the wall) for more stretch.
