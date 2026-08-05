# Volumetric Measuring Scoop

A **measuring scoop** generated with **CadQuery** (B-Rep) where you enter a
**target volume in millilitres** and the geometry *solves the bowl* to hold it.
No trial and error — the bowl dimensions come from a closed-form volume formula,
so the carved interior matches the volume you asked for.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Scoop** | `scoop` | The bowl + handle. |
| **Flat-Bottom Scoop** | `scoop_flat_bottom` | Adds a flat pad under the bowl so it stands upright on a counter (does not change the interior volume). |

## How the volume is solved

Given a target `V` (mL → mm³), the interior is built directly from these
dimensions, so the cavity volume equals the target by construction:

| `shape` | Interior formula | Solved dimensions |
| :--- | :--- | :--- |
| `hemispherical` | V = ⅔·π·r³ | r = (3V / 2π)^⅓ |
| `cylindrical` | V = π·r²·h, h = r | r = (V / π)^⅓, h = r |
| `conical` | V = ⅓·π·r²·h, h = 1.5·r | r = (2V / π)^⅓, h = 1.5·r |

**Verified interior volume vs target** (rendered cavity, measured in trimesh):

| Shape | Deviation from target |
| :--- | :--- |
| hemispherical | ≈ −0.17 % across 1.25–500 mL |
| cylindrical | ≈ −0.04 % across 1.25–500 mL |
| conical | +0.4 % (large) to +2.6 % (at 1.25 mL) |

All shapes and sizes land well inside the ~5 % target. The small residuals come
from mesh faceting and a sub-millimetre flat at each bowl's pole (added so the
revolve does not leave a cracked, non-watertight vertex on the axis).

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Target Volume | `target_ml` | 15 mL | The interior is solved to this (1 mL = 1 cm³). |
| Bowl | `shape` | `hemispherical` | `hemispherical`, `cylindrical`, or `conical`. |
| Bowl | `wall` | 2.0 mm | Wall thickness (does not affect interior volume). |
| Handle | `handle_length` | 60 mm | Length past the rim (0 = no handle). |
| Handle | `handle_width` / `handle_thick` | 14 / 5 mm | Handle cross-section. |
| Handle | `hang_hole` | on | Hole at the handle end to hang the scoop. |

## Presets

- **Coffee Scoop (15 mL / 1 tbsp)** — hemispherical, the everyday tablespoon.
- **Protein / Detergent 30 mL** — cylindrical, flat-bottom so it stands in the tub.
- **Quarter Cup (60 mL)** — conical, longer handle.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Volumetric Bowl** (`surface`, internal) — the solved interior, defined by
    `target_ml`, `shape`, and `wall`. The interface *is* the volume: any scoop
    generated at the same `target_ml` holds the same amount regardless of shape,
    so a recipe expressed in mL maps to a printable object.
- **Material awareness:** `tolerance_by_material` is declared — wall thickness is
  exposed independently of the interior so a stiffer or food-safe material can be
  given more wall without changing the measured volume.
- **Societal benefit:** turns an abstract measurement into a printed object — any
  recipe, dose, or portion in millilitres becomes a scoop that holds exactly that
  amount, replacing a drawer of single-size measuring cups with one solved-to-order
  tool.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- Bowls are revolved with a tiny off-axis flat at the pole so every shape, both
  modes, and the 1–500 mL range render **watertight**; the cavity is cut with a
  collar that opens above the rim, and the flat-bottom pad only overlaps the bowl
  exterior so the measured volume is untouched.
