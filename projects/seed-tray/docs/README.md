# Seed Tray / Cell Insert

A seed-starting tray generated with **CadQuery** (B-Rep): an array of **tapered
cells** (wide at the top, narrower at the bottom so the plug pops out) each with a
drainage hole. Drop it into a standard 1020 propagation flat, or use it
free-standing. A single-row cell strip and a vented humidity dome complete the set.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Cell Tray** | `tray` | `cols`×`rows` tapered cells with drainage, optional 1020 lip. |
| **Cell Strip** | `cell_strip` | A single row of cells — a small propagation strip. |
| **Humidity Dome** | `humidity_dome` | A vented cover that sits over the tray during germination. |

Each mode's `parts[]` id equals the `target_part` the code dispatches on.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cell Grid | `cols` / `rows` | 6 / 4 | Cells across / down. |
| Cell Shape | `cell_top` | 30 mm | Cell opening width at the top. |
| Cell Shape | `cell_taper` | 6 mm | How much narrower at the bottom. |
| Cell Shape | `depth` | 45 mm | Cell depth. |
| Options | `drainage` | on | One hole per cell bottom. |
| Options | `fit_1020` | off | Rim lip to seat in a 1020 flat. |
| Options | `wall` | 2.0 mm | Wall between cells / outer wall. |

## Presets

- **24-Cell Tray (6×4)** — the standard starter tray.
- **Deep 9-Cell (3×3)** — deeper cells for larger transplants.
- **6-Cell Strip** — a single sowable row.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Seed Cell Array** (`grid`, 1020 tray) — the cell grid, defined by `cols`,
    `rows`, `cell_top`, `depth`. The `fit_1020` lip mates the array to a standard
    1020 propagation flat.
- **Material awareness:** `wall` and taper tune per material/printer;
  `tolerance_by_material` is declared.
- **Societal benefit:** grow-your-own from seed — reusable printed cell trays replace
  flimsy single-use six-packs, starting dozens of seedlings cheaply.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The `tray` and `cell_strip` are solids: every cell cavity + drainage hole is unioned
  into ONE compound cutter and removed with a **single** boolean cut, which keeps
  large arrays (up to 12×12) fast and the mesh **watertight**.
- The `humidity_dome` is intentionally an **open cover** — a walls-and-roof shell with
  an open bottom (a lid that fits over the tray has no floor), so it is a valid open
  shell rather than a closed watertight solid. The two functional parts (`tray`,
  `cell_strip`) are watertight.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
