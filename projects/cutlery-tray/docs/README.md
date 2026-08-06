# Cutlery Drawer Tray

A drawer-filling cutlery tray generated with **CadQuery** (B-Rep), sized by its
**interior** dimensions with a configurable compartment grid. Reuses the shared
bin/tray body idiom (a five-wall shell + evenly spaced partition walls) that the
kitchen batch shares with `cabinet-bin`.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Straight Tray** | `tray` | N columns × M rows of straight compartments. |
| **Angled Tray** | `angled_tray` | Column dividers raked so cutlery lies at a slant. |
| **Expandable Segment** | `expandable` | One modular segment with side tabs that tile to any width. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Drawer Size | `inner_w` / `inner_d` / `inner_h` | 360 / 240 / 50 mm | Interior X / Y / Z. |
| Compartments | `cols` / `rows` | 5 / 1 | Columns across width, rows across depth. |
| Compartments | `rake_deg` | 20° | Compartment slant (angled tray). |
| Compartments | `seg_w` | 80 mm | Segment width (expandable). |
| Walls | `wall` | 2.0 mm | Wall, floor, divider thickness. |
| Walls | `corner_r` | 2.0 mm | Outer corner rounding (0 = sharp). |

## Presets

- **Standard 5-Slot Cutlery** — 360×240×50, five columns.
- **Angled Flatware** — 380×260×55, five columns raked 22°.
- **Modular Segment** — 90 mm-wide tiling segment.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:**
  - **Cutlery Compartments** (`grid`, internal) — the compartment grid, defined by
    `inner_w`, `inner_d`, `inner_h`, `cols`, `rows`, `wall`. The `expandable`
    segment carries side tabs/recesses so several print at the same height and
    tile to fill any drawer width.
- **Material awareness:** `wall` is exposed; `tolerance_by_material` is declared so
  divider fit and segment-tab clearance can be tuned per material.
- **Societal benefit:** a tray sized to the exact drawer eliminates the wasted gaps
  of one-size store trays; the expandable segment fills any drawer from tiling parts.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Straight dividers are unioned into the shell; raked dividers are rotated about Z
  and **intersected with the interior volume** so nothing pokes past the walls.
- The script is **self-contained** (sandbox-safe): parameters via
  `PARAM(lambda: name, default)`; the final solid is assigned to `result`.
