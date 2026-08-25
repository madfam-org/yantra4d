# PV Cable Clip

Cable management for photovoltaic strings — clips sized to the real solar lead and the real module frame lip.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

PV leads left hanging under an array chafe against the module frame, pool water at the connector, and enclose a large loop area that raises induced-surge voltage in a lightning event. The usual field fix is a zip tie, which perishes in UV within a couple of seasons and drops the cable back onto the roof. These three parts dress the run against the hardware that is actually there, and can be reprinted on site from UV-stable filament.

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `frame_clip` | Frame-Lip Clip | CadQuery B-Rep | `main.py` |
| `rail_clip` | Rail Saddle | CadQuery B-Rep | `main.py` |
| `twin_bundle` | Twin Bundler | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`cable_dia` sets the lead the channel grips and `cable_count` how many it carries. `mouth` sets how far the snap channel closes over the cable — lower grips harder. `clearance`, `wall` and `depth` size the clip body. `lip_t` and `jaw_depth` fit the C-jaw to a module frame lip; `screw_dia` sizes the rail saddle's fixings. All labels and tooltips are bilingual (en/es).

## Adjacent to mc4-holder, not overlapping it

The lead channel here uses the **same** PV cable series the published `mc4-holder` strain block already expects (`cable_dia`, ~5-7 mm nominal for 4-6 mm2 H1Z2Z2-K). A lead dressed by these clips arrives at an `mc4-holder` strain block on the same diameter, so the two cartridges compose along a run instead of each inventing a cable size. The frame jaw likewise reuses the module-edge geometry `solar-mount` established rather than publishing a second panel-edge standard.

This is deliberately **not** the deferred `mc4-junction`: nothing here touches the connector interface or the current path. These are passive supports for the cable between connectors.

## Standards encoded

| Feature | Dimension |
| :--- | :--- |
| PV lead Ø, 4 mm2 (H1Z2Z2-K) | ~5.5-6.0 mm |
| PV lead Ø, 6 mm2 (H1Z2Z2-K) | ~6.5-7.2 mm |
| Channel bore radius | `cable_dia`/2 + `clearance` |
| Channel mouth width | `mouth` × bore Ø |
| Module frame lip thickness | 1.5-3.0 mm typical anodised extrusion |
| Jaw throat gap | `lip_t` + 2 × `clearance` |

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **PV Lead Channel** (`socket`, H1Z2Z2-K 4-6 mm² solar lead OD series) — compatible with `mc4-holder`, `conduit-clip`, `cable-gland`.
  - **Module Frame Lip Jaw** (`profile`, anodised PV module frame lip) — compatible with `solar-mount`.
  - **Saddle Screw Mount** (`bolt_pattern`, internal) — the rail saddle's two-screw pattern.
- **Material awareness:** tolerance-by-material (snap fit tuned per filament).
- **Societal benefit:** extends array service life and inspectability by supporting cable properly, and shrinks string loop area against induced surge.
- **License:** CERN-OHL-W-2.0

## Printing and material notes

Print with the cable axis along the bed (channels opening up), so the snap mouth flexes across layer lines rather than splitting along them. These parts live outdoors under an array: **ASA or PETG**, not PLA. PLA creeps at rooftop temperatures and embrittles in UV within a season — exactly the failure mode of the zip tie this replaces. Pigmented filament, ideally black, resists UV markedly better than natural.

The snap mouth is a friction fit, not a strain relief: it supports cable weight and stops chafe. It does not take pull-out load off a connector crimp — that is what the `mc4-holder` strain block is for.

This is passive cable support. It carries no current, forms no part of the earthing path, and makes no claim about compliance with any electrical code; array wiring remains the installer's responsibility.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every slider that applies to the mode — 43/43 cases, each `is_watertight == True` with `body_count == 1`.

Derived dimensions are clamped in `main.py` rather than trusted from the UI. The channel pitch is forced to `2 × bore_r + max(1.2, wall × 0.6)` so adjacent channels always leave a real web between them instead of going tangent and severing the bank; the frame-clip blank width is `max(jaw_w, bank_w)` so a wide channel bank never overhangs its own jaw; and the rail saddle's screw pads are set at `screw_dia/2 + 3` from the bank so a large screw never breaks out through the plate edge. The twin bundler opens its two channels to **opposite** faces, which is what keeps the central web intact at maximum `mouth`. Those clamps are what hold the extremes watertight.
