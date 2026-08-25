# Test-Tube Centrifuge Adapter

Sleeve adapters that let 15 mL or 50 mL conical (Falcon-type) centrifuge tubes spin safely in a larger rotor bore, plus a conical-tip cushion that supports the tube point against g-force. A new lab family/cluster that complements — and interoperates with — the `centrifuge-adapter` cartridge on the shared 15/50 mL conical standard.

> Verify balance and rotor rating before spinning. Always balance opposing buckets.

## Parts / Modos

| Mode | Part | What it is |
|------|------|------------|
| `adapter_15` | 15 mL Adapter | Sleeve seating a 15 mL conical tube (Ø17 mm) in a larger rotor bore. |
| `adapter_50` | 50 mL Adapter | Sleeve for a 50 mL conical tube (Ø30 mm) with a ribbed grip collar at the mouth. |
| `cushion` | Conical-Tip Cushion | Bucket-bottom insert with a conical seat that supports and centres the tube tip. |

## Standards & dimensions

- **Conical ("Falcon") tubes:** 15 mL ~ Ø17 mm × ~120 mm; 50 mL ~ Ø30 mm × ~115 mm, with a ~17° conical tip.
- **Interface:** the 15/50 mL conical socket shared with `centrifuge-adapter` (15/50 mL Falcon).
- **Seat:** a lofted conical frustum supports the tube's tapered tip instead of hanging it on its rim.

## Parameters

- `tube_dia` (10–34 mm) — outer diameter of the conical tube (15 mL ~17, 50 mL ~30 mm).
- `rotor_bore` (18–50 mm) — diameter of the rotor bore / bucket.
- `clearance` (0.1–1.0 mm/side) — slip clearance so the tube drops in and out.
- `depth` (30–120 mm) — how far the sleeve runs down the bore.
- `floor` (2–10 mm) — solid material under the tube tip.

## Printing notes / Notas de impresión

**EN:** Print dense (≥40% infill) so the sleeve survives rotor g-force, tip-down or tip-up (the cone forms without supports either way). Start clearance at 0.4 mm. Confirm the tube, adapter and rotor are rated for your speed.

**ES:** Imprime denso (≥40% relleno) para que el manguito resista la fuerza g del rotor, con la punta hacia abajo o arriba (el cono se forma sin soportes). Empieza con holgura de 0.4 mm. Confirma que el tubo, el adaptador y el rotor estén clasificados para tu velocidad.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **15/50 mL Conical Tube Socket** (`socket`, `15/50 mL conical (Falcon)`) — defined by `tube_dia`, `rotor_bore`, `clearance`, `depth`. **compatible_with:** `centrifuge-adapter`.
- **Material awareness:** `shrinkage_compensation` + `tolerance_by_material` declared — the bore adds user clearance per side.
- **Societal benefit:** run small conical tubes in whatever centrifuge and rotor a lab already owns, extending equipment life at the cost of filament.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`; final solid assigned to `result`; dispatch on `target_part`.
- The bore + lofted cone are recesses over a solid floor; the 50 mL grip collar is fused to the barrel with a deep overlap before boring, so every output is **watertight, single-body**.
