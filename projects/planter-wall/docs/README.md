# Planter Wall

A modular vertical-garden wall: interlocking pocket modules hang on a base rail and clip
to each other on a grid, so a bare wall becomes a living green field. Each pocket holds
soil with drainage; corner modules close row edges; a base rail carries the bottom row.

## Modes / Parts

| Mode | Part id | What it is |
|------|---------|------------|
| Pocket Module | `pocket_module` | A soil pocket with drainage, side interlocks, and a rear rail hook. |
| Corner Module | `corner_module` | A pocket with one closed side to finish a row edge. |
| Base Rail | `base_rail` | A wall-screw rail with a ledge the bottom pockets hook onto. |

## Key Parameters

- **Module Width / Height** — module size and grid pitch.
- **Pocket Depth** — how far the pocket projects (soil volume).
- **Wall Thickness** — pocket and rail walls.
- **Interlock Peg / Fit** — side peg / rail hook size and socket clearance.
- **Screw Clearance** — base-rail wall screw hole.
- **Drainage Hole** — floor drainage diameter.

## How It Builds (watertight & fast)

Every part is prismatic: the pocket is an open-top box hollowed for soil, with a sloped
front mouth, floor drainage holes, a rear hook lip that catches the rail ledge, and a
side peg (+X) / socket (-X) so modules tile into a **grid**. The corner module unions a
closed cap over the -X side. The base rail is a screw plate with a forward ledge and
upstand. No expensive booleans — all variants export watertight in a couple of seconds.

## Printing Notes

Print in PETG for UV and moisture resistance outdoors; PLA is fine indoors. Line pockets
with landscape fabric or use a nursery liner. Screw the base rail level first, hook the
bottom row of pockets onto it, then build upward — each row's rear hook rests on the row
below and the side pegs lock neighbours together.

## Hyperobject Profile

- **Domain:** household (gardening).
- **CDG interface:** `planter_wall_module` (`grid`) — the module pitch and peg/socket grid
  interlock, standard `internal`, driven by `module_w`, `module_h`, `peg`, `fit`.
- **Material awareness:** tolerance-by-material (interlock fit tuned per filament; PETG outdoors).
- **Commons license:** CERN-OHL-W-2.0.
- **Societal benefit:** grows food and greenery on any wall from tileable printed pockets —
  vertical gardening for small spaces and food resilience without proprietary green-wall systems.
