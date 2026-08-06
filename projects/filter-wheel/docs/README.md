# Cuvette / Filter Wheel

A benchtop optics hyperobject for swapping filters and organizing spectroscopy cells.

## Parts / Modos

| Mode | Part | What it is |
|------|------|------------|
| `wheel` | Filter / Optic Wheel | Detented rotating disc with N optic pockets, per-seat light-path holes, central shaft bore, rim index notches. |
| `cuvette_block` | Cuvette Holder Block | Multi-well block for 12.5 mm square (10 mm path) cuvettes, with a beam-access window at each well. |
| `hub_cap` | Retaining Hub Cap | Stepped cap with locating boss + shaft bore that pins the wheel to its shaft. |

## Standards & dimensions

- **Optics:** Ø1 in = 25.4 mm, Ø25 mm metric, Ø1/2 in = 12.7 mm — selectable via `optic_diameter`.
- **Cuvettes:** 12.5 mm square external footprint (standard 10 mm path-length cell), ~45 mm body height.
- **Optic seats** use +0.2 mm radial clearance; each seat has a concentric light-path bore.

## Parameters

- `optic_diameter` (12.7–25.4 mm) — optic seat size.
- `positions` (3–8) — number of filter stations (and rim detents).
- `wheel_thickness` (4–14 mm).
- `bore_diameter` (3–10 mm) — central shaft bore, shared with the hub cap.
- `cuvette_wells` (1–8) — number of cuvette pockets.

## Printing notes / Notas de impresión

**EN:** Print the wheel and cuvette block flat, seats facing up, no supports. Use opaque black filament to suppress stray light between filter positions. The hub-cap boss is a slip-fit into the wheel bore — scale `bore_diameter` to your shaft.

**ES:** Imprime la rueda y el bloque planos, con los asientos hacia arriba, sin soportes. Usa filamento negro opaco para suprimir luz parásita entre posiciones. El cubo de la tapa entra a presión ligera en el barreno de la rueda; ajusta `bore_diameter` a tu eje.

## License

CERN-OHL-W-2.0
