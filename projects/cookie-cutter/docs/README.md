# Parametric Cookie Cutter & Stamp

A press-and-cut cookie / fondant cutter generated with CadQuery (B-Rep). The
cutting edge follows a chosen outline; a wider top flange gives you something to
press on.

## Modes

| Mode | `target_part` | What it makes |
| --- | --- | --- |
| **Cutter** | `cutter` | A thin closed-loop cutting wall + top pressing flange in your chosen shape. |
| **Cutter + Stamp** | `cutter_stamp` | The cutter plus an interior relief ridge that embosses a detail into the dough in the same press. |
| **Double Cutter** | `double_cutter` | Two concentric outlines bridged by the flange — cuts a ring / donut of dough in one press. |

## Shapes

`circle` · `star` (5-point) · `heart` · `square` · `hex` (hexagon). Select with
the **Shape** parameter and set the widest span with **Size**.

## Key parameters

- **Size (mm)** — widest span of the outline.
- **Cutter Height (mm)** — how deep the cutting wall goes.
- **Cutting Edge (mm)** — wall thickness (default 0.8 mm). Thinner cuts cleaner
  but is more fragile; 0.6 mm is the practical floor.
- **Press Flange (mm)** — extra width of the top flange you press with a thumb.
- **Stamp Relief (mm)** — height of the embossing detail (Cutter + Stamp).
- **Ring Gap (mm)** — width of the dough ring left by the Double Cutter.

## Geometry notes

The cutting wall is a genuine **hollow prism** (outer filled outline minus inner
filled outline), so it is watertight with a real wall thickness — not a
zero-thickness swept skin. The flange and stamp are fused with a small vertical
overlap so every boolean is volumetric. Verified watertight across all shapes and
both extra modes, with no negative-volume bodies.

## Printing

- Print the cutter **flange-up** (open cutting edge on the bed) for the cleanest
  edge, or upright with the edge up. A 0.4 mm nozzle prints the 0.6–0.8 mm wall
  in ~2 perimeters.
- Slow the first layers for the thin wall; brim helps tall cutters stay put.

## Food-contact responsibility

This cartridge models **geometry only**. Whether the printed part is safe for
direct food contact depends on choices outside this model: use a food-safe
filament, be aware that FDM layer lines can harbour residue, and apply a
food-safe sealing/coating and hygienic cleaning as appropriate. Food safety,
sealing, and compliance are the maker's responsibility.

## License

Open hardware under **CERN-OHL-W-2.0**. Part of the Yantra4D Hyperobject Commons.
