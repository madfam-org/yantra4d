# Bag Reseal & Pour Clip

A slide-on **C-channel** clip generated with **CadQuery** (B-Rep) that reseals an
open bag by trapping its folded edge in a tight channel — like a freezer-bag rail.
An optional **pour nozzle** bores through the back wall into the channel so you can
dispense from the sealed corner without unclipping.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Reseal Clip** | `clip` | Plain C-clip at `clip_width`; optional grip ribs. |
| **Pour-Spout Clip** | `spout_clip` | The clip plus a tapered pour nozzle through the back wall. |
| **Wide Clip** | `wide_clip` | A wider clip (1.8× width) for cereal / freezer bags. |

The plain `clip` mode also exposes a `style` select (`clamp` / `clamp_with_spout`)
so it can grow a spout without switching modes.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Clip Size | `clip_width` | 90 mm | Seal length (wide mode ×1.8). |
| Clip Size | `depth` | 18 mm | Overall clip height. |
| Clip Size | `wall` | 2.4 mm | Back wall + lip thickness. |
| Channel & Grip | `channel` | 3.0 mm | Gap that grips the folded bag edge. |
| Channel & Grip | `lip` | 10.0 mm | How far the lips reach over the bag. |
| Channel & Grip | `grip_ribs` | on | Ribs inside the channel that bite the bag. |
| Pour Spout | `spout_dia` / `spout_len` | 10 / 16 mm | Pour nozzle bore and length. |

## Presets

- **Snack Bag Clip** — 90 mm plain clip, tight channel.
- **Flour Pour Clip** — 120 mm with a 12 mm pour nozzle.
- **Freezer Bag Clip** — 150 mm wide clip, deeper channel.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:**
  - **Bag Clamp** (`snap`, internal) — the C-channel grip, defined by
    `clip_width`, `channel`, `lip`, `wall`, `depth`. Any bag whose folded edge
    fits the channel is held; the same profile scales to a family of widths.
- **Material awareness:** the `channel` gap and `wall` are exposed so grip force
  can be tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** a reusable reseal clip keeps food fresh without single-use
  ties, and the pour variant turns any bag into a controllable dispenser.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The C cross-section is a single closed profile extruded once across the width,
  so the body is inherently **watertight**; grip ribs are unioned with their root
  embedded in the lip (volumetric boolean, no tangent-kiss cracks).
- The script is **self-contained** (sandbox-safe): parameters via
  `PARAM(lambda: name, default)`; the final solid is assigned to `result`.
