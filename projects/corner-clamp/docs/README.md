# Corner Assembly Clamp

A 90° assembly clamp generated with **CadQuery** (B-Rep) that holds two
workpieces square while glue or fasteners set. An L-shaped body registers both
faces at a true right angle; a clamp-screw bore lets a bolt or clamp pull the
joint tight. Sized by the material thickness and width it must hold.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Right-Angle Jaw** | `corner_clamp` | Rigid L-jaw with two registration channels and a clamp-screw bore through each leg. |
| **Strap-Clamp Corner** | `band_corner` | Adjustable outside corner block with a strap slot so one band pulls four frame corners in evenly. |
| **Miter Corner** | `picture_frame` | 45° miter cradle with a diagonal relief and a screw bore across the miter for picture frames. |

Each mode's part id equals the `target_part` the code dispatches on, so every
mode renders its own distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Material Held | `mat_thick` | 18.0 mm | Thickness of the boards being clamped (registration pocket width). |
| Material Held | `mat_width` | 60.0 mm | Board width / leg length the jaw registers against. |
| Clamp Body | `wall` | 6.0 mm | Wall thickness of the clamp body. |
| Clamp Body | `height` | 40.0 mm | Height of the clamp along the joint. |
| Clamp Screw | `screw_bore` | 6.5 mm | Through-bore for the bolt/clamp that pulls the joint tight. |
| Strap | `band_w` / `band_t` | 25.0 / 2.0 mm | Strap width and slot depth (strap-clamp corner). |

## Presets

- **Cabinet Carcass (18mm ply)** — a right-angle jaw for 18 mm plywood carcasses.
- **Drawer Box Strap Set** — a strap-clamp corner block for a four-corner glue-up.
- **Photo Frame Miter (20mm)** — a 45° miter cradle for 20 mm frame stock.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **90° Clamp Jaw** (`profile`, internal) — the right-angle registration
    profile, defined by `mat_thick`, `mat_width`, `wall`, `height`. Any board
    within the pocket seats against a true 90° inside corner.
  - **Clamp-Screw Bore** (`socket`, internal) — `screw_bore`; accepts a bolt,
    threaded rod or clamp screw to pull the joint closed.
- **Material awareness:** `tolerance_by_material` — the registration pocket can
  be tuned per material so boards seat snug without splitting.
- **Societal benefit:** square, repeatable glue-ups for cabinets, boxes and
  frames without buying a set of steel corner clamps.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
