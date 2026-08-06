# Microscope Objective Case

A protective threaded storage hyperobject for microscope objectives. Threads are real fused helical ribs — objectives screw in exactly as on a microscope nosepiece.

## Parts / Modos

| Mode | Part | What it is |
|------|------|------------|
| `threaded_nest` | Single Threaded Case | Knurled body with a female objective thread and a lens-clearance well. |
| `multi_nest_block` | Multi-Nest Storage Block | Tray block with N female-threaded objective nests in a row. |
| `dust_cap` | Threaded Dust Cap | Male-threaded plug with a knurled head that screws into a nest to seal it. |

## Standards & dimensions

- **RMS thread:** W 0.800 in × 36 TPI — major Ø 20.32 mm, pitch 0.7056 mm (DIN 58888 / ISO 8038 / BS 7012).
- **M25 thread:** M25 × 0.75 — major Ø 25.0 mm, pitch 0.75 mm.
- **Thread modeling:** true pitch and major diameter, built as a volumetric helical rib swept from a triangular profile and fused into the wall (not cut grooves). Engagement is a fixed ~3.5 turns for a well-conditioned, printable thread.
- **Clearance:** user `clearance` is added per side on top of the nominal major diameter.

## Parameters

- `thread_standard` — `RMS` or `M25`.
- `clearance` (0.1–0.5 mm/side) — printed-thread fit slop.
- `nest_count` (1–5) — nests in the storage block.
- `well_depth` (4–20 mm) — lens-clearance well below the thread.

## Printing notes / Notas de impresión

**EN:** Print all parts thread-axis vertical (open end up) so the helical thread forms cleanly without supports. Start clearance at 0.25 mm and increase if the objective binds. Use PETG for chemical resistance around immersion oils.

**ES:** Imprime todas las piezas con el eje de la rosca vertical (extremo abierto hacia arriba) para que la rosca helicoidal se forme limpiamente sin soportes. Empieza con holgura de 0.25 mm y auméntala si el objetivo se atasca. Usa PETG para resistencia química cerca de aceites de inmersión.

## License

CERN-OHL-W-2.0
