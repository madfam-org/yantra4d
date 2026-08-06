# Tool Holder (CNC / Lathe)

A shop organizer generated with **CadQuery** (B-Rep) that holds cutting tools by
their shank. A block carries an array of correctly-sized bores or pockets for the
selected tool family — straight-shank end mills, **ER collets**, indexable lathe
inserts, or a graduated drill index — and can be freestanding, wall-mounted, or
dropped into a drawer as a low tray.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Block** | `block` | A freestanding block with the tool array. |
| **Wall Rack** | `wall_rack` | The block with a back plate + wall screw holes. |
| **Drawer Insert** | `drawer_insert` | A low tray version for a drawer. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Tool | `tool_type` | end_mill | `end_mill` / `er_collet` / `lathe_insert` / `drill_index`. |
| Tool | `shank_dia` | 6 mm | Straight-shank diameter (end mill family). |
| Tool | `er_series` | ER20 | ER collet series → bore diameter (ER11–ER32). |
| Tool | `insert_w` | 14 mm | Square pocket size (lathe insert family). |
| Tool | `drill_min` / `drill_step` | 2 / 1 mm | Drill-index start size and increment. |
| Array | `slots` / `rows` | 8 / 1 | Openings per row and number of rows. |
| Array | `pitch` | 25 mm | Centre-to-centre spacing. |
| Block | `bore_depth` / `block_h` | 22 / 30 mm | Bore depth and block height. |
| Wall Mount | `screw_dia` | 4.5 mm | Wall screw clearance (Wall Rack mode). |

## Presets

- **6 mm End Mill Block (8)** — eight Ø6 bores in a freestanding block.
- **ER20 Collet Wall Rack** — six ER20 bores with a wall back plate.
- **Drill Index 2–14 mm** — a graduated 13-hole drill index.
- **Lathe Insert Drawer Tray** — a 6×2 shallow tray of insert pockets.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Tool Shank Bore** (`socket`, *ER / straight-shank*) — the per-tool opening,
    defined by `tool_type`, `shank_dia`, `er_series`, `bore_depth`. Bores are sized
    to real ER collet ODs and straight shank diameters.
  - **Tool Array Grid** (`grid`, internal) — `slots`, `rows`, `pitch`.
  - **Wall Screw Pattern** (`bolt_pattern`, internal) — `screw_dia` (Wall Rack).
- **Material awareness:** `tolerance_by_material` is declared so the bore fit can
  be tuned per material and printer.
- **Societal benefit:** shank-sized organization for machinists and hobby shops —
  one holder family sizes bores to end mills, ER collets, lathe inserts, or a
  graduated drill set, protecting cutting tools without buying dedicated trays.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`. `target_part`
  dispatches which mode part is built.
- All shipped presets and defaults render **watertight**.
