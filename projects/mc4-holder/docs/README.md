# Solar MC4 / Connector Holder

Holders and strain reliefs that organize MC4 photovoltaic connectors. The socket bore lands on the real MC4 body / panel-cutout diameter, so a printed holder grips a standard MC4 coupling and dresses PV leads on a panel edge, combiner box or rail.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `panel_mount` | Panel-Mount Collar | CadQuery B-Rep | `main.py` |
| `rail_organizer` | Rail Organizer | CadQuery B-Rep | `main.py` |
| `strain_block` | Strain-Relief Block | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`socket_dia` (default 16 mm, the MC4 body) sizes the bore; socket clearance, wall and depth are sliders, plus socket count and pitch (rail), PV-lead diameter (strain block) and mount-screw diameter. All labels/tooltips are bilingual (en/es).

## Standards encoded

| Feature | Dimension |
| :--- | :--- |
| MC4 coupling body Ø | ~16.0 mm (Staubli MC4 family) |
| MC4 panel cutout Ø | ~17.0 mm |
| PV lead (4–6 mm²) Ø | ~6.5 mm |

Socket bores are single cylinder cuts from solid, filleted blanks; on the rail the sockets keep a guaranteed gap so adjacent bosses never touch tangentially, and the end pads fully contain the mounting screws so no hole runs tangent to an edge.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **MC4 Body Socket** (`socket`, MC4) — the bore sized to the connector body.
  - **Screw-Mount Rail** (`rail`, internal) — the multi-socket rail on a fixed pitch.
- **Material awareness:** tolerance-by-material (socket fit tuned per filament).
- **Societal benefit:** Dresses PV leads neatly and takes the strain off the crimp for off-grid and rooftop solar builders who otherwise zip-tie connectors to the frame, extending connector life and improving inspectability.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and full min/max slider extremes) and render as distinct geometries (`body_count == 1`, no negative-volume bodies).
