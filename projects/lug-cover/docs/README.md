# Battery Terminal / Lug Cover

Insulating covers and boots for battery terminals, threaded studs and bolted lug joints — the short-circuit and accidental-contact protection that keeps a dropped spanner off a live post. The pocket lands on standard post / stud / lug sizes.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `post_cover` | Post Cover | CadQuery B-Rep | `main.py` |
| `stud_boot` | Stud Boot | CadQuery B-Rep | `main.py` |
| `bar_boot` | Bus-Link Cover | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`terminal` (positive/negative SAE post) and `stud` (M8/M10) are `select`s that size the pocket; pocket clearance, cover wall, cover height, lug reach and cable-notch width are sliders. All labels/tooltips are bilingual (en/es).

## Standards encoded

| Feature | Dimension |
| :--- | :--- |
| SAE positive post top Ø | 17.5 mm (post height ~19 mm) |
| SAE negative post top Ø | 15.9 mm |
| Ring-lug stud M8 / M10 | 8 / 10 mm (lug body Ø ~20 / 24 mm) |

Every cover is a solid, filleted blank with a pocket cut that **opens to the bottom face** (never a sealed cavity). The post cover's wall stays full-radius through the pocket zone so the roof cap can never be severed; its lug skirt passes through the body center for a deeply volumetric union.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Terminal Post Pocket** (`pocket`, internal) — the cavity sized to the post/stud/lug.
  - **Cable Exit Notch** (`profile`, internal) — the notch that seats the boot with the lug installed.
- **Material awareness:** tolerance-by-material (pocket fit tuned per filament).
- **Societal benefit:** Restores the touch-safe insulation routinely missing on DIY solar, EV-conversion and off-grid battery banks, cutting short-circuit and arc-flash risk on uncovered terminals and bus lugs for a few grams of filament.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and full min/max slider extremes) and render as distinct geometries (`body_count == 1`, no negative-volume bodies).
