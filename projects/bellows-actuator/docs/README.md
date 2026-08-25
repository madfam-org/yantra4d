# Pneumatic Bellows Actuator

A parametric **pneumatic bellows** — the base primitive of soft robotics — generated
with **CadQuery** (B-Rep). Pressurise it and the convolutions unfold along the
stroke axis; vent it and the wall elasticity pulls it back. It is the linear
counterpart to the bending `pneu-net-finger`, and the two share the same inlet.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **LOW-PRESSURE service only.** A printed bellows is not a pressure vessel.
> Print in TPU with generous perimeters, test behind a shield, and never run it
> near a person at a pressure you have not verified on that exact print.

## Why this cartridge exists

Soft robotics had exactly **one** cartridge in the commons before this wave. The
bellows is the field's base primitive: almost every other soft actuator either
*is* a bellows or *ports into* one. Landing it first gives the rest of the
soft-robotics family — `pneu-net-finger`, `suction-cup-bellows`,
`vacuum-manifold-block` — something real to interoperate with.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Bellows** | `bellows` | The convoluted actuator body with an integral barb inlet. |
| **Flanged Bellows** | `bellows_flange` | The same body on a bolt-pattern base flange, for bolting into a frame. |
| **End Cap** | `end_cap` | The moving end plate — the face a gripper or tool bolts to. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bellows | `outer_dia` | 34.0 mm | Outer diameter at the convolution crests. |
| Bellows | `inner_dia` | 22.0 mm | Diameter at the convolution roots — the crest/root difference is the stroke. |
| Bellows | `convolutions` | 5 | Number of folds. More folds = more stroke, less side stiffness. |
| Bellows | `conv_pitch` | 7.0 mm | Axial spacing between folds. |
| Bellows | `wall` | 1.6 mm | Membrane wall thickness — the single most safety-relevant number here. |
| Bellows | `cap_th` | 3.0 mm | End-plate thickness. |
| Inlet | `tube_id` | 4.0 mm | Tubing inner diameter — the shared barb series. |
| Inlet | `bore` | 2.6 mm | Air passage through the inlet. |
| Flange | `flange_dia` | 52.0 mm | Base flange diameter. |
| Flange | `bolt_dia` | 4.3 mm | Bolt clearance (4.3 = M4). |
| Flange | `bolt_count` | 4 | Bolts on the flange circle. |

## Presets

- **Standard 34 mm Bellows** — the general-purpose actuator.
- **Long-Stroke** — more convolutions at a wider pitch, for reach over force.
- **Flanged Frame Mount** — bolted into a fixed frame, driving a moving tool.

## Hyperobject Profile

- **Domain:** soft-robotics
- **CDG interfaces:**
  - **Pneumatic Barb Series** (`profile`, 2 / 3 / 4 mm tube ID) — the shared inlet,
    defined by `tube_id` and `bore`. Compatible with `pneumatic-barb-port` and
    `vacuum-manifold-block`: a bellows and a manifold generated at the same
    `tube_id` share tubing without an adapter.
  - **Stroke Axis** (`rail`, internal) — the linear-motion interface published for
    gripper assemblies, defined by `convolutions`, `conv_pitch`, `inner_dia`,
    `cap_th`. Compatible with `soft-gripper-pad`.
  - **Base Bolt Flange** (`bolt_pattern`, internal) — `flange_dia`, `bolt_dia`,
    `bolt_count`.
- **Material awareness:** `wall` and the barb fit are exposed so the membrane can
  be tuned per material; `tolerance_by_material` is declared (TPU seals at a
  tighter barb fit than PLA).
- **Societal benefit:** commercial soft actuators are sold per-unit at prices that
  keep soft robotics out of teaching labs; an open, parametric bellows whose inlet
  is a published interface makes the whole family reproducible.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- Every derived dimension is **clamped** so the membrane wall and the inlet bore
  can never invert at a parameter extreme.
- All shipped presets, defaults, **and the minimum/maximum of every parameter**
  render **watertight** (single body).
