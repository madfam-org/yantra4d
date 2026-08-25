# Gridfinity Baseplate (Screw-Down)

A **Gridfinity baseplate** on the open **42 mm grid**, generated with **CadQuery**
(B-Rep): an `nx x ny` field of cells, each with the standard **stacked-chamfer
socket** (0.8 mm + 1.8 mm + 2.15 mm, 41.5 mm opening) that a Gridfinity bin foot
drops into. Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Screw-Down Baseplate** | `screw_baseplate` | A countersunk screw hole at each cell centre so the plate fixes down to a drawer or bench. |
| **Magnet Baseplate** | `magnet_baseplate` | Four magnet pockets per cell (inset from the corners) so a bin with corner magnets snaps down. |
| **Weighted Frame** | `weighted_frame` | A solid perimeter skirt hanging below the plate so it sits stable on a desk without fixings (fill the skirt for extra mass). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Grid | `nx` / `ny` | 2 / 2 | Cells across X / Y (capped at 4 x 4). |
| Grid | `floor_th` | 4.0 mm | Solid floor below the cell sockets. |
| Fixing | `screw_d` / `screw_head_d` | 4.4 / 8.5 mm | M4 screw clearance + head counterbore (`screw_baseplate`). |
| Fixing | `magnet_d` / `magnet_h` | 6.2 / 2.2 mm | Magnet pocket bore + depth (`magnet_baseplate`). |
| Fixing | `skirt_h` | 8.0 mm | Perimeter skirt depth (`weighted_frame`). |

## The Gridfinity socket (why bins seat, and it stays watertight)

Each cell carries the real Gridfinity **bin-foot chamfer stack** — a 0.8 mm 45°
lead-in, a 1.8 mm straight run and a 2.15 mm 45° lower bevel — built as **stacked
lofted frusta** (a loft to a flat bottom, **never a revolve of a cut profile**,
which would yield a multi-component non-watertight mesh). Each socket is **cut
individually** from the slab, which is far faster than fusing one giant cutter.
Screw counterbores and magnet pockets are **bores that vent to the underside**;
the skirt is a **solid ring unioned with overlap**. The blank is filleted (3.75 mm
Gridfinity corner radius) before the sockets are cut. The grid is capped at
**4 x 4** so even the largest plate renders well under the time budget.

## Presets

- **2x3 Drawer Baseplate** — a screw-down plate for a shallow drawer.
- **2x2 Magnet Baseplate** — a magnet plate for quick-swap bins.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Gridfinity 42 mm Baseplate** (`grid`, *Gridfinity 42 mm*) — the cell field
    defined by `nx`, `ny`. Mates `grid-hub`, `gridfinity`, `cabinet-bin`,
    `cutlery-tray`.
  - **Screw / Magnet Fixing** (`bolt_pattern`, *internal*) — the fixing pattern
    defined by `screw_d`, `magnet_d`.
- **Material awareness:** `tolerance_by_material` is declared — the socket fit and
  magnet pockets tune per material/printer.
- **Societal benefit:** Gridfinity is the open, community-owned 42 mm storage grid
  any bin can share; a printed baseplate anchors a Gridfinity field to any drawer
  or bench on demand.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- All shipped modes and per-mode extreme parameter cases render **watertight**,
  single-body; a full 4 x 4 plate renders in roughly 16 s.
