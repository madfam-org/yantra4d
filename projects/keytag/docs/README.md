# Keychain / Tag

A flat keychain tag with an embossed or debossed name/number and a ring hole,
generated with **CadQuery** (B-Rep). The personalization gateway: pick a shape,
type a label, print.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Tag** | `tag` | A flat tag + one text line. |
| **Two-Line Tag** | `tag_2line` | The same tag with a second text line. |
| **Luggage Tag** | `luggage_tag` | A larger tag with a strap slot and room for a longer label. |

Shapes: **rounded rectangle**, **circle**, **dog tag**, **bone**.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Shape & Size | `shape` | rounded_rect | Tag outline. |
| Shape & Size | `size` | 45 mm | Nominal length. |
| Shape & Size | `thick` | 3.0 mm | Plate thickness. |
| Text | `text` | KEY-01 | Primary line. |
| Text | `text2` | (empty) | Second line (two-line / luggage). |
| Text | `text_mode` | deboss | Debossed or embossed. |
| Text | `text_depth` | 0.8 mm | Deboss depth / emboss height. |
| Ring Hole | `hole_dia` | 5.0 mm | Ring hole (or strap-slot width on luggage). |
| Ring Hole | `hole_pos` | 6.0 mm | Inset from the leading edge. |

## Text robustness

Text is applied via CadQuery `text()`, and the boolean result is **validated with
`.val().isValid()`** inside the sandbox. Findings that shaped the design:

- ASCII labels are watertight in **both** deboss and emboss.
- Some **accented glyphs break a debossed cut** (the resulting solid is invalid /
  non-manifold) but emboss cleanly. So the code **tries the requested mode, and if
  the solid is invalid, automatically falls back to the other mode**, then finally
  to a blank (but watertight) plate.
- A missing CJK/glyph font degrades to a blank plate rather than crashing.

Result: **every shipped variant renders watertight**, including accented text — the
accented-deboss case transparently falls back to emboss.

## Presets

- **Numbered Key Tag** — a debossed rounded-rect key tag.
- **Pet Bone Tag** — an embossed bone tag.
- **Address Luggage Tag** — a two-line luggage tag with a strap slot.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:** **Tag Outline + Text** (`profile`, internal) — defined by
  `shape`, `size`, `text`, `text_mode`.
- **Material awareness:** `tolerance_by_material` — text legibility and depth depend
  on filament/printer; tune `text_depth`.
- **Societal benefit:** the gateway print for personalization — a named, numbered,
  or labelled tag anyone can make in seconds.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; final solid assigned to `result`.
- All shipped presets and defaults render **watertight** (text included).
