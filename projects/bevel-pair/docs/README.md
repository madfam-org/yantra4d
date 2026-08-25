# Bevel Gear Pair

A **right-angle bevel gear set** — generated with **CadQuery** (B-Rep). A pinion, its
mating gear, and a demonstrator that fuses both onto one L-bracket so the roll can be
printed and held. Tooth flanks are the true involute of the base circle, lofted toward
the pitch-cone apex so the teeth taper the way a real bevel does (ISO 23509).

The functional interface is the **ISO 23509 pitch cone**: module, pressure angle, tooth
count and shaft angle. A pinion from this cartridge meshes a gear from anywhere in the
bevel family that shares module and shaft angle — it grows that family rather than
standing alone.

Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Pinion** | `pinion` | The small (drive) bevel — solid back hub, axial bore. |
| **Mating Gear** | `gear` | The mate: equal teeth for a 1:1 miter, or `ratio`× teeth for a reduction. Same module and shaft angle. |
| **Meshing Demonstrator** | `mesh_demo` | Pinion and gear meshing at the shaft angle, both fused to one L-bracket so the set prints as a single connected body. |

## Parameters

| Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- |
| `m` | 1.5 mm | 0.5 – 3.0 | Module — the mesh currency. Two gears mesh only at equal module. |
| `teeth` | 16 | 10 – 40 | Pinion tooth count. |
| `ratio` | 1.0 | 1.0 – 3.0 | Gear teeth ÷ pinion teeth. 1.0 is a miter pair. |
| `pressure_angle` | 20° | 14.5 – 25 | Involute pressure angle; 20° is the modern default. |
| `shaft_angle` | 90° | 60 – 120 | Angle between the two shafts. 90° is the classic bevel. |
| `face_width` | 8 mm | 3 – 20 | Tooth length along the cone; capped at 85 % of the cone distance so the small end stays off the apex. |
| `back_height` | 5 mm | 2 – 14 | Back hub height behind the teeth. |
| `bore` | 4 mm | 0 – 12 | Shaft bore; 0 leaves it solid. |
| `flank_pts` | 7 | 4 – 12 | Involute samples per flank — higher is smoother and slower. |

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:** Involute Tooth Form (`profile` — ISO 53 / DIN 867), Bevel Pitch
  Cone (`surface` — ISO 23509), Shaft Bore (`socket`).
- **Commons license:** CERN-OHL-W-2.0

## Approximation note

Exact spherical-involute (octoid) flanks are **not** modelled. Each tooth is the planar
involute of the back cone, linearly scaled toward the apex — the classic **Tredgold
approximation**. Pitch cone, module and tooth count are dimensionally correct; this is
adequate for maker-scale right-angle drives, not for precision spiral-bevel metrology.

## Fabrication notes

Each bevel is a single loft from the closed involute wire at the large end to a scaled
copy at the small end, unioned with a back hub extruded from **the same large-end
wire**. Using a plain circle for the hub instead leaves a tangent seam that tessellates
non-watertight at wide shaft angles. Bores are cut straight through so they vent both
faces.

### `.located()` is a Shape method, not a Workplane method

`mesh_demo` shipped unrenderable, and the reason is worth recording because the error
message points at the symptom rather than the cause:

```
AttributeError: 'Workplane' object has no attribute 'located'
```

Relocating the tilted gear was written as `gear.located(loc)`. `Workplane` has no such
method — `located` belongs to `Shape`. The fix is to take the solid out, relocate it,
and wrap it back up:

```python
gear_m = cq.Workplane("XY").newObject([gear.val().located(loc)])
```

Every single parameter case failed identically, which is the signature of a plain API
error rather than a geometry one: a kernel problem varies with the numbers, an
attribute error does not.

In `mesh_demo` the two gears **overlap** a solid bracket, so the union is volumetric and
yields one body — there is no floating meshing assembly. The gears are printed
pre-meshed as a static demonstrator of the pitch cones, not as a free-spinning pair.
