# Broom / Tool Wall Gripper

A sprung-jaw **wall gripper** generated with **CadQuery** (B-Rep) that holds a
cylindrical tool handle (broom, mop, rake, push-broom) by friction. The jaw mouth
is slightly narrower than the handle: pushing the handle in flexes the compliant
arms, and their springback grips it.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Single Gripper** | `gripper` | One sprung jaw on a two-hole screw-mount plate. |
| **Gripper Strip** | `gripper_strip` | `count` jaws on one shared plate, so a row of tools hangs from a single rail. |

The studio dispatches the active part via `target_part` (`gripper` /
`gripper_strip`).

## How the grip works

The jaw is an annulus (inner radius = handle radius, wall = `jaw_wall`) with a
front mouth removed. The mouth width is `mouth_factor × handle_dia`, which is
**less than the handle diameter** — so the arms must spread as the handle enters
and then spring back to clamp it. `mouth_factor` tunes the grip: lower is tighter,
`jaw_wall` tunes arm stiffness. Small lead-in lips flare the mouth so the handle
self-centres.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Handle & Jaw | `handle_dia` | 25.0 mm | Round tool handle diameter the jaw grips. |
| Handle & Jaw | `mouth_factor` | 0.78 | Mouth width ÷ handle diameter (must be < 1 to grip). |
| Handle & Jaw | `jaw_wall` | 3.0 mm | Compliant arm thickness (stiffness of the grip). |
| Handle & Jaw | `jaw_depth` | 16.0 mm | How much of the handle the jaw wraps along its axis. |
| Wall Plate | `plate_thick` | 4.0 mm | Wall-plate thickness. |
| Wall Plate | `plate_margin` | 8.0 mm | Material around the jaw / screw holes. |
| Wall Plate | `screw_dia` | 4.5 mm | Wall-screw clearance hole diameter. |
| Strip | `count` | 3 | Grippers on one shared plate. |
| Strip | `spacing` | 70.0 mm | Centre-to-centre gripper spacing. |

## Presets

- **Broom Gripper (25 mm)** — a standard broom / mop handle.
- **Thin Handle (16 mm)** — a slim handle with softer arms.
- **Garage Rail (3 tools)** — a 3-gripper strip at 75 mm spacing.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Sprung Handle Jaw** (`snap`, internal) — the compliant C-jaw, defined by
    `handle_dia`, `mouth_factor`, `jaw_wall`, and `jaw_depth`. The mouth is
    deliberately under-sized relative to the handle to create the snap grip.
  - **Wall Screw Mount** (`bolt_pattern`, internal) — the screw-hole plate,
    defined by `plate_thick`, `screw_dia`, and `plate_margin`.
- **Material awareness:** the mouth is expressed as a fraction of the handle so
  the interference (and thus grip force) tunes per material stiffness / printer;
  `tolerance_by_material` is declared.
- **Societal benefit:** long-handled tools slump into a corner and get damaged
  when there is nowhere to hang them. A friction jaw tuned to the exact handle
  keeps brooms, mops, and rakes off the floor with no hooks or hardware beyond
  two screws, printable to any handle a home already has.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- Every jaw is unioned onto the plate as a solid ring; each mode and preset
  renders **watertight**.
