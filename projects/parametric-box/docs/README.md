# Parametric Storage Box

A fits-anything storage box generated with **CadQuery** (B-Rep), sized by its
**interior** dimensions so the printed cavity is exactly what you asked for.
Independent wall/floor control, rounded corners, an optional press-fit lid, and
an optional interior divider grid.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Box** | `box` | The container: hollow body, optional dividers, softened rim. |
| **Lid** | `lid` | A press-fit lid whose skirt nests inside the box walls. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Interior Size | `inner_w` / `inner_d` / `inner_h` | 80 / 60 / 40 mm | Usable interior X / Y / Z. |
| Walls & Corners | `wall` | 2.0 mm | Side wall thickness. |
| Walls & Corners | `floor` | 2.0 mm | Bottom thickness. |
| Walls & Corners | `corner_r` | 4.0 mm | Outer corner rounding (0 = sharp). |
| Walls & Corners | `fillet_top` | on | Round the top rim. |
| Dividers | `div_x` / `div_y` | 0 / 0 | Interior partitions along X / Y. |
| Dividers | `div_thick` | 1.6 mm | Partition thickness. |
| Lid | `lid_height` | 8.0 mm | Skirt nesting depth. |
| Lid | `lid_clear` | 0.3 mm | Per-side clearance for a printable press fit. |

## Presets

- **Small Parts Tray (2×2)** — 90×90×25 with a 1×1 divider cross.
- **Deep Bin** — 70×50×90, thicker walls.
- **Lidded Case (base)** — 100×60×30 paired with the Lid mode.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Press-Fit Lid Seam** (`snap`, internal) — the box/lid mating geometry,
    defined by `inner_w`, `inner_d`, `lid_height`, `lid_clear`, `wall`. Any lid
    generated at the same interior size + clearance fits the box.
  - **Interior Divider Grid** (`grid`, internal) — `div_x`, `div_y`, `div_thick`.
- **Material awareness:** clearance is exposed (`lid_clear`) so the press fit can
  be tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** the most-printed functional object class — storage sized
  to the exact space and contents, reducing packaging waste and store dependency.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
