# Belt Hanger

The printable **multi-loop belt and accessory rack** — generated with **CadQuery**
(B-Rep). A vertical spine carrying a column of open hooks, topped by a rod hook
for the closet rail.

Each open hook takes one belt folded at its buckle, or a scarf, a tie, or a bag
strap, and comes off the **front** without disturbing its neighbours. That is what
an open hook does that a closed loop cannot, and it is why a rack of open hooks
stays sorted while a rack of loops does not.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

The three modes are the **same hook family re-proportioned** — same topology,
different throat, lip, pitch and section — so a rack is chosen by what it holds
rather than by hand-tuning six sliders.

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Belt Rack** | `belt` | Baseline proportions. The throat swallows a belt folded double at its buckle. |
| **Scarf Rack** | `scarf` | 35 % wider throat, shallower lip, 30 % looser pitch, lighter section — bulky but light. |
| **Tie Rack** | `tie` | Narrow throat, **taller** lip so a slippery tie cannot slide off, and a tight pitch so a dozen fit on one spine. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Hooks | `hook_count` | 6 | Open hooks on the spine. The spine grows to fit — check a 14-hook rack against your bed's Z. |
| Hooks | `strap_w` | 38 mm | Widest strap the rack must take. **20 / 25 / 38 / 50 mm** are the standard webbing and belt widths. Sizes the throat and the pitch. |
| Hooks | `hook_reach` | 34 mm | How far each hook stands off the spine. 34 clears most folded leather belts; a rolled scarf wants 50+. |
| Spine | `spine_w` | 26 mm | Spine width. Wider resists the twist a heavy belt puts on a loaded hook. |
| Spine | `spine_t` | 9 mm | Spine thickness. Sets the whole rack's bending stiffness **and** the hook arm section — raise this first if a loaded hook sags. |
| Mount | `rod_dia` | 32 mm | Rail the top hook goes over. 25 mm steel, 32 mm timber dowel; adds 1.2 mm clearance. |

## Presets

- **Leather Belts** — 38 mm × 6 hooks.
- **50 mm Webbing** — heavy section, 4 hooks.
- **Scarves and Shawls** — long reach, wide throat.
- **Ties** — 12 small hooks.

## Print notes

Print **flat on its back**: the spine lies in the XY plane with the hooks
projecting sideways, all in one plane. Every hook arm is then a horizontal slab
and every lip is a torus arc lying flat — **no supports anywhere**, and the layers
run across the hook arms rather than along them, which is the orientation where a
loaded hook resists bending instead of peeling apart.

PETG at 4 perimeters and 30 % infill for belts; the arm root is the stress
concentration and perimeters carry it, not infill. A rack of 50 mm work webbing is
genuinely heavy — raise `spine_t` to 13 mm and the rack stops feeling springy.

A rack taller than your bed's Z is not a print failure waiting to happen, it is a
sizing error: drop `hook_count` and print two racks. They hang side by side on the
same rail.

## Geometry notes

The lip is a **lower half** of a torus, not a quadrant. That is deliberate:
abutting quadrants meet along a single tangent circle, which is a coincident
surface rather than an overlap, and OCCT fuses it into a shape with a crack. A
half meets the straight arm across a full tube section.

The top rod hook is the same three-quarter-torus technique the `garment-hanger`
cartridge uses — one torus, one quadrant cut away — and it carries an extra fix
found here: seating the curl against a bare stem cylinder leaves a thin lens of
overlap whose fusion is fragile, and at the default proportions the curl detached
outright. The stem therefore carries a short **fatter collar** at the junction, so
the overlap is fat for any combination of `spine_t` and `rod_dia`.

The hook and curl are folded into the spine **one piece at a time**, never
pre-fused, because OCCT's fuse is order-sensitive on this composition.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Strap Throat** (`rail`, internal) — the open hook mouth the strap drops
    into; defined by `strap_w`, `hook_reach`, `spine_t`.
  - **Rod Hook** (`custom`, internal) — the closet-rail engagement; defined by
    `rod_dia`, `spine_t`.
  - **Hook Pitch** (`grid`, internal) — the spacing along the spine; defined by
    `hook_count`, `strap_w`, `spine_w`.

The strap **passes through** the throat rather than being sewn along an edge, so
the throat is declared `rail` — the same geometry type `belt-buckle` uses for its
strap slot — and not a flange-style edge interface. Nothing on this rack is
stitched.

## Fashion Cabinet bridge

FC notions and garments that consume this object: the **belt**, **sash**,
**scarf**, **tie** and **bag-strap** records — anything FC describes with a
finished strap width.

FC-side `hardware_ref` block on the accessory record:

```json
{
  "accessory": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "belt-hanger",
      "linked": true,
      "params_map": {
        "strap_w": "strap_width_mm",
        "hook_reach": "max(18, folded_bulk_mm * 1.4)",
        "spine_t": "max(6, strap_width_mm * 0.24)",
        "spine_w": "max(16, strap_width_mm * 0.68)"
      }
    }
  }
}
```

The accessory drives the hardware: FC's **finished strap width** sizes the
`strap_throat` interface directly — this is the same 20 / 25 / 38 / 50 mm webbing
ladder that `belt-buckle` and `strap-buckle` size their hardware from, so a belt
generated in FC and a rack generated here agree without a conversion. FC's
**folded bulk** (how thick the accessory is when doubled at its buckle) sets
`hook_reach` so the hook clears it.

`CERN-OHL-W-2.0`.
