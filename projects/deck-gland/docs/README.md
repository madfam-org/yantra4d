# Deck Cable Gland

A sealed cable pass-through plate for a boat deck, RV roof, or panel. Cables enter
through a raised gland boss with a stepped grommet cavity, and the plate bolts down on
a gasket. Sized by cable diameter and a rectangular bolt pattern.

## Modes / Parts

| Mode | Part id | What it is |
|------|---------|------------|
| Single Gland Plate | `gland_plate` | One sealed cable boss centred on a bolt-patterned plate. |
| Split (Retrofit) Gland | `split_gland` | A two-half plate that clamps around an already-terminated cable. |
| Multi-Cable Gland | `multi_gland` | A wider plate with a row of `cable_count` sealed bosses. |

## Key Parameters

- **Cable Diameter** — outer diameter of the cable being sealed.
- **Boss Height** — how far the sealing boss rises above the plate.
- **Grommet Counterbore** — top step depth that seats a rubber grommet.
- **Plate Thickness / Edge Margin** — base plate body and material past the bolts.
- **Bolt Clearance / Spacing X / Spacing Y** — the rectangular deck bolt pattern.
- **Cable Count** — number of bosses in a multi-cable row.

## Printing Notes

Print in PETG or ASA. Bed the plate on butyl tape or a silicone gasket and seat a
rubber grommet in the top counterbore for a watertight cable seal. The split gland lets
you seal a pre-wired cable without cutting the connector off.

## Hyperobject Profile

- **Domain:** hybrid (marine / RV deck & roof penetrations).
- **CDG interfaces:**
  - `deck_bolt_pattern` (`bolt_pattern`) — the rectangular corner bolt layout (`internal`), driven by `bolt_dia`, `bolt_dx`, `bolt_dy`, `margin`.
  - `cable_seal_bore` (`socket`) — the stepped cable/grommet cavity (`internal`), driven by `cable_dia`, `boss_h`, `seal_step`.
- **Material awareness:** tolerance-by-material (grommet counterbore fit varies by filament).
- **Commons license:** CERN-OHL-W-2.0.
- **Societal benefit:** a watertight cable entry sized to the exact cable and bolt layout,
  keeping water out of decks, roofs, and enclosures without a fixed-size commercial gland.
