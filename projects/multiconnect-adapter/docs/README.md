# Multiconnect / GOEWS Adapter

An accessory back that snaps into the popular **Multiconnect** (and **GOEWS**)
wall-mount systems, built with **CadQuery** (B-Rep). The back carries the male
snap profile — a keyed, tapered snap tab that slides into the channel and locks —
so any printable hook, bin, or holder becomes a snap-in accessory.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part id | Description |
| :--- | :--- | :--- |
| **Blank Back (base)** | `blank_back` | A flat plate with the snap back and nothing else — glue / screw your own object to it. |
| **Hook** | `hook_back` | The plate + snap plus a J-hook projecting forward, for cables, tools, bags, or cups. |
| **Bin** | `bin_back` | The plate + snap plus a small open bin for parts, pens, or oddments. |

The platform renders per-part via `target_part`; each mode's `parts[]` id equals
the value the code dispatches on. The `system` select switches the snap geometry
between Multiconnect and GOEWS spacing.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Wall System | `system` | `multiconnect` | `multiconnect` or `goews` snap geometry. |
| Wall System | `snap_rows` | 2 | Snap tabs stacked up the back at the system slot pitch (25 mm). |
| Wall System | `snap_w` / `slot_pitch` | 0 / 0 | Overrides (0 = system default) for fit tuning. |
| Accessory Plate | `plate_w` / `plate_h` | 50 / 50 mm | Plate size across / up the wall. |
| Accessory Plate | `plate_t` | 4.0 mm | Plate thickness. |
| Hook | `hook_len` / `hook_dia` | 35 / 8 mm | Forward reach and rod diameter (hook mode). |
| Bin | `bin_depth` / `bin_height` | 40 / 35 mm | Forward projection and wall height (bin mode). |
| Bin | `bin_wall` | 2.4 mm | Bin wall / floor thickness. |

## Presets

- **Multiconnect Blank (2 snaps)** — the base adapter, two snap rows.
- **Multiconnect Hook** — a tall plate with a J-hook.
- **GOEWS Parts Bin** — a three-snap plate with a parts tray on GOEWS spacing.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Multiconnect / GOEWS Back** (`snap`, standard *Multiconnect / GOEWS*) — the
    male snap interface, defined by `system`, `snap_rows`, `snap_w`, `slot_pitch`,
    `plate_t`. This is the interface that mates to the wall channel.
  - **Accessory Face** (`profile`, internal) — `plate_w`, `plate_h`, `hook_len`,
    `bin_depth`, `bin_height` define the forward-facing accessory you attach.
- **Material awareness:** the snap `snap_w` / `slot_pitch` are exposed so a tighter
  or looser fit can be tuned per printer/material; `tolerance_by_material` is
  declared.
- **Societal benefit:** extends the open Multiconnect / GOEWS wall ecosystem — one
  adapter back turns any printable accessory into a snap-in part, so a shared
  community interface keeps growing without proprietary parts.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): all injected parameters are
  read once at module scope via `PARAM(lambda: name, default)`; the final solid is
  assigned to `result`.
- The snap tab is a trapezoidal wedge with a lower undercut lip, extruded across
  `snap_w` and fused behind the plate (in -Y) at the system slot pitch; the plate
  and accessory project forward (in +Y). It is a **dimensionally close
  approximation** of the community snap profile — verify against your board for a
  critical fit, or use the `snap_w` / `slot_pitch` overrides. All three modes
  export watertight and are volumetrically distinct.
