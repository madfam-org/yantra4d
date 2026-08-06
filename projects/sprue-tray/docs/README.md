# Sprue Tray

A model-kit parts tray with a compartment grid, a magnetized variant, and a sorting
lid for tiny parts. CadQuery (B-Rep) hyperobject cartridge.

## Modes (parts)

| Mode | Part id | Description |
|------|---------|-------------|
| Parts Tray | `parts_tray` | An open tray with a `cols` × `rows` compartment grid for sprue-cut pieces. |
| Magnetic Tray | `magnetic_tray` | The same tray with 6×2 mm magnet pockets in the underside (2 or 4) so it clings to a steel bench and stacks. |
| Sorting Lid | `sorting_lid` | A friction lid whose top carries its own finer grid (`fine_cols` × `fine_rows`) of blind small-parts pockets. |

The active mode is selected by the `target_part` parameter.

## Key parameters

- **tray_w**, **tray_d**, **tray_h** — outer footprint and interior depth.
- **wall**, **floor**, **corner_r** — shell thickness and rounding.
- **cols**, **rows**, **div_th** — compartment grid and divider thickness.
- **magnet_d**, **magnet_h**, **mag_n** — magnet size and count (2 sides or 4 corners).
- **fine_cols**, **fine_rows**, **fine_depth** — sorting-lid small-parts grid and pocket depth.
- **lid_skirt**, **lid_clear** — lid grip depth and print fit.

## CDG interfaces

- **Parts Compartments** (`grid`, internal) — the compartment grid (`cols`, `rows`,
  `div_th`) that sorts a kit's pieces.
- **Tray Magnet** (`pocket`, internal) — the underside 6 × 2 mm magnet pockets that
  anchor the tray to a steel bench.

## Printing notes

Print all parts flat, no supports. The magnetic tray prints floor-down; drop magnets
into the underside pockets before the last layers or glue them after. Tune `lid_clear`
for your printer's tolerance. The sorting lid doubles as a shallow dish when inverted.

## Watertight strategy

The tray is a solid outer block with a **blind** interior cavity cut from the top (a
cup); dividers are solid walls unioned onto the floor. Magnet pockets are blind
recesses in the underside that never pierce the floor. The sorting lid is a plate plus
a hollow downward skirt (a closed shell), with its small-parts pockets cut as blind
recesses into the plate top — none pierce through. No sphere-tangent unions; every
mode exports watertight with zero negative-volume bodies.
