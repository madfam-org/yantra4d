# Modular Grid Interoperability Hub

**The Commons interoperability keystone (#300).** One hub, generated with
**CadQuery** (B-Rep), that bridges the major shop / desk organization grids so a
bin, tool, or accessory built for one system mounts on another. Real standard
geometry for each grid.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Grids bridged

| Grid | Standard geometry |
| :--- | :--- |
| **Gridfinity** | 42 mm cell; baseplate socket built with the standard chamfer stack (0.8 mm @ 45° + 1.8 mm straight + 2.15 mm @ 45°), 0.5 mm inter-cell gap, 3.75 mm outer radius. |
| **Multiboard** | 25 mm cell pitch with the board's core cell holes. |
| **French cleat** | a 45° interlocking wall rail (mating hook on the hub's back). |
| **Pegboard** | 1 in (25.4 mm) hole pitch, 1/4 in (6.35 mm) posts, on the hub's back. |

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Gridfinity → Cleat** | `gridfinity_cleat` | Gridfinity baseplate cell(s) on the front + a French-cleat hook on the back: hang Gridfinity bins on a cleat wall. |
| **Pegboard → Gridfinity** | `pegboard_grid` | Pegboard hook posts on the back + a Gridfinity cell on the front: put Gridfinity on a pegboard. |
| **Multiboard ↔ Gridfinity** | `multiboard_tile` | A Multiboard-pitch tile fused to a Gridfinity baseplate cell: connect the 25 mm and 42 mm grids. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Gridfinity Cells | `gx` / `gy` | 1 / 1 | Number of 42 mm Gridfinity cells (1–4 each). |
| Gridfinity Cells | `base_th` | 5 mm | Solid floor below the Gridfinity sockets. |
| Body & Mount | `back_th` | 6 mm | Back plate / tile thickness. |
| Body & Mount | `cleat_ang` | 45° | French-cleat rail bevel angle. |
| Body & Mount | `wall` | 2.4 mm | General wall thickness. |

## Presets

- **1×1 Gridfinity Cleat Mount** — one Gridfinity cell on a French cleat.
- **2×1 Gridfinity Pegboard Mount** — a 2-wide Gridfinity cell on pegboard.
- **Multiboard ↔ Gridfinity Tile** — the grid bridge tile.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Gridfinity 42 mm Baseplate** (`grid`, *Gridfinity 42 mm*) — the 42 mm socket
    grid (`gx`, `gy`, `base_th`). `compatible_with: [cabinet-bin, cutlery-tray]`.
  - **Multiboard 25 mm Grid** (`grid`, *Multiboard 25 mm*) — the 25 mm tile.
  - **French-Cleat Rail** (`rail`, *French cleat 45°*) — the back cleat hook
    (`cleat_ang`, `back_th`).
  - **Pegboard Hooks** (`snap`, *Pegboard 1 in / 6.35 mm*) — the back peg posts.
- **Material awareness:** socket / hook fit tunes with `base_th`, `back_th`, and
  `wall` per printer; `tolerance_by_material` is declared.
- **Societal benefit:** the maker world has fractured into rival organization
  grids and a bin built for one will not mount on another; as the Commons' #300
  keystone this hub is the single adapter that bridges them — Gridfinity on a
  cleat wall, a pegboard carrying a Gridfinity cell, Multiboard meeting Gridfinity
  — so the whole catalog becomes mountable anywhere.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained + sandbox-safe: params via `PARAM(lambda: name, default)`, final
  solid assigned to `result`.
- **Watertight by construction:** the Gridfinity chamfer-stack socket is a
  **loft to a flat bottom** (never a revolve of a cut profile, which would leave
  a zero-volume seam); pegboard posts and the cleat rail are **solid** unions with
  overlap (post down-hooks are seated to overlap the post so nothing detaches);
  every pocket / hole opens to a face (no trapped void); corners are filleted
  before feature cuts. All three modes and the MIN/MAX extremes — up to a 4×4
  Gridfinity grid — render watertight with a single body.
