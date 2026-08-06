# Ice / Chocolate / Casting Mold Tray

A tray of cavities generated with CadQuery (B-Rep). Pour into it directly (ice,
chocolate, wax, resin) or use it as a printed master to cast a flexible silicone
mold. Three parts share one CDG interface — the mold cavity array.

## Modes

| Mode | `target_part` | What it makes |
| --- | --- | --- |
| **Cavity Tray** | `cavity_tray` | A solid tray with a `cols` × `rows` grid of the chosen cavity. |
| **Bar Mold** | `bar_mold` | A row of long bar cavities (chocolate bars / ice sticks). |
| **Single Large** | `single_large` | One large cavity (~1.8×) of the chosen shape in a snug tray. |

## Cavity shapes

`cube` (square pocket) · `sphere_half` (half-sphere bowl) · `bar` (elongated
pocket) · `custom` (round pocket). Set with the **Cavity Shape** parameter.

## Key parameters

- **Cavity Size (mm)** — nominal plan size of each cavity.
- **Cavity Depth (mm)** — how deep each cavity goes.
- **Release Draft (mm)** — taper (mouth wider than base) for easy release.
- **Columns / Rows** — grid count (Bar Mold uses Columns as the bar count).
- **Wall Between (mm)** — spacing between cavities.
- **Floor Thickness (mm)** — solid floor kept under every cavity.

## Geometry notes

Every cavity is **cut** from a solid tray blank (hollow-by-cut). Box and round
pockets are single lofted frustums (draft in one solid). The half-sphere bowl is
built as a **loft of stacked circles down to a tiny flat bottom**, not a
sphere/revolve — a true bowl apex is a pole singularity that the STL tessellator
leaves as a sliver crack (topologically closed but not watertight). The flat spot
(~0.8 mm) removes the pole so the STL is genuinely watertight. Outer edge fillets
are applied to the clean blank before cavities are cut. Cavities always open up
through the top face, and a solid floor is always kept beneath them.

Verified watertight across every cavity shape, both extra modes, and an 8×8
extreme, with **zero negative-volume bodies**. All three modes are distinct.

## Printing

- Print **cavity-up** on the bed; no supports needed. For direct-pour food use,
  a smooth-ish top surface and a food-safe filament matter.
- For **silicone casting**, print the tray as a master, cast platinum-cure
  silicone over it, then use the silicone for food — the print never touches food.

## Food-contact responsibility

Direct-pour food use contacts the print. Geometry only — food-safe
filament/resin, sealing, and hygiene are the maker's responsibility. Casting a
silicone mold from the printed master is the recommended food-safe route.

## License

Open hardware under **CERN-OHL-W-2.0**. Part of the Yantra4D Hyperobject Commons.
