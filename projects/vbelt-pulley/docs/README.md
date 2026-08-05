# V-Belt / Round-Belt Pulley

A parametric friction-drive pulley (sheave) generated with **CadQuery** (B-Rep),
for A-section V-belts or for round belts and O-rings. The rim carries one or more
grooves cut as bodies of revolution about the pulley axis.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Groove geometry

- **V-Belt A / 13 mm** — a ~40° included-angle V-groove (ISO 4183 A / SPZ
  family), ~13 mm wide at the rim. The belt wedges into the V and drives by
  friction on the flanks. Built as the union of two coaxial cones so the channel
  is exactly a revolved triangle. The top width is auto-clamped to what the
  included angle and depth allow.
- **Round belt / O-ring** — a semicircular groove built as a torus of the belt
  radius centred on the rim circle.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **V-Belt** | `vbelt` | A single A-section V-groove sheave. |
| **Round Belt** | `roundbelt` | A single semicircular groove for a round belt / O-ring. |
| **Multi-Groove** | `multi_groove` | A stacked sheave with `grooves` parallel V-grooves. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Belt & Groove | `belt_profile` | A/13 | V-belt or round-belt groove. |
| Belt & Groove | `outer_dia` | 60 mm | Rim outer diameter. |
| Belt & Groove | `groove_angle` | 40° | V included angle. |
| Belt & Groove | `groove_width` / `groove_depth` | 13 / 11 mm | V top width / radial depth. |
| Belt & Groove | `belt_dia` | 5 mm | Round-belt / O-ring cross-section. |
| Multi-Groove | `grooves` / `groove_pitch` | 2 / 15 mm | Groove count / spacing. |
| Body & Bore | `bore` | 8 mm | Shaft hole. |
| Hub & Set Screw | `hub` / `hub_dia` / `hub_height` | on / 22 / 8 mm | Set-screw hub. |
| Hub & Set Screw | `setscrew` / `setscrew_dia` | on / 4.2 mm | Radial M4 set screw. |

## Presets

- **A-Section Ø60 · 8 mm bore** — a general-purpose V-belt sheave.
- **O-Ring Drive Ø40 (5 mm belt)** — a light round-belt drive.
- **Twin-Groove Sheave Ø80** — a two-groove V-belt sheave.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **V-Belt Groove** (`profile`, ISO 4183 A/SPZ) — the friction interface,
    defined by `belt_profile`, `groove_angle`, `groove_width`, `groove_depth`,
    `outer_dia`.
  - **Round-Belt / O-Ring Groove** (`profile`, internal) — `belt_dia`,
    `outer_dia`.
  - **Shaft Bore & Set Screw** (`socket`, internal) — `bore`, `setscrew`,
    `setscrew_dia`.
- **Material awareness:** `tolerance_by_material` is declared; the round-belt
  groove and bore carry a small print clearance.
- **Societal benefit:** printable sheaves let a maker set a drive ratio or
  replace a cracked pulley without sourcing a proprietary casting.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
