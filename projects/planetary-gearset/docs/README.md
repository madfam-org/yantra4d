# Planetary Gearset

A compact **planetary (epicyclic) reduction stage** generated with **CadQuery**
(B-Rep): a central **sun**, orbiting **planets**, and a surrounding internal
**ring**, all involute and sharing one module (**ISO 53 / DIN 867**). Tooth
flanks are sampled directly from the true involute of the base circle, so any two
members mesh correctly.

The defining relation of a planetary train — **ring = sun + 2 × planet** — is
enforced by *computing* the ring tooth count from the sun and planet counts, so
the train always closes and the planets sit on the carrier circle
`(sun + planet)·m/2` without interference.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Sun Gear** | `sun` | The central external gear, watertight, with a shaft bore. |
| **Planet Gear** | `planet` | One orbiting external gear with a pin bore. |
| **Ring Gear** | `ring` | The internal (annular) gear — teeth cut inward from a solid rim. |
| **Full Assembly** | `sun`, `planet`, `ring` | All members positioned (sun centre, planets on the carrier circle, ring outside) as a multi-body compound. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Gear Geometry | `m` | 2.0 mm | Shared module for every member. |
| Gear Geometry | `pressure_angle` | 20° | Flank inclination (14.5 / 20 / 25). |
| Tooth Counts | `sun_teeth` | 12 | Sun count. |
| Tooth Counts | `planet_teeth` | 12 | Planet count; sets carrier radius and ring size. |
| Tooth Counts | `planets` | 3 | Planets in the assembly view. |
| Body & Bores | `thickness` | 8.0 mm | Face width (Z). |
| Body & Bores | `sun_bore` / `planet_bore` | 5.0 / 4.0 mm | Shaft / pin bores (0 = solid). |
| Body & Bores | `rim_width` | 6.0 mm | Ring wall outside the roots. |

**Ring tooth count is derived**, never entered: `ring_teeth = sun_teeth + 2 ×
planet_teeth`. The theoretical reduction with the ring fixed and the carrier as
output is `1 + ring_teeth / sun_teeth`.

## Presets

- **Compact ~4:1 Stage** — 12/12 M1.5, 3 planets (ring = 36, ratio ≈ 4:1).
- **High Reduction (small sun)** — 9-tooth sun, 18-tooth planets, 4 planets.
- **Printable Sun (M2)** — a standalone 16-tooth sun for test printing.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Planetary Involute Set** (`spline`, ISO 53) — the shared involute mesh,
    defined by `m`, `sun_teeth`, `planet_teeth`, `pressure_angle`.
  - **Internal Ring Mesh** (`spline`, ISO 53) — the annular ring, `m`,
    `sun_teeth`, `planet_teeth`, `rim_width`.
- **Material awareness:** `tolerance_by_material` declared — backlash tunable per
  material/printer.
- **Societal benefit:** coaxial high-ratio reduction in a small envelope for
  robotics, actuators, and hand tools, with the closing relation enforced so the
  printed stages actually mesh.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- **Self-contained** (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; final geometry assigned to `result`.
- Sun, planet, and ring each export **watertight**. The assembly is a positioned
  multi-body compound (a solid per member).
