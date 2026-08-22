# Ladder Lock

The printable **one-piece webbing adjuster** — generated with **CadQuery** (B-Rep). A
rectangular frame with a fixed bar across its middle: the dead end of the tape is sewn
round the far bar, the live end threads up through the near slot, over the center bar and
back down. Friction on that wrap holds the setting; lifting the tape off the bar releases
it in one motion. Fashion Cabinet's `ladder-lock` notion owns the fashion semantics
(strap routing and dead-end placement) and bridges to **this** solid for the hardware.

Distinct from the siblings: `tri-glide-slider` is the flat **three-bar** glide (no quick
release), `d-ring` is a single anchor loop, and `side-release-buckle` is a closure rather
than an adjuster.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Ladder Lock** | `lock` | The whole adjuster. The object is one piece by design — there is no meaningful second part. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Webbing | `webbing_w` | 25.0 mm | 15–50 | Nominal tape width. Slots span this + 1 mm. |
| Webbing | `webbing_t` | 1.6 mm | 0.8–4.0 | Tape thickness. Slots open to 2× this, since the tape doubles at the wrap. |
| Frame | `frame_t` | 3.0 mm | 2.0–6.0 | Outer rail thickness — the load path under tension. |
| Frame | `bar_w` | 4.5 mm | 3.0–10.0 | Center bar width along the pull. Wider spreads the wrap. |
| Frame | `body_h` | 5.0 mm | 3.0–10.0 | Frame height (= print height lying flat). |
| Grip | `teeth` | 4 | 0–8 | Grip ribs on the bar. Set 0 for a smooth bar that releases slippery PP easily. Auto-clamped — see below. |

**On the rib count.** `teeth` is clamped to at most one rib per millimetre of `bar_w`,
minus one, so the ribs always keep a real valley between them. At the 4.5 mm default bar
that ceiling is 3, so asking for 4 or 8 both give 3 ribs; a 8 mm bar takes 7. This is a
deliberate physical limit rather than a silent no-op: without it the ribs merge into one
continuous band and the setting stops meaning anything. **Widen `bar_w` if you want more
ribs.**

## Presets

- **Shoulder Strap** — the 25 mm pack default.
- **Haul Strap** — 50 mm heavy section, six ribs.
- **Smooth Bar** — 20 mm with `teeth = 0` for slippery polypropylene.

## Print notes

Print **flat on the bed**. Both slots are vertical through-holes, so nothing bridges and no
supports are needed. The grip ribs stand only a few tenths proud of the bar on both faces —
they are deliberately blunt round-topped lofts, not teeth: they bite the weave without
cutting the tape. Nylon or PETG for a load-bearing strap; PLA is fine for an apron tie.
Four perimeters and 50 % infill matter more than layer height here, because the failure
mode is the frame rail splitting along a layer under tension.

If the setting creeps under load, raise `teeth` or widen `bar_w` before reaching for a
thicker frame. Every mode exports watertight; no fillet runs after the slot cuts.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Webbing Slots** (`flange`, internal) — **the threaded tape edge for the dimensional
    handshake**: both slots the webbing passes through. Defined by `webbing_w`,
    `webbing_t`, `frame_t`.
  - **Center Bar Grip** (`profile`, internal) — the friction face, defined by `bar_w`,
    `teeth`, `body_h`.

## Fashion Cabinet bridge

FC garments and notions that consume this object: **pack shoulder straps** and **sternum
straps**, **apron and smock ties**, **adjustable overall straps**, **dog harness** cinches,
and any garment notion whose strap length must be reset repeatedly by the wearer.

FC-side `hardware_ref` block on the `ladder-lock` notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "ladder-lock",
      "linked": true,
      "params_map": {
        "webbing_w": "strap_width_mm",
        "webbing_t": "strap_thickness_mm",
        "frame_t": "max(2.4, strap_width_mm * 0.12)",
        "bar_w": "max(3.5, strap_width_mm * 0.18)",
        "body_h": "max(4.0, strap_width_mm * 0.20)",
        "teeth": "4"
      }
    }
  }
}
```

The garment drives the hardware: the finished strap width flows into `webbing_w`, sizing
both slots and the frame span together; `webbing_slots` is the interface FC uses for the
dimensional handshake when routing the tape.

`CERN-OHL-W-2.0`.
