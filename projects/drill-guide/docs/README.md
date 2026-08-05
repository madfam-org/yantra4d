# Drill Guide / Bushing Jig

A drill jig generated with **CadQuery** (B-Rep) that guides a bit — or a
press-fit steel drill bushing — to **repeatable** hole positions. A solid guide
block carries full-depth bores; the block thickness keeps the bit square. Choose
a linear row, a rectangular grid, or an edge guide with a registration fence.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Linear Guide** | `linear_guide` | A single row of bores at `pitch`, `holes` count. |
| **Grid Guide** | `grid_guide` | A `rows` × `cols` rectangular array of bores. |
| **Edge Guide** | `edge_guide` | Bores set back `edge_offset` from a registration lip that hooks the workpiece edge. |

Each mode's part id equals the `target_part` the code dispatches on, so every
mode renders its own distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bore & Bushing | `hole_dia` | 6.0 mm | Nominal drill / bushing diameter. |
| Bore & Bushing | `bushing_fit` | 0.2 mm | Per-side oversize so a printed hole accepts a steel bushing (0 = raw drill guide). |
| Guide Block | `block_thick` | 12.0 mm | Guide depth (bushing length) — longer keeps the bit square. |
| Guide Block | `wall` | 5.0 mm | Material surrounding each bore. |
| Hole Pattern | `pitch` | 25.0 mm | Centre-to-centre hole spacing. |
| Hole Pattern | `holes` | 4 | Holes in a linear/edge row. |
| Hole Pattern | `rows` / `cols` | 3 / 3 | Grid dimensions. |
| Hole Pattern | `edge_offset` | 15.0 mm | Bore setback from the registration edge. |
| Registration Fence | `fence` / `fence_h` / `fence_t` | on / 8.0 / 4.0 mm | Lip that indexes off the workpiece edge. |

## Printer hole-shrinkage note

FDM and SLA holes print **undersize**. For a raw drill guide leave
`bushing_fit = 0`. To **press-fit a steel drill bushing**, oversize the bore by
your printer's measured hole shrinkage — typically **+0.1–0.3 mm per side** — via
`bushing_fit`. `shrinkage_compensation` and `tolerance_by_material` are declared
so the allowance can be tuned per material/printer.

## Presets

- **Shelf-Pin Row (5mm @32)** — the cabinet 32 mm system, six 5 mm bores.
- **Pegboard Grid (6mm @25)** — a 4×4 array at 25 mm pitch.
- **Dowel Edge Jig (8mm bushed)** — 8 mm bushed bores 9.5 mm off the edge with a fence.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Drill Bushing Bore** (`socket`, internal) — the guided hole itself,
    defined by `hole_dia`, `bushing_fit`, `block_thick`, `pitch`, `holes`,
    `rows`, `cols`. Any bushing sized to the same bore drops in.
  - **Hole Grid Pattern** (`grid`, internal) — `pitch`, `rows`, `cols`, `holes`.
- **Material awareness:** `shrinkage_compensation` + `tolerance_by_material` — the
  bushing oversize is exposed so the fit is tunable per material/printer.
- **Societal benefit:** turns a printer into a machine-shop jig maker —
  repeatable, square holes without a drill press or layout marking.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
