# Optical Post & Breadboard Mount

A parametric optics-bench hyperobject. Three interoperable parts share the real optical-breadboard hole grid so you can print a benchtop optics kit on demand.

## Parts / Modos

| Mode | Part | What it is |
|------|------|------------|
| `post` | Optical Post | Ø12.7 mm cylindrical post, tapped-head mounting socket, base fastener bore, milled setscrew flat. |
| `base_clamp` | Breadboard Base Clamp | Footed plate that seats a post and bolts to the breadboard with two counterbored grid fasteners. |
| `grid_plate` | Mini Breadboard Tile | Plate drilled with a rectangular array of counterbored holes on the true 25 mm grid. |

## Standards & dimensions

- **Grid:** 25 mm metric / 1.00 in (25.4 mm) imperial hole centers — Thorlabs breadboard convention, 12.5 mm edge border.
- **Fasteners:** M6 (metric) or 1/4-20 (imperial, Ø6.35 mm), selectable via `mount_thread`.
- **Post:** Ø12.7 mm (1/2 in, TR-series) default; Ø25.4 mm (1 in, P-series) at the slider maximum.

## Parameters

- `post_height` (20–200 mm) — beam height.
- `post_diameter` (10–25.4 mm) — Ø12.7 for 1/2 in, Ø25.4 for 1 in.
- `grid_pitch` (20–30 mm) — 25 metric, 25.4 imperial.
- `mount_thread` — `M6` or `1/4-20`.
- `grid_cols`, `grid_rows` (2–6) — breadboard tile array size.

## Printing notes / Notas de impresión

**EN:** Print posts vertically for a round cross-section; use 100% infill or PETG for posts over 100 mm to limit beam-height drift under load. The base clamp and tile print flat with no supports.

**ES:** Imprime los postes en vertical para una sección circular; usa relleno 100% o PETG para postes de más de 100 mm y limitar la deriva de altura del haz. La base y la placa se imprimen planas sin soportes.

## License

CERN-OHL-W-2.0
