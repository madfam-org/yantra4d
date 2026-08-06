# Bench Dog / Hold-Down

Bench workholding generated with **CadQuery** (B-Rep) that drops into a workbench
dog hole. A round shank sized to the hole (19 mm, 20 mm or 3/4 in) registers the
tool; a head above the bench pushes, pins or clamps the work.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Round Stop Dog** | `round_dog` | A round shank with a low stop head and a collar that can't fall through. Pairs with a vise dog to trap stock. |
| **Cam Hold-Down** | `holdfast` | A cam / hook hold-down whose offset arm levers a pad down onto the work when cammed in the hole. |
| **Planing Stop** | `planing_stop` | A wide-headed stop with a buttressed face that gives a broad end-stop for hand planing. |

Each mode's part id equals the `target_part` the code dispatches on, so every
mode renders its own distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Dog Hole | `hole` | 19mm | Dog-hole standard the shank fits (**19mm / 20mm / 3/4in**). |
| Dog Hole | `fit` | 0.3 mm | Per-side shank clearance so the print slides in the hole. |
| Dog Hole | `shank_len` | 40.0 mm | Depth of shank below the bench top. |
| Head | `head_h` / `head_w` | 16 / 30 mm | Head height and push-face width. |
| Reach & Face | `reach` | 55.0 mm | Hold-down arm reach over the work. |
| Reach & Face | `face_h` | 24.0 mm | Planing-stop face height. |

## Presets

- **20mm Stop Dog** — a metric round stop dog.
- **3/4in Cam Hold-Down** — a cam hold-down for imperial dog holes.
- **19mm Planing Stop** — a broad hand-planing end stop.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Dog Hole** (`socket`, standard *19mm/20mm dog hole*) — the round shank
    defined by `hole`, `fit`, `shank_len`. The `hole` select maps to 19.0, 20.0
    or 19.05 mm so the shank matches real bench hardware.
  - **Work Contact Face** (`profile`, internal) — the head / pad / stop face
    defined by `head_w`, `head_h`, `reach`, `face_h`.
- **Material awareness:** `shrinkage_compensation` + `tolerance_by_material` —
  the shank clearance is exposed so the fit is tuned per material/printer.
- **Societal benefit:** turns any bench with dog holes into a full workholding
  station, printed to fit the exact hole size.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
