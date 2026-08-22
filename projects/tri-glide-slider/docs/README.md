# Tri-Glide Slider

The printable **flat three-bar webbing glide** — generated with **CadQuery** (B-Rep). A
rectangular frame with two bars across it, giving three openings. The tape goes over the
near bar, under the middle bar and back over the far bar; that double reversal is what
holds a length setting. Fashion Cabinet's `tri-glide-slider` notion owns the fashion
semantics (strap routing and dead-end placement) and bridges to **this** solid for the
hardware.

Deliberately distinct from its shelf siblings: `d-ring` is a single anchor loop,
`bra-ring-slider` is the small lingerie ring-and-slider pair, and `ladder-lock` is the
one-bar adjuster with a quick release. **This** is the flat three-bar glide — no release,
just a setting that stays put.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Tri-Glide** | `glide` | The whole glide. One piece by design — there is no second part. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Webbing | `webbing_w` | 25.0 mm | 15–50 | Nominal tape width. All three openings span this + 1 mm. |
| Webbing | `webbing_t` | 1.6 mm | 0.8–4.0 | Tape thickness. Outer openings pass one; the middle passes two. |
| Frame | `rail_t` | 3.2 mm | 2.0–6.0 | Outer rail thickness — the load path. |
| Frame | `bar_w` | 4.0 mm | 2.5–8.0 | Internal bar width along the pull. |
| Frame | `body_h` | 4.0 mm | 2.5–9.0 | Glide height (= print height lying flat). |
| Style | `round_bar` | on | — | Fillet the bars' long edges so the tape rolls over a rounded section. |

## Presets

- **Sternum Strap** — the 25 mm default.
- **Apron Tie** — 38 mm, rounded bars.
- **Harness Glide** — 50 mm heavy section, square bars for maximum grip.

## Print notes

Print **flat on the bed**. All three openings are vertical through-holes; nothing bridges
and no supports are needed. The flat lay also puts the layer lines across the rails, which
is the correct orientation — the load path here is tension along X through both end rails,
not a bending flexure. Nylon or PETG for a load-bearing strap; PLA is adequate for an apron
tie or a camera sling. Four perimeters and 50 % infill.

`round_bar` off gives a square-cornered bar that grips harder — the right choice for a
slippery polypropylene harness strap; `round_bar` on is kinder to lightweight or
delicate webbing that would crease over a sharp corner. Every mode exports watertight; the
bar fillets are bounded, guarded selections, never a blanket fillet after the cuts.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Webbing Openings** (`flange`, internal) — **the threaded tape edge for the
    dimensional handshake**: all three openings the webbing passes through. Defined by
    `webbing_w`, `webbing_t`, `rail_t`.
  - **Bar Profile** (`profile`, internal) — the friction section the tape reverses over,
    defined by `bar_w`, `body_h`, `round_bar`.

## Fashion Cabinet bridge

FC garments and notions that consume this object: **overall and dungaree straps**, **apron
and smock ties**, **camera and bag slings**, **sternum straps**, **dog harness** adjusters,
and any garment notion where a strap is set once and left alone rather than released
repeatedly.

FC-side `hardware_ref` block on the `tri-glide-slider` notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "tri-glide-slider",
      "linked": true,
      "params_map": {
        "webbing_w": "strap_width_mm",
        "webbing_t": "strap_thickness_mm",
        "rail_t": "max(2.4, strap_width_mm * 0.13)",
        "bar_w": "max(3.0, strap_width_mm * 0.16)",
        "body_h": "max(3.0, strap_width_mm * 0.16)",
        "round_bar": "true"
      }
    }
  }
}
```

The garment drives the hardware: the finished strap width flows into `webbing_w`, sizing
all three openings and the frame span together; `webbing_openings` is the interface FC uses
for the dimensional handshake when routing the tape.

`CERN-OHL-W-2.0`.
