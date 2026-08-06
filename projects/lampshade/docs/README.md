# Lampshade

A patterned lampshade or pendant — a thin shell with a bulb-socket ring at the top
(sized to an E26/E27 lamp holder) and a perforated pattern that casts light. Dial top and
bottom diameter, height, wall, socket standard, and pattern density.

## Modes / Parts

| Mode | Part id | What it is |
|------|---------|------------|
| Drum Shade | `drum_shade` | A straight cylindrical drum (top diameter used for both ends). |
| Cone Shade | `cone_shade` | A tapered empire/cone shade (top smaller than bottom). |
| Pendant | `pendant` | A deeper downlight flare with a small cord-set ring. |

## Key Parameters

- **Top / Bottom Diameter** — the openings (cone/pendant taper between them).
- **Height / Wall** — shade height and shell thickness (1.2–2 mm glows).
- **Lamp Socket** — E27 (Europe) or E26 (US) holder the top ring fits.
- **Pattern** — holes, slots, or solid (no pattern).
- **Pattern Rows / Columns / Feature Size** — perforation density and size.

## How It Builds (watertight & fast)

The shell is a **circle-loft cone** (a solid cone lofted between two circles) with a
slightly-smaller circle-loft cone cut out — this yields a clean conical B-rep surface, so
the pattern boolean stays watertight even on the taper (a polyline-annulus loft does not).
The pattern is cut in a **single boolean** using a `Compound` of all hole/slot cutters —
per-hole cuts are far too slow. The column count is auto-capped so even the densest
request renders in under ~20 s. A three-spoke ring hub bores the E26/E27 socket seat.

## Printing Notes

Print in a translucent or white filament at 1.2–2 mm wall for a soft glow; use a cool LED
bulb (never near a real flame). The top ring seats over a standard lamp holder; the
pendant ring takes a cord-set. Print upright with the wide opening down.

## Hyperobject Profile

- **Domain:** household (lighting / décor).
- **CDG interface:** `shade_pattern` (`surface`) — the perforation + socket seat, standard
  **E26/E27 socket**, driven by `pattern`, `pat_rows`, `pat_cols`, `pat_size`, `socket`.
- **Material awareness:** tolerance-by-material (wall tuned per filament; translucent for glow).
- **Commons license:** CERN-OHL-W-2.0.
- **Societal benefit:** a custom shade sized to a standard bulb holder and printed to taste,
  making lighting fixtures repairable and personal instead of disposable retail goods.
