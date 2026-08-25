# Worm & Wheel Set

A **high-reduction, potentially self-locking right-angle drive** — generated with
**CadQuery** (B-Rep). The worm is a trapezoidal Acme-style thread swept along a genuine
`makeHelix` (DIN 3975); the wheel is a helical spur gear cut to the worm's lead angle,
with flanks sampled from the true involute of the base circle.

The functional interface is the **DIN 3975 worm pair**: module, starts, pressure angle
and the lead angle they imply. A worm from this cartridge drives a wheel from the
worm-gear family that shares module and starts.

Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Worm Screw** | `worm` | Single- or multi-start worm, squared ends, axial bore. |
| **Worm Wheel** | `wheel` | The mating wheel — a helical spur gear at the worm's lead angle. |
| **Meshing Demonstrator** | `mesh_demo` | Worm and wheel meshing at 90°, both fused to one base bracket so the set prints as a single connected body. |

## Parameters

| Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- |
| `m` | 1.5 mm | 0.5 – 3.0 | Module — the mesh currency. |
| `starts` | 1 | 1 – 3 | Thread starts. More starts raise the lead angle and cost self-locking. |
| `worm_dia` | 14 mm | 6 – 30 | Worm pitch diameter. |
| `worm_turns` | 2.5 | 1.0 – 4.0 | Visible turns; the worm is never shorter than four axial pitches. |
| `teeth` | 30 | 15 – 80 | Wheel teeth. Reduction ratio is `teeth ÷ starts`. |
| `pressure_angle` | 20° | 14.5 – 25 | Involute pressure angle. |
| `thickness` | 9 mm | 4 – 20 | Wheel face width. |
| `worm_bore` | 5 mm | 0 – 12 | Worm shaft bore; 0 leaves it solid. |
| `wheel_bore` | 6 mm | 0 – 16 | Wheel shaft bore. |
| `flank_pts` | 8 | 4 – 14 | Involute samples per flank. |

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:** Worm Pair Lead (`thread` — DIN 3975), Involute Tooth Form
  (`profile` — ISO 53 / DIN 867), Shaft Bore (`socket`).
- **Commons license:** CERN-OHL-W-2.0

## Approximation note

A truly **throated (globoid)** wheel hugging the worm is not modelled — that needs an
enveloping cut and is very heavy. The wheel here is a helical spur gear set to the
worm's lead angle: correct pitch, module and hand of helix, meshing on a line rather
than over an arc. This is the standard maker-scale approximation, adequate for
light-duty drives.

## Fabrication notes

Three traps in this cartridge are worth carrying to any swept-thread geometry.

### The swept profile must use ABSOLUTE radii

The thread profile was written relative to the pitch radius and then translated out to
it:

```python
prof = cq.Workplane("XZ").polyline([(r_root - rp_worm, ...), ...]).close()
prof = prof.translate((rp_worm, 0, phase))     # ← silently discarded
```

`sweep(isFrenet=True)` re-frames the profile onto the helix's own moving frame, which
throws that translation away. The rib was therefore swept at radius `r_out - rp_worm`
about the **axis** instead of about the pitch cylinder — that is, entirely buried inside
the root cylinder. Every worm rendered as a **bare cylinder**, watertight and
single-bodied and completely unthreaded.

The giveaway was a face count of exactly **1008 regardless of module or starts**. A real
thread's tessellation varies with both; a constant means the thread is not there. This
is the failure mode to fear most: it passes every watertightness check while producing
the wrong object. Absolute radii, matching the thread helper used elsewhere in the
commons, put the rib where DIN 3975 wants it.

### Clip each start BEFORE fusing it

Multi-start worms failed in every arrangement — `Null TopoDS_Shape`, two bodies, or a
torn shell — as long as the ribs were fused first and the ends squared afterwards. The
overhanging run-out spirals hang outside the blank while the union runs, and OCCT
returns garbage. Intersecting **each** rib with the finished length band first means
every fuse is core-plus-one-buried-rib, which is well conditioned:

```python
worm = worm.union(thread.intersect(band))     # not: union all, then intersect once
```

Two smaller notes in the same loop: the profile must be rebuilt on every pass, because
`sweep()` consumes the Workplane's pending wires (a hoisted profile raises "No pending
wires present" on the second start); and the rib's inner edge is sunk well inside the
root cylinder rather than a hundredth of a millimetre in, because a rib that merely
touches the core is a tangency and the two come apart.

### Relieve the dedendum, do not rewrite the module

A coarse module on a thin worm drives the root radius toward the axis until the swept
rib wraps back on itself. The tempting fix — clamp the module — silently breaks the DIN
3975 mesh contract with the wheel the user is pairing it with. Instead the **dedendum**
is shortened so the root cylinder keeps at least 45 % of the worm radius. Module, pitch
and lead all stay exactly as asked; only the depth of the root relief is trimmed on the
thinnest worms, which is what a machinist would do anyway.

### The demonstrator's posts must clear the tooth tips

In `mesh_demo` the posts and bridge live at `y = 0`, where the worm axis is; standing
them off at the plate edge left the bridge floating beside the worm and the worm came
out as a second body. The bridge's top face is sunk into the worm's **measured**
underside — derived estimates sit millimetres low, because the worm's real radius is the
thread root and its ends are squared by intersection.

The posts then have to stand entirely outside the wheel's tip circle. A post that merely
overlaps the tips shears little crescents off them, and those slivers survive as extra
bodies — the mode reported `bodies=3` with two 20-face fragments at the tooth radius.
The base plate is sized **after** the posts so it always reaches under them.
