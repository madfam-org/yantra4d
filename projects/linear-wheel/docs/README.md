# Linear Bushing / V-Wheel

A parametric OpenBuilds-style V-wheel generated with **CadQuery** (B-Rep) that
rolls in a V-slot aluminium extrusion rail, plus a plain flat idler variant.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## V geometry

The running surface runs from the full outer radius at each face down to a
minimum radius at the centre, forming a double-V. For a 90°-included V (two 45°
flanks that match the V-slot rail's 45° slot edges), the radius drops by
`width / 2` from face to centre, so `R_min = R_out − width / 2`. It is built as
two coaxial cones (frustums) joined at the centre — an exact, watertight
double-V. The V angle is auto-clamped to keep a solid core around the bore.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **V-Wheel** | `vwheel` | Double-V wheel bored for a bearing press-fit. |
| **Flat Wheel** | `flat_wheel` | Flat-rim idler wheel, same bearing bore. |
| **Solid Wheel** | `solid_wheel` | Bearingless double-V wheel with a printed axle hole. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Wheel | `wheel_type` | vslot | Double-V or flat idler. |
| Wheel | `outer_dia` | 24 mm | Outer diameter (mini V-wheel). |
| Wheel | `width` | 10.9 mm | Axial width (OpenBuilds V-wheel). |
| V Profile | `v_angle` | 90° | Included V angle (90° = two 45° flanks). |
| Bore | `bearing_bore` | 16 mm | Bearing OD press-fit (625 = 16). |
| Bore | `counterbore` / `cb_depth` | on / 0 mm | Bearing shoulder recess each face. |
| Bore | `axle_bore` | 5 mm | Plain axle hole (solid wheel). |

## Presets

- **Mini V-Wheel (625)** — the standard OpenBuilds mini V-wheel on a 625 bearing.
- **Flat Idler (625)** — a flat idler wheel on the same bearing.
- **Solid V-Wheel (5 mm axle)** — a bearingless printed wheel.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **V-Slot Wheel Groove** (`profile`, OpenBuilds V-slot) — the rolling
    interface, defined by `wheel_type`, `outer_dia`, `width`, `v_angle`. A 90° V
    matches the V-slot rail's 45° edges.
  - **Bearing Bore** (`socket`, ISO 15 625/608) — `bearing_bore`, `counterbore`,
    `cb_depth`.
- **Material awareness:** `tolerance_by_material` is declared; the bearing bore
  carries a small print clearance for a tuned press fit.
- **Societal benefit:** V-wheels are the rolling interface of the OpenBuilds
  motion ecosystem — a printable wheel keeps a gantry rolling when one wears out.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
