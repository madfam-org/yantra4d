# Dice Tower

A dice tower with internal angled baffles and a matching catch tray. CadQuery
(B-Rep) hyperobject cartridge.

## Modes (parts)

| Mode | Part id | Description |
|------|---------|-------------|
| Tower | `tower` | Four-wall chimney (open top, closed floor) with a front exit window and `baffles` alternating angled ramps. |
| Rolling Tray | `tray` | A shallow catch / rolling tray with a raised, filleted rim. |
| Compact Tower | `compact_tower` | A shorter, smaller-footprint tower (auto-scaled to ~60% height, ~80% bore, ≤3 baffles) for travel. |

The active mode is selected by the `target_part` parameter.

## Key parameters

- **tower_h**, **bore**, **wall** — tower height, clear interior width/depth, and
  wall thickness.
- **baffles** — number of internal ramps. They alternate side to side so a die
  leaving one ramp always lands on the next.
- **baffle_slope** — ramp angle from horizontal (steeper = faster tumble).
- **tray_w**, **tray_d**, **tray_rim**, **tray_wall**, **tray_floor** — the catch
  tray footprint, rim height, wall and floor thickness.

## CDG interfaces

- **Baffle Stack** (`surface`, internal) — the internal ramp surfaces defined by
  `baffles` / `baffle_slope` / `bore`; the working surface that makes the roll fair.
- **Dice Exit Window** (`profile`, internal) — the front opening the dice roll out
  of, sized from `bore` and `wall`.

## Printing notes

Print the tower upright — the open top and front window print without supports
because the baffles self-support at their slope. The floor gives it a stable base.
Print the tray flat. No hardware required.

## Watertight strategy

The tower is a closed-floor cup (an outer prism with a blind interior cavity) — one
closed manifold. The dice exit is a rectangular window cut fully **through** one wall
face (never a rim notch), so no free edges appear. Baffles are solid wedges,
intersected with the interior column and unioned into the shell, so nothing protrudes
and the result stays manifold and positive-volume. The tray is a solid slab with a
blind recess. Every mode exports watertight with zero negative-volume bodies.
