# Toothbrush / Razor Holder

A bathroom organizer generated with **CadQuery** (B-Rep), sized to the **real
handle diameters** of the things it holds: manual toothbrushes (~13–16 mm),
electric toothbrush bodies (~25–32 mm), and disposable razor handles
(~10–14 mm). Three distinct socket-interface modes.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Counter Caddy** | `counter_caddy` | A rounded puck with a row of upright handle bores and a drain slot through the floor, so water runs out instead of pooling. |
| **Wall Rail** | `wall_rail` | A wall strip whose keyhole (obround) slots grip a handle from the side; a brush drops in from the top. Two screw mounts anchor it. |
| **Razor Cradle** | `razor_cradle` | A single wall hook: a back plate + a C-collar arm that cradles one handle by the neck, pressed in from the front. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Handles | `hole_d` | 16 mm | Handle bore diameter. Manual brush ~16, electric ~28, razor ~12. |
| Handles | `hole_count` | 4 | How many handles the caddy / rail holds (1–8). |
| Body | `wall` | 4 mm | Material between bores and around the outside. |
| Body | `height` | 45 mm | Body height (caddy) or plate height (rail / cradle). |
| Body | `depth` | 30 mm | Front-to-back depth / cradle arm reach. |
| Wall Mount | `screw_d` | 4.2 mm | Wall-mount screw clearance (M4 ~4.2 mm). |

## Presets

- **Family Caddy (4 brushes)** — the everyday counter caddy.
- **Electric Brush Caddy** — two wide 28 mm bores, taller body.
- **Wall Strip (3-up)** — three keyhole slots on a wall rail.
- **Single Razor Hook** — one 12 mm cradle.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Handle Socket** (`socket`, *internal*) — the vertical / keyhole bore sized
    by `hole_d` and `hole_count`; the functional interface that grips a handle.
  - **Wall Screw Mount** (`bolt_pattern`, *ISO 7045 M4*) — the wall-mount screw
    clearance (`screw_d`), so the rail and cradle anchor with a standard screw.
- **Material awareness:** `tolerance_by_material` is declared — the printed bore
  fit can be tuned via `hole_d` and `wall` for the filament / printer in use.
- **Societal benefit:** a holder that fits your exact brush or razor is normally
  a proprietary purchase; sizing the socket to real handle diameters lets anyone
  print one that fits what they already own.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- **Watertight by construction:** the blank is filleted **before** any bore is
  cut; every bore opens to a face (the caddy floor drains through an obround
  slot rather than trapping a void); the C-collar is bored through both faces.
  All three modes and the MIN/MAX parameter extremes render watertight with a
  single body.
