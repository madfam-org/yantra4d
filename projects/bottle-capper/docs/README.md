# Homebrew Crown-Cap Seat

Bottling tools for standard **26 mm crown caps**, generated with CadQuery
(B-Rep). Three parts share one CDG interface — the 26 mm crown-cap seat.

## Modes

| Mode | `target_part` | What it makes |
| --- | --- | --- |
| **Capper Bell** | `cap_bell` | A closed-top cylinder with an internal cap pocket that steps down to a neck-clearance bore. Placed over a capped bottle, its shoulder crimps the cap flutes down when struck / pressed. Optional grip flutes. |
| **Bench Seat** | `bench_seat` | A puck the bottle stands on: a neck-locating counterbore on top with a deeper crown-cap recess at its floor, keeping the bottle aligned under a lever press. |
| **Cap Organizer** | `cap_organizer` | A shallow tray with a grid of cap-diameter recesses to hold loose crown caps upright and ready. |

## Standard dimensions (nominal)

- Crown-cap OD (uncrimped) ≈ **32.1 mm** (`cap_dia`)
- Crown-cap seat the flutes crimp down to ≈ **26 mm** (the interface)
- Cap height ≈ 6 mm

## Key parameters

- **Crown-Cap OD (mm)** — outer diameter of an uncrimped cap.
- **Wall Thickness (mm)** — body/bell wall; a striking tool wants this thick
  (default 4 mm, 2.5 mm floor).
- **Bell Height (mm)** — overall height of the capper bell.
- **Bottle Neck OD (mm)** — the bottle finish OD to clear (bell) or locate (seat).
- **Cap Recess Depth (mm)** — how deep the cap sits in the bench seat.
- **Recesses per Row** — organizer grid width (rows derive from it).

## Geometry notes

Every part is a solid with pockets **cut** into it (hollow-by-cut). Pocket
heights are derived from a fixed solid floor so no cavity is ever sealed into an
internal void — verified across all modes with **zero negative-volume bodies**.
All three modes are geometrically distinct.

## Printing

- Print the **bell** open-end-up; a 4 mm wall gives it striking mass. For a
  hand-strike tool, PETG/ABS survives impact better than PLA.
- The **bench seat** prints flat, counterbore up.

## Food-contact responsibility

Geometry only. Only the cap seat contacts the bottle rim — not the beverage —
but food-safe filament choice, hygiene, and any sealing remain the maker's
responsibility.

## License

Open hardware under **CERN-OHL-W-2.0**. Part of the Yantra4D Hyperobject Commons.
