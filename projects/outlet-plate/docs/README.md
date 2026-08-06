# Outlet / Switch Plate

Wall cover plates for device boxes whose mounting-screw pattern lands on the real device-box standard. US single-gang boxes put the two 6-32 screws 3.28 in (83.34 mm) apart on the vertical centerline; EU round boxes use 60 mm spacing.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `single_gang` | Single-Gang Plate | CadQuery B-Rep | `main.py` |
| `blank_plate` | Blank Plate | CadQuery B-Rep | `main.py` |
| `eu_round` | EU Round Cover | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`device` is a `select` (duplex outlet, toggle, rocker/Decora, round) that cuts the matching window on the single-gang plate. Plate thickness, jumbo oversize, corner radius, EU window diameter and a countersink toggle are the remaining controls. All labels/tooltips are bilingual (en/es).

## Standards encoded

| Feature | Dimension |
| :--- | :--- |
| US single-gang plate | 2.75 × 4.5 in (69.85 × 114.3 mm) |
| US box screw spacing | 3.28 in (83.34 mm), 6-32 (~3.6 mm) |
| Duplex cutout | Ø34.9 mm lobes on 34.9 mm centers (figure-8) |
| Toggle slot | 9.5 × 21 mm |
| Rocker/Decora window | 26.4 × 66.7 mm |
| EU round box screw spacing | 60 mm |

Every window, screw hole and countersink is a boolean cut from a single blank that is **filleted before** any feature cut, so the mesh stays watertight; countersinks are frusta opening to the front face.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Device Box Screw Pattern** (`bolt_pattern`, US/EU wall box) — the 3.28 in / 60 mm mounting pattern.
  - **Device Window** (`profile`, internal) — the device-specific opening.
- **Material awareness:** none required (rigid flat plate).
- **Societal benefit:** Restores a safe, finished wall opening on the real 3.28 in (US) or 60 mm (EU) screw pattern for pennies; blanks safely close off unused boxes and custom windows fit mixed devices.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and full min/max slider extremes) and render as distinct geometries (`body_count == 1`, no negative-volume bodies).
