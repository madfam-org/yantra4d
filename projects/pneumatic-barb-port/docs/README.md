# Pneumatic Barb Port

The **connector that makes the soft-robotics family interoperable** rather than
six isolated objects. A parametric barb fitting for 2 / 3 / 4 mm ID tubing,
generated with **CadQuery** (B-Rep), published as the shared inlet interface for
`bellows-actuator`, `pneu-net-finger`, `suction-cup-bellows`, and
`vacuum-manifold-block`.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **LOW-PRESSURE service only.** A printed barb holds by friction on an elastic
> tube. Verify the grip at your working pressure before trusting it, and expect
> a printed fitting to seep where a moulded one seals.

## Why this cartridge exists

Six soft-robotics cartridges that each invent their own inlet are six objects. Six
that share one published barb series are a **family**: any actuator generated at a
given `tube_id` shares tubing with any manifold generated at the same `tube_id`,
with no adapter and no measuring. This cartridge is that series, made explicit and
printable on its own so it can also patch non-commons hardware into the family.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Flange Port** | `flange_port` | A barb on a bolt flange — bolts onto a plate or an enclosure wall. |
| **Boss Port** | `boss_port` | A barb on a plain boss, to be unioned into another cartridge's body. |
| **Barb Coupler** | `barb_coupler` | Barbs at both ends — joins two lengths of tube. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Barb | `tube_id` | 4.0 mm | **The series parameter** — tubing inner diameter (2 / 3 / 4 mm). |
| Barb | `barb_count` | 3 | Number of retaining ridges. |
| Barb | `barb_pitch` | 3.4 mm | Axial spacing between ridges. |
| Barb | `barb_rise` | 0.7 mm | How far each ridge stands proud — the tube grip. |
| Barb | `bore` | 2.6 mm | Air passage through the fitting. |
| Barb | `wall` | 2.0 mm | Wall around the bore. |
| Flange | `flange_dia` | 20.0 mm | Flange diameter. |
| Flange | `flange_th` | 3.0 mm | Flange thickness. |
| Flange | `bolt_dia` | 3.4 mm | Bolt clearance (3.4 = M3). |
| Flange | `bolt_count` | 3 | Bolts on the flange circle. |

## Presets

- **4 mm Standard Port** — the family default.
- **3 mm Micro Port** — for small actuators and dense arrays.
- **2 mm Fine Port** — the smallest series member.
- **Tube Coupler** — a double-ended joiner.

## Hyperobject Profile

- **Domain:** soft-robotics
- **CDG interfaces:**
  - **Pneumatic Barb Series** (`profile`, 2 / 3 / 4 mm tube ID) — `tube_id`,
    `barb_count`, `barb_pitch`, `barb_rise`, `bore`. **This is the family's
    canonical definition**, compatible with `bellows-actuator`,
    `pneu-net-finger`, `suction-cup-bellows`, and `vacuum-manifold-block`.
  - **Port Bolt Flange** (`bolt_pattern`, internal) — `flange_dia`, `flange_th`,
    `bolt_dia`, `bolt_count`.
- **Material awareness:** `barb_rise` and `wall` are exposed so the grip can be
  tuned per material; `tolerance_by_material` is declared (a rigid barb into soft
  tubing needs less rise than a soft barb into rigid tubing).
- **Societal benefit:** pneumatic fittings are cheap individually and ruinous as a
  dependency — the wrong barb size stalls a build for a week's shipping. A printed,
  parametric barb series turns that dependency into a twenty-minute print, and
  publishing it as an interface is what lets the rest of the family assume it.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- Ridges are **unioned onto** the stem before the bore is cut, so no ridge can
  ever be left as a floating ring; `bore` is clamped against `wall` so the
  passage can never break out through the side.
- All shipped presets, defaults, **and the minimum/maximum of every parameter**
  render **watertight** (single body).
