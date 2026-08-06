# Conduit Clip / Spacer

Snap clips and standoffs that hold electrical conduit to a surface. The cradle diameter lands on the real outside diameter of EMT or metric conduit, and the snap mouth opens just under the OD so the tube clicks in and stays put.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `snap_clip` | Snap Clip | CadQuery B-Rep | `main.py` |
| `standoff_clip` | Standoff Clip | CadQuery B-Rep | `main.py` |
| `gang_clip` | Gang Rail | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`conduit_size` is a `select` whose real OD sizes the cradle; cradle clearance, wall, width, snap-mouth fraction and screw diameter are sliders, plus standoff height (standoff mode) and gang cradle count (gang mode). All labels/tooltips are bilingual (en/es).

## Standards encoded

| Size | Outside Ø (mm) |
| :--- | :--- |
| EMT 1/2" | 17.9 |
| EMT 3/4" | 23.4 |
| EMT 1" | 29.5 |
| Metric 16 / 20 / 25 | 16.0 / 20.0 / 25.0 |

The C mouth is a single rectangular slot cut from a solid ring (never an arc-fan, which crashes OCCT `clean()`); stacked bodies overlap so unions are volumetric, and the standoff post is solid with the screw bore open to both faces (no trapped void).

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Conduit OD Snap** (`snap`, EMT 1/2-1in / 16-25mm) — the cradle + mouth sized to the tube OD.
  - **Screw Mount Pattern** (`bolt_pattern`, internal) — the mounting screw holes.
- **Material awareness:** tolerance-by-material (snap fit tuned per filament).
- **Societal benefit:** A strip of printed clips sized to the exact tube OD lets anyone dress a conduit run cleanly; standoff and gang variants keep runs off hot surfaces and organize multi-circuit routes.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and full min/max slider extremes) and render as distinct geometries (`body_count == 1`, no negative-volume bodies).
