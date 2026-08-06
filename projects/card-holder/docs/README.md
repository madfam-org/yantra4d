# Card / Book Holder

Holders that present cards and pages **hands-free** for people with limited
dexterity or grip. Generated with **CadQuery** (B-Rep). A card rack stands a
fanned hand of playing cards upright so they can be seen and played one-handed; a
book stand props a book or tablet at a reading angle; a page holder pins a single
card or page open on a weighted base.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **Fit is user-specific.** The right angle, height, and reach depend on where
> the holder sits and how the user sees and moves. An occupational therapist (OT)
> can advise on placement, viewing angle, and stability. The card groove is sized
> for standard poker cards (63 x 88 mm, ~0.3 mm each) — widen `groove_gap` for a
> thicker fan or laminated cards, and print a test rack before a long print.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Card Rack** | `card_rack` | A base with parallel angled grooves that stand a fan of playing cards upright. Cards spread along each groove; `n_grooves` sets how many rows. |
| **Book Stand** | `book_stand` | An inclined easel with a front ledge that holds a book or tablet open at a reading angle. |
| **Page Holder** | `page_holder` | A low weighted base with an upright slot that pins a single card or page open — a recipe-card or reference holder. |

Each mode dispatches on `target_part`; the manifest `parts[]` ids (`card_rack` /
`book_stand` / `page_holder`) match the dispatched values, so every mode renders
its own geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Base | `base_len` | 150 mm | Overall length of the holder. |
| Base | `base_depth` | 55 mm | Front-to-back depth (footprint stability). |
| Base | `base_h` | 16 mm | Height / mass of the base block. |
| Card / Page Hold | `card_t` | 1.2 mm | Thickness of a single card or page (a poker card is ~0.3 mm; a fan is thicker). |
| Card / Page Hold | `groove_gap` | 2.4 mm | Slot width — wider holds more cards. |
| Card / Page Hold | `groove_ang` | 65° | How upright the cards stand (`card_rack`). |
| Card / Page Hold | `n_grooves` | 3 | Number of parallel card rows (`card_rack`). |
| Card / Page Hold | `lip_h` | 12 mm | Front ledge height (`book_stand`, `page_holder`). |
| Card / Page Hold | `stand_ang` | 60° | Easel reading angle (`book_stand`). |

## Presets

- **Playing-Card Rack** — a three-row rack sized to standard poker cards.
- **Reading / Tablet Stand** — a 60° easel with a ledge for a book or tablet.
- **Recipe-Card Holder** — a small page holder for a kitchen or reference card.

## Hyperobject Profile

- **Domain:** medical
- **CDG interface:**
  - **Card / Page Groove** (`profile`, *playing card 63x88mm*) — the slot that
    stands the cards or page, defined by `card_t`, `groove_gap`, and `groove_ang`.
    Standard poker cards (63 x 88 mm) sit in the default groove; the groove width
    scales for a thicker fan.
- **Material awareness:** `groove_gap` and `card_t` are exposed so the hold can be
  tuned to card stock and to rigid vs. slightly flexible filament;
  `tolerance_by_material` is declared.
- **Societal benefit:** fanning and holding cards, or keeping a book or recipe
  open, are small pleasures and daily tasks that arthritis, tremor, hemiplegia, or
  a missing hand can take away. A holder sized to standard cards and common books
  restores play, reading, and cooking one-handed and unaided at low cost.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a `PARAM(lambda: name,
  default)` guard; `target_part` dispatches the part; the final solid is `result`.
- Each holder is one manifold solid. Card and page grooves are box slots cut from
  the top face straight down (open to the top → vented, never trapped); the book
  stand is a single extruded right-trapezoid easel with the ledge unioned on
  (overlapping); the page holder unions a short back wall then slots it. No
  revolves of cut profiles. All shipped modes and both parameter extremes render
  **watertight**, `body_count == 1`.
