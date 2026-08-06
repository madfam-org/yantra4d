# Hobby Servo Bracket

A **hobby-servo bracket** that cradles a servo by its **body**, generated with
**CadQuery** (B-Rep). The cradle is a pocket sized to the servo (**SG90** micro =
23 x 12.2 mm, **MG996R** standard = 40.7 x 19.7 mm) with a floor window clearing
the output shaft and mounting tabs matching the servo's own flange screws.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Servo table

| Servo | Body | Flange spacing | Screw | Cradle depth |
| :--- | :--- | :--- | :--- | :--- |
| SG90 micro | 23 x 12.2 mm | 28 mm | M2 (2.2 mm) | 16 mm |
| MG996R standard | 40.7 x 19.7 mm | 49.5 mm | M3 (3.2 mm) | 26 mm |

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Servo Mount** | `servo_mount` | A single body cradle — four walls around the servo, a floor with a shaft window, and two flange tabs carrying the servo's screw holes. |
| **Pan/Tilt Bracket** | `pan_tilt_bracket` | A base (pan) cradle carrying an upright yoke that holds a second cradle rotated 90° for the tilt servo. |
| **U Bracket** | `u_bracket` | A U-shaped output arm — a cross web with two side arms and a pivot boss hole, the classic part a servo horn drives. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Servo | `servo` | SG90 | `SG90` or `MG996R` — sets body pocket + flange spacing. |
| Cradle | `wall` | 2.4 mm | Cradle / arm wall. |
| Cradle | `floor` | 2.5 mm | Cradle floor / U-bracket web. |
| Cradle | `clear` | 0.4 mm | Servo body-to-wall clearance (print fit). |
| Cradle | `tab_len` | 7 mm | Flange tab length beyond the body. |
| Arm | `arm_len` | 22 mm | U-bracket side-arm length. |
| Arm | `boss_d` | 6 mm | Pivot boss hole through the arms. |

## The body pocket (why it fits)

Micro and standard servos come in two dominant footprints (SG90 and MG996R). The
cradle hollows a pocket to that footprint plus a print clearance, and the flange
tabs place the mounting-screw holes at the servo's own flange spacing — so the
servo drops in and the same two screws that hold its case now hold the bracket.
The pocket is cut from a filleted clean outer blank and stays **open at the top**
(no trapped void), and every solid overlaps at its union, so all modes are
watertight.

## Presets

- **SG90 Mount** — single micro-servo cradle.
- **SG90 Pan/Tilt** — two-servo pan/tilt head.
- **MG996R U-Arm** — output arm for a standard servo.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Servo Mount** (`bolt_pattern`, *SG90/MG996R*) — the flange-screw pattern,
    defined by `servo`, `clear`. Matches the servo's mounting flange.
  - **Servo Body Pocket** (`pocket`, *internal*) — the body cradle, defined by
    `servo`, `wall`, `floor`.
- **Material awareness:** `tolerance_by_material` is declared — the body clearance
  can be tuned per material.
- **Societal benefit:** a printed bracket cut to the SG90/MG996R body and flange
  lets any of these interchangeable servos build a pan/tilt head, a gripper joint
  or a robot limb from parts on hand.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. All modes render **watertight**.
