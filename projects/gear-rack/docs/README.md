# Involute Gear Rack

A linear **involute gear rack** generated with **CadQuery** (B-Rep) that meshes
with a spur pinion. The rack tooth is the exact conjugate of an involute gear —
a straight-sided trapezoid whose flanks are inclined at the pressure angle
(**ISO 53 / DIN 867**). Any pinion sharing the same module and pressure angle
engages it correctly. The optional pinion's flanks are sampled directly from the
true involute of the base circle, so the pair is dimensionally real.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Rack** | `rack` | A bare rack bar with involute-conjugate teeth. |
| **Rack with Mounting Holes** | `rack` | Rack plus evenly-spaced through-holes in the back. |
| **Rack and Pinion** | `rack`, `pinion` | Rack plus a matching involute pinion positioned in a meshing pose (a multi-body compound). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Gear Geometry | `m` | 2.0 mm | Module; circular pitch = π·m. Must match the pinion. |
| Gear Geometry | `pressure_angle` | 20° | Flank inclination (14.5 / 20 / 25). |
| Rack Body | `rack_teeth` | 12 | Length = teeth × π × m. |
| Rack Body | `width` | 12.0 mm | Face width (Z). |
| Rack Body | `height` | 10.0 mm | Solid backing below the roots. |
| Mounting | `mount_holes` | off | Through-holes in the back. |
| Mounting | `hole_dia` / `hole_count` | 4.0 mm / 3 | Mounting-hole size and count. |
| Pinion | `include_pinion` | off | Add a matching involute pinion. |
| Pinion | `pinion_teeth` | 16 | Pinion tooth count (shares m + pressure angle). |
| Pinion | `bore` | 6.0 mm | Pinion shaft bore (0 = solid). |

## Tooth geometry

- **Circular pitch** `p = π·m`; addendum `= m`, dedendum `= 1.25·m`.
- **Tip land** `= p/4 − m·tan(pa)`, **root width** `= p/4 + 1.25·m·tan(pa)`.
- Flanks inclined at the pressure angle make the rack the conjugate of an
  involute gear of the same module.

## Presets

- **CNC Axis Rack (M2)** — 24-tooth M2 rack with 4 mounting holes.
- **Rack-and-Pinion Demo Set** — 14-tooth rack + 16-tooth pinion in a meshing pose.
- **Heavy Rack (M4)** — 16-tooth M4 rack at 25° for high load.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Involute Rack Tooth** (`spline`, ISO 53) — the meshing flank, defined by
    `m`, `pressure_angle`, `rack_teeth`. Any pinion at the same module and
    pressure angle meshes.
  - **Rack Back Mounting Pattern** (`bolt_pattern`, internal) — `mount_holes`,
    `hole_dia`, `hole_count`, `height`.
- **Material awareness:** `tolerance_by_material` declared — module/backlash can
  be tuned per material/printer.
- **Societal benefit:** printable, interoperable linear-motion parts for CNC
  axes, sliding gates, and lab positioners.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- **Self-contained** (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard because the render sandbox does not expose `globals()` /
  `eval`. Final geometry assigned to `result`.
- All shipped presets and defaults render **watertight**. The rack-and-pinion
  mode is a positioned multi-body assembly.
