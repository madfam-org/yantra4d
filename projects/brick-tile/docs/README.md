# Building-Brick Compatible Tile

Plates, tiles and adapters that clutch with the ubiquitous **construction-brick
system**, generated with **CadQuery** (B-Rep): an **8 mm stud pitch** with
**Ø4.8 mm studs** and hollow underside tubes, so a printed part snaps onto any
brick from the same family.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> This cartridge produces geometry *compatible with* the 8 mm construction-brick
> standard. It is an independent open-hardware design and is not affiliated with,
> nor endorsed by, any brick manufacturer.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Studded Plate** | `stud_plate` | The load-bearing building element: a hollow-underside shell with an *m × n* stud array on top and clutch tubes underneath. |
| **Smooth Tile** | `smooth_tile` | The same footprint and underside clutch, but a flat top — for smooth surfaces and lettering blanks. |
| **Base Adapter** | `base_adapter` | A thicker studded slab with a solid bottom and counterbored mount holes — bolts a brick build to a wall, desk or another surface. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Footprint | `cols` / `rows` | 4 / 2 | Stud array size (X × Y). |
| Brick Geometry | `pitch` | 8.0 mm | Stud-to-stud spacing (the standard). |
| Brick Geometry | `stud_dia` / `stud_h` | 4.8 / 1.8 mm | Stud diameter and height. |
| Brick Geometry | `plate_h` | 3.2 mm | Body height (1 plate; a brick = 9.6 mm). |
| Brick Geometry | `wall` | 1.5 mm | Wall / top thickness of the hollow shell. |
| Brick Geometry | `tube_od` / `tube_id` | 6.5 / 4.9 mm | Underside clutch tube outer / inner diameter. |
| Base Adapter | `adapter_h` | 6.0 mm | Base-adapter slab height. |
| Base Adapter | `mount_dia` | 4.2 mm | Counterbored mount hole (M4 clearance). |

## How the clutch works

Bricks hold together by friction between the **studs** of one part and the
**underside tubes** of the part above. The studs sit on the 8 mm grid at
`stud_dia`; the clutch tubes sit on the *interior* crossings of the grid — the
`(cols−1) × (rows−1)` points between studs — at `tube_od` / `tube_id`. The tube
inner wall grips four surrounding studs, and the outer wall bears against the
skirt, giving the familiar clutch. The plate body is hollowed from below (an open
shell that vents to outside — no trapped void), so any part built at the same
pitch stacks with any other. A single 1×1 element is printed solid; from 2×2 up,
the underside tubes appear automatically.

## Presets

- **4×2 Studded Plate** — a standard building plate.
- **4×2 Smooth Tile** — a flat-top finishing tile with the same clutch.
- **4×2 Wall Adapter** — a bolt-down base for mounting builds.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **8 mm Stud Grid** (`grid`, *construction brick 8mm*) — the stud lattice
    defined by `pitch`, `stud_dia`, `stud_h`. Any part on the same pitch clutches
    with any brick of the family.
  - **Underside Clutch Tube** (`socket`, *construction brick 8mm*) — the tube
    ring defined by `tube_od`, `tube_id` that grips the studs below.
- **Material awareness:** `tolerance_by_material` is declared — stud and tube
  diameters are exposed so the clutch fit tunes per material / printer (clone
  bricks vary by fractions of a millimetre).
- **Societal benefit:** the 8 mm stud grid is the most widely owned construction
  toy interface; printable compatible plates, tiles and adapters let families
  repair, extend and remix builds from open files instead of discarding sets.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The plate is a solid box hollowed from below (open bottom → vented); studs are
  solid cylinders unioned on top; clutch tubes are hollow rings whose bore opens
  to the bottom face. The base adapter keeps a solid bottom, omits the stud at
  each mount cell so the counterbore never clips a neighbour, and cuts through
  holes (vented both faces). All shipped modes and extreme-parameter cases render
  **watertight**, single-body.
