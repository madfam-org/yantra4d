# Worm & Worm-Wheel

A high-reduction, potentially **self-locking** right-angle drive generated with
**CadQuery** (B-Rep), in two parts:

- **Worm** — a screw: a trapezoidal (Acme-style) thread swept along a true helix
  on a cylinder (**DIN 3975**), single- or multi-start.
- **Worm-Wheel** — a gear whose teeth are angled to mesh the worm. Its involute
  flanks are sampled from the true involute of the base circle and twist-extruded
  at the worm's lead angle (a helical spur gear), so the module and mesh geometry
  are dimensionally real.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Approximation notes

- **Throated wheel not modelled.** A production worm-wheel has a *concave
  (throated)* rim that wraps the worm, cut by a globoid enveloping process — very
  heavy geometry. This wheel is a **helical spur gear** set to the worm's lead
  angle: correct pitch, module, and hand of helix, meshing on a line rather than
  wrapped. Standard maker-scale approximation, adequate for light-duty drives.
- **Multi-start turn cap.** A helical sweep self-intersects and tessellates
  non-watertight once the *total* swept revolutions grow large. The code caps
  `starts × worm_turns ≤ 3`, so every start count (1–3) stays watertight while
  still showing multiple visible turns. 4-start worms are not offered.

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Worm** | `worm` | The screw alone: helical thread on a bored cylinder. |
| **Worm-Wheel** | `wheel` | The helical gear alone. |
| **Worm + Wheel Pair** | `worm`, `wheel` | Both, positioned meshing at 90° (a multi-body compound). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Gear Geometry | `m` | 2.0 mm | Shared module. |
| Gear Geometry | `pressure_angle` | 20° | Flank inclination (14.5 / 20 / 25). |
| Worm | `starts` | 1 | Thread starts (1 = highest reduction / self-locking). |
| Worm | `worm_dia` | 16.0 mm | Worm pitch diameter. |
| Worm | `worm_turns` | 2.5 | Visible turns (auto-capped by starts). |
| Worm | `worm_bore` | 5.0 mm | Worm shaft bore. |
| Worm-Wheel | `teeth` | 30 | Wheel teeth; ratio = teeth / starts. |
| Worm-Wheel | `thickness` | 10.0 mm | Wheel face width. |
| Worm-Wheel | `wheel_bore` | 6.0 mm | Wheel shaft bore. |

The worm **lead** = `π·m·starts`; the **lead angle** = `atan(lead / (π·worm_dia))`
sets the wheel's helix angle. The **reduction ratio** is `teeth / starts`.

## Presets

- **Self-Locking 30:1 Set** — single-start M2 worm + 30-tooth wheel.
- **Two-Start 15:1 Set** — 2-start M2 worm + 30-tooth wheel (turns auto-capped to 1.5).
- **Printable Worm (M2)** — a standalone 3-turn worm for test printing.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Worm Thread + Wheel** (`spline`, DIN 3975) — the meshing pair, defined by
    `m`, `starts`, `teeth`, `pressure_angle`.
  - **Worm Helical Thread** (`thread`, DIN 3975) — the worm screw, `m`, `starts`,
    `worm_dia`, `worm_turns`.
- **Material awareness:** `tolerance_by_material` declared — backlash tunable per
  material/printer.
- **Societal benefit:** high reduction and self-locking in one compact right-angle
  stage for lifts, clamps, tuners, and rotary tables that must hold position.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- **Self-contained** (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; final geometry assigned to `result`.
- All three modes export **watertight**. The worm uses a genuine helical
  `makeHelix` sweep (fast: ~1 s per start); the pair is a positioned multi-body
  compound.
