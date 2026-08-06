# Grip-Aid Utensil Cuff

A universal cuff that holds a fork, spoon, pen or toothbrush against the palm for a user with limited hand grip. A new adaptive-aid family/cluster.

> An adaptive daily-living aid, **not** certified medical equipment. Fit is user-specific — an occupational therapist can help size it.

## Parts / Modos

| Mode | Part | What it is |
|------|------|------------|
| `cuff` | Palm Cuff | Palm C-band with a utensil socket to hold a fork, pen or toothbrush. |
| `strap_cuff` | Strap Cuff | Cuff whose band takes a hook-and-loop strap through slots to cinch to any hand. |
| `wide_grip` | Wide Grip | A fat fluted grip that slides onto a thin utensil handle to enlarge it. |

## Standards & dimensions

- **Universal cuff (OT aid):** a band around the palm (~40 mm across the hand) with a socket gripping a utensil handle.
- **Utensil handles:** common cutlery / pen / toothbrush handles are ~8–16 mm.
- **Strap:** the slots take ~25 mm hook-and-loop webbing.

## Parameters

- `palm_dia` (30–60 mm) — inner diameter of the palm band around the hand.
- `handle_dia` (6–22 mm) — utensil / pen handle diameter (or what the wide grip fits over).
- `band_wall` (2.5–8 mm) — palm-band / grip wall thickness.
- `band_w` (16–45 mm) — how wide the band and socket pad are across the hand.
- `clearance` (0.1–1.2 mm/side) — palm-band and utensil-socket fit.
- `strap_w` (12–38 mm) — width of the webbing the strap slots accept.

## Printing notes / Notas de impresión

**EN:** Print the band in flexible TPU for comfort and grip; the wide grip in PLA / PETG. Set `palm_dia` and `handle_dia` to the individual. Orient the band flat so the C-mouth and socket print without supports. An occupational therapist should confirm the fit.

**ES:** Imprime la banda en TPU flexible para comodidad y agarre; el mango grueso en PLA / PETG. Ajusta `palm_dia` y `handle_dia` a la persona. Orienta la banda plana para que la boca en C y el socket salgan sin soportes. Un terapeuta ocupacional debe confirmar el ajuste.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Utensil Handle Socket** (`socket`, `standard utensil handle`) — defined by `handle_dia`, `clearance`.
- **Material awareness:** `tolerance_by_material` declared — palm band and socket clearance tune to the print material.
- **Societal benefit:** restores independent eating, writing and self-care for people with reduced hand strength — printed to their hand and utensils for a few pesos of filament.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`; final solid assigned to `result`; dispatch on `target_part`.
- The band mouth, utensil socket and strap slots open to a face; band, pad and grip are joined with deep overlaps, so every output is **watertight, single-body**.
