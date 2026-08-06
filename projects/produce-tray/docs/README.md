# Egg / Produce Tray

Stackable trays for storing eggs and produce, generated with CadQuery (B-Rep).
Three parts share one CDG interface — the cup array — and a common stacking lip
so trays nest.

## Modes

| Mode | `target_part` | What it makes |
| --- | --- | --- |
| **Egg Tray** | `egg_tray` | An array of round egg cups (chamfered mouths) that cradle eggs upright, with a stacking lip. |
| **Produce Tray** | `produce_tray` | A flat tray divided into a grid of open compartments by interior walls, for berries and small produce. |
| **Stacking Tray** | `stacking_tray` | A plain shallow tray with the shared stacking lip — a drip base or nesting spacer. |

## Key parameters

- **Cup Diameter (mm)** — egg-cup diameter (a chicken egg is ~45 mm); also sets
  the tray cell size shared across all three modes.
- **Cup Depth (mm)** — how deep each egg cup goes.
- **Columns / Rows** — grid count.
- **Wall Thickness (mm)** — tray and divider wall.
- **Floor Thickness (mm)** — tray floor.
- **Stacking Lip (mm)** — rim height that lets trays nest.
- **Compartment Height (mm)** — produce compartment wall height.

## Geometry notes

Solids with pockets **cut** in. Egg cups are plain cylinders with a chamfered
mouth (cylinders tessellate watertight and fast — no pole singularity). Divider
walls and the stacking-lip rim are unioned with a small vertical overlap so every
boolean is volumetric. All cavities open up through the top face — no trapped
voids. Verified watertight across all three modes and 8×8 extremes, with **zero
negative-volume bodies**. All three modes are distinct.

## Printing

- All three print flat, cups/compartments up, no supports. A 0.4 mm nozzle with
  2 perimeters is plenty. The chamfered cup mouths ease eggs in and out.
- The shared cell size means the egg, produce, and stacking trays at the same
  column/row count nest together.

## Food-contact responsibility

Eggs and produce contact the print. Geometry only — food-safe filament, hygiene,
and regular washing are the maker's responsibility.

## License

Open hardware under **CERN-OHL-W-2.0**. Part of the Yantra4D Hyperobject Commons.
