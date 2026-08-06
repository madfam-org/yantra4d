# Servo Horn

A **replacement servo arm with a real splined bore**, generated with **CadQuery**
(B-Rep). The bore is cut with **N internal teeth** matching the servo output
spline standard — **24T** (~5.8 mm, Futaba / Savox) or **25T** (~6.0 mm,
Spektrum / Hitec) — so the printed horn presses onto the shaft and drives it.
Linkage holes sit along the arm at a chosen pitch.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Single Arm** | `single_arm` | One tapered arm off the splined hub with a row of linkage holes. |
| **Double Arm** | `double_arm` | Two opposed arms (a 180° bar) for pull-pull or balanced linkages. |
| **Wheel Horn** | `wheel_horn` | A round disc on the splined hub with holes on a bolt circle — for steering / heavy pulls. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Spline | `spline` | 24T | Output spline: `24T` (Futaba/Savox) or `25T` (Spektrum/Hitec). |
| Spline | `hub_d` | 10 mm | Boss diameter around the splined bore. |
| Spline | `horn_t` | 4.0 mm | Overall horn thickness. |
| Spline | `screw_d` | 2.5 mm | Central retaining-screw clearance. |
| Spline | `tooth_h` | 0.35 mm | Internal spline ridge depth (fit tuning). |
| Arm | `arm_len` / `arm_w` | 22 / 7 mm | Arm length and tip width. |
| Arm | `hole_d` / `hole_count` / `hole_pitch` | 2.0 mm / 4 / 3.0 mm | Linkage holes. |
| Wheel | `wheel_d` | 32 mm | Wheel-horn disc diameter (wheel mode). |

## The splined bore (why it grips)

The servo output shaft carries **N external teeth** on a nominal pitch diameter
(24 teeth ≈ 5.8 mm, 25 teeth ≈ 6.0 mm). The horn bore is the negative: a base
circle of radius `pitch_r − tooth_h` unioned with **N small teeth** at the rim,
leaving a bore with N internal ridges that mesh with the shaft. `tooth_h` tunes
how deep those ridges bite so the press-fit can be adjusted per printer/material.
A central counterbore clears the servo retaining screw. The spline is modelled
directly (no slow swept helix), so every mode renders in well under 20 s.

## Presets

- **Futaba 24T Single** — standard single arm for a Futaba/Savox spline.
- **Spektrum 25T Double** — two-sided bar for a Spektrum/Hitec spline.
- **Steering Wheel 24T** — round horn with a 4-hole bolt circle.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Servo Spline** (`spline`, *24T Futaba / 25T Spektrum*) — the N-tooth
    internal bore, defined by `spline`, `tooth_h`, `hub_d`. Meshes with the
    matching 24T/25T servo output shaft.
  - **Linkage Holes** (`bolt_pattern`, *internal*) — the row / bolt-circle of
    control-linkage holes, defined by `hole_d`, `hole_count`, `hole_pitch`.
- **Material awareness:** `tolerance_by_material` is declared — the spline tooth
  depth is exposed so the grip fit can be tuned per material (stiff PLA vs
  tougher nylon/PETG).
- **Societal benefit:** servo horns snap and strip, and the OEM part is
  proprietary and often unavailable; an on-demand horn cut to the correct
  24T/25T spline restores a servo on any craft or machine.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. The splined bore is built as a boolean negative (no
  swept helix). All modes render **watertight** in well under 20 s.
