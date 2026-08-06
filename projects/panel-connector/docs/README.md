# Panel Connector Frame

A panel-mount frame that carries the correct cutout for a chosen connector, so a bare enclosure wall gets a clean, sized opening plus the connector's own fixing holes. Pick the connector and the plate gets the right window and screw pattern; bolt the frame into a rectangular panel aperture, or use it as a drilling template.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `single_cutout` | Single Cutout | CadQuery B-Rep | `main.py` |
| `dual_cutout` | Dual Cutout | CadQuery B-Rep | `main.py` |
| `blank_plate` | Blank Plate | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; `parts[]` ids match the built values so the platform renders each mode distinctly.

## Parameters

`connector` is a `select` (XT60, USB-A, RJ45, GX16 aviation) whose panel opening and fixing pattern the plate reproduces — rectangular windows for XT60/USB/RJ45, a keyed round bore for GX16. Plate thickness, border, corner radius, corner mount bore and the dual-cutout gap are sliders. All labels/tooltips are bilingual (en/es); see `project.json` → `parameters`.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Connector Cutout** (`pocket`, XT60/USB/RJ45/GX16) — the panel opening + fixing holes for the selected connector, driven by `connector` / `plate_t`.
  - **Panel Mount Holes** (`bolt_pattern`, internal) — the four corner holes that bolt the frame into the panel.
- **Material awareness:** tolerance-by-material (cutout fit tuned per filament).
- **Societal benefit:** Gives any project box a professional, sealed connector opening without a machine shop — named cutouts for the connectors makers actually use mean a bolt-in frame or an accurate drilling template.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and a GX16 dual-cutout extreme) and render as distinct geometries.
