# Wheelchair Cup Holder

A cup holder that snap-clamps to the round frame tube of a wheelchair, walker or rollator (**3/4″–1″, 19–25 mm**) so a drink stays within reach. A new mobility family/cluster that shares the mobility-tube clamp with the `mobility-accessory` cartridge.

> An adaptive aid, **not** certified medical equipment. Fit is user-specific — confirm the clamp grips your frame before loading.

## Parts / Modos

| Mode | Part | What it is |
|------|------|------------|
| `cup_holder` | Cup Holder | C-clamp carrying an open cup basket sized to a standard drink cup. |
| `bottle_clamp` | Bottle Cradle | C-clamp carrying a deeper, narrower cradle for a water bottle. |
| `clamp_only` | Universal Clamp | Bare C-clamp with a bolt pad so you can mount your own tray or accessory. |

## Standards & dimensions

- **Frame tubing:** 3/4″–1″ (19.05–25.4 mm) round tube — the common wheelchair / walker / rollator size.
- **Clamp:** a C-shaped snap clamp (the shared interface with `mobility-accessory`); the bore adds user clearance per side and grips by spring.
- **Cup:** standard drink cups are ~74 mm across the base.

## Parameters

- `tube_dia` (19–32 mm) — outer diameter of your mobility frame tube.
- `cup_dia` (50–100 mm) — drink cup / bottle base diameter.
- `clamp_wall` (2.5–8 mm) — C-clamp wall thickness (thinner flexes more).
- `clearance` (0–1.2 mm/side) — tube-bore gap; 0 for a tight grip.
- `cup_wall` (2–6 mm) — cup basket wall and floor.
- `cup_h` (30–90 mm) — basket height around the cup.

## Printing notes / Notas de impresión

**EN:** Print with the clamp bore axis vertical so the C-mouth prints cleanly. Use PETG (or TPU for the clamp) so it flexes over the tube without cracking. Set `tube_dia` to your frame. Check the grip before hanging a full cup.

**ES:** Imprime con el eje del barreno de la abrazadera vertical para que la boca en C salga limpia. Usa PETG (o TPU para la abrazadera) para que flexione sobre el tubo sin romperse. Ajusta `tube_dia` a tu marco. Verifica la sujeción antes de colgar un vaso lleno.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Mobility Tube Clamp** (`socket`, `3/4-1in mobility tube`) — defined by `tube_dia`, `clamp_wall`, `clearance`. **compatible_with:** `mobility-accessory`.
- **Material awareness:** `tolerance_by_material` declared — the clamp bore clearance tunes to the print material.
- **Societal benefit:** keeps a drink within reach for wheelchair / walker / rollator users, printed to fit their exact frame tube, interoperable with the wider mobility-accessory family.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`; final solid assigned to `result`; dispatch on `target_part`.
- The clamp mouth, basket bore and wall windows all open to a face; the clamp, neck and basket are joined with deep overlaps, so every output is **watertight, single-body**.
