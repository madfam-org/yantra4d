# Zipper

The zipper **closure** itself — two tapes carrying a molded coil of interlocking
teeth plus the slider that mates them — generated with **CadQuery** (B-Rep).
Distinct from [`zipper-pull`](../../zipper-pull), which is only the replacement
pull tab: this is the whole working closure the Fashion Cabinet `zipper-notion`
bridges to.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Closed-end chain** | `tape_left`, `tape_right`, `slider` | A continuous zipper stopped at both ends; the slider parks at the top. |
| **Separating (jacket)** | + `pin_box` | An open-end zipper with a pin box at the bottom so the halves fully part; slider parks low. |
| **Slider only** | `slider` | The slider body alone (a Y-channel puller) for repairs. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Chain | `zip_length` | 200 mm | Working coil length; maps from a garment opening's length. |
| Chain | `chain_size` | `5` | Nominal gauge (#3 / #5 / #8 / #10) = closed-chain width in mm. |
| Tape | `tape_width` | 6.0 mm | One tape strip's width (the sewn allowance beside the coil). |
| Tape | `tape_thick` | 1.4 mm | Tape thickness. |
| Print Fit | `gap` | 0.35 mm | Clearance between halves and inside the slider channel; tune to your printer. |

## Presets

- **Dress Back** — #3, 55 cm, closed-end (an invisible-style back zip).
- **Jacket Front** — #5, 65 cm, separating (the everyday jacket zipper).
- **Duffel Bag** — #8, 80 cm, closed-end (a heavy bag zip).

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sewn Tape Edge** (`flange`, internal) — the sewn allowance beside the
    coil, defined by `tape_width`, `tape_thick`, `zip_length`. This is the edge a
    Fashion Cabinet placket sews to.
  - **Slider Channel** (`socket`, internal) — the guide the meshed coil rides
    through, defined by `chain_size`, `gap`.
- **Fashion Cabinet bridge:** `zipper-notion.hardware_ref.params_map` maps
  `length_mm → zip_length` and `tape_width_mm → tape_width`.

## Fabrication notes

Every part exports as a watertight solid. The two coil halves are interleaved by
half a pitch so the teeth **mesh** rather than collide; print the closed/separating
modes flat with the tapes in the bed plane and tune `gap` (start 0.35 mm) so the
slider moves but the coil holds. `chain_size` sets tooth pitch and size from the
nominal gauge, so a printed #5 matches a real #5 opening.
