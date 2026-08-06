# Switch-Adapted Toy / AT Switch Mount

A mount that cradles a round **assistive-technology (AT) switch** at a reliable,
repeatable position for **single-switch access** to toys, devices, and
communication aids. Generated with **CadQuery** (B-Rep). The switch drops into a
shallow recess and its 3.5 mm (1/8 in) mono cable exits a side channel.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **Fit is user-specific.** Measure your actual switch body and mounting surface,
> and set positioning with an occupational therapist (OT) or speech-language
> pathologist (SLP). Placement — height, angle, and travel — is part of the
> access assessment, not a fixed dimension. Print a test cradle first and adjust
> the clearance before committing.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Screw-Down Cradle** | `switch_cradle` | A flat cradle with a screw-down flange (four holes on a ring). The switch seats in the top recess; the cable exits the side. |
| **Tilt Wedge** | `switch_wedge` | The recess set into an inclined ramp so the switch face tilts toward the user — often easier to reach and press from a seated position. |
| **Strap Mount** | `switch_strap_mount` | The cradle with two transverse strap slots so a hook-and-loop strap lashes it to a tray edge, wheelchair armrest, or lap tray. |

Each mode dispatches on `target_part`; the manifest `parts[]` ids
(`switch_cradle` / `switch_wedge` / `switch_strap_mount`) match the dispatched
values, so every mode renders its own geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Switch Fit | `switch_dia` | 63 mm | Body diameter of the round switch (Specs-class ~63 mm). |
| Switch Fit | `recess_depth` | 8 mm | How deep the switch seats. |
| Switch Fit | `clearance` | 0.6 mm | Radial slip gap around the switch. |
| Switch Fit | `cable_dia` | 4.5 mm | Cable-exit channel for the 3.5 mm jack lead. |
| Mounting | `wall` | 4 mm | Cradle wall and floor thickness. |
| Mounting | `flange` | 12 mm | Screw-down flange width (`switch_cradle`). |
| Mounting | `screw_dia` | 4.2 mm | Mounting screw clearance (#8 / M4). |
| Mounting | `tilt_ang` | 20° | Ramp incline (`switch_wedge`). |
| Mounting | `strap_w` | 26 mm | Strap slot width (`switch_strap_mount`). |

## Presets

- **Specs Switch Cradle (63mm)** — a flat cradle sized to a Specs-class switch.
- **20° Tilt Wedge** — the recess on a 20° ramp toward the user.
- **Tray-Edge Strap Mount** — the cradle with strap slots for a lap tray.

## Why a mount at all

AT switches use the de-facto **1/8 in / 3.5 mm mono jack** (AbleNet Specs, Big
Red, and compatible switches), so a switch that fits one device fits most. What
varies is *where* the switch has to be for a given user to hit it every time —
and an unmounted switch that slides, rotates, or drifts turns a learned press
into a miss. Fixing the switch body at a measured position is the whole point:
the mount converts an inconsistent action into dependable cause-and-effect.

## Hyperobject Profile

- **Domain:** medical
- **CDG interface:**
  - **AT Switch Recess** (`socket`, *3.5mm AT switch*) — the circular pocket that
    receives the switch body, defined by `switch_dia`, `clearance`, and the
    `cable_dia` exit channel. Any switch whose body matches `switch_dia` (within
    `clearance`) seats in the cradle; the channel clears the standard 3.5 mm lead.
- **Material awareness:** `clearance` is exposed so the seat fit can be tuned for
  rigid (PLA/PETG) or grippier (TPU) filament; `tolerance_by_material` is declared.
- **Societal benefit:** reliable, repeatable switch placement is the foundation of
  single-switch access — the primary route to play, communication, and
  environmental control for people with significant motor impairments — at
  near-zero cost, reprintable as needs change.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a `PARAM(lambda: name,
  default)` guard; `target_part` dispatches the part; the final solid is `result`.
- Every part is one manifold solid. The switch recess is an open-topped pocket
  (vents to the top face — no trapped void); the cable channel is a straight box
  slot through the side wall into the pocket (open to air); screw holes and strap
  slots are through-cuts. The wedge is a single extruded slab-plus-ramp profile
  with the pocket cut into the ramp on a matched tilted plane. All shipped modes
  and both parameter extremes render **watertight**, `body_count == 1`.
