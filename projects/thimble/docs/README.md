# Thimble

A 3D-printed **closed-top tailor's thimble with a debossed grip surface** — generated with
**CadQuery** (B-Rep). The domed cap that rides the middle finger and drives a hand needle
through heavy cloth without piercing the fingertip, sized from a measured `finger_girth`
instead of a coarse retail size run.

Part of the **Yantra4D Hyperobjects Commons** (an atelier-tools shelf finding).
Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part |
| :--- | :--- |
| **Single Thimble** | `thimble` |
| **Size Run (3)** | `set` |

`set` lays out three thimbles at `finger_girth`, `+4 mm`, and `+8 mm` — print the run, keep
the one that fits, and the two others are the sizes you lend out.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:** Finger Bore (`socket`) and Needle Seat (`surface`). The bore is a
  point-fitted body interface, not a sewn edge, so it is a `socket` — the Fashion Cabinet
  handshake couples a measured finger circumference to it.

## Fabrication notes

The shell is a **revolved wall profile**, not a cylinder unioned with a sphere cap — that
seam cracks. The grip dimples are **debossed** (cut in) so the needle eye seats in a pocket
instead of skating off a bump, and they are batched into one compound cutter and subtracted
in a single boolean; cutting several hundred spheres one at a time is correct but takes
minutes instead of seconds.

Two watertightness rules are baked into the numbers here, both found the hard way on this
part:

- **Circumferential pitch is 3.2 × dimple diameter.** At a tighter 2.6 × pitch, adjacent
  spherical pockets intersect each other and leave knife-edge webs that OCCT cannot stitch —
  the mesh reads as dozens of zero-volume bodies.
- **The crown seat is a revolved dish with a small flat across the axis, not a sphere.** A
  sphere centred on the revolve axis puts its own pole on that axis and meshes as a
  degenerate zero-area triangle.

Dimple depth is clamped to `wall_t × 0.55`, so a pocket can never breach into the finger
bore. Prints open-end-down with no supports. `CERN-OHL-W-2.0`.

## Fashion Cabinet bridge

Fashion Cabinet garments that specify hand-finishing consume this: **hand-picked lapels and
collars** on tailored jackets, **felled hems** and **hand-sewn linings**, and any pattern
whose construction notes call for a **hand-worked buttonhole** or **bar tack**. The mating
dimension is `finger_girth` — the same body circumference measure FC already carries for
glove and cuff fits, so a maker's stored hand measurements size their thimble directly.
`wall_t` and `thimble_h` follow as fit tuning, and `dimple_dia` couples to the needle gauge
the garment's construction spec names.
