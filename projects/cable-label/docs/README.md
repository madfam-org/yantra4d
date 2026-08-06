# Wire / Cable Labels & Markers

Clip-on cable labels generated with **CadQuery** (B-Rep) that snap onto a wire
and carry a short text marker embossed or debossed on a plate. The clip bore is
sized to the cable diameter.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Flag Label** | `flag_label` | A C-clip that snaps on, with a flat tag sticking out to the side carrying the text — reads like a little flag on the wire. |
| **Wrap Label** | `wrap_label` | A fuller band that cuffs most of the cable (narrow snap mouth) with a raised text panel on the outside. |
| **Clip Marker** | `clip_marker` | A compact C-clip with a small marker face and text. |

The studio dispatches the active part via `target_part`
(`flag_label` / `wrap_label` / `clip_marker`); the same choice is exposed as the
`style` parameter. Each mode renders distinct geometry.

## Text

Text is rendered with CadQuery's `text()` on the label face and is **optional**:

- `text_mode = deboss` (default) cuts the glyphs a shallow `text_depth` into the
  plate — the most reliably watertight option.
- `text_mode = emboss` raises the glyphs off the face.
- `text_mode = none` ships a blank plate.

Every glyph operation is wrapped in `try/except`: if a font or glyph fails, the
label degrades to a blank (still watertight) plate rather than crashing. Keep
the string short (a couple of characters is best); `text_depth` is auto-clamped
below the plate thickness.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cable & Clip | `style` | `flag` | `flag`, `wrap`, or `clip`. |
| Cable & Clip | `cable_dia` | 6.0 mm | Cable OD = clip bore. |
| Cable & Clip | `clip_wall` | 2.0 mm | Ring wall thickness. |
| Cable & Clip | `clip_len` | 12.0 mm | Grip length along the cable. |
| Cable & Clip | `gap_frac` | 0.55 | Snap mouth width (× diameter). |
| Label Plate | `plate_w` / `plate_h` | 22 / 12 mm | Label face size. |
| Label Plate | `plate_t` | 2.0 mm | Plate thickness. |
| Text | `text` | `A1` | Short marker string. |
| Text | `text_mode` | `deboss` | `deboss`, `emboss`, or `none`. |
| Text | `text_depth` | 0.6 mm | Glyph cut / raise depth. |

## Presets

- **Patch Cable Flag** — a Ø6 flag label with debossed `A1`.
- **Power Cord Wrap** — a Ø9 wrap band with embossed `PC`.
- **Thin Wire Clip (Ø3)** — a compact Ø3 clip marker reading `7`.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Cable Clip + Label** (`profile`, internal) — the C-clip snap section,
    defined by `cable_dia`, `clip_wall`, `clip_len`, and `gap_frac`. Any clip at
    the same `cable_dia` snaps onto the same wire.
  - **Text Marker Face** (`profile`, internal) — the label plate and its
    embossed/debossed text (`text`, `text_mode`, `text_depth`, plate size).
- **Material awareness:** the clip bore equals the raw `cable_dia`; add a
  per-material clearance for a firmer or looser snap, and note that a stiffer
  material wants a larger `gap_frac`. `tolerance_by_material` is declared.
- **Societal benefit:** unlabeled cables cost hours in racks, walls, and
  workshops; a snap-on marker sized to the exact wire and printed with its ID
  makes every cable traceable without adhesive tags that fall off.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- The clip is a solid tube with a through bore and a radial snap mouth (a
  boolean cut), and text is applied as a guarded emboss/deboss. Verified
  **watertight** across all three modes, all text modes (deboss / emboss / none),
  long and special-character strings, and the parameter extremes.
