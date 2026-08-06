# Espresso Dosing Funnel & Ring

A dosing aid that slips over an espresso portafilter basket rim to guide ground
coffee in cleanly, generated with CadQuery (B-Rep). Three parts share one CDG
interface — the portafilter basket rim.

## Modes

| Mode | `target_part` | What it makes |
| --- | --- | --- |
| **Dosing Funnel** | `dosing_funnel` | A gripping ring that slips over the basket rim, with a flared funnel wall above to guide grounds in. Optional magnet pockets for a magnetic funnel. |
| **Dosing Ring** | `dosing_ring` | A short ring / collar only (no flare) — a minimal cuff that raises the basket wall a few mm. |
| **Leveler Base** | `leveler_base` | A low base disc with a basket-locating skirt and a central bore — a leveling / distribution reference that sits on the basket. |

## Basket sizes

`58mm` · `54mm` · `51mm` (nominal portafilter basket rim OD). Set with the
**Basket Size** parameter. The ring slips **over** the basket rim, so the fit is
sized to the basket outer diameter plus the slip-fit clearance.

## Key parameters

- **Basket Size** — 58 / 54 / 51 mm.
- **Slip-Fit Clearance (mm)** — per-side gap over the rim.
- **Grip Bead (mm)** — inward retaining bead depth (0 = plain friction fit).
- **Wall Thickness (mm)** — ring / funnel wall.
- **Ring Height (mm)** — height of the gripping ring.
- **Funnel Height / Funnel Flare (mm)** — the flare above the ring (funnel mode).
- **Magnet Pockets** — blind pockets for magnets (magnetic funnel).

## Geometry notes

Solids of revolution built by hollow-by-cut (outer cylinder minus rim bore). The
funnel flare is an outer loft minus an inner loft (a real-thickness cone) fused
with a vertical overlap. The rim grip is a revolved bead fused to the wall (like
the reference cup-lid grip bead), not a tangent kiss. Magnet pockets are blind
cylinders cut from the underside, leaving a solid floor — no through-void, opening
downward so nothing is sealed. Verified watertight across all three basket sizes,
the magnetic variant, and extremes, with **zero negative-volume bodies**. All
three modes are distinct.

## Printing

- Print the **funnel** ring-down (funnel opening up); no supports for moderate
  flares. Steep flares may want a light support or a brim.
- If using magnets, pause the print at the pocket floor to drop them in, or glue
  after printing. The grip bead gives a positive click onto the basket.

## Food-contact responsibility

Ground coffee passes through. Geometry only — food-safe filament, hygiene, and
regular cleaning are the maker's responsibility.

## License

Open hardware under **CERN-OHL-W-2.0**. Part of the Yantra4D Hyperobject Commons.
