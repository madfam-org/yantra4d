# PneuNet Bending Finger

The canonical **PneuNet** (pneumatic network) bending actuator, generated with
**CadQuery** (B-Rep). A row of air chambers sits above a stiff strain-limiting
layer; pressurise the chambers and they expand against each other, so the finger
can only relieve the strain by **curling** toward the limiting layer. No joints,
no linkages — the bend is the geometry.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **LOW-PRESSURE service only.** A printed PneuNet is not a pressure vessel.
> Print in TPU with generous perimeters, test behind a shield, and never run it
> near a person at a pressure you have not verified on that exact print.

## Why this cartridge exists

The bending actuator is what most people actually mean by "soft gripper", and it
was missing. It pairs with the commons' existing rigid-compliant grippers —
`sentinel-gripper-hyperobject`, `finray-gripper`, `tool-gripper` — by bolting to
the same root pattern, so a soft finger can replace a rigid jaw on hardware that
already exists.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Finger** | `finger` | A single PneuNet bending finger with root flange and barb inlet. |
| **Finger Pair** | `finger_pair` | Two opposed fingers on one root — a printable two-finger gripper. |
| **Root Flange** | `root_flange` | The bolt-pattern root on its own, for adapting a finger to other hardware. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Finger | `finger_len` | 90.0 mm | Root-to-tip length. |
| Finger | `finger_w` | 20.0 mm | Finger width. |
| Chambers | `chamber_h` | 14.0 mm | Chamber height — taller chambers bend harder. |
| Chambers | `chamber_pitch` | 9.0 mm | **Chamber spacing — this drives the bend radius**, published as a CDG parameter. |
| Chambers | `chamber_gap` | 2.0 mm | Wall between adjacent chambers. |
| Chambers | `wall` | 1.8 mm | Chamber membrane wall. |
| Chambers | `strain_th` | 3.0 mm | Strain-limiting layer — the stiff back that forces the curl. |
| Chambers | `channel_w` | 3.0 mm | Cross-channel linking the chambers. |
| Inlet | `tube_id` | 4.0 mm | Tubing inner diameter — the shared barb series. |
| Inlet | `bore` | 2.6 mm | Air passage through the inlet. |
| Root | `root_len` | 18.0 mm | Length of the mounting root. |
| Root | `bolt_dia` | 3.4 mm | Bolt clearance (3.4 = M3). |

## Presets

- **Standard 90 mm Finger** — the general-purpose bending actuator.
- **Tight-Curl Finger** — a shorter chamber pitch for a smaller bend radius.
- **Two-Finger Gripper** — the opposed pair, ready to pressurise.
- **Long Reach** — fewer, wider-pitched chambers over a longer body.

## Hyperobject Profile

- **Domain:** soft-robotics
- **CDG interfaces:**
  - **Chamber Pitch Profile** (`profile`, internal) — `chamber_pitch`,
    `chamber_gap`, `chamber_h`, `finger_len`, `strain_th`. The bend radius is a
    published function of the pitch, not an emergent surprise.
  - **Root Bolt Pattern** (`bolt_pattern`, internal) — `root_len`, `finger_w`,
    `bolt_dia`. Compatible with `soft-gripper-pad` and `tool-gripper`, so a soft
    finger bolts to the same face a rigid jaw came off.
  - **Pneumatic Barb Series** (`profile`, 2 / 3 / 4 mm tube ID) — `tube_id`, `bore`.
    Compatible with `pneumatic-barb-port` and `vacuum-manifold-block`.
- **Material awareness:** `wall` and `strain_th` are exposed so the chamber/limiter
  stiffness ratio can be tuned per material; `tolerance_by_material` is declared.
- **Societal benefit:** PneuNet designs are widely published as papers but rarely
  as parametric, printable geometry; a cartridge that also speaks the commons'
  existing gripper bolt pattern turns the paper into a part.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- Chamber count is **derived** from length and pitch and floored at 1; every
  chamber wall is clamped so a chamber can never break out of the finger.
- All shipped presets, defaults, **and the minimum/maximum of every parameter**
  render **watertight** (single body).
