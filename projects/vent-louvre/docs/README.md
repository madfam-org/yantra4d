# Vent Louvre

A parametric **vent louvre / airflow deflector** generated with **CadQuery**
(B-Rep) — a rectangular frame spanned by a bank of angled blades that steer or
diffuse air.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Louvre Insert** | `louvre_insert` | A flat framed louvre with a front locating lip that drops into a vent opening. |
| **Deflector** | `deflector` | The louvre on a protruding hood/scoop that throws air away from a surface. |
| **Grille** | `grille` | A fine straight-slat grille (many thin blades + cross ribs) for a cover or intake screen. |

The studio dispatches the active part via `target_part`; each mode renders a
distinct body around the shared blade-in-frame construction.

## The blade profile

Blades run the full opening width, are spaced evenly up the opening height, and
are each tilted `blade_angle` from vertical about the X axis. The whole bank is
**unioned into one solid** and then intersected with the opening prism, so tilted
ends never poke past the frame and the result stays watertight. The grille mode
forces a near-straight angle and a denser blade count, and adds a couple of
stiffening cross ribs.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Opening | `open_w` / `open_h` | 80 / 50 mm | Clear opening the blades span. |
| Opening | `frame_w` | 5.0 mm | Border width around the opening. |
| Opening | `depth` | 10.0 mm | Frame and blade depth. |
| Blades | `blade_count` | 6 | Blades across the opening height. |
| Blades | `blade_angle` | 35° | Blade tilt from vertical (Louvre/Deflector). |
| Blades | `blade_thick` | 2.0 mm | Blade / slat thickness. |
| Frame Extras | `rim_lip` | 2.0 mm | Wider front locating lip. |
| Frame Extras | `hood_len` | 22.0 mm | Deflector hood projection (Deflector mode). |

## Presets

- **Dash Vent Insert** — an 80 × 45 louvre at 35°.
- **Footwell Deflector** — a 90 × 55 scoop at 45° with a 26 mm hood.
- **Intake Grille** — a 100 × 60 fine 12-slat grille.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Louvre Blade** (`profile`, internal) — the angled blade bank defined by
    `blade_count`, `blade_angle`, `blade_thick`, `depth`. The same profile drives
    all three modes.
  - **Vent Opening Frame** (`pocket`, internal) — the rectangular frame and
    locating lip, defined by `open_w`, `open_h`, `frame_w`, `rim_lip`.
- **Material awareness:** the locating-lip and frame clearances tune the insert
  fit per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** broken vent louvres and missing deflectors are unfixable
  OEM assemblies you normally replace whole; a parametric frame-and-blade insert
  restores or redirects airflow for the cost of a small print, and doubles as a
  general-purpose grille.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- Every blade is a **solid unioned bar** clipped to the opening (no zero-thickness
  surfaces), so all modes and presets render **watertight** — verified with 0, 6
  and 12 blades.
