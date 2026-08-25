# Cord End (Aglet & Bell Tip)

The printable tip that finishes a drawcord — generated with **CadQuery** (B-Rep).
A straight **aglet** (shoelace point) or a flared **bell tip** for hoodie and
waistband strings. It crimps onto the cord end so the braid cannot fray or vanish
back into its channel, and it feeds the cord through eyelets.

Fashion Cabinet's `cord-end` notion owns the fashion semantics (which cord, which
channel, where the tip sits at rest) and bridges to **this** solid for the
hardware. The companion [`cord-lock`](../../cord-lock) cartridge owns the *stop*
function — this object is purely the tip, and shares its `cord_dia` / `wall`
naming so a garment can drive both from one cord spec.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com). `CERN-OHL-W-2.0`.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Both Tips** | `set` | An aglet and a bell tip side by side, on a computed gap. |
| **Aglet** | `aglet` | Straight sleeve with a rounded closed end. |
| **Bell Tip** | `bell` | Cone frustum flaring to `bell_flare ×` the sleeve diameter at the mouth. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Cord | `cord_dia` | 4.0 mm | 2.0–8.0 | Drawcord diameter; the bore adds 0.15 mm clearance per side. |
| Cord | `wall` | 1.5 mm | 0.8–3.0 | Sleeve wall, and the solid thickness of the closed tip. |
| Tip | `tip_length` | 15 mm | 8–30 | Overall length, mouth to closed end. Bore depth is `tip_length − wall`. |
| Tip | `bell_flare` | 1.4 | 1.0–2.0 | Mouth diameter as a multiple of sleeve OD. `1.0` renders a straight sleeve. |
| Tip | `lanyard_hole` | off | checkbox | Small cross-hole through the solid cap, for a charm or zipper pull. Auto-suppressed if the cap is too short to hold it. |

Outer diameter is `cord_dia + 2 × wall` (plus bore clearance). Every parameter is
clamped in `main.py`, including the cross-clamps that keep the bore inside the
wall and the cap at least `wall` thick — which is why `constraints` is empty.

## Print notes

Print **mouth-down** (open end on the bed): the bore then needs no support and the
rounded nose is the last thing printed. PLA or PETG at 0.12–0.16 mm layers; three
perimeters is plenty at `wall ≥ 1.2`. To crimp, warm the sleeve briefly and press,
or run a drop of glue into the bore. Prints well in recycled and offcut material
(`recycled_material_toggle` in the hyperobject profile). Bell tips at
`bell_flare ≥ 1.7` overhang about 35° at the mouth — still bridgeable, but slow
the first layers.

## Fashion Cabinet bridge

The FC-side notion carries:

```json
{
  "hardware_ref": {
    "platform": "yantra4d",
    "project_slug": "cord-end",
    "linked": true,
    "params_map": {
      "cord_dia": "drawcord_diameter_mm",
      "wall": "max(0.8, drawcord_diameter_mm * 0.35)",
      "tip_length": "clamp(drawcord_diameter_mm * 3.75, 8, 30)",
      "bell_flare": "eyelet_diameter_mm / (drawcord_diameter_mm + 2 * max(0.8, drawcord_diameter_mm * 0.35))",
      "lanyard_hole": "notion.has_zipper_pull"
    }
  }
}
```

The **dimensional handshake** flange is `cord_mouth` — the crimped open edge that
meets the cord and must clear the garment's eyelet. FC sizes it from the eyelet
diameter (via `bell_flare`) so the tip always passes through the channel it feeds.
`cord_bore` (`socket`) is the mating interface to the cord itself and is the one
`cord-lock` shares, so a garment's single `drawcord_diameter_mm` drives the tip
and the stopper together.
