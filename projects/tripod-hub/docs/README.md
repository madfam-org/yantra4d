# Universal Tripod Hub

A **capstone multi-standard hub** — generated with **CadQuery** (B-Rep). It bridges the
three interfaces every photo, video and optics rig is built around but which never all
meet in one part: the **1/4"-20 UNC** camera screw, the **3/8"-16 UNC** heavy-mount
screw, and the **Arca-Swiss 38 mm** quick-release dovetail. Each mode fuses at least two
of them, so a rig built on one standard bolts onto another.

Threads are real geometry, not cosmetic grooves: trapezoidal ribs swept along a genuine
`makeHelix` and fused into the wall or shaft, cut to nominal UNC dimensions.

| Standard | Major Ø | Pitch | Minor Ø |
| :--- | ---: | ---: | ---: |
| 1/4"-20 UNC | 6.35 mm | 1.27 mm | 4.976 mm |
| 3/8"-16 UNC | 9.525 mm | 1.5875 mm | 7.749 mm |
| Arca-Swiss | 38.0 mm platform | ~45° flanks | ~9.0 mm block |

Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Distribution Hub Plate** | `hub_plate` | Arca dovetail underside, a central 3/8-16 socket, and a ring of 1/4-20 sockets — mount a cluster of accessories on one Arca head. |
| **Arca Plate with 1/4-20 Stud** | `quarter_to_arca` | An Arca dovetail carrying a real male 1/4-20 stud: an Arca head now drives any 1/4-20 device. |
| **3/8-16 to 1/4-20 Reducer** | `reducer_bushing` | The classic camera thread reducer — external male 3/8-16, internal female 1/4-20, hex wrench flange. |

## Parameters

| Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- |
| `plate_w` | 60 mm | 30 – 100 | Plate width. The socket ring is fitted inside it. |
| `plate_h` | 9 mm | 6 – 16 | Arca dovetail block height. |
| `n_quarter` | 6 | 2 – 10 | 1/4-20 sockets in the ring. |
| `ring_dia` | 40 mm | 16 – 90 | Bolt-circle diameter; clamped to keep every socket on the plate. |
| `thread_len` | 8 mm | 4 – 16 | Stud height / socket depth, bounded by the material available. |
| `clearance` | 0.35 mm | 0 – 0.8 | Printed-thread fit, per side. |
| `turns` | 4.0 | 1.5 – 4.5 | Requested engagement turns; snapped to a half-integer. |

## Hyperobject Profile

- **Domain:** consumer
- **CDG interfaces:** Arca-Swiss Dovetail (`profile`), 1/4"-20 UNC Thread (`thread`),
  3/8"-16 UNC Thread (`thread`).
- **Commons license:** CERN-OHL-W-2.0

## Fabrication notes

Threads are volumetric fused helical ribs with the root buried in the surrounding
material. Turn counts are snapped to a **half-integer** (`floor(n) + 0.5`) because an
integer count degenerates the OCCT helical sweep to a null body. Studs and dovetails
attach on closed faces, never on an open thread rim.

Four further traps were found while bringing this cartridge to watertight, and each one
is a rule with wider reach.

### The dovetail is a feature under the plate, not the plate

`hub_plate` used the bare Arca bar as its body. That caps the work surface at the
dovetail's **narrow top** — 38 mm — so at the default `plate_w = 60`, `ring_dia = 40`
the socket ring sat at r = 20 while the platform only reached x = ±19. Every socket in
the ring was bored through thin air, and the dangling rib fragments are what returned
`Null TopoDS_Shape` from the fuse. All fifteen `hub_plate` cases failed.

A real slab of `plate_w` now carries the ring and the dovetail hangs beneath it, which
is also how an actual Arca plate is made. The ring radius is additionally clamped so
each socket keeps a real ligament to the plate edge and stays clear of the central
3/8-16 socket.

### The rib must fit inside the hole it threads

`half_int_turns` snaps **up** to the next half turn. A socket whose depth falls just
under a half-integer multiple of the pitch therefore gets a thread taller than the hole:
the surplus spiral sticks out of the closed bottom into solid plate, and each buried end
tears off as its own body. The turn count is now trimmed **down** to what the depth can
actually hold — still to a half-integer, never to a whole one.

A socket too shallow for even half a turn legitimately has no rib left. That is reported
as `None` rather than an empty Workplane, so the caller skips the union instead of
raising *"must have at least one solid on the stack to union"*. A plain unthreaded pilot
bore is the honest result.

### Deep sockets stop fusing — cap the slab

Past a socket depth of roughly **5.7 mm**, the ring's ribs stop fusing into the plate and
survive as separate bodies. This is not a modelling error: probing the plate showed solid
material at all six socket sites, identical rib overlap at working and failing depths,
and no change from widening the overlap to 1.0 mm. It is kernel behaviour at that size.

Rather than ship a parameter range that silently produces six pieces, the slab is capped
at 7.2 mm — a 5.7 mm socket, which is more than four turns of 1/4-20 and far more
engagement than any tripod fitting uses. `plate_h` still varies the dovetail as
documented; it just stops driving the socket deeper than the kernel will fuse.

### A reducer cannot carry a sloppy fit on both threads at once

In `reducer_bushing` the 3/8-16 male thread **shrinks** with clearance while the 1/4-20
female bore **grows** with it, so the two march toward each other. At `clearance = 0.8`
the shaft radius is 3.37 mm and the bore radius 3.98 mm — the bore is wider than the
shaft it sits inside, and the wall is **−0.6 mm**. That is not a bushing, and the
boolean returns torn shells. The clearance used for this mode is stepped back until a
0.6 mm ligament survives.

The clearance is also **floored** at 0.15 mm. At a true zero the male thread grows to
its full nominal major diameter at the same moment the female bore shrinks to its own,
and the socket's rib stops fusing into the shaft — the part comes back as the bushing
plus a loose thread coil rattling inside it. A printed thread needs some fit allowance
regardless; 0.15 mm is the tightest this geometry builds and is still a firm press fit.

Separately, `male_stud` sizes itself from its own half-integer turn count, so the real
top of the shaft is `stud_top` — **not** `body_h`, which is derived from `thread_len`
and runs well ahead of it. At `thread_len = 16` the socket was bored 16 mm down into a
9.5 mm stud and ran straight out of the bottom, taking the closed base with it. The
socket depth is now bounded by the shaft that actually exists.

### Never drill coaxially through a finished thread

The clearance hole is drilled into **every component before any helical rib is fused
on** — into the stud's plain core inside `male_stud`, and into the hex flange before it
is unioned. Cutting the same cylinder through the completed part instead is a boolean
OCCT does not converge on:

```
male_stud     5.9s
flange        0.9s
socket_cut    0.5s
cut socket    0.4s
cut thru      … no result at 400 s
```

The mode **hung** rather than failing, which is considerably worse than an error — a
timeout gives no shape to inspect and no exception to read, and it looks identical to a
slow render. Reordering so the cut only ever meets prismatic material takes the same
hole from unbounded to milliseconds.

The wrench flange is likewise unioned on before the socket is bored. Cutting the vent
and then unioning a flange across its mouth re-closes the hole from outside and leaves
interior faces the tessellator reports as torn. The result is one clean cylinder running
the length of the piece — the only through-void in it.
