# Terrain Clip

Modular-terrain hardware — connectors and magnet bases that lock printed or boxed
terrain tiles together during play and break down flat for storage. CadQuery (B-Rep)
hyperobject cartridge built around the 6×2 mm disc magnet.

## Modes (parts)

| Mode | Part id | Description |
|------|---------|-------------|
| Magnet Base | `magnet_base` | A flat plate with a grid (`mag_cols` × `mag_rows`) of blind 6×2 mm magnet pockets, glued under a terrain piece. |
| Peg Connector | `peg_connector` | A low bar with two chamfered pegs that plug into holes in two adjacent tiles, joining them edge to edge. |
| Panel Clip | `clip` | A U-channel clip that slides over the touching edges of two panels and squeezes them together, with a small retaining lip. |

The active mode is selected by the `target_part` parameter.

## Key parameters

- **magnet_d**, **magnet_h** — magnet size (default 6 × 2 mm).
- **plate_th**, **mag_cols**, **mag_rows**, **mag_pitch**, **mag_margin** — magnet
  base plate thickness, pocket grid, spacing and border.
- **peg_d**, **peg_h**, **peg_span**, **bar_th** — connector peg size, height,
  spacing, and bar thickness.
- **clip_gap**, **clip_arm**, **clip_w**, **clip_wall** — the panel thickness the
  clip grips, its grip depth, width and wall.

## CDG interfaces

- **Terrain Magnet** (`pocket`, internal) — the 6 × 2 mm pocket grid (`magnet_d`,
  `magnet_h`, `mag_pitch`) that mates any tile to a steel sheet or another
  magnetized piece.
- **Edge Peg** (`socket`, internal) — the two-peg edge interface (`peg_d`,
  `peg_span`, `peg_h`) that joins adjacent tiles.

## Printing notes

Print all parts flat, no supports. The magnet base prints pockets-up or pockets-down
(pockets-down needs no bridging). Drop the magnets in before the final layers or glue
them after. Tune `clip_gap` to your panel thickness; the clip flexes to snap over.

## Watertight strategy

The magnet base is a solid plate with **blind** pockets cut from the underside (never
through the top face). The peg connector and the clip are pure unions of extruded
boxes and cylinders — all closed primitives — so no free edges appear. No
sphere-tangent unions and no through-hollows; every mode exports watertight with zero
negative-volume bodies.
