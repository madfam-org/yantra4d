# Pegboard Hook Set

A set of parametric **pegboard accessories** generated with **CadQuery** (B-Rep).
Each part carries peg / insert geometry modeled to the real board pitch, so a
printed part actually seats in the holes of the board you already own.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **J-Hook** | `hook` | A hook to hang tools, cables, or straps, with an up-return at the tip. |
| **Hanging Bin** | `bin` | A small open bin (walls + floor + front vent slot) that hangs on the pegs. |
| **Tool Holder** | `tool_holder` | A forward tongue with a vertical bore of `tool_dia` that a round tool drops through and hangs by. |

The studio dispatches the active part via `target_part` (`hook` / `bin` /
`tool_holder`).

## Board standards

| `board_standard` | Pitch | Hole | Peg geometry | Standard |
| :--- | :--- | :--- | :--- | :--- |
| `us_1inch` | 25.4 mm square grid | ~6 mm round | Round peg + downward retention lip | 1-inch pegboard (Wall Control / DuraBoard) |
| `skadis` | 40 mm slotted grid | ~5 mm × 15 mm vertical slot | Flat tongue + downward catch behind the web | IKEA SKÅDIS |

For **1-inch** boards, two pegs are spaced 25.4 mm apart to fit adjacent rows.
For **SKÅDIS**, pegs are 40 mm apart and use a flat tongue sized to the slot
with a hook that catches behind the board web.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Board & Pegs | `board_standard` | `us_1inch` | `us_1inch` or `skadis`. |
| Board & Pegs | `peg_count` | 2 | 1 or 2 vertically stacked pegs. |
| Back Plate | `plate_w` | 26.0 mm | Plate width (hook / tool holder). |
| Back Plate | `plate_thick` | 4.0 mm | Plate thickness (stiffness / load). |
| Hook | `hook_reach` | 35.0 mm | How far the hook projects out. |
| Hook | `hook_dia` | 6.0 mm | Hook arm round-stock diameter. |
| Hook | `hook_up` | 14.0 mm | Upward return at the tip. |
| Bin | `bin_w` / `bin_d` / `bin_h` | 60 / 45 / 45 mm | Bin interior size and projection. |
| Bin | `bin_wall` | 2.4 mm | Bin wall thickness. |
| Tool Holder | `tool_dia` | 20.0 mm | Round tool shaft diameter cradled. |
| Tool Holder | `tool_ring` | 6.0 mm | Material around the tool hole. |

## Presets

- **1-inch Utility Hook** — a 2-peg 35 mm hook for a standard pegboard.
- **SKÅDIS Long Hook** — a deeper 55 mm hook on a 40 mm SKÅDIS pitch.
- **1-inch Parts Bin** — a 70 × 50 × 55 mm hanging bin.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Pegboard Peg Pattern** (`grid`, 1-inch pegboard / IKEA SKÅDIS) — the peg /
    insert geometry that mates with the board, defined by `board_standard`,
    `peg_count`, and `plate_thick`. Any part built for the same standard fits the
    same board.
  - **Tool Cradle Bore** (`socket`, internal) — the vertical bore in the tool
    holder, defined by `tool_dia` and `tool_ring`.
- **Material awareness:** peg and slot dimensions carry a small clearance under
  the nominal pitch so the fit tunes per material / printer; `tolerance_by_material`
  is declared.
- **Societal benefit:** pegboard is the ubiquitous open standard for wall
  organization. Printing accessories to the exact tool and the board you already
  own eliminates blister-pack hooks and lets one board serve any shop, kitchen,
  or craft wall.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The J-hook is built as one solid overlapping into the back plate, and the bar
  root is seated in a peg-free Z-band, so every mode and preset renders
  **watertight**.
