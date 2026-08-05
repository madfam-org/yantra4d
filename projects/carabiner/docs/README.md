# Carabiner / Quick-Link (Utility)

A utility clip for keys, gear, bags, and organisation, generated with **CadQuery**
(B-Rep). A flat racetrack body with a choice of gate mechanism.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## ⚠️ Safety — NOT for climbing or life-safety

**This is a utility / gear clip only. It is NOT load-rated and MUST NOT be used for
climbing, mountaineering, fall protection, rigging, lifting people or loads, or any
application where failure could cause injury.** Printed plastic is not a safety
device. Use a certified metal carabiner for anything load-bearing. This model is for
keys, bags, cables, tools, and organisation.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Spring Carabiner** | `spring_carabiner` | Racetrack body + a printed cantilever sprung gate that flexes open and springs shut. |
| **Screw Link** | `screw_link` | A quick-link whose gap is flanked by a **real threaded post** (volumetric-rib helix, ~2.5 turns) so a printed sleeve/nut screws down to close it. |
| **S-Hook** | `s_hook` | An open S / double hook for hanging. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Body | `length` | 60 mm | End-to-end length. |
| Body | `spine` | 6.0 mm | Rail cross-section (thicker = stronger). |
| Body | `inner_w` | 20 mm | Loop opening width. |
| Gate | `gate_type` | spring_gate | Informational; each mode builds its matching gate. |
| Gate | `opening` | 12 mm | Gate / hook opening size. |

## Thread technique (Screw Link)

The threaded post uses the repo's watertight thread idiom: a trapezoidal profile
swept along a real `makeHelix` path for ~2.5 turns, unioned as a rib whose root is
pushed **into** the post wall (the overlap). The post extends a full pitch beyond the
thread on both ends so the helix start/end embed in solid material — this is what
keeps the union watertight and the render fast (~1.5 s).

## Presets

- **Keychain Clip** — a compact sprung clip.
- **Gear Screw Link** — a screw-sleeve quick-link.
- **Utility S-Hook** — an open double hook.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:** **Utility Gate** (`snap`, internal) — defined by `gate_type`,
  `opening`, `spine`. A non-safety closure interface.
- **Material awareness:** `tolerance_by_material` — sprung-gate flex and screw fit
  depend on filament; tune per material.
- **Societal benefit:** an everyday utility clip printed on demand at any size —
  explicitly a non-safety gear clip, sized to the task.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; final solid assigned to `result`.
- All shipped presets and defaults render **watertight**.
