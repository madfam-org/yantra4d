# NEMA Stepper Bracket

A **NEMA 17 / NEMA 23 stepper-motor bracket**, generated with **CadQuery**
(B-Rep). The motor face carries the correct **square bolt pattern** and a central
**pilot bore** that clears the motor's raised register boss and shaft, so a real
motor bolts straight on.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Motor table

| NEMA | Body | Bolt square | Bolt | Pilot bore |
| :--- | :--- | :--- | :--- | :--- |
| NEMA 17 | 42.3 mm | 31.0 mm | M3 (3.4 mm) | 23.0 mm |
| NEMA 23 | 57.0 mm | 47.14 mm | M4/M5 (5.2 mm) | 38.5 mm |

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **L-Bracket** | `l_bracket` | A vertical motor plate joined to a horizontal base, gusseted at the corner. Motor bolts on the face; base bolts down through the slab. |
| **Flat Plate** | `flat_bracket` | The flat motor plate with four extra corner holes so the plate itself bolts flat to a panel around the motor. |
| **2020 Extrusion Foot** | `extrusion_mount` | A vertical motor plate on a foot sized to sit across a 2020 aluminium T-slot extrusion, with bolt holes on 20 mm centres for M5 T-nuts. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Motor | `nema` | NEMA17 | `NEMA17` or `NEMA23` — sets bolt square, bolt size, pilot bore. |
| Motor | `pilot_open` | true | Cut the central pilot bore. |
| Plate | `plate_t` | 5.0 mm | Motor plate thickness. |
| Plate | `margin` | 6.0 mm | Material around the bolt square. |
| Base | `base_len` | 45 mm | Horizontal base (L) or extrusion-foot length. |
| Base | `base_t` | 5.0 mm | Base / foot slab thickness. |
| Base | `base_bolt_d` | 5.2 mm | Base / corner mounting bolt clearance (M5 T-nut). |
| Base | `gusset` | true | Triangular corner gusset (L & extrusion). |

## The bolt pattern (why it fits)

NEMA motors are defined by a **square bolt pattern** on the output face: NEMA 17
uses a 31 mm square with M3, NEMA 23 a 47.14 mm square with M4/M5. The plate cuts
those four holes on the exact square and a central pilot bore whose diameter
clears the motor's raised register boss (so the motor seats flat). Both are cut as
grouped `pushPoints` operations, and the plate is filleted **as a clean blank
before** any holes are drilled — so the boolean feature-cuts never intersect a
rounded edge, keeping every mode watertight.

## Presets

- **NEMA 17 L-Bracket** — the classic right-angle mount.
- **NEMA 23 Flat Plate** — a panel plate for the larger motor.
- **NEMA 17 on 2020** — foot for aluminium-extrusion frames.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **NEMA Bolt Pattern** (`bolt_pattern`, *NEMA 17/23*) — the square motor-bolt
    pattern + pilot bore, defined by `nema`, `pilot_open`. Mates with the motor's
    standard output face.
  - **Mount Holes** (`bolt_pattern`, *internal*) — the base / corner mounting
    holes, defined by `base_bolt_d`, `base_len`.
- **Material awareness:** `tolerance_by_material` is declared — bolt/pilot
  clearances can be tuned per material (stiff PLA vs tougher PETG/nylon).
- **Societal benefit:** stepper motors outlive their machines; an on-demand
  bracket cut to the exact NEMA bolt square lets a salvaged motor drive a new
  build without a proprietary mount.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. All modes render **watertight**.
