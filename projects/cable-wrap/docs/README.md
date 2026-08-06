# Cable Wrap & XLR Label

Tames stage and studio cabling, generated with **CadQuery** (B-Rep). A figure-8
winder, an XLR label ring with **engraved text**, and a wall hook keeper — sized
by the cable diameter so the channel grips your specific cable.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Figure-8 Winder** | `wrap` | Dumbbell winder to coil a cable kink-free. |
| **XLR Label Ring** | `xlr_label` | Snap ring engraved with a channel label. |
| **Hook Keeper** | `hook_keeper` | Wall hook with a rounded cable saddle. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cable | `cable_dia` | 7 mm | Cable OD — sizes the channel/saddle. |
| Cable | `wall` | 3.0 mm | Body wall thickness. |
| Winder | `wrap_len` | 90 mm | Figure-8 winder length. |
| Winder | `spool_dia` | 34 mm | End spool flange diameter. |
| XLR Label | `label_text` | MIC 1 | Engraved text (≤ 10 chars). |
| XLR Label | `label_dia` | 19 mm | XLR barrel diameter to clip onto. |
| Cable | `screw_dia` | 4.5 mm | Hook keeper screw clearance. |

## Presets

- **Instrument Cable Winder** — 7 mm cable, 90 mm winder.
- **Mic Channel Label** — "MIC 1" on a 19 mm ring.
- **Rack / Wall Hook** — 8 mm cable keeper.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Cable Wrap** (`profile`, internal) — the cable channel/spool profile,
    defined by `cable_dia`, `spool_dia`, `wall`.
  - **XLR Barrel Clip** (`snap`, internal) — the snap ring, `label_dia`, `wall`.
- **Material awareness:** `tolerance_by_material` declared — channel and snap fits
  adapt to the printed material.
- **Societal benefit:** cable chaos wastes setup time and destroys cables; on-demand
  winders and engraved labels replace single-use velcro and tape.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The label is engraved (debossed) into the ring pad via `.text(...)` cut — the
  recessed glyphs are snag-free and keep the mesh watertight.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  the final solid is assigned to `result`.
- All shipped presets render **watertight**.
