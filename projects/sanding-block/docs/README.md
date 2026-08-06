# Sanding Block

A hand sanding block generated with **CadQuery** (B-Rep), sized to a sheet of
abrasive, with paper-clamp slots at each end that pinch a torn sheet so it can't
slip. The sanding face is flat, convex (for hollows) or a soft contour (for
mouldings).

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Flat Block** | `flat_block` | A flat-faced block for flat surfaces, with an ergonomic top and end clamp slots. |
| **Convex Block** | `round_block` | A convex cylindrical face for sanding inside curves and coves. |
| **Contour Block** | `contour_block` | A gentle cove channel down the face for shaped mouldings. |

Each mode's part id equals the `target_part` the code dispatches on, so every
mode renders its own distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Block Size | `block_l` / `block_w` / `block_h` | 120 / 65 / 35 mm | Overall block dimensions. |
| Sanding Face | `face_r` | 60.0 mm | Convex face radius (smaller = tighter curve). |
| Sanding Face | `contour_d` | 6.0 mm | Cove depth of the contour face. |
| Grip & Clamp | `grip_scoop` | on | Scoop the top for a comfortable grip. |
| Grip & Clamp | `clamp_slot` | 2.5 mm | Width of the end slots that pinch the abrasive. |

## Presets

- **Quarter-Sheet Flat** — a flat block sized to a torn quarter sheet.
- **Cove Convex (R60)** — a convex block for hollows.
- **Moulding Contour** — a coved block for shaped mouldings.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Sanding Face** (`profile`, internal) — the working face defined by
    `block_l`, `block_w`, `face_r`, `contour_d`; flat, convex or coved.
  - **Paper Clamp Slots** (`pocket`, internal) — `clamp_slot`, `block_l`; the
    angled end slots that self-lock a torn abrasive sheet.
- **Material awareness:** `recycled_material_toggle` — a shop consumable that
  prints happily in recycled filament.
- **Societal benefit:** a comfortable, sized-to-your-paper block that holds torn
  abrasive without adhesive, replacing a drawer of one-shape store blocks.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
