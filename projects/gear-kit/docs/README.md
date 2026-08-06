# Gear / Linkage Learning Kit

A snap-together **STEM kit** for teaching gear ratios, torque and linkages,
generated with **CadQuery** (B-Rep). Every piece shares one interface — a square
**peg grid on an 8 mm pitch** with **Ø4 mm pegs** — so involute spur gears,
idlers and linkage bars relocate to any grid node and mesh correctly.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Spur Gear + Crank** | `gear_plate` | A true involute spur gear (ISO 53 / DIN 867, 20° pressure angle) with a central hub that drops onto a grid peg and turns freely, plus an optional off-centre finger crank. |
| **Linkage Bar** | `link_bar` | A flat bar with a row of grid-pitch pivot holes — the four-bar / pantograph element that couples gear axles. |
| **Peg Baseboard** | `peg_base` | A slab with an *m × n* array of upright pegs on the grid pitch; gears and links mount and rotate on the pegs. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Peg Grid | `grid_pitch` | 8.0 mm | Peg-to-peg spacing shared by every part. |
| Peg Grid | `peg_dia` | 4.0 mm | Upright peg diameter (hubs turn on it). |
| Peg Grid | `peg_clear` | 0.4 mm | Bore-over-peg running clearance. |
| Gear | `module` | 2.0 mm | ISO 53 module: pitch dia = module × teeth. |
| Gear | `teeth` | 16 | Tooth count; ratio = driven / driver teeth. |
| Gear | `pressure_angle` | 20° | Involute pressure angle (DIN 867). |
| Gear | `gear_thick` / `hub_height` | 6.0 / 5.0 mm | Face width and hub rise. |
| Gear | `crank` | on | Add a finger-crank knob. |
| Linkage | `link_holes` / `link_thick` | 4 / 4.0 mm | Pivot-hole count and bar thickness. |
| Baseboard | `base_cols` / `base_rows` | 4 / 4 | Peg array size (X × Y). |
| Baseboard | `base_thick` / `peg_len` | 4.0 / 10.0 mm | Slab thickness and peg height. |

## Why the parts interoperate

The kit rests on a single **Common Denominator Geometry**: a square grid of
round pegs on `grid_pitch`. Gear hubs and linkage holes are bored to
`peg_dia + peg_clear`, a running fit, so any part spins on any peg. Because the
teeth are sampled from the **true involute** of the base circle (not a faceted
approximation), any two gears sharing `module` and `pressure_angle` engage
correctly — a 16- and 32-tooth pair on adjacent grid nodes gives an exact 2:1
reduction. The linkage bar's holes sit on the same pitch, so it bridges two
peg-mounted axles into a four-bar mechanism. Grow the set indefinitely: every
new gear stays compatible with the ones already printed.

## Presets

- **2:1 Reduction Gear (16T)** — a 16-tooth module-2 gear with crank.
- **Four-Bar Linkage Arm** — a 4-hole bar on the 8 mm pitch.
- **4×4 Classroom Baseboard** — a 16-peg board the whole set mounts on.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **8 mm Peg Grid** (`grid`, *internal peg grid 8mm*) — the square peg lattice
    defined by `grid_pitch`, `peg_dia`, `peg_clear`. Any part built at the same
    pitch mounts on any baseboard.
  - **Involute Gear Mesh** (`profile`, *ISO 53 / DIN 867, 20°*) — the tooth
    flank defined by `module`, `teeth`, `pressure_angle`; gears mesh iff they
    share module and pressure angle.
- **Material awareness:** `tolerance_by_material` is declared — `peg_clear` is
  exposed so the running fit tunes per material / printer.
- **Societal benefit:** physical gear-ratio and linkage manipulatives make
  reduction, torque and mechanical advantage tangible; the shared grid and true
  involute teeth let a classroom grow a compatible open set instead of buying
  closed proprietary kits.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The gear body is one extrusion of the closed involute wire; the hub and crank
  are solid cylinders unioned coaxially, with the axle bore cut through both
  faces (vented — no trapped void). The baseboard pegs are solid cylinders
  unioned onto a fillet-cleaned slab. All shipped modes and extreme-parameter
  cases render **watertight**, single-body.
