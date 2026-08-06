# Trellis / Plant Clip

A gentle clip that ties a plant stem to a stake, a trellis wire, or itself,
generated with **CadQuery** (B-Rep). Three styles: a figure-of-eight **stake clip**,
a **wire clip** that snaps over a trellis wire, and a soft **spiral wrap**. The
C-loops grip a little smaller than the stem so they hold, but spring on without
crushing the plant.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Stake Clip** | `stake_clip` | Figure-of-eight — one C-loop for the stem, one for the stake. |
| **Wire Clip** | `wire_clip` | Stem C-loop plus a slot that snaps over a trellis wire. |
| **Spiral Wrap** | `spiral_clip` | A soft helical coil that hugs a stem without pinching. |

Each mode's `parts[]` id equals the `target_part` the code dispatches on.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Stem | `stem_dia` | 10 mm | Plant stem diameter the clip holds. |
| Attachment | `stake_dia` | 11 mm | Stake diameter (stake clip). |
| Attachment | `wire_dia` | 3 mm | Trellis wire diameter (wire clip). |
| Clip Form | `mouth` | 0.7 | Opening as a fraction of stem diameter. |
| Clip Form | `width` | 10 mm | Clip width along the stem. |
| Clip Form | `wall` | 2.4 mm | Wall thickness (thinner = more spring). |

## Presets

- **Tomato Stake Clip** — the classic figure-of-eight tomato tie.
- **Vine Wire Clip** — grips a thin vine and snaps onto trellis wire.
- **Soft Spiral (seedling)** — a gentle coil for delicate seedlings.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Stem Clip** (`snap`, internal) — the compliant C-mouth that snaps onto a stem,
    defined by `stem_dia`, `mouth`, `wall`. Any clip at the same `stem_dia`/`mouth`
    grips the same plants.
- **Material awareness:** `wall` and `mouth` tune the spring/grip per material
  (softer TPU vs stiff PLA); `tolerance_by_material` is declared.
- **Societal benefit:** healthier gardens with less plastic — reusable clips replace
  throwaway ties and stem-damaging metal, training tomatoes, vines, and climbers gently.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Each C-loop is a tube ring with a mouth slot cut on one side; loops overlap at a
  web so the whole clip is one **watertight** solid. The spiral is a round profile
  swept along a real-radius `makeHelix` (non-singular frame), the same fast, watertight
  sweep the thread cartridges use.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
