# Bellows Suction Cup

A **vacuum end-effector** — the pick-and-place primitive — generated with
**CadQuery** (B-Rep). A thin sealing lip meets the part; the bellows above it
collapses under vacuum, which both lifts the part and gives the cup compliance to
land on a surface that is not quite square to the tool.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **LOW-PRESSURE / vacuum service only.** Lift capacity depends on the seal your
> print achieves against your actual surface — test it, do not assume it, and do
> not lift anything overhead.

## Why this cartridge exists

The commons had grippers that **pinch** and none that **stick**. Vacuum is how
most real pick-and-place actually moves flat, smooth, or fragile parts, and the
cup Ø series here (20 / 30 / 40 mm) matches the common tooling sizes so a printed
cup can stand in for a bought one on existing equipment.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Bellows Cup** | `cup` | The convoluted compliant cup — lands on off-square surfaces. |
| **Flat Cup** | `cup_flat` | A plain flat-lipped cup, for rigid, square, smooth parts. |
| **Cup Mount** | `cup_mount` | The cup on a bolt-flange mount, for fixing to a tool plate. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cup | `cup_dia` | 30.0 mm | Sealing lip diameter — the 20 / 30 / 40 mm tooling series. |
| Cup | `lip_th` | 1.2 mm | Lip thickness — thinner seals better and tears sooner. |
| Cup | `lip_h` | 4.0 mm | Lip height. |
| Cup | `neck_dia` | 12.0 mm | Neck diameter — the press-fit interface to the tool. |
| Bellows | `convolutions` | 2 | Folds in the compliant section. |
| Bellows | `conv_pitch` | 5.0 mm | Axial spacing between folds. |
| Bellows | `conv_depth` | 3.0 mm | How deep each fold cuts — the compliance. |
| Bellows | `wall` | 1.6 mm | Bellows wall thickness. |
| Port | `tube_id` | 4.0 mm | Vacuum tubing inner diameter — the shared barb series. |
| Port | `bore` | 2.6 mm | Vacuum passage. |
| Mount | `bolt_dia` | 3.4 mm | Bolt clearance on the mount flange (3.4 = M3). |

## Presets

- **Standard 30 mm Cup** — the general pick-and-place size.
- **Small 20 mm Cup** — for small components and dense arrays.
- **Large 40 mm Cup** — for sheet and panel handling.
- **Flat Rigid Cup** — no bellows, for square, rigid parts.

## Hyperobject Profile

- **Domain:** soft-robotics
- **CDG interfaces:**
  - **Pneumatic Barb Series** (`profile`, 2 / 3 / 4 mm tube ID) — `tube_id`, `bore`.
    Compatible with `pneumatic-barb-port` and `vacuum-manifold-block`: a cup array
    plugs straight into a manifold generated at the same `tube_id`.
  - **Cup Diameter Series** (`profile`, 20 / 30 / 40 mm) — `cup_dia`, `lip_th`,
    `lip_h`. The published tooling series.
  - **Neck Press Socket** (`socket`, internal) — `neck_dia`, `wall`, `bolt_dia`.
- **Material awareness:** `lip_th` and `wall` are exposed so the seal can be tuned
  per material; `tolerance_by_material` is declared (TPU seals where PLA will not).
- **Societal benefit:** vacuum cups are a consumable sold per-cup with proprietary
  necks; an open cup whose Ø series matches standard tooling and whose port is a
  published interface makes the consumable reprintable.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- The cup is a **revolved profile** — trivially one body — with the port bore cut
  after the revolve; every fold depth is clamped against the wall so a
  convolution can never cut through the membrane.
- All shipped presets, defaults, **and the minimum/maximum of every parameter**
  render **watertight** (single body).
