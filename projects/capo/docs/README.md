# Capo / Slide (parametric)

A parametric **capo** that clamps across the fretboard to raise every string's
pitch, generated with **CadQuery** (B-Rep). The functional interface is the
**fretboard radius** — the contact bar's face is a concave cylinder matched to
the neck crown so it presses every string evenly.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Yoke Capo** | `yoke_capo` | A C-yoke that hooks over the neck with a thumbscrew boss; the screw tensions a radiused pad down onto the strings. |
| **Lever Capo** | `lever_capo` | A quick-change body with a radiused pad and a back slot for a band/spring that snaps the capo shut. |
| **Partial Capo** | `partial_capo` | A short capo covering only some strings (open / drop tunings), radiused to the same neck, with strap holes. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Neck | `fret_radius` | `9.5in` | Neck crown radius the pad matches (7.25/9.5/12/16 in, classical). |
| Neck | `neck_w` | 46.0 mm | Fretboard width where the capo sits. |
| Neck | `neck_th` | 22.0 mm | Neck front-to-back depth the yoke wraps. |
| Pad | `pad_w` | 10.0 mm | Width of the string-contact bar. |
| Pad | `strings` | 6 | Strings the partial capo spans. |
| Body | `screw_d` | 5.2 mm | Thumbscrew hole (M5). |
| Body | `wall` | 6.0 mm | Yoke / body / spine wall. |

## The radius (why it presses evenly)

A fretboard is a **convex cylinder** — the six strings sit on a crown, not a
flat. A flat capo bar presses the outer strings and leaves the middle buzzing (or
vice-versa). The pad's contact face is scooped to a **concave cylinder** of the
same radius (`R`), so its sagitta `s = R - √(R² - (w/2)²)` exactly follows the
crown across the pad width. Choosing the real neck radius — **7.25 in (184 mm),
9.5 in (241 mm), 12 in (305 mm), 16 in (406 mm)** or near-flat classical — makes
the capo press all strings with equal force.

## Presets

- **9.5 in Yoke Capo** — the screw-tension capo for a modern Fender neck.
- **Quick-Change Lever Capo** — a band-sprung quick capo (12 in Gibson).
- **Partial Capo (3-string)** — for DADGAD-style partial/open tunings.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interface:** **Fretboard Radius Pad** (`profile`, *internal*) — the
  concave contact arc, defined by `fret_radius`, `neck_w`, `neck_th`. Capos and
  slides built to the same radius match the same neck.
- **Material awareness:** none declared — the radius match is geometric; band /
  screw tension does the clamping.
- **Societal benefit:** a capo that doesn't match the radius buzzes or mutes
  strings; matching real radii lets a player print a capo that presses all
  strings evenly on their exact neck, plus partial capos stores rarely stock.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The radiused pad face is a shallow concave cylinder **cut from the underside**
  (an arc open to the outside, never a cavity); the yoke is a **C-section** (a
  block minus an open-bottom neck window, so bridge + walls stay one body);
  screw and strap holes are **through-holes**. All modes render **watertight**,
  single-body.
