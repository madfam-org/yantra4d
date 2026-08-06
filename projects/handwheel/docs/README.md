# Machine Handwheel / Crank

A replacement handwheel, crank, or adjust knob generated with **CadQuery**
(B-Rep) for a machine shaft. The shaft **bore is modelled per type** — round,
D-flat, keyway, or hex — with a radial setscrew, so the part actually drives the
real shaft instead of just looking the part.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Handwheel** | `handwheel` | A spoked (or solid-disc) wheel with hub + rim and an optional revolving handle. |
| **Crank** | `crank` | A single offset crank arm from the hub to a revolving handle (no rim). |
| **Adjust Knob** | `knob` | A small fluted knob for fine adjustment. |

Each mode's part id equals the `target_part` the code dispatches on, so every
mode renders its own distinct geometry.

## Bore types

| `bore_type` | Geometry |
| :--- | :--- |
| `round` | Plain circular bore. |
| `dflat` | Circle with one chord shaved flat (D-shaft). |
| `keyway` | Circle plus a rectangular keyseat. |
| `hex` | Across-flats hexagonal socket (`bore_dia` = AF). |

`bore_fit` adds per-side clearance because printed holes come out undersize;
`tolerance_by_material` is declared so the fit can be tuned per material/printer.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Shaft Bore | `bore_dia` | 10.0 mm | Shaft diameter (AF for hex). |
| Shaft Bore | `bore_type` | round | round / dflat / keyway / hex. |
| Shaft Bore | `bore_fit` | 0.2 mm | Per-side bore clearance. |
| Shaft Bore | `setscrew` / `setscrew_d` | on / 4.0 mm | Radial locking screw. |
| Wheel & Hub | `hub_dia` / `hub_len` | 26 / 22 mm | Boss around the bore. |
| Wheel & Hub | `wheel_dia` / `rim_t` / `rim_w` | 90 / 12 / 14 mm | Rim outer Ø / radial thickness / axial width. |
| Wheel & Hub | `spokes` / `spoke_w` | 3 / 10 mm | Spoke count (0 = solid disc) + width. |
| Handle | `handle` / `handle_off` / `handle_dia` / `handle_len` | on / 34 / 12 / 28 mm | Revolving handle knob. |
| Crank Arm | `crank_len` | 70 mm | Centre-to-handle radius. |

## Presets

- **Lathe Cross-Feed Wheel** — 100 mm 3-spoke wheel, 12 mm keyway bore, handle.
- **Valve Hand Crank** — 80 mm crank arm, 10 mm D-flat bore.
- **Fine-Adjust Knob (hex)** — fluted knob on a 6 mm hex shaft.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Shaft Bore** (`socket`, internal) — the shaft interface, defined by
    `bore_dia`, `bore_type`, `bore_fit`, `setscrew`, `setscrew_d`. Any part
    built to the same bore fits the same shaft.
  - **Handle Mount** (`socket`, internal) — `handle_off`, `handle_dia`,
    `handle_len`.
- **Material awareness:** `shrinkage_compensation` + `tolerance_by_material` are
  declared; the bore clearance is exposed for per-material tuning.
- **Societal benefit:** keeps old machines running — a broken cast handwheel,
  crank, or knob is a common reason a lathe, mill, or valve gets scrapped. Model
  the exact bore and print the replacement.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The handle knob is a single revolved solid so every mode exports **watertight**;
  all shipped presets and defaults render watertight.
