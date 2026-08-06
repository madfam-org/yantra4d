# Motor Soft-Mount Pod

A **vibration-isolating motor pod** for FPV / RC brushless motors, generated with
**CadQuery** (B-Rep). The motor bolts to a square plate carrying the standard
hole pattern (**9×9 M2**, **16×16** or **19×19 M3**); the pod clamps to the frame
arm. In **soft** mode a compliant comb neck lets the motor plate float on the
clamp so airframe vibration is damped — print that variant in **TPU**.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Soft Mount (flex)** | `soft_mount` | Motor plate decoupled from the arm clamp by a comb of horizontal flex slots. Print in TPU for real isolation. |
| **Rigid Mount** | `rigid_mount` | Same plate + clamp with a solid neck — a stiff, minimal pod. |
| **Skid Mount (landing foot)** | `skid_mount` | Motor plate on a neck ending in a stubby landing foot for camera clearance / hand-launch protection. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Motor | `motor_pattern` | 16x16 | Square motor bolt pattern: `9x9` (M2), `16x16`/`19x19` (M3). |
| Motor | `plate_thick` | 4.0 mm | Motor plate thickness. |
| Motor | `bore_d` | 10.0 mm | Central clearance bore for the motor bell / shaft. |
| Arm Clamp | `arm_width` / `arm_thick` | 12 / 5 mm | Frame arm cross-section the clamp grips. |
| Arm Clamp | `clamp_wall` | 3.0 mm | Wall around the arm. |
| Isolation | `iso_gap` | 2.4 mm | Flex-slot width (soft mode). |
| Isolation | `flex_slots` | 3 | Number of compliant comb slots (soft mode). |
| Foot | `foot_dia` / `foot_drop` | 16 / 14 mm | Landing-foot size and drop (skid mode). |

## The motor bolt-pattern interface

The pod hosts the shared **motor bolt-pattern** CDG interface used across the
drone Commons. The four screw centres form a square of side 9, 16 or 19 mm;
`9x9` boards take **M2** screws (2.4 mm clearance), `16x16`/`19x19` take **M3**
(3.4 mm). The same `motor_bolt_points()` helper drives the prop-guard motor arms
and the landing-skid, so a motor that bolts to one bolts to all.

## Presets

- **Cinewhoop Soft (16x16)** — flex pod tuned for a 10 mm ducted-whoop arm.
- **Freestyle Rigid (19x19)** — stiff pod for a thick freestyle arm.
- **Tiny Skid (9x9)** — micro pod with a small landing foot.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Motor Bolt Pattern** (`bolt_pattern`, *16×16 / 19×19 / 9×9 brushless motor
    mount*) — the square 4-hole pattern plus central bore, defined by
    `motor_pattern` and `bore_d`. Interoperable with every FPV motor and the
    other drone-Commons parts that expose the same pattern.
  - **Frame Arm Clamp** (`profile`, *internal*) — the rectangular arm slot and
    split kerf, defined by `arm_width`, `arm_thick`, `clamp_wall`.
- **Material awareness:** `tolerance_by_material` is declared — clamp gap and the
  flex-slot width are exposed so fit and compliance can be tuned per material
  (rigid PLA/PETG plate, flexible TPU soft-mount).
- **Societal benefit:** motors are the most vibration-critical joint on a
  multirotor; on-demand soft-mounts damp jello out of FPV footage and extend
  motor life, matched to the exact arm and bolt pattern.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; `target_part` dispatches which part to build; the final solid
  is assigned to `result`. Fillets are clamped and wrapped in try/except with a
  non-fatal fallback. All modes render **watertight** in well under 20 s.
