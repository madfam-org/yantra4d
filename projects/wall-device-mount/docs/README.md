# Universal Device Wall Mount

A fit-anything wall cradle for a rectangular device, built with **CadQuery**
(B-Rep). Enter the device's width, depth, and height and the mount wraps it with
a printer-clearance gap and a wall-screw (or adhesive) backplate — one cartridge
for remotes, routers, network switches, hubs, and handsets.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part id | Description |
| :--- | :--- | :--- |
| **Cradle (open shelf)** | `cradle_mount` | A floor + a low front lip that the device drops into; back open to the wall. Easiest access. |
| **Pocket (deep wrap)** | `pocket_mount` | A four-wall wrap hollowed to the device cavity, with a front access scallop; holds more securely. |
| **Strap (band)** | `strap_mount` | A slim backplate with a raised band the device tucks behind — minimal material. |

The `style` select mirrors these three families and stays in sync with the active
mode; the platform renders per-part via `target_part`, and each mode's `parts[]`
id equals the value the code dispatches on.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Style | `style` | `cradle` | Mount family (`cradle` / `pocket` / `strap`). |
| Device Size | `dev_w` / `dev_d` / `dev_h` | 60 / 25 / 110 mm | The object envelope: width, depth off the wall, height up the wall. |
| Shell & Fit | `wall_t` | 3.0 mm | Wall / backplate thickness. |
| Shell & Fit | `margin` | 4.0 mm | Extra material beyond the device each side. |
| Shell & Fit | `clearance` | 0.6 mm | Per-side printable fit gap around the device. |
| Shell & Fit | `lip_h` | 14 mm | Front lip (cradle) / retaining band (strap) height. |
| Wall Mounting | `screw_dia` | 4.2 mm | Clearance diameter for the two wall screws (#8 ≈ 4.2). |
| Wall Mounting | `adhesive` | off | Skip the screw holes for a flat adhesive backplate. |

## Presets

- **TV Remote Shelf** — a tall, slim open cradle for a TV remote.
- **Router Pocket** — a deep four-wall wrap for a home router.
- **USB Hub Strap (adhesive)** — a minimal band with an adhesive backplate.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Device Cradle** (`pocket`, internal) — the printable pocket that receives
    the device, defined by `dev_w`, `dev_d`, `dev_h`, `clearance`, `wall_t`. This
    is the interface that mates to the physical object.
  - **Wall Screw Pattern** (`bolt_pattern`, internal) — the two-point wall fix
    (`screw_dia`, `dev_h`), suppressed when `adhesive` is on. Drilled by the
    shared `bolt_grid` helper.
- **Material awareness:** `clearance` is a printer/material-tunable fit gap;
  `tolerance_by_material` is declared.
- **Societal benefit:** reclaims wall space and tidies the home — one parametric
  cradle fits any remote, router, or hub exactly, replacing per-product
  proprietary holders and loose-device clutter.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- Each style builds a solid backplate then fuses (cradle: floor + lip + side
  ribs; strap: uprights + bridge) or cuts (pocket: cavity + front scallop) so the
  result stays a watertight, manifold solid. All three modes export watertight
  and are volumetrically distinct (cradle ≈ open shelf, pocket ≈ full wrap, strap
  ≈ minimal band).
