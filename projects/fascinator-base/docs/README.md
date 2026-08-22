# Fascinator Base

A printable **millinery fascinator base** — a shallow disc or dome with a flat sewing brim,
a comb-slot pair underneath, and a ring of sew holes around the brim. Generated with
**CadQuery** (B-Rep).

Commercial fascinator bases are buckram or sinamay-covered card in four diameters, one
crown height, and no comb provision at all: you sew the comb on by hand and hope. This base
takes the diameter, the crown rise **and the comb it will actually be worn with** as
parameters. The trim sews to the brim ring; the comb spine slides through the slot pair and
holds the whole thing to the head.

`dome_h` below 1 mm gives a flat plate base — the kind worn tilted on the side of the head.
Raising it gives the pillbox dome that sits over the crown.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Fascinator Base** | `base` | One base — dome or flat plate depending on `dome_h`. |
| **Base Pair** | `pair` | Two bases side by side (a fascinator and its matching mini, or a spare). |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Base | `base_dia` | 90.0 mm | 40–200 | Outside diameter. Millinery stocks 60/80/100/120 mm. |
| Base | `dome_h` | 14.0 mm | 0–60 | Crown rise above the brim; < 1 mm gives a flat plate. Clamped to 45 % of `base_dia`. |
| Base | `base_t` | 2.4 mm | 1.2–6.0 | Shell and brim wall thickness. |
| Sewing | `brim_w` | 9.0 mm | 4–30 | Flat sewing land width; auto-widened to hold the hole ring. |
| Sewing | `sew_holes` | 16 | 0–48 | Perimeter stitch holes. Zero leaves a plain brim. |
| Sewing | `hole_dia` | 2.0 mm | 1.0–4.0 | Stitch hole diameter; clamped to fit inside `brim_w`. |
| Comb Fit | `comb_w` | 38.0 mm | 15–90 | Comb spine width the slots must pass. Standard combs 35–45 mm. |
| Comb Fit | `comb_t` | 2.2 mm | 1.2–5.0 | Comb spine thickness; the slot is cut 0.4 mm wider. |

## Geometry notes

The dome is **one revolved profile** — rim edge, brim top, outer dome, flat apex ring, inner
dome, underside — so the whole shell is a single solid whose hollow opens downward. It
drains and prints without a bridge.

Two things were deliberately avoided. The crown is **never closed at the pole**: a profile
that touches the revolve axis tessellates into degenerate slivers and reads non-watertight,
so the apex is a small flat ring instead. And the dome arc is a **polyline sampled on a true
quarter ellipse**, not a three-point circular arc — a circular arc through the two ends
overshoots the stated crown rise by several per cent, and `dome_h` is a number a milliner
measures against a head.

## Print notes

Print **brim down on the plate**, dome up. The dome's outer surface is a shallow overhang
that self-supports at these proportions; the comb slots cut straight through, so they need
no bridging. 0.2 mm layers, 3 perimeters, 15 % infill. PETG or recycled PETG is the right
material — it takes the needle pressure of hand-stitching sinamay without cracking. PLA is
acceptable for a base worn once. If the comb will not slide in, raise `comb_t` one step and
reprint rather than reaming the slot, which weakens the crown wall.

Every mode exports watertight; the `pair` mode returns an assembly of two separate bases,
not a fused body.

## Hyperobject Profile

Domain `wearable`. Three CDG interfaces:

- **`trim_sew_ring`** (`flange`, parameters `base_dia`, `brim_w`, `sew_holes`, `hole_dia`) —
  the genuine sewn edge: sinamay, veiling and trim are stitched along the brim through this
  hole ring, so the brim width and the ring pattern are the dimensions the trim pattern is
  cut from. This is the FC dimensional handshake.
- **`comb_slot`** (`socket`, parameters `comb_w`, `comb_t`) — the point-fixed slot pair that
  receives a hair comb's spine. Hardware-to-hardware, not a sewn edge, so `socket`.
- **`crown_profile`** (`profile`, parameters `base_dia`, `dome_h`, `base_t`) — the silhouette
  a headwear pattern speaks in.

## Fashion Cabinet bridge

Expected FC consumers: the **fascinator** and **pillbox hat** garments, and the
**veiling / birdcage veil** and **millinery trim** notions that sew to the brim.

FC drives `base_dia` from the finished base diameter the design calls for and `dome_h` from
the crown rise; `sew_holes` and `hole_dia` follow the trim notion's stitch pattern, so the
veiling's gather spacing and the base's hole ring agree. `comb_w` / `comb_t` come from the
comb notion the wearer already owns rather than from the garment.

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "fascinator-base",
  "linked": true,
  "params_map": {
    "base_dia": "base_finished_diameter_mm",
    "dome_h": "crown_rise_mm",
    "base_t": "base_stiffness_mm",
    "brim_w": "trim_seam_allowance_mm + 4",
    "sew_holes": "round(base_finished_diameter_mm * 3.1416 / trim_stitch_pitch_mm)",
    "hole_dia": "2.0",
    "comb_w": "comb_spine_width_mm",
    "comb_t": "comb_spine_thickness_mm"
  }
}
```

The **`trim_sew_ring`** flange is what FC reads for the handshake: a change to the trim
notion's stitch pitch or seam allowance resizes the brim and re-counts the holes without
anyone retyping millimetres. The sibling **`veil-comb`** cartridge covers the case where the
veiling gathers onto a comb bar instead of onto a base brim.

`CERN-OHL-W-2.0`.
