# FPV Camera Cage

**Protects and angles a micro FPV camera**, generated with **CadQuery** (B-Rep).
The camera drops into a cradle pocket sized to the standard form factor
(**nano 14 mm, micro 19 mm, mini 21 mm**) and the whole housing tilts to a chosen
up-angle, with tabs that bolt to the frame side plates.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Protective Cage** | `cage` | Full shell + a front rim frame and diagonal guard strut that shield the lens on impacts. |
| **Tilt Bracket** | `tilt_mount` | The shell only (open front) on the tilting mount — lighter, still cradles the cam. |
| **Naked Mount** | `naked_mount` | A thin backing plate with the lens aperture and board-mount holes for a "naked"/board cam. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Camera | `cam_size` | micro | Form factor: `nano` 14, `micro` 19, `mini` 21 mm. |
| Camera | `tilt` | 30° | Up-tilt angle (higher = faster flight). |
| Camera | `lens_hole` | on | Cut a rear lens/focus aperture. |
| Housing | `wall` | 2.0 mm | Cradle wall thickness. |
| Housing | `cam_clear` | 0.4 mm | Per-side clearance around the cam. |
| Frame Mount | `base_h` | 6.0 mm | Mount base height below the cradle. |
| Frame Mount | `mount_width` | 19 mm | Spacing between the frame-plate tabs. |
| Frame Mount | `tab_thick` / `tab_hole_d` | 3.0 / 2.2 mm | Tab thickness and bolt hole (M2). |

## Interfaces

The cradle pocket is derived directly from `cam_size` (plus `cam_clear` per side
and `wall`), so a housing generated for a *micro* cam accepts a 19 mm micro cam.
The two side tabs form the frame-mount bolt interface at `mount_width` spacing.
The whole housing is rotated up by `tilt` about the pitch axis before it is
joined to the base, exactly like a real cam mount.

## Presets

- **Micro Cage 30°** — the common freestyle setup.
- **Nano Tilt 40°** — light racing bracket for a nano cam.
- **Mini Naked 20°** — flat board-cam mount for a mini sensor.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **FPV Camera Cradle** (`pocket`, *FPV micro/nano cam — nano 14 / micro 19 /
    mini 21 mm*) — the cradle pocket, defined by `cam_size`, `cam_clear`, `wall`.
    Any camera of the selected form factor drops in.
  - **Frame Mount Tabs** (`bolt_pattern`, *internal*) — the two side tabs and
    bolt holes, defined by `mount_width`, `tab_thick`, `tab_hole_d`.
- **Material awareness:** `tolerance_by_material` is declared — the cam clearance
  and wall are exposed so the pocket fit can be tuned per material/printer.
- **Societal benefit:** the camera is the most-crashed and most-swapped part on
  an FPV craft; on-demand cages sized to the exact cam and tilt keep the picture
  level and the lens protected.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. Base fillets are clamped and guarded. All modes render
  **watertight** in well under 20 s.
