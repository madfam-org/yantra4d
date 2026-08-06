# Desk Headphone Stand

A free-standing desk stand that holds a headset by its headband on a broad,
rounded cradle, generated with **CadQuery** (B-Rep). The desktop, post-on-a-base
companion to the wall/under-desk Headphone Hook — here the headset hangs from a
saddle atop a weighted pillar.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Desk Stand** | `desk_stand` | Single saddle on a post + weighted base. |
| **Dual Stand** | `dual_stand` | Taller post with two saddles (front/back). |
| **Clamp Stand** | `clamp_stand` | Post on a desk-edge C-clamp (no free base). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Headband Cradle | `cradle_w` | 30 mm | Width of the headband rest saddle. |
| Post & Base | `post_h` | 260 mm | Stand height. |
| Post & Base | `post_dia` | 26 mm | Support pillar diameter. |
| Post & Base | `base_dia` | 120 mm | Weighted disc base diameter. |
| Post & Base | `base_h` | 14 mm | Base thickness (stability). |
| Post & Base | `wall` | 4.0 mm | Shell wall thickness. |
| Post & Base | `desk_t` | 28 mm | Desk edge thickness (clamp mode). |

## Presets

- **Gaming Headset Stand** — 34 mm cradle, 260 mm post.
- **Studio Pair** — dual-saddle, 140 mm base.
- **Desk-Edge Clamp** — clamp version for a 28 mm desk.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Headband Cradle** (`surface`, internal) — the broad half-round saddle that
    spreads the band load, defined by `cradle_w`, `wall`.
  - **Post & Base Stack** (`profile`, internal) — the pillar/base geometry,
    `post_h`, `post_dia`, `base_dia`, `base_h`.
- **Material awareness:** `tolerance_by_material` declared — print the saddle in a
  softer material to protect the headband.
- **Societal benefit:** a broad saddle sized to the exact headset prevents the
  band-denting that ruins headphones on generic hooks.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The post and base are hollowed shells to save material while staying closed
  solids; the saddle overlaps the post for a watertight union.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  the final solid is assigned to `result`.
- All shipped presets render **watertight**.
