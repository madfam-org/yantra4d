# Hydroponic Net Cup Lid

**Reservoir lids and collars for hydroponics** — generated with **CadQuery** (B-Rep).
Kratky and deep-water culture are the cheapest routes to reliable food from a small
footprint: a bucket, water, nutrient and a lid. The cup is standardised, the bucket is
whatever you have, and the lid between them is the only part with no standard at all —
so growers hole-saw tote lids by hand, and a cup that sits crooked drops its plant.

The shared interface is the **net-cup rim seat**: a 2" cup seats in a ~50 mm hole, a 3"
cup in a ~76 mm hole, with a counterbore the cup's lip rests on so it hangs flush.

Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Single-Hole Bucket Lid** | `single_lid` | A round lid with a locating skirt that drops onto a bucket or tote. |
| **Multi-Hole Raft** | `multi_lid` | A rectangular Kratky / DWC raft on a `cols` × `rows` grid. |
| **Retrofit Hole Collar** | `hole_collar` | A stepped grommet collar that adapts a hole in a lid you already own. |

## Parameters

| Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- |
| `hole_dia` | 50 mm | 20 – 110 | Rim seat hole — 50 mm for a 2" cup, 76 mm for a 3". |
| `lip_seat` | 3 mm | 1.5 – 10 | Counterbore ledge the cup lip rests on. |
| `lid_thick` | 4 mm | 2 – 10 | Slab thickness; thicker carries more plants without sagging. |
| `lid_dia` | 120 mm | 60 – 300 | Round lid outer diameter — match your vessel mouth. |
| `skirt_h` | 12 mm | 4 – 40 | Locating skirt depth, or how deep the collar drops in. |
| `wall` | 3 mm | 1.6 – 8 | Skirt or grommet-tube wall thickness. |
| `cols` | 3 | 1 – 6 | Raft holes across. |
| `rows` | 2 | 1 – 6 | Raft holes along. |

A manifest constraint enforces `lid_dia > hole_dia + 2 × lip_seat + 10`, so the lid is
always wider than the hole it carries plus its seat and rim.

## Hyperobject Profile

- **Domain:** agriculture
- **CDG interfaces:** Net-Cup Rim Seat (`socket` — 2" Ø50 mm and 3" Ø76 mm), Vessel Rim
  Locating Skirt (`rail`), Raft Hole Grid (`grid` — Kratky / DWC spacing).
- **Commons license:** CERN-OHL-W-2.0

The rim seat is the handshake with the companion **`net-cup`** cartridge: a cup printed
there drops into a lid printed here at the same `hole_dia` and `lip_seat`.

## Material note

This part sits in standing nutrient solution in the light, often outdoors, for the whole
length of a grow. PLA hydrolyses and goes brittle in exactly those conditions. PETG or
PP is the appropriate choice, and recycled stock is well suited here — the manifest's
`recycled_material_toggle` says so deliberately. Opaque material also matters for a
second reason: light reaching the reservoir is what grows algae in it.

## Fabrication notes

This cartridge rendered watertight at defaults and at every parameter extreme on the
first verification pass — all three modes, 35 cases, with no kernel intervention.

The geometry earns that by construction. Every hole is a **through** cut that vents both
faces, so there is no trapped void anywhere in the part. The counterbore is a second,
shallower through-cut coaxial with the first rather than a pocket, which keeps the step
between them a clean annular face. The locating skirt is unioned to the lid with real
overlap into the slab rather than butted against its underside — a butt joint there is
the tangency that would tear the mesh, and it is the same failure that had to be fixed
by hand in several of the geared cartridges landed alongside this one.

Ordering does the rest of the work: the blank is **filleted first**, on its clean outer
edges, before any hole exists. Filleting after the holes are cut asks the kernel to
round edges that now intersect the bores, which is where fillet operations usually fail.
Within each cell the counterbore is cut before the through-hole, so both cutters always
open to a face rather than terminating inside material.
