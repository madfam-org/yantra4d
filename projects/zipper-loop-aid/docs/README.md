# Zipper Loop Aid

A printable **large finger ring that clips onto any zipper pull tab**. One piece: a C-clip
that springs over the tab, and a generous ring for a finger, two fingers or a hooked thumb.
Generated with **CadQuery** (B-Rep).

A standard pull tab is a 2 mm slip of metal about 20 mm long, and working it needs a
thumb-and-forefinger pinch with fine control. Arthritis, tremor, neuropathy, hemiparesis,
missing digits, a cast, thick gloves, or simply reaching a back zipper all defeat that
pinch. Occupational therapy's usual improvisation is a loop of cord or a keyring — which
slides, twists, and has to be knotted on with the very fingers that cannot work the zipper.
This clips on and stays put.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Loop Aid** | `aid` | One aid, printed flat as a single piece. |
| **Loop Aid Pair** | `pair` | Two aids nested head-to-toe — the fitting for a jacket with two sliders or a two-way zipper. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Finger Ring | `ring_id` | 28.0 mm | 14–70 | Ring bore. 22 mm one finger, 28 mm two, 40 mm a gloved hand. |
| Finger Ring | `ring_w` | 5.0 mm | 2.5–14 | Ring wall width in plane; spreads the pull across the finger. |
| Finger Ring | `part_t` | 4.0 mm | 2–14 | Thickness out of plane; with the wall width this is the bearing section. |
| Tab Clip | `tab_t` | 2.0 mm | 0.8–6.0 | Pull tab thickness. YKK #5 ≈ 1.5–2 mm; #8/#10 outerwear 2–3 mm. |
| Tab Clip | `tab_w` | 10.0 mm | 4–30 | Tab width the clip spans. Need not be the tab's full width. |
| Tab Clip | `clip_wrap` | 0.7 | 0.35–0.92 | Mouth as a fraction of `tab_t`. Below 1 it snaps on with interference. |
| Tab Clip | `clip_arm` | 3.0 mm | 1.4–8.0 | Clip arm wall thickness. |

## How the clip works

The pocket lies flat: its long dimension takes the tab's width, its short one the tab's
thickness. The tab is pushed in **sideways**, past a throat whose height is `mouth =
tab_t × clip_wrap` — deliberately *less* than the tab is thick. The arms spring apart, the
tab passes, and they close behind it.

The geometry is oriented so that pulling the ring loads the clip **across** the mouth rather
than out of it: the grip tightens under load instead of releasing. That is the difference
between this and a cord loop, which pulls straight out of whatever it is looped through.

## Print notes

Print **flat on the plate** — the whole aid is one plane of material with flat top and
bottom faces, so no supports are needed and the clip's spring works along the layer plane
rather than across it. An assistive device that requires support removal is one a person
with limited hand function cannot finish making.

**PETG** at 0.2 mm layers, 4 perimeters, 40 % infill for a clip that snaps firmly and
survives daily use. **TPU 95A** is better if the aid will be taken on and off often — the
arms stay springy indefinitely, at the cost of a softer ring. PLA arms will fatigue and
break within weeks.

If the clip will not go on by hand, raise `clip_wrap` one or two steps and reprint rather
than forcing it; if it falls off, lower `clip_wrap`. Do not compensate by changing `tab_t`,
which should stay the measured truth about the tab.

Every mode exports watertight; the `pair` mode returns an assembly of two separate aids, not
a fused body.

## Hyperobject Profile

Domain `wearable`. Two CDG interfaces:

- **`pull_tab_clip`** (`snap`, parameters `tab_t`, `tab_w`, `clip_wrap`, `clip_arm`) — the
  interference C-clip that engages a pull tab. Point-fixed clip-on hardware, not a sewn
  edge, so `snap`.
- **`finger_ring`** (`profile`, parameters `ring_id`, `ring_w`, `part_t`) — the bearing
  section the hand pulls on.

## Sibling cartridge: `zipper-pull`

This aid **grips** what the `zipper-pull` cartridge **makes**. That cartridge's `pull_tab`
mode produces a replacement tab of `grip_w` wide by `thick` thick; those are exactly the two
dimensions this clip is sized to. Printing both from one set of numbers gives a matched
pair — a replacement tab and the loop that clips onto it:

| `zipper-pull` param | → | `zipper-loop-aid` param |
| :--- | :-- | :--- |
| `grip_w` | → | `tab_w` |
| `thick` | → | `tab_t` |

Use `zipper-pull` when the original tab is lost or broken and a new one is needed; use this
aid when the tab is fine and only the *grip* is the problem. They stack: a printed
`zipper-pull` tab plus this loop clipped onto it is the fullest adaptation of a zipper that
does not touch the garment.

## Fashion Cabinet bridge

Expected FC consumers: any FC garment carrying a **zipper** — the **jacket**, **hoodie**,
**back-zip dress**, **boot** and **trouser fly** — plus the **zipper** and **pull tab**
notions, and any FC garment flagged as adaptive dressing.

The handshake is on the tab, not the garment: FC's zipper notion knows the chain size (#3,
#5, #8, #10) and the pull-tab dimensions that come with it, and those two numbers size the
clip. Nothing about the garment's own pattern is involved, which is the point — the aid
adapts a zipper without altering the garment.

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "zipper-loop-aid",
  "linked": true,
  "params_map": {
    "tab_t": "pull_tab_thickness_mm",
    "tab_w": "min(10, pull_tab_width_mm)",
    "clip_wrap": "0.7",
    "clip_arm": "3.0",
    "ring_id": "wearer_ring_bore_mm",
    "ring_w": "5.0",
    "part_t": "4.0"
  }
}
```

The **`pull_tab_clip`** interface is what FC reads: change the FC zipper's chain size and the
clip resizes to the tab that chain ships with. The sibling **`button-hook-aid`** cartridge
covers the button equivalent of the same accessibility problem.

`CERN-OHL-W-2.0`.
