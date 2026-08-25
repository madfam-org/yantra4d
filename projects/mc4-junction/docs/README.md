# MC4 Junction Bracket

**Solar PV connector management** — generated with **CadQuery** (B-Rep). MC4 connector
pairs are the joint every rooftop and ground-mount array is made of, and they are
almost always left dangling: mated pairs swinging in the wind, leads chafing on rail
edges, junctions that no one can trace two years later. This cartridge cradles them.

The shared interface is the **MC4 barrel** — a Ø16 mm nominal connector body — and the
**PV lead** that leaves it, 4–6 mm² cable at about Ø6.5 mm.

Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Four-Up Junction Plate** | `junction_4` | A surface-fixed plate carrying four MC4 cradles on a common pitch, with M4 mounting holes. |
| **Mated Pair Bracket** | `pair_bracket` | A block that captures one mated MC4 pair so the joint is held, not hanging. |
| **Strain-Relief Comb** | `strain_comb` | Open-top obround slots that grip PV leads on pitch, with a zip-tie channel across the back. |

## Parameters

| Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- |
| `body_d` | 16 mm | 10 – 24 | MC4 connector barrel diameter. |
| `lead_d` | 6.5 mm | 3 – 12 | PV lead outside diameter (4–6 mm² cable). |
| `clearance` | 0.4 mm | 0 – 1.0 | Printed fit. Floored at 0.02 mm internally — see below. |
| `plate_th` | 4 mm | 2.5 – 8 | Base plate thickness. |
| `wall` | 3 mm | 2 – 6 | Cradle and comb wall thickness. |
| `count` | 4 | 2 – 8 | Comb slots. |
| `pitch` | 22 mm | 14 – 40 | Centre-to-centre spacing. |

## Hyperobject Profile

- **Domain:** energy
- **CDG interfaces:** MC4 Socket (`socket` — Ø16 mm nominal barrel), PV Lead
  Passthrough (`pocket` — Ø6.5 mm nominal), M4 Mount Holes (`bolt_pattern` — Ø4.4 mm
  clearance).
- **Commons license:** CERN-OHL-W-2.0

## Field note

MC4 is a **safety-relevant** connector: mating dissimilar brands is a known arcing and
fire risk, and in most jurisdictions the connector itself must be a certified part.
Nothing here replaces a connector. These are brackets that hold certified connectors and
their leads in a defined position — the mechanical problem the certified part does not
solve.

## Fabrication notes

Two tangency traps sit in this geometry, and both are the same lesson in different
clothes: **a boolean whose surfaces land exactly on each other is not a boolean.**

### Zero clearance makes the cut tangent to the bore

A `clearance` of exactly 0 makes the cradle bore equal the cradle's own nominal
diameter, so the snap-slot cut lands tangent to the bore wall. OCCT keeps that as one
valid shell, but the tangency tessellates into a cracked, non-watertight STL. The
clearance is floored at 0.02 mm — geometrically still a press fit, kernel-wise a real
intersection.

### The mounting hole must not graze the end face

In `strain_comb` the two mounting holes were inset from the bar end by `wall`, with a
2.0 mm hole radius. At `wall = 2.0` the bore's outer edge therefore sits **exactly** on
`bar_l / 2` — tangent to the end face, and grazing the corner fillet at the same time.
The part reported `watertight=False bodies=0`: a shell torn open rather than a solid.

The bisection is worth recording, because the failure only appeared at the last step:

```
bar             wt=True  bodies=1
after slots     wt=True  bodies=1
after tie       wt=True  bodies=1
after holes     wt=False bodies=0     ← the tangency
```

The inset is now `max(wall, hole_r + fillet_r/2 + 0.8)`, which keeps real material
between the bore wall and the filleted end at every wall thickness.
