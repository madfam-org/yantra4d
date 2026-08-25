# Cuvette Adapter Sleeve

A drop-in sleeve that adapts cuvette sizes to the universal **12.5 mm square** holder slot used by spectrophotometers, cuvette racks and filter wheels. Companion to the `cuvette` family — mates the `cuvette-rack` and `filter-wheel` cuvette wells.

## Parts / Modos

| Mode | Part | What it is |
|------|------|------------|
| `sleeve` | Square Drop Sleeve | Square outer footprint to the holder slot; square inner pocket for a smaller cuvette. |
| `round_adapter` | Round-to-Square Adapter | Square outer prism with a round bore to seat a round cuvette or vial in a square slot. |
| `riser_sleeve` | Height Riser Sleeve | Sleeve with a solid riser base + thumb slot so a short cuvette's window centres in a tall light path. |

## Standards & dimensions

- **Cuvette:** 10 mm optical path, ~12.5 mm square outer footprint, ~45 mm tall (ISO / Beckman / Hellma macro-cuvette convention).
- **Holder slot:** 12.5 mm square — the interface shared with `cuvette-rack` (10 mm cuvette) and `filter-wheel` (12.5 mm square well).
- **Fit:** user `clearance` is added per side to the inner pocket / bore.

## Parameters

- `cuvette_size` (6–12 mm) — inner size (square side for a cuvette, diameter for a round vial).
- `holder_size` (10–25 mm) — outer square footprint matching the holder slot.
- `sleeve_h` (20–60 mm) — cuvette height reference; sets sleeve proportions.
- `clearance` (0.1–1.0 mm/side) — slip clearance.
- `floor_th` (1–6 mm) — sealed bottom under the cuvette.
- `riser` (0–30 mm) — solid base height lifting a short cuvette into the light path.

## Printing notes / Notas de impresión

**EN:** Print open-end-up so pockets form without supports. For optical work print opaque and matte to avoid stray light in the beam path. Start clearance at 0.4 mm. This is a bench aid, not a calibrated optical accessory.

**ES:** Imprime con el extremo abierto hacia arriba para que los huecos se formen sin soportes. Para trabajo óptico imprime opaco y mate para evitar luz parásita en el paso del haz. Empieza con holgura de 0.4 mm. Es una ayuda de mesa, no un accesorio óptico calibrado.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **10 mm Cuvette to 12.5 mm Holder Socket** (`socket`, `10 mm path / 12.5 mm square cuvette`) — defined by `cuvette_size`, `holder_size`, `clearance`. **compatible_with:** `cuvette-rack`, `filter-wheel`.
- **Material awareness:** `tolerance_by_material` declared — pocket clearance tunes to the print material.
- **Societal benefit:** lets a lab reuse one spectrophotometer / rack across cuvette sizes and round vials on the universal 12.5 mm slot instead of buying dedicated adapters.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`; final solid assigned to `result`; dispatch on `target_part`.
- Every pocket / bore is a blind recess leaving a solid floor (the thumb slot opens to a face and to the pocket), so every output is **watertight, single-body**.
