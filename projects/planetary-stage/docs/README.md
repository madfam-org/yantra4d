# Planetary Gear Stage

An **epicyclic reduction stage** — generated with **CadQuery** (B-Rep). Sun, planet and
internal ring, all cut to the same module and pressure angle so the three actually mesh
as a set. Flanks are the true involute of the base circle, not a circular approximation.

The functional interface is the **epicyclic tooth-sum constraint**: `ring = sun + 2 ×
planet`. Any sun and planet from this cartridge that satisfy it will run inside the
matching ring, and a gear from elsewhere in the involute family meshes on shared module
and pressure angle.

Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Sun Gear** | `sun` | Central external gear with a shaft bore. |
| **Planet Gear** | `planet` | External gear with a bearing bore; three or more orbit the sun. |
| **Ring Gear** | `ring` | Internal gear: a solid annulus with teeth pointing inward, backlash applied on the flanks. |

## Parameters

| Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- |
| `module` | 1.0 mm | 0.5 – 2.0 | The mesh currency — all three gears share it. |
| `teeth_sun` | 16 | 10 – 40 | Sun tooth count. |
| `teeth_planet` | 16 | 8 – 40 | Planet tooth count; ring teeth derive as `sun + 2 × planet`. |
| `pressure_angle` | 20° | 14.5 – 25 | Involute pressure angle. |
| `gear_thick` | 6 mm | 3 – 16 | Face width, shared by all three. |
| `sun_bore` | 5 mm | 0 – 12 | Sun shaft bore; 0 leaves it solid. |
| `planet_bore` | 4 mm | 0 – 12 | Planet bearing bore. |
| `ring_backlash` | 0.12 mm | 0 – 0.5 | Flank relief on the ring's internal teeth. |
| `ring_rim` | 5 mm | 2 – 12 | Wall thickness outside the tooth roots. |
| `flank_pts` | 8 | 4 – 14 | Involute samples per flank. |

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:** Involute Tooth Form (`profile` — ISO 53 / DIN 867), Planetary
  Tooth Sum (`custom` — the epicyclic meshing constraint), Shaft Bore (`socket`).
- **Commons license:** CERN-OHL-W-2.0

## Fabrication notes

The sun and planet are straightforward twist-free extrusions of a closed involute wire.
The ring is where the geometry earns its keep — and where both of this cartridge's
kernel traps live.

### The internal teeth must physically reach the annulus bore

The ring is a solid annular blank (outer disc minus a bore at the root circle) with a
polar array of tooth solids unioned onto its inner rim. The tooth profile was sampled
from the tip radius out to `rp + module` — the largest radius at which the involute is
still meaningful — but the blank's bore sits further out at `rp + 1.25 × module`. That
leaves a **0.25 mm gap** at the default module, and the arrayed tooth ring lands as a
free-floating disc inside the annulus:

```
body0  outer annulus, r → 30.25
body1  tooth ring,    r → 24.87     ← never touches body0
```

Both bodies were individually watertight, which is why the failure reported
`watertight=True bodies=2` rather than a torn mesh. The fix is to keep sampling the
flank **past** the bore (`ro = r_root_outer + 0.5 × module`) and clip the surplus away
afterwards, so the teeth interpenetrate the wall. The clip circle is likewise set a hair
*outside* the bore rather than on it: a tangent seam fuses into a shell that tessellates
cracked even when OCCT reports one solid.

### Backlash is tangential, never a radial shrink

Backlash was applied by scaling the whole tooth profile toward the centre. That is not
what backlash means, and it re-opened the gap above: shrinking the tooth pulls its
**outer** end back inside the bore, so at `ring_backlash = max` the teeth detached into
a second body again. Backlash is now applied by rotating each point toward the tooth
centreline — a narrower tooth in the same space, which is the physical definition.

That change carries its own trap. The two tip points of an involute tooth sit only about
**0.013°** apart. An uncapped angular shift collapses them onto each other, degenerating
the polyline into a wire OCCT refuses to extrude:

```
Standard_Failure: BRep_API: command not done
```

The shift is therefore capped at **half** each point's own offset from the centreline.
Scaling rather than subtracting keeps every point strictly on its own side of the tooth,
so the profile stays simple and correctly ordered at any backlash value.
