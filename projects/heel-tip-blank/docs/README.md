# Heel Tip Blank

A printable **replacement heel top-lift** — the small wearing piece at the very bottom of a
shoe heel. Generated with **CadQuery** (B-Rep).

The heel tip is the one part of a shoe that is *designed* to be consumed: it meets the
pavement, it wears, and it is meant to be swapped. But heel-tip sizes are a manufacturer's
private grid rather than a standard, so the exact tip for a given shoe is routinely
unobtainable and a pair of otherwise sound shoes gets thrown out over a two-gram part. This
cartridge is the blank you size to the heel in your hand.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Round Tip** | `round` | The round tip — stiletto, dress heel, round block heel. Sized by `tip_w` alone. |
| **Square Tip** | `square` | The square tip with radiused corners — louis heel, cuban heel, boot top-lift. Uses `tip_w` × `tip_l`. |
| **Round + Square Set** | `set` | One of each on a plate, for sizing a pair by eye before committing. |

## Parameters

| Group | Parameter | Default | Range | Modes | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Tip Profile | `tip_w` | 11.0 mm | 5–40 | all | Seat width (round mode: seat diameter). Stiletto 7–11 mm, block heel 20–35 mm. |
| Tip Profile | `tip_l` | 11.0 mm | 5–40 | square, set | Seat length, front to back. Square mode only. |
| Tip Profile | `tip_h` | 6.0 mm | 2–20 | all | Seat face to ground face. Dress tip 5–8 mm, boot top-lift 8–14 mm. |
| Tip Profile | `taper` | 0.9 | 0.6–1.0 | all | Ground face size ÷ seat face size — the moulded draft. 0.85–0.92 for most dress heels. |
| Tip Profile | `corner_r` | 2.0 mm | 0.3–12 | square, set | Square-tip corner radius; match the heel's own corner. |
| Pin | `pin_dia` | 3.2 mm | 1.2–6.0 | all | Center bore for the steel pin. Standard dress-heel pin 3.0–3.4 mm. Auto-clamped to keep a wall. |
| Pin | `pin_depth` | 0.0 mm | 0–16 | all | **0 = through bore.** Any other value drills blind up from the seat so the wearing face stays solid. |
| Finish | `edge_ch` | 0.6 mm | 0–2.5 | all | Chamfer around the ground face. Keeps the tip off grating edges and gives it margin to wear. |

## Matching a worn tip

Pull the old tip with pliers (it is a friction-fit pin, not glue) and measure the **seat**,
not the ground face — the ground face is already worn undersize and out of round. Set
`tip_h` to the *original* height, not what is left of it: printing taller changes the heel
pitch and the whole shoe walks differently. If the old tip's pin sheared and stayed in the
heel, drive it out from inside the heel cavity before fitting the new one.

`pin_depth` is the choice worth thinking about. A **through bore** (0) lets the pin head sit
flush on the ground face and lets the hole drain, which is what most factory dress tips do.
A **blind bore** leaves the wearing face solid, so the tip wears longer before anything
metal touches pavement — better on a boot top-lift where the tip is thick enough to afford
the material.

## Print notes

Print **ground face down**, seat up — no supports, and the wearing surface gets the smooth
bed finish, which is exactly the face you want dense. Use a **tough** filament: PETG at
0.12 mm layers, 6 perimeters, 60 % infill is the realistic minimum, and TPU 95A at 100 %
infill wears far better and is quieter on hard floors. PLA will crack off a heel within a
week of real walking — do not.

Roughen the pin with a file before pressing it in so the printed bore grips, and press it
in with a vise rather than hammering it.

Every mode exports watertight. The wearing chamfer is a **loft section**, not a `.chamfer()`
call — chamfering a tapered loft's bottom edge loop is unreliable and was observed to split
the solid at low `tip_h`, so it is built into the loft instead. Both loft ends are flat
closed sections; nothing lofts to a point and there are no sphere caps. The bore overshoots
its faces, so a through bore drains and a blind bore opens upward.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Heel Seat Face** (`profile`, internal) — the footprint that meets the heel's bottom,
    defined by `tip_w`, `tip_l`, `corner_r`, `taper`. Not a sewn edge: this hardware is
    pin-fixed into a heel block, so it is a profile match, not a flange.
  - **Steel Pin Bore** (`socket`, internal) — the bought-pin interface, defined by
    `pin_dia`, `pin_depth`, `tip_h`.

## Fashion Cabinet bridge

Expected FC consumers: **heeled shoes, pumps and boots** — any FC footwear item whose
heel-tip notion needs a wearing piece, plus **repair and refurbishment** entries that
specify a replacement top-lift as a serviceable part rather than a fixed component.

FC-side `hardware_ref` block on the heel-tip notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "heel-tip-blank",
      "linked": true,
      "params_map": {
        "tip_w": "heel_base_w_mm",
        "tip_l": "heel_base_l_mm",
        "tip_h": "heel_top_lift_h_mm",
        "taper": "0.90",
        "pin_dia": "3.2",
        "pin_depth": "0",
        "corner_r": "heel_base_corner_r_mm",
        "edge_ch": "0.6"
      }
    }
  }
}
```

The mating geometry is sized by **`tip_w`, `tip_l` and `corner_r`** — the seat profile that
has to match the heel block's bottom face exactly, since any overhang catches and any
undersize exposes the heel to wear — with **`tip_h`** setting the heel pitch. The FC
footwear item's heel-base dimensions are the driving values; `pin_dia` comes from the pin
standard, not the garment.

`CERN-OHL-W-2.0`.
