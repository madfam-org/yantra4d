# VESA Thin-Client Mount

Mounts a **mini-PC / thin-client / SBC** enclosure behind a monitor on the
**VESA MIS-D 100 x 100 mm** bolt pattern (M4), generated with **CadQuery**
(B-Rep). Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Strap Cage** | `strap_cage` | A VESA plate with a raised four-wall cage that cradles the device box, capture lips folding inward so the box is trapped; a front airflow window vents it. |
| **Shelf Tray** | `tray_shelf` | A VESA plate with a horizontal L-shelf at the bottom edge that the device rests on, a front curb, and two strap holes. |
| **Bracket Pair** | `bracket_pair` | A VESA plate with two side brackets standing off the front face that pinch the device from left and right, each with an inward foot and a cable-tie slot. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| VESA Plate | `vesa_sq` | 100.0 mm | MIS-D bolt square (75 or 100). |
| VESA Plate | `plate_t` | 5.0 mm | Backing plate thickness. |
| VESA Plate | `bolt_d` | 4.5 mm | M4 clearance hole diameter. |
| Device Box | `dev_w` / `dev_h` / `dev_t` | 120 / 120 / 30 mm | Device box footprint and depth. |
| Capture | `wall` | 4.0 mm | Cage / shelf / bracket wall thickness. |
| Capture | `lip` | 10.0 mm | Capture lip / curb / foot depth. |
| VESA Plate | `corner_r` | 5.0 mm | Plate corner fillet radius. |

## How it holds (and stays watertight)

The plate is a flat panel; the **monitor side is one face, the device stands off
the other in +Z**. Every capture structure — cage walls, shelf, brackets — is
**unioned into the plate with an overlap** (never tangent, which would leave a
zero-volume seam) so the whole part is a single watertight body. The VESA holes,
airflow window and cable/strap holes are **through-cuts that vent to outside**, so
no trapped voids form. The plate is **filleted before any hole is cut**.

## Presets

- **Standard Cage (120 mm box)** — the reference cage for a typical mini-PC.
- **SBC Tray** — a shallow shelf for a single-board-computer enclosure.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **VESA MIS-D Mount Face** (`bolt_pattern`, *VESA MIS-D*) — the backing bolt
    square defined by `vesa_sq`, `bolt_d`. Mates `vesa-mount`,
    `vesa-arm-extender`, `framing-hyperobject`.
  - **Device Cradle** (`pocket`, *internal*) — the captured device volume defined
    by `dev_w`, `dev_h`, `dev_t`.
- **Material awareness:** `tolerance_by_material` is declared — the device
  clearance tunes per material/printer.
- **Societal benefit:** thin-clients and SBCs ship without a VESA mount and
  off-the-shelf cradles rarely fit; a printed VESA-100 mount cradles any device
  box behind a monitor on demand.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- All shipped modes and per-mode extreme parameter cases render **watertight**,
  single-body, in well under 20 s.
