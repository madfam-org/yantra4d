# Spice / Jar Rack

A jar organizer generated with **CadQuery** (B-Rep). Holds round jars in a row of
circular cradles sized to the jar body. Set the jar diameter and count, arrange
them across one or more tiers, and optionally add a magnet-pocket back so the rack
clamps to steel.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Rack** | `rack` | A shelf with N through-bored circular cradles; optional magnet-pocket back wall. |
| **Magnetic Lid Holder** | `magnetic_lid_holder` | A plate of 6 × 2 mm magnet pockets that grabs the steel lids of jars hung under a shelf. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Jars | `jar_dia` | 45 mm | Jar body diameter. |
| Jars | `clearance` | 1.0 mm | Radial gap so a jar drops in (rack mode). |
| Layout | `cols` | 5 | Cradles across. |
| Layout | `rows` | 1 | Rows / tiers. |
| Layout | `wall` | 3.0 mm | Material between and around cradles. |
| Layout | `shelf_thick` | 6.0 mm | Cradle shelf thickness (rack mode). |
| Magnets | `magnet` | off | Rear wall with 6 × 2 mm magnet pockets (rack mode). |

## Presets

- **Five-Jar Spice Strip** — 5 × Ø45 in one row.
- **Two-Tier Spice Rack** — 4 × Ø50 over two tiers, magnet back.
- **Under-Shelf Lid Holder** — 4 × 2 grid of magnet pockets.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Jar Cradle** (`pocket`, internal) — the circular cradle grid, defined by
    `jar_dia`, `cols`, `rows`, `clearance`.
  - **Disc Magnet Pocket (6×2 mm)** (`pocket`, internal) — the neodymium disc
    pockets, defined by `magnet`, `cols`, `rows`.
- **Material awareness:** `tolerance_by_material` declared; cradle `clearance` is
  exposed so the drop-in fit tunes per printer / material.
- **Societal benefit:** turns a jumble of spice jars and reused food jars into a
  tidy, wall- or shelf-mounted set sized to whatever jars you already own.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- **Watertight by design:** cradles are bored fully through the shelf, and magnet
  pockets are blind recesses in a plate always thicker than the pocket is deep, so
  a solid floor remains under each — every preset and extreme renders watertight.
