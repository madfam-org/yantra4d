# Shoe Horn

The printable **classic curved shoe horn** — generated with **CadQuery** (B-Rep). A blade
that slides between a heel and a shoe's heel counter so the foot glides in without the
counter folding under.

Folding a heel counter once is what kills a dress shoe. The crease never comes out, the
counter stops standing up, and the shoe stops holding the heel — after which the whole
upper works loose. The tool that prevents that costs almost nothing to make.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Short (pocket / travel)** | `short` | Hand-length horn with a tight curve that hugs a dress-shoe counter. |
| **Long (standing / accessible)** | `long` | The long-handled horn used standing up — no bending. `horn_len` is raised to at least 380 mm and `curve_deg` capped at 40° so it still reaches the floor. |
| **Short + Long Set** | `set` | One of each on a plate — two separate bodies. |

The long mode is the one that matters most. It lets someone with limited hip, knee or back
mobility put on their own shoes standing up, which is the difference between dressing
independently and waiting for help.

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Blade | `horn_len` | 190.0 mm | 90–620 | Length along the curved spine. Pocket 120–200 mm, standing 400–600 mm. |
| Blade | `scoop_w` | 42.0 mm | 14–80 | Width at the heel scoop. 38–46 mm suits most adult shoes. Auto-raised above `handle_w`. |
| Blade | `blade_t` | 3.4 mm | 1.8–8.0 | Thickness at the handle; the blade tapers ~35 % thinner toward the scoop. |
| Curve | `curve_deg` | 62.0° | 15–110 | Total spine turn. Tighter hugs a dress counter; flatter reaches further. |
| Curve | `sections` | 14 | 8–28 | Loft cross-sections. Raise for a long horn's smoother curve. |
| Handle | `handle_w` | 16.0 mm | 8–40 | Width at the handle end. Wider is easier with a weak grip. |
| Handle | `hang_hole` | 6.0 mm | 0–14 | Hole through the handle for a lace or hook. **0 = plain handle.** Auto-clamped to half `handle_w`. |

## Sizing it for a hand and a shoe

Two dimensions do the real work. **`scoop_w`** should be a little narrower than the inside
of the shoe's heel counter — too wide and the horn will not go in, too narrow and it digs a
line into the counter lining instead of spreading the load. **`curve_deg`** should roughly
match the counter's own curve; a boot counter is nearly straight and wants 30–45°, a dress
pump is much rounder and wants 70–90°.

For a weak or arthritic grip, raise `handle_w` to 22–28 mm and `blade_t` toward 5 mm — the
thicker handle is far easier to hold than a thin blade, and on a long horn the extra
thickness is what keeps it from snapping when leaned on.

## Print notes

Print **lying on its side, blade flat to the bed**, which is how the geometry arrives — the
curve lies in the XZ plane, so the whole blade is self-supporting with no bridging and needs
no supports. PETG at 0.2 mm layers, 3 perimeters, 25 % infill for a short horn; for a long
horn raise to 4 perimeters and 35 % and print it in PETG or nylon, **not PLA** — a long horn
is a lever and PLA snaps at the handle root. A long horn may exceed a small printer's bed
diagonal; check `horn_len` against your machine before committing.

Sand the scoop's leading edge smooth before use. A print's layer lines will scuff a lining
over time; two minutes with 400 grit fixes that permanently.

Every mode exports as a single watertight solid. The blade is **one loft** through a stack
of closed rounded-rect wires marched along the spine — both end sections are flat closed
wires, so there are no sphere caps and nothing lofts to a point. Because the loft is the
entire body, nothing is ever extruded off a loft face via `toPending`. The hang hole is a
single cylinder cut normal to the blade face, overshooting both faces so it drains.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Heel-Counter Scoop** (`profile`, internal) — the working face that goes between heel
    and counter, defined by `scoop_w`, `blade_t`, `curve_deg`. Not a sewn edge: the horn is
    a hand tool that contacts a shoe, so it is a profile match, not a flange.
  - **Hang Point** (`socket`, internal) — the lace or hook hole, defined by `hang_hole`,
    `handle_w`.

## Fashion Cabinet bridge

Expected FC consumers: **dress shoes, pumps, loafers and boots** — any FC footwear item
whose care-and-fitting notion specifies a shoe horn — plus **dressing-aid** and
**accessible-dressing** kits, where the long mode is the actual product. Sibling
`dressing-aid` covers reachers and button hooks; this covers the footwear half.

FC-side `hardware_ref` block on the footwear care/fitting notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "shoe-horn",
      "linked": true,
      "params_map": {
        "horn_len": "fitting_reach_mm",
        "scoop_w": "heel_counter_inside_w_mm - 4",
        "blade_t": "3.4",
        "curve_deg": "heel_counter_curve_deg",
        "handle_w": "grip_width_mm",
        "hang_hole": "6.0",
        "sections": "14"
      }
    }
  }
}
```

The mating geometry is sized by **`scoop_w` and `curve_deg`** — together they are what has
to fit inside the FC footwear item's heel counter without binding or digging in — with
**`blade_t`** setting how much clearance the counter has to give. The footwear item's
heel-counter inside width and curve are the driving dimensions; `horn_len` and `handle_w`
come from the user's reach and grip, not from the shoe.

`CERN-OHL-W-2.0`.
