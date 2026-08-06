# Go/No-Go Gauge

An attribute inspection gauge generated with **CadQuery** (B-Rep) that checks a
dimension against its limits. By convention the **GO** feature is made to the
**lower limit** and must pass; the **NO-GO** feature is made to the **upper
limit** and must not. A part is in tolerance when GO goes and NO-GO does not.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Plug Gauge** | `plug_gauge` | Double-ended plug for a **hole** — GO pin (lower limit) + NO-GO pin (upper limit) on a shared handle. |
| **Slot Gauge** | `slot_gauge` | Stepped blade for a **slot/groove width** — thin GO step + thick NO-GO step. |
| **Snap Gauge** | `snap_gauge` | C-frame snap gauge for a **shaft OD** — GO throat (upper limit) + NO-GO throat (lower limit). |

Each mode's part id equals the `target_part` the code dispatches on, so every
mode renders its own distinct geometry.

## Limit convention

- **GO** dimension `= nominal + tol_minus` (the lower limit).
- **NO-GO** dimension `= nominal + tol_plus` (the upper limit).

`tol_minus` may be negative (e.g. a shaft g6 band sits entirely below nominal).
Inverted inputs are auto-corrected so GO is always the smaller feature.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Nominal & Tolerance | `nominal` | 10.0 mm | The inspected target size. |
| Nominal & Tolerance | `tol_plus` | 0.05 mm | Upper deviation → NO-GO limit. |
| Nominal & Tolerance | `tol_minus` | 0.0 mm | Lower deviation (may be negative) → GO limit. |
| Gauging Feature | `pin_len` | 22.0 mm | GO pin/step length (NO-GO is shorter by design). |
| Gauging Feature | `blade_h` | 20.0 mm | Slot-gauge blade height. |
| Handle & Frame | `frame` | 8.0 mm | Snap-gauge C-frame thickness. |
| Handle & Frame | `handle_dia` / `handle_len` | 16.0 / 45.0 mm | Handle grip. |
| Handle & Frame | `knurl_flat` | on | Two grip flats so the handle can't roll. |

## Presets

- **10 H7 Bore Plug** — a plug gauge for a 10 mm H7 hole.
- **6 mm Keyway Slot** — a slot gauge for a 6 mm keyway width.
- **20 g6 Shaft Snap** — a snap gauge for a 20 mm g6 shaft (both limits below nominal).

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Tolerance Gauge** (`profile`, internal) — the GO/NO-GO feature profile,
    defined by `nominal`, `tol_plus`, `tol_minus`.
  - **Gauge Handle** (`socket`, internal) — the shared grip, `handle_dia`,
    `handle_len`.
- **Material awareness:** `shrinkage_compensation` + `tolerance_by_material` are
  declared. A **printed** gauge should be verified against gauge blocks before
  use — feature shrinkage varies by material/printer and matters at these
  tolerances.
- **Societal benefit:** puts attribute inspection in every workshop — the fit
  decision is encoded as geometry, checkable at the bench with no calipers.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
