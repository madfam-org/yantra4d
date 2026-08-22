# Kiss-Lock Frame

A simplified printable **purse frame** — generated with **CadQuery** (B-Rep). Two mirror
half-frames pivot on a pin-bore hinge at each outer corner and meet at a ball-clasp kiss
in the middle. Along the whole underside of each arch runs the **sew channel**: the open
groove the purse fabric is folded into and glued or whip-stitched through, exactly the way
a metal kiss-lock frame is set. Fashion Cabinet's `kiss-lock-frame` notion owns the fashion
semantics (gusset pattern, finished mouth width) and bridges to **this** solid for the
hardware.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Half Frame** | `half_frame` | One arch: sew channel, both hinge knuckles, the ball nub at the crown. |
| **Frame Set (both halves)** | `set` | Both halves as two separate bodies on one plate — one carries the ball, one the dished cup. |

The two halves are geometrically identical apart from the clasp feature, so `half_frame`
renders the ball version; `set` is where the cup half appears.

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Mouth | `frame_w` | 90 mm | 50–220 | Finished mouth width, hinge centre to hinge centre. 60–100 mm coin purse/clutch, 140–200 mm doctor bag. |
| Mouth | `arch_h` | 22 mm | 8–90 | Crown rise above the hinge line. Clamped to `frame_w × 0.45`. |
| Rod Section | `rod_t` | 5.0 mm | 3–12 | Front-to-back rod thickness — the dimension the channel is cut into. |
| Rod Section | `rod_h` | 7.0 mm | 4–16 | Radial rod height, top face down to the channel lip. |
| Sewing | `channel_w` | 2.4 mm | 1.2–6.0 | Fabric groove width; auto-clamped to `rod_t − 1.6` so wall survives on both sides. |
| Hinge & Clasp | `pin_dia` | 2.0 mm | 1.2–4.0 | Hinge pin bore. 2 mm takes cut brass rod or a steel dowel. |
| Hinge & Clasp | `ball_dia` | 4.0 mm | 2.5–8.0 | Kiss-clasp ball; the cup half is cut 0.25 mm larger. |

## Presets

- **Coin Purse** — 70 mm, fine section.
- **Evening Clutch** — 120 mm.
- **Doctor Bag** — 180 mm, heavy leather section with a 4 mm channel.

## Geometry notes

The arch is a rounded-rect ring built in plan, trimmed to a half-ring, then stood upright —
one boolean pair, no swept arcs. The sew channel is a **shell** offset from that same plan
outline, so it tracks the rod centreline around the corners rather than only along the
straight run, and it is trimmed so the slot opens downward: never a sealed internal void.
The clasp ball is a **revolved profile with a flat crown land**, not a cylinder plus a
sphere cap — that union is banned here because the sphere's pole reads as a crack.

## Print notes

Print each half **flat on its face**, channel opening sideways — the arch is self-supporting
in that orientation and the channel needs no bridging. PETG or PLA+ at 4 perimeters and
40 % infill; the hinge knuckle and the channel lip are the stress path. Ream the pin bore
after printing and pin with 2 mm brass rod peened over, or a 2 mm steel dowel with a drop
of epoxy at each end.

To set the fabric: fold the shell and lining edge together, run a bead of leathercraft
cement into the channel, seat the folded edge, clamp with binder clips until dry, then
whip-stitch through the fabric on both lips for a mechanical belt as well as the glue.

Both modes export watertight. `set` exports as two separate bodies with a real print gap —
never a `.union()` of non-touching solids.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sew Channel** (`flange`, internal) — **the sewn flange for the dimensional
    handshake**: the groove the folded fabric edge is set into. Defined by `frame_w`,
    `channel_w`, `rod_t`.
  - **Hinge Pin Bore** (`socket`, internal) — the pivot, defined by `pin_dia`, `frame_w`,
    `rod_h`.
  - **Kiss Clasp** (`snap`, internal) — the ball/cup engagement between the two halves,
    defined by `ball_dia`, `rod_t`. Internal contract, not FC-driven beyond tolerance.

## Fashion Cabinet bridge

Consumed by FC's **framed clutch**, **coin purse**, **doctor bag** and **framed cosmetic
pouch** garments — anything whose pattern is drafted around a rigid mouth rather than a
zipper.

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "kiss-lock-frame",
  "linked": true,
  "params_map": {
    "frame_w": "bag_mouth_width_mm",
    "arch_h": "bag_mouth_width_mm * 0.24",
    "rod_t": "shell_fabric_thickness_mm * 2 + lining_thickness_mm + 1.8",
    "rod_h": "bag_mouth_width_mm * 0.08",
    "channel_w": "shell_fabric_thickness_mm * 2 + lining_thickness_mm + 0.4",
    "pin_dia": "2.0",
    "ball_dia": "bag_mouth_width_mm * 0.045"
  }
}
```

The **`sew_channel`** interface is the handshake surface: FC drives its own finished mouth
width into `frame_w`, and the material stack it plans to fold in (shell plies + lining +
cement) sizes `channel_w` — the same number that then constrains `rod_t`. Change the
fabric on the FC side and the frame's section grows to match, which is the whole point of
the coupling.

`CERN-OHL-W-2.0`.
