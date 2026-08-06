# Cuvette & Vial Rack

A benchtop rack that holds spectrophotometer cuvettes (the standard **10 mm
square** footprint) and round sample vials in a configurable grid of pockets,
generated with **CadQuery** (B-Rep). Choose a cuvette rack, a vial rack, or a
combo block with both.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Cuvette Rack** | `rack` | A grid of square 10 mm cuvette pockets. |
| **Vial Rack** | `vial_rack` | A grid of round vial pockets. |
| **Combo Rack** | `combo_rack` | Cuvettes on the back rows, round vials on the front rows. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Vessels | `cuvette` | 10.0 mm | Square cuvette footprint (spectrophotometry standard). |
| Vessels | `vial_dia` | 12.0 mm | Round vial diameter. |
| Grid | `cols` / `rows` | 6 / 4 | Pockets across / deep. |
| Body | `clearance` | 0.4 mm | Per-side slip gap. |
| Body | `wall` | 3.0 mm | Material between/around pockets. |
| Body | `depth` | 22.0 mm | Pocket depth. |
| Body | `floor` | 3.0 mm | Solid base under the pockets. |

## Presets

- **Cuvette Rack 6×4** — the standard 10 mm cuvette.
- **HPLC Vials (12 mm)** — 8×5 round-vial grid.
- **Combo Bench Rack** — cuvettes + vials in one block.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Cuvette Array** (`grid`, `10mm cuvette`) — the pocket grid, defined by
    `cuvette`, `vial_dia`, `cols`, `rows`, `clearance`. Any rack at the 10 mm
    footprint accepts standard cuvettes.
- **Material awareness:** `tolerance_by_material` is declared — pocket clearance
  tunes to the print material.
- **Societal benefit:** standardises sample handling for teaching and field labs
  using the universal 10 mm cuvette, printable on demand.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- Every pocket is a blind recess leaving a solid floor, so all outputs are
  **watertight**.
