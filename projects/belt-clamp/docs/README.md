# Timing Belt Clamp

A **timing-belt clamp / tensioner** that grips a belt by its **teeth**, generated
with **CadQuery** (B-Rep). The gripping face is a comb of ridges cut to the belt's
tooth pitch (**GT2** = 2 mm, **HTD-3M** = 3 mm); the belt lies teeth-down and its
valleys seat between the ridges so it cannot pull out.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Belt table

| Belt | Pitch | Ridge height | Typical width |
| :--- | :--- | :--- | :--- |
| GT2 2 mm | 2.0 mm | 0.75 mm | 6 mm |
| HTD 3M | 3.0 mm | 1.2 mm | 9 mm |

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Belt Clamp** | `belt_clamp` | A U-channel with a toothed floor and side guides; four end bolts squeeze a cover/frame onto the belt to terminate an end. |
| **Tensioner** | `tensioner` | The toothed grip plus a lengthwise adjustment **slot**, so the clamp can slide along a frame bolt to take up slack before nipping. |
| **Belt Joiner** | `belt_joiner` | A bar with a tooth comb at **each** end to splice two belt ends into a closed loop. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Belt | `belt` | GT2-2mm | `GT2-2mm` or `HTD-3M` — sets ridge pitch and depth. |
| Belt | `teeth` | 6 | Gripping ridges per jaw. |
| Belt | `belt_w` | 7 mm | Belt channel width. |
| Body | `wall` | 2.4 mm | Side-wall / body wall. |
| Body | `floor` | 3.0 mm | Material under the ridges. |
| Mount | `bolt_d` | 3.4 mm | Clamp bolt clearance (M3). |
| Mount | `slot_len` | 16 mm | Tensioner adjustment slot travel. |
| Mount | `mount_d` | 4.5 mm | Tensioner slot / mount bolt (M4). |

## The tooth grip (why it holds)

A timing belt transmits force through its **teeth**, not friction — so the clamp
mirrors the belt: a comb of trapezoidal ridges at the exact belt pitch (2 mm GT2 /
3 mm HTD). The belt is laid teeth-down and its valleys drop between the ridges; the
clamp bolt only needs to hold the belt seated, and the meshed teeth carry the pull.
Ridges are unioned onto a shared root as one solid, and the floor slab is filleted
**as a clean blank before** the bolt holes are cut, so every mode is watertight.

## Presets

- **GT2 6 mm Clamp** — terminate a 6 mm GT2 belt end.
- **GT2 Tensioner** — slotted grip to take up slack.
- **HTD 3M Joiner** — splice a 9 mm HTD loop.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Belt Tooth Grip** (`profile`, *GT2 2mm / HTD 3M*) — the pitched ridge comb,
    defined by `belt`, `teeth`, `belt_w`. Meshes with the belt's tooth profile.
  - **Clamp Bolts** (`bolt_pattern`, *internal*) — the clamp / slot bolts, defined
    by `bolt_d`, `mount_d`.
- **Material awareness:** `tolerance_by_material` is declared — the belt-channel
  and ridge fit can be tuned per material.
- **Societal benefit:** a printed tooth-matched clamp terminates open belt stock to
  any length, splices a broken loop, or tensions a slack run, keeping printers and
  CoreXY robots moving from a reel of raw belt.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. All modes render **watertight**.
