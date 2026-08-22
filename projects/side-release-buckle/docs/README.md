# Side-Release Buckle

The printable **two-part snap buckle** — generated with **CadQuery** (B-Rep). A male half
whose pair of sprung cantilever prongs slides into a female housing and clicks out through
its side windows when you squeeze them. This is the closure on pack straps, sternum straps,
dog collars and duffel lids. Fashion Cabinet's `side-release-buckle` notion owns the
fashion semantics (strap placement, tape routing) and bridges to **this** solid for the
hardware.

The sibling `belt-buckle` cartridge covers center-bar **belt** hardware instead; this one
is for **webbing** — nominal trade widths 20, 25, 38 and 50 mm.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Buckle Set (male + female)** | `set` | Both halves laid side by side with a print gap — two separate solids on one plate. |
| **Male Half (prongs)** | `male` | The nose plate, two sprung prongs with lofted catch ramps, and the webbing tail. |
| **Female Half (housing)** | `female` | The hollow housing with its two side windows and webbing tail. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Webbing | `webbing_w` | 25.0 mm | 15–50 | Nominal tape width. Trade sizes are 20 / 25 / 38 / 50. |
| Webbing | `webbing_t` | 1.6 mm | 0.8–4.0 | Tape thickness; sets the channel opening. |
| Body | `body_t` | 8.0 mm | 5–14 | Overall thickness of both halves. |
| Body | `wall_t` | 2.2 mm | 1.4–4.0 | Housing wall and prong stock. Below 2 mm the prongs get whippy. |
| Snap Action | `prong_len` | 20.0 mm | 10–40 | Free cantilever length. Longer = softer squeeze at the same stress. |
| Snap Action | `snap_clear` | 0.35 mm | 0.15–0.8 | Male-nose to female-cavity running clearance. |

## Presets

- **SR25 Pack Strap** — the 25 mm workhorse.
- **SR50 Duffel Lid** — 50 mm heavy section.
- **SR20 Sternum Strap** — 20 mm fine section.

## Print notes

Print **flat on the bed**, both halves as they lie — every feature is self-supporting and
nothing needs supports. The prongs are the whole point of the part, so orient so their
layers run **along** the arm (which is what the flat lay gives you): a prong printed with
layer lines across the flexure snaps off on the first squeeze. PETG or nylon; PLA will
work for a light closure but goes brittle at the prong root after a few dozen cycles. Four
perimeters, 40 % infill, 0.15 mm layers.

If the halves are too tight to click home, reprint the **female** with `snap_clear` one
step higher rather than sanding the prongs. If the buckle releases under load, raise
`wall_t` (a stiffer prong holds its catch deeper in the window).

Every mode exports watertight. The housing cavity opens out through the mating mouth so it
is never a sealed internal void, and the catch ramps are flat-topped lofts, never points.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Webbing Channel** (`flange`, internal) — **the threaded tape edge for the
    dimensional handshake**: the slot the webbing passes through on each half. Defined by
    `webbing_w`, `webbing_t`, `body_t`.
  - **Prong Catch** (`snap`, internal) — the internal mating contract between the halves,
    defined by `prong_len`, `wall_t`, `snap_clear`.

## Fashion Cabinet bridge

FC garments and notions that consume this object: **pack and duffel closures**, **sternum
straps** on technical outerwear, **dog-collar and harness closures**, and any **detachable
strap** notion whose tape must be released one-handed.

FC-side `hardware_ref` block on the `side-release-buckle` notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "side-release-buckle",
      "linked": true,
      "params_map": {
        "webbing_w": "strap_width_mm",
        "webbing_t": "strap_thickness_mm",
        "body_t": "max(6.0, strap_width_mm * 0.32)",
        "wall_t": "max(1.8, strap_width_mm * 0.09)",
        "prong_len": "strap_width_mm * 0.8",
        "snap_clear": "0.35"
      }
    }
  }
}
```

The garment drives the hardware: the finished strap width flows into `webbing_w`, which
sizes the channel, the housing span and the prong spacing together. `webbing_channel` is
the interface FC uses for the dimensional handshake when it routes the tape.

`CERN-OHL-W-2.0`.
