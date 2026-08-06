# NEMA Damper Mount

A **vibration-damping mount** for **NEMA 17 / 23** stepper motors, generated with
**CadQuery** (B-Rep): the motor bolts through **rubber grommets** so motor noise
and resonance are isolated from the frame. Part of the **Yantra4D Hyperobjects
Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

Real motor dimensions: **NEMA 17** — 42.3 mm body, **31 mm** bolt square, M3,
22 mm pilot. **NEMA 23** — 57 mm body, **47.14 mm** bolt square, M4/M5, 38.5 mm
pilot.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Grommet Plate** | `grommet_plate` | A flat plate where each motor bolt passes through a rubber-grommet counterbore, isolating the motor from the plate; a pilot bore clears the register boss. |
| **Sandwich Spacer** | `sandwich_spacer` | A spacer between the motor face and the frame with grommet pockets on **both** faces, so a grommet on each side sandwiches the vibration. |
| **Bracket Isolator** | `bracket_isolator` | An L-bracket that stands the motor off a frame with grommet isolation on the vertical face, a gusseted base and frame bolt slots. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Motor | `nema` | NEMA17 | Frame size — sets bolt square, bolt size, pilot bore. |
| Motor | `plate_t` | 6.0 mm | Mount plate / leg thickness. |
| Damper | `grommet_d` / `grommet_depth` | 10.0 / 3.0 mm | Rubber grommet pocket bore + depth. |
| Mount | `margin` | 7.0 mm | Material around the bolt square. |
| Mount | `leg_h` | 45.0 mm | Vertical motor leg height (`bracket_isolator`). |
| Mount | `frame_bolt_d` | 4.5 mm | Frame mounting bolt clearance (`bracket_isolator`). |

## The damper interface (why it isolates, and stays watertight)

The motor mounts on the NEMA bolt square through **grommet counterbores** — open
pockets that a commodity rubber grommet seats into, so the bolt never metal-to-
metal contacts the plate. Plates are **filleted rounded slabs**, filleted before
any hole is cut. Bolt holes and the pilot bore are **through-holes that vent to
both faces**; grommet pockets are **open counterbores**; nothing traps a void. The
L-bracket leg, base and gussets are **unioned with overlap** (never tangent), and
the leg pattern is drilled with **Y-axis cylinders** so it lands cleanly on the
vertical face. The NEMA table lookup is **case-normalised** so a size string never
silently falls back to the wrong geometry.

## Presets

- **NEMA 17 Grommet Plate** — the reference flat isolator for a 42 mm stepper.
- **NEMA 23 Isolator Bracket** — a taller L-bracket for a 57 mm stepper.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **NEMA Bolt Pattern** (`bolt_pattern`, *NEMA 17/23*) — the motor bolt square
    selected by `nema`. Mates `nema-bracket`, `motor-mount`, `scara-robotics`.
  - **Rubber Grommet Isolator** (`socket`, *internal*) — the grommet pocket
    defined by `grommet_d`, `grommet_depth`.
- **Material awareness:** `tolerance_by_material` is declared — the grommet pocket
  and bolt clearances tune per material/printer.
- **Societal benefit:** steppers are the motion muscle of printers, CNC and
  robotics, and their vibration radiates as noise; a printed damper mount isolates
  the motor through commodity grommets, cutting noise on any machine.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- All shipped modes (both NEMA sizes) and per-mode extreme parameter cases render
  **watertight**, single-body, in well under 20 s.
