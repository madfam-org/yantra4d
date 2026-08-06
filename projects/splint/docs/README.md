# Finger / Wrist Splint

An adjustable immobilization splint that wraps a limb, generated with **CadQuery**
(B-Rep) and sized by the diameter it wraps. The body is an open-back contoured
shell so it slips on and is secured with straps; a ventilation pattern keeps it
breathable.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> This is a printable *aid*, not a certified orthosis. For an injury, follow a
> clinician's guidance on immobilization; use this as a low-cost or interim fit
> where clinical bracing is unavailable.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Finger Splint** | `finger_splint` | A near-full trough for a finger, open on top. |
| **Wrist Brace** | `wrist_brace` | A longer, shallower curved brace, always ventilated, with strap slots. |
| **Mallet Splint** | `mallet_splint` | A short fingertip splint with a closed domed tip to hold a mallet finger extended. |

Each mode dispatches on `target_part`; the manifest `parts[]` ids match the
dispatched values (`finger_splint` / `wrist_brace` / `mallet_splint`). The
`splint_type` selector mirrors the mode for the standalone/preview path.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Splint Type | `splint_type` | finger | Mirrors the active mode. |
| Limb Fit | `limb_dia` | 18 mm | Finger/wrist diameter the splint wraps. |
| Limb Fit | `clearance` | 1.0 mm | Gap between shell and skin. |
| Shell | `length` | 70 mm | Length along the limb. |
| Shell | `wrap` | 240 deg | How far the shell wraps around. |
| Shell | `wall` | 3.0 mm | Shell wall thickness (stiffness). |
| Ventilation & Straps | `vents` | on | Breathable hole pattern. |
| Ventilation & Straps | `straps` | 2 | Strap slot pairs along the edges. |

## Presets

- **Finger Splint (18 mm)** — a strapped finger trough.
- **Wrist Brace (60 mm)** — a longer ventilated wrist support.
- **Mallet Finger (16 mm)** — a closed-tip fingertip splint.

## Hyperobject Profile

- **Domain:** medical
- **CDG interface:**
  - **Limb Contour Shell** (`surface`, internal) — the open-back contoured shell,
    defined by `limb_dia`, `clearance`, `wrap`, `wall`. Sizing to the limb
    diameter shapes the inner surface to the patient.
- **Material awareness:** `clearance` is exposed so the fit can be tuned per
  material/printer (rigid PLA/PETG vs a softer print); `tolerance_by_material` is
  declared.
- **Societal benefit:** a custom-fit splint printed to the patient's own limb
  diameter immobilizes an injury more comfortably than a generic one, at a
  fraction of the cost, where clinical orthoses are unavailable.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`.
- The shell is a C-channel (an annulus minus an open wedge) — one manifold solid
  like a gutter; the mallet tip is a lofted dome, and vents/strap slots are clean
  through-cuts. All shipped presets render **watertight**.
