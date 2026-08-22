# Folding Board

The printable **garment folding board** — generated with **CadQuery** (B-Rep).
A centre panel with a hinged wing on each side, so a shirt laid face-down folds to
an identical rectangle every time.

Retail folding boards come in one adult size. That is why a folded child's tee and
a folded XXL sweatshirt never stack, and why anyone folding to a shelf that is not
30 cm deep has been folding by eye. This one is generated from the folded width
and height you actually want on the shelf.

The hinges are **real pin knuckles**, not living hinges: each panel carries
interleaved barrels and a printed pin runs through them. Living hinges in PLA
survive a few hundred folds; a pin hinge outlives the board.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Full Set** | `set` | Centre panel, one wing, and one pin laid out flat on one plate as three separate bodies. |
| **Center Panel** | `center_panel` | The middle panel with a knuckle row on each edge. Print **1**. |
| **Side Panel** | `side_panel` | One wing with the complementary interleaving row. Print **2** — flip one on the bed. |
| **Hinge Pin** | `pin` | One pin. Print **2** (a spare is cheap). |

A complete board is 1 × centre + 2 × side + 2 × pin. The `set` mode gives you one
of each; run it twice, or run the single-part modes with the quantities above.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Fold Size | `fold_w` | 200 mm | Finished folded width — the centre panel is exactly this wide. Each wing is 46 % of it, which is what makes the sleeve fold overlap. |
| Fold Size | `fold_h` | 280 mm | Finished folded height; sets the hinge line (72 % of it) and therefore the pin length. |
| Build | `panel_t` | 4.0 mm | Panel thickness. A 300 mm board wants 5–6 mm or it flexes mid-fold. |
| Hinge | `pin_dia` | 4.0 mm | Pin diameter; clamped to 1.6 × `panel_t`. The bore adds 0.35 mm diametral clearance. |
| Hinge | `knuckles` | 3 | Knuckles on the centre-panel side; the wing gets the complement. |
| Build | `lighten` | on | Cut two windows per panel. Skipped automatically if the remaining frame would be too thin. |

## Presets

- **Adult Tee** — 200 × 280.
- **Child Tee** — 140 × 190, no lightening windows.
- **Sweatshirt** — 300 × 400, 6 mm panels.
- **Retail Shelf Gauge** — 240 × 320, centre panel only.

## Print notes

Every part prints **flat on the bed with no supports**. The panels are plates; the
knuckle barrels are cylinders lying on their sides with their axes parallel to the
bed, and a barrel of this diameter self-supports at the 45° tangent without a
brim. The pin prints standing on its head end.

PLA is fine — the board is a jig, not a spring, and nothing in it flexes by
design. 3 perimeters, 15 % infill, 0.2 mm layers. Print at **100 % scale on both
axes**: the interleaved knuckles depend on the 0.4 mm per-side running gap the
model already carries, and a printer running fat extrusions will fuse them.

To assemble: rest a wing beside the centre panel so the two knuckle rows mesh,
then push a pin through. The pin's lead-in taper starts the first knuckle; the
head on the far end stops it walking back out. If a pin is tight, chase the bore
with a drill of the nominal `pin_dia` rather than sanding the pin — an undersized
pin gives the hinge slop, and slop shows up as a crooked fold.

## Geometry notes

The knuckle barrels are cylinders unioned with a **root block that overlaps the
panel edge**, so a barrel is never merely tangent to a flat wall. Both pin bores
are cut with a cylinder that overshoots the hinge line by 20 mm at each end, so no
cut face is ever coincident with a knuckle's own skin. The lightening windows are
cut with a cutter oversized in Z past both faces.

The pin's lead-in is a `loft` to a small **flat** circle, never to a point — a
point is a pole singularity and reads non-watertight — and the chamfer that
receives it is cut on a clean blank before the head is added, never with
`.chamfer()` after a cut.

`set` combines the three parts as a `cq.Compound`, not a `.union()` of
non-touching solids.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Fold Footprint** (`profile`, internal) — the finished folded rectangle;
    defined by `fold_w`, `fold_h`.
  - **Pin Knuckle** (`socket`, internal) — the interleaved hinge barrel and its
    bore; defined by `pin_dia`, `knuckles`, `panel_t`, `fold_h`.
  - **Panel Face** (`surface`, internal) — the surface the garment lies on;
    defined by `fold_w`, `fold_h`, `panel_t`.

No flange-style edge interface is declared: nothing is sewn or threaded along an
edge of a folding board. The garment rests on the `panel_face` surface and the
board's contract with it is the `fold_footprint` profile.

## Fashion Cabinet bridge

FC garments that consume this object: **tee**, **shirt**, **sweatshirt**,
**knit-top** — anything with a `folded_dimensions` block, which is to say the
whole flat-pack side of the catalogue.

FC-side `hardware_ref` block on the garment record:

```json
{
  "garment": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "folding-board",
      "linked": true,
      "params_map": {
        "fold_w": "folded_width_mm",
        "fold_h": "folded_length_mm",
        "panel_t": "max(3, folded_width_mm * 0.02)",
        "pin_dia": "max(3, folded_width_mm * 0.02) * 1.2",
        "knuckles": "2 + round(folded_length_mm / 160)"
      }
    }
  }
}
```

The garment drives the hardware: FC's **folded width** and **folded length** — the
dimensions a catalogue already carries for shipping and shelf planning — become
`fold_w` and `fold_h` through the `fold_footprint` interface, and the panel
thickness scales with the width so a large board stays stiff. `pin_knuckle` is the
interface a shop uses when it wants two boards of different sizes to share a pin
stock.

`CERN-OHL-W-2.0`.
