# Vacuum Suction Cup Mount

A **compliant vacuum-suction gripper base**, generated with **CadQuery** (B-Rep).
A suction cup is a flexible lip that seals against a surface; pulling a vacuum
through the central bore holds the part. This cartridge builds the cup body and
mount as **printable single-body solids** with the vacuum bore routed out a
**barbed side port**, and a **1/4-20 hex-nut trap** so the gripper mounts on any
1/4-20 post, arm, or plate — the universal camera/optics/robot thread.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **Compliant-mechanism note.** The cup is a **single filled solid of revolution**
> with a concave sealing dish and no trapped voids. Printed in **TPU** the lip
> flexes and seals; printed rigid (PLA/PETG) it is a geometry / mold master. The
> 1/4-20 interface is a **captive hex-nut trap + clearance hole** (drop in a
> standard 1/4-20 nut), which prints robustly as one body — no fragile swept
> thread.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Suction Cup** | `cup_mount` | A single suction cup on a mount boss; central vacuum bore tees out a barbed side port; 1/4-20 hex-nut trap underneath. |
| **Bellows Cup** | `bellows_cup` | A taller accordion-bellows cup (extra Z-compliance / travel) on the same 1/4-20 boss, for uneven surfaces. |
| **Vacuum Manifold** | `vacuum_manifold` | A flat block that tees one vacuum port to a **row of cup sockets** — the base of a multi-cup array end-effector. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cup | `cup_d` | 40 mm | Cup outer diameter. |
| Cup | `cup_h` | 16 mm | Cup height (dome + lip). |
| Cup | `lip_t` | 2.0 mm | Sealing-lip / wall thickness. |
| Cup | `n_conv` | 3 | Bellows rings (bellows cup). |
| Vacuum & Mount | `bore_d` | 6.0 mm | Central vacuum bore / feed channel. |
| Vacuum & Mount | `thread_d` | 6.35 mm | 1/4-20 clearance (1/4 in); nut sits in the hex trap. |
| Vacuum & Mount | `boss_h` | 12 mm | Mount-boss / manifold-block height. |
| Array | `n_cups` | 3 | Cup ports in the manifold row. |

## How the vacuum routes (and why it's watertight)

The cup is one **filled profile revolved 360°** — crown, central column and
flared skirt are a single connected solid, with a **concave dish** on the base
forming the suction pocket. The vacuum path is a **central bore** from the crown
down to just above the mount, then a **side cross-bore** out to a **barbed port**;
every drilling opens to an exterior face, so there is **no enclosed cavity** —
`is_watertight == True` and `body_count == 1` for every mode. The 1/4-20 mount is
a hexagonal nut pocket coaxial with a 6.35 mm clearance hole (all boolean cuts),
so it is always a single body.

## Presets

- **Standard 40 mm Cup** — a general pick-and-place cup.
- **Tall Bellows Cup** — extra travel for uneven or tilted surfaces.
- **Triple-Cup Manifold** — one vacuum line feeding three cups.

## Hyperobject Profile

- **Domain:** hybrid
- **CDG interfaces:**
  - **Suction Cup** (`socket`, *suction cup*) — the sealing cup pocket, defined
    by `cup_d`, `cup_h`, `lip_t`, `bore_d`.
  - **1/4-20 Mount** (`bolt_pattern`, *ASME B1.1 1/4-20 UNC*) — the hex-nut trap
    + clearance, defined by `thread_d`, `boss_h`. **Compatible with** the 1/4-20
    commons — `arca-plate`, `optical-post`, `nato-rail`, `shoe-mount`,
    `rod-rig-clamp`, `sensor-mount-plate`.
- **Material awareness:** `tolerance_by_material` is declared — lip thickness is
  exposed so the cup prints as a rigid master or a thin-wall TPU sealing cup.
- **Societal benefit:** vacuum suction lifts flat, fragile parts that jaws would
  crack; an open, parametric cup with a standard barbed port and a 1/4-20 mount
  lets a lab build an end-effector to the exact part and grow it into an array.
- **License:** CERN-OHL-W-2.0
- **Family:** new soft-robotics cluster; the 1/4-20 mount ties into the existing
  1/4-20 commons.

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. Cups are single filled revolves; all internal passages
  vent to a face (no trapped void).
