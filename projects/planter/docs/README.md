# Self-Watering Planter

A pot with a water reservoir in the base and a wicking path up to the soil,
generated with **CadQuery** (B-Rep), so plants water themselves between fillings. A
false floor sits above the reservoir; wick holes pull water up; an overflow hole
stops over-filling. Round or square, with a matching saucer and a lift-out inner pot.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Planter** | `planter` | The pot: reservoir base, false floor with wick holes, overflow hole. |
| **Saucer** | `saucer` | A shallow drip tray a touch larger than the pot footprint. |
| **Inner Pot Insert** | `insert` | A lift-out cup with wick legs that stand in the reservoir. |

Each mode's `parts[]` id equals the `target_part` the code dispatches on.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Pot Size | `shape` | round | Round or square footprint. |
| Pot Size | `pot_dia` | 120 mm | Diameter (round) or side (square). |
| Pot Size | `height` | 130 mm | Overall pot height. |
| Reservoir & Wicking | `reservoir_h` | 35 mm | Water chamber height at base. |
| Reservoir & Wicking | `wick_count` / `wick_dia` | 4 / 16 mm | Wick holes in the false floor. |
| Reservoir & Wicking | `drainage` | on | Overflow hole at reservoir top. |
| Walls | `wall` | 3.0 mm | Pot wall + floor thickness. |

## Presets

- **Herb Pot (round)** — a compact self-watering herb pot.
- **Square Patio Planter** — larger square pot, deeper reservoir.
- **Matching Saucer** — drip tray for the herb pot.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Self-Watering Reservoir** (`surface`, internal) — the false-floor + wick
    geometry that separates water from soil, defined by `reservoir_h`, `wick_count`,
    `wick_dia`, `wall`. The insert's wick legs mate the same reservoir volume.
- **Material awareness:** `wall` tunes strength/print per material; PLA reservoirs
  are best sealed; `tolerance_by_material` is declared.
- **Societal benefit:** water-thrifty growing at home — seedlings and herbs go days
  between waterings, saving water and rescuing plants from missed days.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The pot is one closed solid: the soil cavity and reservoir cavity are cut from a
  solid body, leaving a false-floor slab that is then drilled for wicks and one
  overflow hole. Because nothing is a zero-thickness surface, all modes export
  **watertight**. Round and square footprints share a `_block()` / `_cavity()` helper.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
