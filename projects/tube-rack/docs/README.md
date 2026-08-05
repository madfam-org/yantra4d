# Test-Tube / Vial Rack

A benchtop rack that holds round test tubes or vials in a `cols x rows` grid,
generated with **CadQuery** (B-Rep). Sized to your tube diameter with a printable
slip clearance.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Rack (cradles)** | `rack` | Solid block with a grid of blind tube wells + optional feet. |
| **Drain Rack (through)** | `rack_drain` | The same grid bored all the way through so washed tubes drain and air-dry. |
| **Single Row** | `single_row` | A compact one-row rack for the benchtop. |

Each mode dispatches on `target_part`, and the manifest `parts[]` ids match the
dispatched values (`rack` / `rack_drain` / `single_row`) so every mode renders
its own geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Tubes | `tube_dia` | 16 mm | Outer diameter of the tube/vial body. |
| Tubes | `clearance` | 0.8 mm | Radial slip gap so tubes drop in/out. |
| Tubes | `well_depth` | 30 mm | Blind cradle depth (blind modes). |
| Grid | `cols` / `rows` | 6 / 4 | Tubes across (X) and deep (Y). |
| Grid | `well_pitch` | 0 (auto) | Centre spacing; 0 derives it from tube dia. |
| Body | `wall` | 3.0 mm | Material between/around bores. |
| Body | `floor` | 3.0 mm | Solid base under blind cradles. |
| Body | `feet` | on | Four small corner feet. |
| Body | `drain` | off | A small drain hole in each blind cradle. |

## Presets

- **Microtube 9 mm SBS (8x12)** — 8 mm tubes at 9 mm pitch, SBS-style density.
- **16 mm Test Tubes (6x4)** — classic test-tube rack.
- **Drying Rack (through)** — through-bored 8x4 for washing and drying.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Tube Well Array** (`grid`, *SBS 9mm pitch (small)*) — the bore grid, defined
    by `tube_dia`, `cols`, `rows`, `well_pitch`, `clearance`. Leaving `well_pitch`
    at 0 for small tubes yields the SBS-style 9 mm density used by microplate
    consumables; larger tubes auto-space by diameter + wall.
- **Material awareness:** `clearance` is exposed so the slip fit can be tuned per
  material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** on-demand labware sized to any tube diameter — clinics,
  schools, and field labs print sample organization matched to what they already
  have, instead of buying fixed-format racks.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`.
- Blind cradles keep a solid `floor` beneath them, through-bores are full manifold
  cuts, and feet are unioned pads — all shipped presets render **watertight**.
