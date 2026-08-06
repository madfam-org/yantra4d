# Cord Guard

Chew-resistant and abrasion sleeves that protect a cable or cord, generated with
**CadQuery** (B-Rep): a straight split sleeve that snaps over an in-place cable,
an L-shaped corner guard for where a cord turns a wall corner or table edge, and
a flexible spiral wrap that coils around the cable.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> Print in a **tough** material (PETG or a semi-flexible filament) for real chew
> resistance. This guards a cable; it does not make a damaged cable safe —
> replace frayed cords.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Split Sleeve** | `split_sleeve` | A straight tube with a lengthwise slit so it clips over a cable already in place. |
| **Corner Guard** | `corner_guard` | Two split-sleeve arms meeting at a rounded 90° elbow for a cable turning a corner. |
| **Spiral Wrap** | `spiral_wrap` | A helical band that coils around the cable, staying flexible. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cable | `cable_dia` | 6.0 mm | Cable outer diameter. |
| Cable | `clearance` | 0.4 mm | Per-side slip gap. |
| Sleeve Body | `wall` | 2.4 mm | Wall thickness (thicker = tougher). |
| Sleeve Body | `length` | 80.0 mm | Sleeve length (per arm for the corner; scales spiral turns). |
| Sleeve Body | `split` | 0.55 | Slit width as a fraction of cable diameter. |
| Spiral | `pitch` | 12.0 mm | Axial distance per coil turn. |

## Presets

- **Charger-Cable Sleeve (6 mm)**.
- **Desk-Edge Corner Guard**.
- **Flexible Spiral Wrap**.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Cord Sleeve** (`profile`, internal) — the split-tube cross-section,
    defined by `cable_dia`, `clearance`, `wall`, `split`. The same bore + slit
    profile drives all three forms so any of them fits the same cable.
- **Material awareness:** `tolerance_by_material` is declared — a semi-flexible
  material clips on with less clearance and flexes better.
- **Societal benefit:** protects both pet and cable from chewed-cord fire/shock
  hazards, snapping over an in-place cord at near-zero cost.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- The spiral wrap sweeps a rectangle along a genuine `makeHelix`; all outputs
  render **watertight**.
