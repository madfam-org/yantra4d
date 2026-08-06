# Drawer Divider / Insert Grid

An adjustable cell grid generated with **CadQuery** (B-Rep), sized to the
**overall drawer envelope** you give it. Pick a column and row count and the
cells resize to fill the space. Print a floored tray, a bottomless drop-in grid,
or a single strip to hand-assemble a custom layout.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Divided Tray** | `tray` | Solid-bottom organiser: floor + perimeter walls + partitions, softened rim. |
| **Drop-in Grid** | `dividers` | Bottomless interlocking grid that drops straight into an existing drawer. |
| **Single Strip** | `single_divider` | One slotted strip; combine several to hand-build a grid. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Drawer Size | `overall_w` / `overall_d` / `overall_h` | 200 / 150 / 50 mm | Interior width, depth and wall height to fill. |
| Cell Grid | `cols` / `rows` | 3 / 2 | Number of cell columns (X) and rows (Y). |
| Cell Grid | `interlock` | on | Slotted half-lap so cross-dividers lock together without a floor. |
| Walls & Floor | `wall` | 1.6 mm | Wall / partition thickness. |
| Walls & Floor | `floor` | 1.6 mm | Bottom thickness (tray only). |

## Presets

- **Cutlery Tray (5×1)** — 400×120×45, five long channels.
- **Junk-Drawer Grid (4×3)** — 240×180×50 bottomless drop-in grid.
- **Deep Tool Bins (3×2)** — 210×150×90 floored tray, thicker walls.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Adjustable Cell Grid** (`grid`, internal) — the core interface. `cols`,
    `rows`, `overall_w`, `overall_d`, `wall` and `interlock` define the partition
    lattice. The tray, the drop-in grid and the single strip all derive their
    partition positions from the same grid, so a strip printed at a given
    `cols`/`overall_w` half-laps into a grid printed at the same values.
- **Material awareness:** `tolerance_by_material` is declared so the half-lap
  slot width can be tuned per material/printer for a snug-but-assemblable fit.
- **Societal benefit:** turns any drawer into right-sized cells on demand,
  replacing multiple bought organiser sets and their packaging.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The bottomless grid is a legitimately closed solid (perimeter frame unioned
  with notched partitions); all shipped modes and presets export **watertight**.
