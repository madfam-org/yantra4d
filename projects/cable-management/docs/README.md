# Cable Comb / Clip / Raceway

Desk and wall **cable management** generated with **CadQuery** (B-Rep). Three
parts share one internal cable-channel profile, so a cable routed through a comb,
snapped into a clip, and run in a raceway is dimensioned consistently.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Cable Clip** | `clip` | A C-profile that snaps around a cable of `cable_dia`, with a selectable mount. |
| **Cable Comb** | `comb` | A bar with `slot_count` open-top slots that separate a ribbon of cables into lanes. |
| **Raceway** | `raceway` | A U-channel duct of `channel_w` × `channel_h` with an optional snap-on lid. |

The studio dispatches the active part via `target_part` (`clip` / `comb` /
`raceway`).

## Clip mounts (`mount_type`)

| Value | Mount |
| :--- | :--- |
| `screw` | A flanged ear with a through hole for a wall / desk screw. |
| `adhesive` | A flat pad to receive foam adhesive tape on its underside. |
| `tslot` | A t-slot-style tab that slides into an extrusion or rail channel. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cable & Wall | `cable_dia` | 6.0 mm | Nominal cable diameter the profile is sized for. |
| Cable & Wall | `wall` | 2.4 mm | Structural wall thickness shared by all parts. |
| Clip | `mount_type` | `screw` | `screw`, `adhesive`, or `tslot`. |
| Clip | `clip_gap` | 0.75 | Mouth width as a fraction of `cable_dia` (smaller grips harder). |
| Clip | `clip_len` | 10.0 mm | Clip length along the cable. |
| Comb | `slot_count` | 5 | Number of cable lanes. |
| Comb | `comb_h` / `comb_t` | 14 / 6 mm | Comb bar height and thickness. |
| Raceway | `channel_w` / `channel_h` | 16 / 12 mm | Internal channel cross-section. |
| Raceway | `raceway_len` | 80.0 mm | Raceway segment length. |
| Raceway | `raceway_lid` | on | Also generate a snap-on lid (printed alongside). |

## Presets

- **USB / Charger Clip** — a small 4 mm adhesive clip.
- **Desk Comb (6 lanes)** — a 6-slot comb for a 6 mm cable bundle.
- **Wall Raceway 16×12** — a 120 mm lidded raceway.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Cable Channel** (`profile`, internal) — the shared internal channel
    cross-section, defined by `cable_dia`, `wall`, `channel_w`, and `channel_h`.
    The comb, clip, and raceway all reference this profile so they route the same
    bundle.
  - **Clip Snap Mouth** (`snap`, internal) — the C-clip opening, defined by
    `cable_dia`, `clip_gap`, and `wall`.
- **Material awareness:** the mouth opening and channel clearances are expressed
  relative to the cable diameter so the snap fit tunes per material / printer;
  `tolerance_by_material` is declared.
- **Societal benefit:** tangled and pinched cables are a universal, avoidable
  failure. A shared cable-channel profile lets a clip, comb, and raceway route
  the same cable consistently, printed to the exact bundle instead of buying
  fixed-size plastic that rarely fits.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- In Raceway mode with the lid enabled, the channel and lid are exported as two
  separate closed bodies laid side by side for printing; each is watertight.
