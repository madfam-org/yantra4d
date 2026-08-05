# Assembly / Welding Fixture

A positioning aid generated with **CadQuery** (B-Rep) that holds parts in a
repeatable location during assembly, welding, gluing, or drilling. A base plate
carries locating pins (in a selectable pattern), optional raised stops forming a
corner reference, or a V-groove for round stock — plus mounting holes to bolt the
fixture to a bench.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Pin Plate** | `pin_plate` | Base plate + array of locating pins (corners / grid / linear). |
| **Stop Fixture** | `stop_fixture` | Base plate + two perpendicular edge fences forming an L / corner reference. |
| **V-Block** | `v_block` | A block with a V-groove that cradles round stock. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Base Plate | `base_w` / `base_d` / `base_t` | 120 / 90 / 10 mm | Plate width / depth / thickness. |
| Locating Pins | `pin_pattern` | corners | `corners` / `grid` / `linear`. |
| Locating Pins | `pin_dia` / `pin_height` | 8 / 18 mm | Pin diameter and height. |
| Locating Pins | `grid_cols` / `grid_rows` | 3 / 2 | Grid pattern layout. |
| Locating Pins | `pin_count` | 4 | Linear pattern count. |
| Stops & Fences | `stop_h` / `stop_t` | 15 / 8 mm | Fence height and thickness. |
| V-Groove | `v_angle` / `v_stock_dia` | 90° / 25 mm | Included angle and nominal round-stock diameter. |
| Mounting | `mount_dia` / `mount_inset` | 6.5 / 10 mm | Bolt-down hole size and edge inset. |

## Presets

- **Corner Locator Plate** — 120×90 plate, four corner pins.
- **Grid Locating Bed (4×3)** — 200×150 bed with a 4×3 pin grid.
- **Welding Corner Jig** — 150×150 with tall corner fences.
- **Pipe V-Block (Ø25)** — a V-block for Ø25 round stock.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Locator Pin Pattern** (`bolt_pattern`, internal) — the array of locating
    pins, defined by `pin_pattern`, `pin_dia`, `pin_inset`, `grid_cols`,
    `grid_rows`, `pin_count`. Any part drilled to the same pin pattern registers
    on the fixture.
  - **Bench Mounting Pattern** (`bolt_pattern`, internal) — `mount_dia`,
    `mount_inset`; a repeatable four-corner bolt-down.
  - **Round-Stock V-Seat** (`profile`, internal) — `v_angle`, `v_stock_dia`.
- **Material awareness:** `tolerance_by_material` is declared so pin/stop fits can
  be tuned per material and printer.
- **Societal benefit:** repeatable workholding for makers and small shops —
  locate, clamp, and reproduce part positions without buying dedicated tooling.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`. `target_part`
  dispatches which mode part is built.
- All shipped presets and defaults render **watertight**.
