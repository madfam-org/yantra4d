# Miniature Base

Wargame / RPG miniature bases in the standard tabletop footprints, plus a
movement tray. CadQuery (B-Rep) hyperobject cartridge.

## Modes (parts)

| Mode | Part id | Description |
|------|---------|-------------|
| Round Base | `round_base` | A round base (25/32/40/50/60 mm) with a beveled top edge, optional rim lip, optional light texture, and an optional 6×2 mm magnet pocket underneath. |
| Square Base | `square_base` | A square base (25/50 mm) with the same top-edge and magnet options. |
| Movement Tray | `movement_tray` | A rimmed tray with a grid (`tray_cols` × `tray_rows`) of recessed seats sized to the chosen base, holding a unit of minis together. |

The active mode is selected by the `target_part` parameter.

## Key parameters

- **base_size** — footprint: `25mm` / `32mm` / `40mm` / `50mm` / `60mm` round, or
  `25sq` / `50sq` square.
- **thickness**, **bevel** — plate thickness and top-edge chamfer.
- **lip** / **lip_h** — optional raised rim on the top face.
- **textured** — a light recessed dimple ring on the top.
- **magnet** / **magnet_d** / **magnet_h** — blind magnet pocket in the underside
  (default 6 × 2 mm). The pocket never pierces the top face.
- **tray_cols** / **tray_rows** / **tray_gap** / **tray_wall** / **tray_seat_h** —
  movement-tray grid, seat spacing, rim wall and seat depth.

## CDG interfaces

- **Base Footprint** (`profile`, "tabletop base sizes") — driven by `base_size`;
  the shared footprint standard that lets any mini interoperate with trays,
  storage sheets and other bases.
- **Magnet Pocket** (`pocket`, internal) — the 6 × 2 mm recess that mates minis to
  steel movement trays and storage.

## Printing notes

Print flat on the bed, no supports. For the magnet pocket, pause the print near the
top of the pocket to drop a magnet in, or glue it afterward. Texture and bevel are
purely cosmetic and printable at any layer height.

## Watertight strategy

Each base is a single primitive (disc or box); the top edge is chamfered on a clean
blank **before** any pockets are cut; the magnet pocket and tray seats are open
blind recesses that never pierce through. No sphere-tangent unions are used, so every
mode exports a closed, manifold, positive-volume solid.
