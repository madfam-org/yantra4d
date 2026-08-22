# Strap End Tip

The cap that finishes the raw end of a **leather strap** or a length of **webbing** —
generated with **CadQuery** (B-Rep). It stops the end fraying, gives the strap a
silhouette, and on a belt it is the piece that leads the tongue through the keeper. The
strap slides into a channel that runs the full width of the tip, so the garment's own
finished strap dimensions size the hardware directly. Fashion Cabinet's `strap-end-tip`
notion owns the fashion semantics (strap length, taper, hole spacing) and bridges to
**this** solid for the hardware.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Rounded Nose** | `rounded` | Semicircular nose — the belt-tip standard, and the safest on a bag strap. |
| **English Point** | `pointed` | V nose — the dress-belt standard. |
| **Square Nose** | `square` | Straight nose with softened corners — webbing and utility straps. |

All three share the identical channel and rivet pattern, so a strap drafted for one mode
fits any of them.

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Strap | `strap_w` | 25 mm | 10–75 | Finished strap/webbing width. Webbing is nominally 20 / 25 / 38 / 50 mm. Channel cut +0.6 mm. |
| Strap | `strap_t` | 3.0 mm | 0.8–8.0 | Strap thickness. Garment leather 1.2–2, belt veg-tan 3–4.5, webbing ≈1.2. Channel cut +0.4 mm. |
| Tip | `wall_t` | 1.6 mm | 1.0–4.0 | Wall around the channel — the whole outside dimension is built from it. |
| Tip | `tip_len` | 26 mm | 8–120 | Overall length; clamped to 0.5–3× the strap width. |
| Tip | `nose_len` | 14 mm | 2–90 | Shaped portion; clamped so a riveted shank always survives. Ignored on `square`. |
| Setting | `rivet_dia` | 3.0 mm | 1.5–5.0 | Rivet bore; clamped to a quarter of the strap width. |
| Setting | `rivets` | 2 | 1–3 | One centred rivet for a narrow strap; two spread across stop the tip rotating. |

## Presets

- **Dress Belt Tip** — 38 mm English point over 3.6 mm veg-tan.
- **Webbing End** — 25 mm square nose over 1.4 mm webbing.
- **Bag Strap** — 20 mm rounded nose, single rivet.

## Geometry notes

The nose outline is drawn in plan and extruded once — no lofts, no sweeps. The rounded
nose uses `threePointArc` rather than `radiusArc`: an arc whose radius equals half the
chord is degenerate and collapsed the whole outline to a sliver when it was first verified.
The strap channel is cut with a cutter that overshoots past the back face, so the slot
genuinely opens rather than becoming a sealed internal void, and all fillets run on the
clean blank before any cut.

## Print notes

Print **flat on the widest face**, channel opening sideways — self-supporting, no bridging,
no supports. PETG or ASA at 3–4 perimeters; PLA is acceptable on a light bag strap but the
channel lips are thin and PLA snaps rather than bending. If the strap will not slide in,
increase `wall_t` and reprint rather than forcing it — the channel already carries a
0.6 × 0.4 mm slip allowance and enlarging it further loses the friction that keeps the tip
seated while you punch.

Set with double-cap rapid rivets through both the tip bores and the strap, from the side
you want the cap to show. All three modes export watertight, single-body.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Strap Channel** (`flange`, internal) — **the slide-on flange for the dimensional
    handshake**: the full-width groove the strap end is threaded into. Defined by
    `strap_w`, `strap_t`, `wall_t`.
  - **Rivet Pattern** (`bolt_pattern`, internal) — the setting pattern through tip and
    strap, defined by `rivets`, `rivet_dia`, `strap_w`.

## Fashion Cabinet bridge

Consumed by FC's **belt**, **bag shoulder strap**, **backpack sternum strap**, **guitar
strap** and **overall strap** garments — anything with a raw strap end that needs
finishing.

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "strap-end-tip",
  "linked": true,
  "params_map": {
    "strap_w": "strap_width_mm",
    "strap_t": "strap_thickness_mm",
    "wall_t": "1.6",
    "tip_len": "strap_width_mm * 1.05",
    "nose_len": "strap_width_mm * 0.55",
    "rivet_dia": "3.0",
    "rivets": "strap_width_mm >= 20 ? 2 : 1"
  }
}
```

The **`strap_channel`** interface is the handshake surface: FC drives its finished
`strap_width_mm` and `strap_thickness_mm` straight into `strap_w`/`strap_t`, and every
other dimension of the tip — outside width, outside thickness, default length and nose —
is derived from those two. Re-draft the strap on the FC side and the tip regenerates to
match with no hardware edits at all, which is the coupling this shelf exists to
demonstrate.

The sibling `strap-ring` and `chicago-screw` cartridges are the other half of a strap's
hardware set: rings at the anchor end, screws at the adjustment, this tip at the free end.

`CERN-OHL-W-2.0`.
