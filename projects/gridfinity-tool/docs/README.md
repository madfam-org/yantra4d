# Gridfinity Tool Holder

A parametric **tool holder** that drops into any **Gridfinity baseplate** on the
open **42 mm grid**, generated with **CadQuery** (B-Rep): an `nx x ny` bin with the
standard **Gridfinity foot** (the male chamfer stack that seats in a baseplate
socket) carrying tool bores on top. Part of the **Yantra4D Hyperobjects Commons**.
Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Bit Block** | `bit_block` | A solid Gridfinity-footed block with a grid of vertical bores for screwdriver bits and small drills. |
| **Plier Rack** | `plier_rack` | A footed block with a row of raked slots so pliers and hand tools hang jaw-down at an angle. |
| **Pen Cup** | `pen_cup` | A footed cup with a divided interior for pens, markers and round tools, drain-vented at the floor. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Grid & Body | `nx` / `ny` | 1 / 2 | Cells across X / Y (capped at 4 x 4). |
| Grid & Body | `body_h` | 30.0 mm | Holder height above the Gridfinity foot. |
| Tool Bores | `bore_d` | 6.5 mm | Bit bore diameter / plier slot width. |
| Tool Bores | `bore_pitch` | 12.0 mm | Bit bore spacing (`bit_block`). |
| Grid & Body | `wall` | 2.4 mm | Cup / rack wall thickness. |
| Tool Bores | `slot_ang` | 20° | Plier slot rake (`plier_rack`). |

## The Gridfinity foot (why it seats, and stays watertight)

Under each cell the holder carries the real Gridfinity **bin foot** — the male
counterpart of the baseplate socket, a 2.15 mm 45° toe, a 1.8 mm straight run and
a 0.8 mm 45° near the body — built as **stacked lofted frusta** and **unioned with
overlap** into the body (a short cap prism above each loft guarantees the weld is
never tangent). Tool bores are **blind holes that vent to the top face**; the cup
interior is an **open pocket** with **drain vents** off the divider line so no
sealed void forms; plier slots are **obround** (robust). Blanks are filleted
(3.75 mm Gridfinity corner radius) before bores are cut. The grid is capped at
**4 x 4**.

## Presets

- **1x2 Bit Block** — the reference bit holder for a common driver set.
- **1x1 Pen Cup** — a single-cell divided cup for desk tools.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Gridfinity 42 mm Foot** (`grid`, *Gridfinity 42 mm*) — the bin foot defined
    by `nx`, `ny`. Mates `grid-hub`, `gridfinity`, `gridfinity-baseplate`.
  - **Tool Bores** (`socket`, *internal*) — the tool holes defined by `bore_d`,
    `bore_pitch`.
- **Material awareness:** `tolerance_by_material` is declared — the foot fit and
  bore clearance tune per material/printer.
- **Societal benefit:** Gridfinity is the open, community-owned 42 mm storage grid;
  a tool holder that seats in any baseplate turns a drawer into a reconfigurable
  tool wall.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- All shipped modes and per-mode extreme parameter cases render **watertight**,
  single-body, within the time budget (largest 4 x 4 cases up to ~50 s).
