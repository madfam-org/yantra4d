# Microscope Objective Turret

A rotating multi-objective nosepiece (turret) with **real** female RMS / M25 objective threads — objectives screw into any port exactly as on a factory turret. Grows the `rms-objective` family; objectives interchange with the `objective-case` cartridge.

## Parts / Modos

| Mode | Part | What it is |
|------|------|------------|
| `nosepiece` | Rotating Nosepiece | Turret disc with N female-threaded objective ports around a central through pivot bore. |
| `male_stub` | Male Objective Stub | Male-threaded stub on a knurled base to hold an objective on the bench outside the scope. |
| `dust_plug` | Port Dust Plug | Male-threaded plug with a knurled head that seals an empty turret port against dust. |

## Standards & dimensions

- **RMS thread:** W 0.800 in × 36 TPI — major Ø 20.32 mm, pitch 0.7056 mm (DIN 58888 / ISO 8038 / BS 7012). Shared with `objective-case`.
- **M25 thread:** M25 × 0.75 — major Ø 25.0 mm, pitch 0.75 mm.
- **Thread modeling:** true pitch and major diameter, built as a volumetric helical rib swept from a triangular profile and fused into the wall (not cut grooves). Engagement is a fixed 3.5 turns (a half-integer) for a well-conditioned, printable thread.
- **Port packing:** ports are placed on a pitch circle sized to clear one bore plus a wall between neighbours.

## Parameters

- `thread_standard` — `RMS` or `M25`.
- `port_count` (2–6) — objective positions on the turret.
- `clearance` (0.1–0.5 mm/side) — printed-thread fit slop.
- `pivot_bore` (3–12 mm) — central axle through-hole.
- `turret_thick` (6–24 mm) — disc thickness; must exceed the thread engagement height.

## Printing notes / Notas de impresión

**EN:** Print the nosepiece flat (pivot axis vertical) so the ports' helical threads form cleanly without supports. Start clearance at 0.25 mm and open it up if objectives bind. This is a hobbyist / repair aid — parfocality and centration are **not** guaranteed on a printed turret; consult an optics technician for precision work.

**ES:** Imprime el revólver plano (eje de pivote vertical) para que las roscas helicoidales de los puertos se formen sin soportes. Empieza con holgura de 0.25 mm y ábrela si los objetivos se atascan. Es una ayuda para aficionados / reparación — la parfocalidad y el centrado **no** están garantizados en un revólver impreso; consulta a un técnico en óptica para trabajo de precisión.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **RMS / M25 Objective Thread Port** (`thread`, `RMS W0.800in x 36 TPI (20.32 mm, DIN 58888) / M25 x 0.75`) — defined by `thread_standard`, `clearance`, `port_count`. **compatible_with:** `objective-case`.
- **Material awareness:** `shrinkage_compensation` + `tolerance_by_material` declared — the port bore adds user clearance per side over the nominal major diameter.
- **Societal benefit:** restores magnification changing to old / teaching / self-built microscopes and lets makers build multi-objective scopes on the open RMS standard.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`; final solid assigned to `result`; dispatch on `target_part`.
- Threads are fused helical ribs (never boolean-cut grooves); objective ports and the pivot are through-holes, so every output is **watertight, single-body**.
