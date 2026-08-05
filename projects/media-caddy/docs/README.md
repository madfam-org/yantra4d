# USB / SD / Battery Caddy

A small-media organizer generated with **CadQuery** (B-Rep) with an array of
correctly-sized pockets for one class of media or battery. Pick the form factor
and how many — every pocket is sized to the real part plus a small clearance.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Tray** | `tray` | A shallow single wide row of pockets — a flat desk tray. |
| **Block** | `block` | A compact near-square standing block with full-depth bores; items stand upright. |
| **Grid** | `grid` | An explicit rows × columns matrix (rows set by `rows`, columns fill to the slot count). |

The studio dispatches the active part via `target_part`
(`tray` / `block` / `grid`); the layout (row count and pocket depth) is baked
per mode, so the three parts always render distinct geometry.

## Media form factors

| `media` | Shape | Nominal size | Default depth |
| :--- | :--- | :--- | :--- |
| `usb_a` | rectangular | 12.0 × 4.5 mm | 16 mm |
| `sd` | rectangular | 24.0 × 2.1 mm | 18 mm |
| `microsd` | rectangular | 11.0 × 1.0 mm | 8 mm |
| `aa` | round | Ø14.5 mm | 40 mm |
| `aaa` | round | Ø10.5 mm | 34 mm |
| `18650` | round | Ø18.5 mm | 55 mm |

Each pocket adds `clear` (default 0.6 mm) per side. Tray mode auto-caps depth to
14 mm for a shallow profile; `pocket_depth` forces an explicit depth in any mode.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Media | `media` | `usb_a` | Form factor (drives pocket size / shape). |
| Layout | `slots` | 8 | Total pocket count. |
| Layout | `rows` | 3 | Rows in Grid mode. |
| Layout | `pocket_depth` | 0 | 0 = media default; else forced depth. |
| Body | `base` | 3.0 mm | Solid floor under the blind pockets. |
| Body | `wall` | 3.0 mm | Material between / around pockets. |
| Body | `clear` | 0.6 mm | Per-side pocket clearance. |

## Presets

- **USB Stick Tray (8)** — an 8-pocket USB-A desk tray.
- **AA Battery Block (12)** — a 12-cell upright AA block.
- **18650 Grid (4×4)** — a 16-cell 18650 matrix.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Media Slot** (`pocket`, USB-A / SD / 18650 form factors) — a single pocket
    sized to the selected `media` (rectangular for cards/drives, round for
    cells), with `clear` per side and depth from `pocket_depth` or the media
    default.
  - **Slot Matrix** (`grid`, internal) — the `slots` / `rows` / `wall` array
    layout.
- **Material awareness:** the `clear` per-side gap tunes the fit to the
  material/printer (tighter for a snug grip, looser for easy insertion);
  `tolerance_by_material` is declared.
- **Societal benefit:** loose USB sticks, SD cards, and cells get lost, shorted,
  or damaged; a caddy sized to the exact media keeps them sorted, upright, and
  contact-safe, extending the life of small storage and batteries.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- Pockets are blind bores cut from the top of a solid block (leaving `base`
  underneath), so every media type, mode, and preset renders **watertight** —
  verified up to a 100-pocket 18650 grid.
