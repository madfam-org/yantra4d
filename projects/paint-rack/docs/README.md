# Paint Rack

A hobby paint rack with cradle holes sized to the chosen bottle, in flat, tiered and
wall-mounted variants. CadQuery (B-Rep) hyperobject cartridge.

## Modes (parts)

| Mode | Part id | Description |
|------|---------|-------------|
| Flat Rack | `flat_rack` | A slab with a `cols` × `rows` grid of blind cradle recesses. |
| Tiered Rack | `tiered_rack` | A staircase of rows, each raised `step_rise` behind the one in front so every label is visible; each tread holds a row. |
| Wall Rack | `wall_rack` | A vertical back plate with a single forward shelf of cradles and two screw holes for wall mounting. |

The active mode is selected by the `target_part` parameter.

## Bottle types

`bottle` sizes every cradle (diameter + `hole_clear` per side):

| Value | Bottle | Diameter |
|-------|--------|----------|
| `citadel` | Citadel base pot | 34 mm |
| `vallejo` | Vallejo dropper | 30 mm |
| `army-painter` | Army Painter dropper | 29 mm |

## Key parameters

- **cols**, **rows** — cradle grid.
- **hole_clear**, **recess** — per-side clearance and how deep bottles sit.
- **gap**, **margin**, **base_th** — wall between cradles, outer border, floor under
  each cradle.
- **step_rise**, **step_run** — tiered staircase rise per row and tread depth
  (0 = auto-fit the bottle).
- **wall_h**, **wall_th**, **screw_d** — wall-mount back plate height, thickness and
  screw hole size.

## CDG interfaces

- **Paint Bottle Array** (`grid`, "Citadel/Vallejo/dropper") — the cradle grid driven
  by `bottle`, `cols`, `rows` and `hole_clear`; the shared standard that fits any of
  the common paint ranges.
- **Wall Mount** (`bolt_pattern`, internal) — the back-plate screw pattern for the
  wall variant.

## Printing notes

Print flat rack and wall rack directly on the bed, no supports. The tiered rack
prints as a staircase — each tread self-supports the one behind it, so it also needs
no supports. Cradles are blind (closed floor), so paints can't fall through.

## Watertight strategy

Every rack is a solid block — or, for the tiered rack, a union of solid tread blocks
that butt front-to-back with a 0.02 mm overlap so the union stays a single manifold —
with **blind** cradle recesses cut from the top only. Because each taller tread starts
at a larger Y it never overhangs the tread in front, so no recess is sealed into an
internal void (a common source of negative-volume shells). The wall plate's screw
holes are clean through-holes in one face. No sphere-tangent unions; every mode
exports watertight with zero negative-volume bodies.
