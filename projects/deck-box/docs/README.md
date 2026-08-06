# Deck Box

A card-game deck box sized to a sleeved deck, with a friction-fit lid, plus a
matching token tray and a two-deck box. CadQuery (B-Rep) hyperobject cartridge.

## Modes (parts)

| Mode | Part id | Description |
|------|---------|-------------|
| Deck Box | `deck_box` | A single-deck box with a friction lid. The lid prints beside the base on one plate. |
| Token Tray | `token_tray` | A shallow open tray for tokens / dice / counters, on the same card footprint, with optional dividers. |
| Dual Deck | `dual_deck` | A wider box with a central divider that holds two decks. |

The active mode is selected by the `target_part` parameter.

## Card formats

`card` selects the interior footprint:

| Value | Card | Interior base (before clearance) |
|-------|------|-----------------------------------|
| `standard` | Poker / MTG / Pokémon | 63 × 88 mm |
| `mini` | Mini American / Loveletter | 41 × 63 mm |
| `tarot` | Tarot / oversized | 70 × 120 mm |

## Key parameters

- **deck_count** × **per_card** — sets the interior height (default 0.55 mm per
  sleeved card).
- **clearance** — per-side gap around the cards.
- **wall**, **floor**, **corner_r** — shell thickness and outer rounding.
- **lid_h**, **lid_clear** — friction-lid grip depth and print fit.
- **tray_h**, **tray_div** — token-tray height and divider count.

## CDG interfaces

- **Card Footprint** (`pocket`, "standard/mini/tarot card") — the interior cavity
  driven by `card` and `clearance`; the shared standard that makes any deck fit.
- **Friction Lid Seam** (`snap`, internal) — the lid-to-wall interface from `lid_h`,
  `lid_clear` and `wall`.

## Printing notes

Print flat, no supports. The deck-box lid is generated alongside the base so the
whole set prints on one plate; if you want the lid separately, render the box and
lid at different scales or split the STL. Tune `lid_clear` for your printer's
tolerance (0.35 mm is a firm friction fit on most FDM machines).

## Watertight strategy

Every part is a solid outer block with a **blind** interior cavity cut from the top
(a cup) — one closed manifold each. The lid is a plate plus a hollow downward skirt
(a closed shell) placed beside the base; the two solids are disjoint but each is
closed and positive-volume. The dual-deck divider is a solid wall unioned into the
floor. No sphere-tangent unions; every mode exports watertight with zero
negative-volume bodies.
