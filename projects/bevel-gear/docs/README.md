# Bevel / Miter Gear

A conical **bevel gear** for right-angle drives, generated with **CadQuery**
(B-Rep). The involute tooth profile is generated at the large (back) end from the
true involute of the base circle and **lofted** to a scaled copy toward the cone
apex, so the teeth taper along the pitch cone like a real bevel gear. Equal tooth
counts at a 90° shaft angle produce a **miter pair**.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Approximation note

Exact bevel-gear teeth have **spherical-involute (octoid)** flanks. This cartridge
uses the classic **Tredgold approximation**: each tooth is the *planar* involute
profile of the back cone, linearly lofted (scaled) toward the apex. The result
has a dimensionally-correct **pitch cone, module, and tooth count** and a
recognizable, printable, watertight bevel — adequate for maker-scale right-angle
drives, but **not** a substitute for precision spiral-bevel metrology.

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Bevel Gear** | `bevel` | A single conical gear with a solid back hub and axial bore. |
| **Miter Pair** | `bevel`, `bevel_mate` | Two equal bevels meshing at the shaft angle, sharing a pitch apex (a multi-body compound). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Gear Geometry | `m` | 3.0 mm | Module at the large (back) end. |
| Gear Geometry | `teeth` | 20 | Tooth count. |
| Gear Geometry | `pressure_angle` | 20° | Flank inclination (14.5 / 20 / 25). |
| Gear Geometry | `shaft_angle` | 90° | Angle between shafts (60 / 90 / 120). |
| Cone & Body | `face_width` | 12.0 mm | Tooth length along the pitch cone. |
| Cone & Body | `back_height` | 6.0 mm | Solid backing for the hub / mounting face. |
| Cone & Body | `bore` | 6.0 mm | Central shaft bore (0 = solid). |

The pitch-cone half-angle is `shaft_angle / 2` (a miter is 45°). The cone
distance is `r_pitch / sin(γ)`; the small end is scaled by
`(cone_dist − face_width) / cone_dist`.

## Presets

- **1:1 Miter Set (M2)** — 20/20 M2 miter pair.
- **Single Bevel (M3)** — a standalone 24-tooth M3 bevel.
- **Shallow-Cone Bevel (60°)** — an 18-tooth bevel on a 60° shaft angle.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Bevel Gear Tooth** (`spline`, ISO 23509) — the tapered involute mesh,
    defined by `m`, `teeth`, `shaft_angle`, `pressure_angle`.
  - **Hub Bore Mount** (`socket`, internal) — `bore`, `back_height`.
- **Material awareness:** `tolerance_by_material` declared.
- **Societal benefit:** right-angle power transfer without a commercial gearbox —
  hand-cranked mechanisms, differentials, rotary tools.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- **Self-contained** (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; final geometry assigned to `result`.
- Both modes export **watertight**. Lofting tapered involute teeth is heavier
  than a plain spur gear: the single bevel renders in ~20 s and the miter pair
  (two lofted cones) in ~25 s; `flank_pts` trades facet smoothness for speed.
