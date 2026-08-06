# Sensor Mount Plate

A universal base for a security camera, motion sensor, dashcam, or small
enclosure, built with **CadQuery** (B-Rep). Every mode is a flat base that fixes
to a surface (adhesive pad or screws) and presents a device-fixing interface on
top.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part id | Description |
| :--- | :--- | :--- |
| **1/4-20 Base** | `quarter20_base` | A base with a 1/4-20 boss stud on top — the universal camera/tripod interface, at the ASME nominal 6.35 mm major diameter. |
| **Screw Base** | `screw_base` | A rectangular base with a 2- or 4-hole surface-screw pattern plus a central device screw. |
| **Adhesive Puck** | `adhesive_puck` | A round disc with a flat underside for a VHB / adhesive pad and one central device screw. |

The platform renders per-part via `target_part`; each mode's `parts[]` id equals
the value the code dispatches on, so the three modes render as distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Base | `base_w` / `base_d` | 40 / 40 mm | Rectangular base size (1/4-20 & Screw). |
| Base | `base_dia` | 45 mm | Disc diameter (Adhesive Puck). |
| Base | `base_thick` | 5.0 mm | Base / disc thickness. |
| Base | `corner_r` | 4.0 mm | Rectangular corner radius. |
| 1/4-20 Boss | `boss_h` | 8.0 mm | Stud height above the base. |
| 1/4-20 Boss | `thread_relief` | on | Cosmetic thread groove (not a functional swept thread). |
| Screws | `screw_holes` | 4 | Surface screws (2 or 4). |
| Screws | `screw_dia` | 4.5 mm | Surface screw clearance. |
| Screws | `screw_inset` | 7.0 mm | Screw inset from the edge. |
| Screws | `device_screw` | 4.5 mm | Central device screw (Screw Base & Puck). |

## Presets

- **Camera 1/4-20 Base** — a 40×40 base with a 1/4-20 stud and four M4 surface holes.
- **Sensor 2-Screw Base** — a small 2-screw plate with a central device screw.
- **Dashcam Adhesive Puck** — a 45 mm disc for a VHB pad with a central device screw.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **1/4-20 Camera Stud** (`thread`, standard **ASME B1.1 1/4-20 UNC**) — the
    universal camera/tripod boss, at the nominal 6.35 mm major diameter and
    1.27 mm pitch. It is modelled as a chamfered cylinder with optional shallow
    cosmetic grooves — **not** a slow swept helix — so the render stays fast and
    watertight; in practice the boss is tapped or takes a knurled nut.
  - **Sensor Base Pattern** (`bolt_pattern`, standard **ASME 1/4-20**, internal)
    — the surface-fixing screw layout plus the central device screw, defined by
    `screw_holes`, `screw_dia`, `screw_inset`, `device_screw`, `base_w`,
    `base_d`. The shared `drill_z` helper cuts every hole.
- **Material awareness:** hole clearances are printable values tunable per
  material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** cameras, sensors, and dashcams each ship with their own
  proprietary bracket; one printable base presenting the universal 1/4-20 stud or
  a plain screw pattern lets a device move between wall, dash, and desk without a
  new mount each time.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- The 1/4-20 boss avoids a swept helix entirely (fast, watertight); the cosmetic
  thread is shallow (0.25 mm) stacked ring grooves that never break the solid
  core. Surface-screw points that would collide with the central device hole are
  dropped automatically, so even the minimum base stays a clean solid. All three
  modes export watertight.
