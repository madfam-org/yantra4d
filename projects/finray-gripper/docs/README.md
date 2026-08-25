# Fin-Ray Gripper Jaw

A **compliant Fin-Ray-effect gripper jaw**, generated with **CadQuery** (B-Rep).
The **Fin Ray Effect**: a triangular finger whose two flanks are joined by angled
cross-ribs. Push the front flank and the finger wraps **toward** the load instead
of buckling away — passive, form-fitting compliance with **no actuator and no
control loop**. This cartridge **bridges soft-robotics to the servo family**: one
mode carries a real **24T/25T servo output spline** (the same negative-tooth bore
as the `servo-horn` cartridge), so a Fin-Ray jaw bolts straight onto a hobby
servo.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **Compliant-mechanism note.** The finger is a **printable single-body solid**
> (a ribbed wedge) with no trapped voids. Printed in PLA/PETG it is a
> light-compliance jaw and a geometry master; printed in **TPU** it becomes a
> soft, fully-wrapping finger.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Fin-Ray Jaw** | `finray_jaw` | The compliant Fin-Ray wedge with a bolt-through root slab (two M4 holes) for a linear-actuator or parallel-jaw gripper. |
| **Servo-Mount Jaw** | `finray_servo_mount` | A Fin-Ray finger whose root is a splined **24T/25T servo boss** with a central retaining-screw clearance — drives directly off a hobby servo. |
| **Modular Finger** | `finray_finger` | A slimmer single Fin-Ray blade with a cross **pivot-pin bore** — stack several on a multi-finger hand. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Finger | `fin_len` | 70 mm | Root-to-tip length. |
| Finger | `fin_base` | 34 mm | Wedge base width. |
| Finger | `fin_th` | 16 mm | Finger thickness (Z). |
| Ribs & Walls | `rib_count` | 6 | Angled cross-ribs — tunes wrap stiffness. |
| Ribs & Walls | `rib_w` | 2.4 mm | Flank and rib thickness. |
| Mounting | `spline` | 24T | Servo spline (servo-mount mode): `24T` / `25T`. |
| Mounting | `hub_d` | 12 mm | Servo boss outer diameter. |
| Mounting | `tooth_h` | 0.35 mm | Spline ridge depth (fit tuning). |
| Mounting | `pin_d` | 4.0 mm | Pivot-pin bore (modular finger). |

## How it grips (and how it mates the servo)

The wedge is a solid triangle, hollowed to leave two flank walls, with **angled
cross-ribs** unioned back in between them. Because the ribs are canted toward the
tip, a load on the front flank shears the ribs and the whole finger **curls
around the object** — the Fin Ray Effect. The **Servo-Mount** mode replaces the
root slab with a cylindrical boss carrying the **servo spline bore**: a base
circle of radius `pitch_r − tooth_h` unioned with **N rim teeth** (24 or 25),
leaving N internal ridges that mesh with the servo shaft. This is byte-for-byte
the idiom the `servo-horn` cartridge uses, so the two **interoperate** on the
same 24T/25T output shaft.

## Presets

- **Standard 70 mm Jaw** — a general parallel-jaw Fin-Ray finger.
- **Servo 24T Jaw** — a jaw that drives off a Futaba/Savox 24T servo.
- **Slim Modular Finger** — a thin blade for a multi-finger hand.

## Hyperobject Profile

- **Domain:** hybrid
- **CDG interfaces:**
  - **Fin-Ray Rib Profile** (`profile`, *internal*) — the compliant rib
    structure, defined by `fin_len`, `fin_base`, `rib_count`, `rib_w`.
  - **Servo Spline** (`spline`, *24T Futaba / 25T Spektrum*) — the internal
    N-tooth bore, defined by `spline`, `hub_d`, `tooth_h`. **Compatible with
    `servo-horn`** — both share the 24T/25T servo output spline.
- **Material awareness:** `tolerance_by_material` is declared — rib width and
  spline tooth depth are exposed so wrap stiffness and grip fit tune per material.
- **Societal benefit:** passive Fin-Ray grippers dominate food and assistive
  handling but are sold proprietary per-robot; an open jaw that also mates the
  ubiquitous hobby-servo spline lets anyone fit a compliant gripper to any servo.
- **License:** CERN-OHL-W-2.0
- **Family:** mates the **servo-spline** family (`servo-horn`).

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. Every mode is a single watertight body; the spline bore
  is a boolean negative (no swept helix).
