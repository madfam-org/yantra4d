# Shoe Tree

The printable **one-piece compliant shoe tree** — generated with **CadQuery**
(B-Rep). A toe form that fills the vamp, a flat-spring shank that stores the
preload, and a heel pad that presses back into the counter.

A commercial cedar tree is a two-piece toe block riding on a sprung steel
spindle. That assembly cannot come off a print bed as one solid, so this cartridge
does what a printed part does well instead: **the spring is the shank** — a wide,
thin ribbon of material bending in its elastic range.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Solid Tree** | `solid` | The plain one-piece tree. |
| **Vented** | `vented` | The same with through-vents bored across the toe form, so a damp shoe dries through the tree rather than around it. |
| **Pair** | `pair` | A left and a right laid out side by side on one plate, as two separate bodies. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Shoe | `shoe_len` | 270 mm | Inside length, toe to heel. EU 42 ≈ 270, EU 38 ≈ 245, EU 34 ≈ 215. Measure the **insole**. |
| Shoe | `ball_w` | 98 mm | Width across the ball — the widest point of the last, reproduced ~30 % back from the toe. Clamped to 48 % of the length. |
| Shoe | `toe_h` | 40 mm | Toe-box internal height. Dress oxford 35–42, boot 55–70. This is what pushes the vamp creases out. |
| Shoe | `heel_h` | 52 mm | Heel pad height. Match the counter so the pad bears on the stiffened back seam, not the soft collar. |
| Spring | `shank_t` | 4.0 mm | Flat-spring ribbon thickness — the single number that sets how hard the tree pushes. Clamped at 2.4 mm minimum. |
| Venting | `vent_rows` | 3 | Rows of through-vents (vented / pair only). |

## Presets

- **Men's Oxford** — EU 42, vented.
- **Women's Pump** — EU 38, lighter spring.
- **Work Boot** — EU 45, 62 mm toe box, heavy spring.
- **Child Pair** — EU 34, both shoes on one plate.

## Print notes

Print **flat on the bed**, the tree lying on its side with the last profile in the
XY plane. The shank's layers then run **along** its bending axis, which is the
only orientation a printed flat spring survives — printed standing up, the ribbon
is a stack of layers loaded in peel and it splits on the first insertion.

PETG is the material: it takes the repeated strain without the creep PLA shows
when a tree is left under load for weeks, which is exactly how a shoe tree is
used. 3–4 perimeters, 20–25 % infill; the shank is thin enough that it is
effectively solid at any infill.

Tune the spring with `shank_t` alone. If the tree pushes so hard it distorts the
counter, drop it 0.4 mm and reprint; if it rattles, raise it. Do not compensate by
lengthening the tree past the measured insole — an over-long tree stretches the
upper permanently, which is the failure the tree exists to prevent.

The vents in `vented` cut clean through both faces. There are **no sealed
pockets** anywhere in this part, deliberately: a sealed void in a shoe tree is a
moisture trap.

## Geometry notes

Both the toe form and the heel pad are single `loft` operations over a chain of
rounded-rect sections pushed onto one workplane — a stack of unions would leave
internal seams. The three sub-solids overlap along X by 3 % of the shoe length,
and they are folded in **one at a time** (`toe.union(shank).union(heel)`) rather
than pre-fusing the shank to the heel, since OCCT's fuse is order-sensitive on
chained lofts.

`pair` combines the two mirrored trees as a `cq.Compound`, never as a `.union()`
of non-touching solids.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Last Profile** (`profile`, internal) — the toe-form section chain; defined
    by `shoe_len`, `ball_w`, `toe_h`.
  - **Counter Pad** (`surface`, internal) — the heel bearing face; defined by
    `heel_h`, `ball_w`, `shoe_len`.
  - **Spring Shank** (`custom`, internal) — the compliant preload ribbon; defined
    by `shank_t`, `shoe_len`, `ball_w`.

No flange-style edge interface is declared: nothing is sewn or threaded along an
edge of a shoe tree. It bears on the shoe's inside surfaces, which is what the
`profile` and `surface` interfaces express.

## Fashion Cabinet bridge

FC garments that consume this object: the **footwear** records — `shoe`, `boot`,
`pump`, `loafer` — as care hardware rather than as a construction notion.

FC-side `hardware_ref` block on the footwear record:

```json
{
  "footwear": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "shoe-tree",
      "linked": true,
      "params_map": {
        "shoe_len": "insole_length_mm",
        "ball_w": "last_ball_girth_mm / 3.1",
        "toe_h": "toe_box_height_mm",
        "heel_h": "counter_height_mm",
        "shank_t": "min(9, 2.4 + upper_weight_g / 90)"
      }
    }
  }
}
```

The garment drives the hardware: FC's **insole length** and **last ball girth**
size the `last_profile` interface, its **counter height** sizes `counter_pad`, and
its **upper weight** — a proxy for how stiff the upper is — sets `shank_t` on the
`spring_shank` interface, so a heavy boot gets a stiffer spring than a pump.

`CERN-OHL-W-2.0`.
