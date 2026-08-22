"""Snap Electrode Carrier — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The disc that carries a standard 10 mm ECG/EMG snap stud as a textile electrode contact.
A sensing garment — a chest strap, an EMG sleeve, a biofeedback vest — needs the snap to
sit on a rigid, flat, sewable island so the stud does not tilt against skin and so the
conductive fabric under it stays in even contact. This carrier is that island: a shallow
disc with a ring of sew holes, a central boss bored for the snap stud's shank, and a
recessed underside pocket that seats the conductive-fabric patch.

Bridges to the `sew-on-snap` family: that cartridge prints the snap ITSELF (a stud disc and
a socket disc as a closure). This cartridge does not print a snap — it prints the carrier
that a bought metal 10 mm snap stud (the medical-electrode standard) is set into, because a
sensing contact must be metal.

Modes (dispatched via `target_part`):
  * "carrier"     — the disc alone with its bored boss.
  * "carrier_lid" — carrier plus a thin retaining ring that traps the fabric patch.
  * "set"         — carrier and ring laid out side by side on one plate.

Geometry: the disc is a chamfered clean cylinder blank (chamfer FIRST, before any cut).
The boss is a cylinder unioned with real overlap into the disc top, then a through bore for
the snap shank and a counterbore for its flange are cut in one pass each, both overshooting
their faces. The fabric pocket is a shallow cylinder cut from the underside — it opens
downward and drains. The retaining ring is a separate annulus.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `disc_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import math

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
disc_dia   = float(PARAM(lambda: disc_dia,   22.0))  # carrier disc outside diameter (mm)
disc_t     = float(PARAM(lambda: disc_t,     2.4))   # disc thickness (mm)
stud_shank = float(PARAM(lambda: stud_shank, 4.2))   # snap stud shank diameter (mm)
stud_flange = float(PARAM(lambda: stud_flange, 10.0))  # snap stud flange diameter (mm)
boss_h     = float(PARAM(lambda: boss_h,     2.0))   # boss height above the disc face (mm)
sew_holes  = int(  PARAM(lambda: sew_holes,  6))     # stitch holes around the rim
hole_dia   = float(PARAM(lambda: hole_dia,   1.6))   # stitch hole diameter (mm)

target_part = str(PARAM(lambda: target_part, "carrier"))  # carrier|carrier_lid|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
disc_t      = max(1.4, min(disc_t, 5.0))
stud_shank  = max(2.0, min(stud_shank, 8.0))
stud_flange = max(stud_shank + 2.0, min(stud_flange, 16.0))
# The disc must clear the flange plus a real sewing rim on every side.
disc_dia    = max(stud_flange + 8.0, min(disc_dia, 45.0))
boss_h      = max(0.8, min(boss_h, 5.0))
sew_holes   = max(4, min(sew_holes, 10))
hole_dia    = max(1.0, min(hole_dia, 2.5))

# Boss: wide enough to hold the flange counterbore with wall around it.
boss_dia = min(stud_flange + 3.0, disc_dia - 5.0)
boss_dia = max(boss_dia, stud_shank + 3.0)

# Counterbore for the stud flange, sunk into the boss top; the shank bore runs on through.
cbore_depth = max(0.6, min(boss_h * 0.6, 2.0))

# Underside fabric pocket: seats the conductive-fabric patch flush with the sew face.
pocket_dia = min(stud_flange + 4.0, disc_dia - 4.0)
pocket_depth = max(0.3, min(disc_t * 0.35, 1.0))

# Stitch ring: outboard of the boss, inboard of the rim.
sew_r = (boss_dia / 2.0 + disc_dia / 2.0) / 2.0
_band = disc_dia / 2.0 - boss_dia / 2.0
hole_dia = min(hole_dia, max(0.8, _band - 1.4))

# Retaining ring: an annulus the same OD as the pocket, trapping the fabric patch edge.
ring_t = max(0.8, min(disc_t * 0.5, 1.6))
ring_id = stud_flange + 1.2
ring_od = pocket_dia - 0.4
ring_od = max(ring_od, ring_id + 2.0)


def _sew_points():
    """Polar stitch-hole centres — one pushPoints op, never a union loop."""
    pts = []
    for i in range(sew_holes):
        a = 2.0 * math.pi * i / sew_holes + math.pi / float(sew_holes)
        pts.append((sew_r * math.cos(a), sew_r * math.sin(a)))
    return pts


def build_carrier():
    """Disc + bored boss + underside fabric pocket + rim stitch holes."""
    # Clean chamfered blank FIRST — no fillet/chamfer survives a complex cut.
    disc = (
        cq.Workplane("XY")
        .circle(disc_dia / 2.0)
        .extrude(disc_t)
        .edges(">Z")
        .chamfer(min(disc_t * 0.25, 0.5))
    )
    # Boss overlaps into the disc so the union is solid, never tangent.
    boss = (
        cq.Workplane("XY")
        .circle(boss_dia / 2.0)
        .extrude(boss_h + 0.6)
        .translate((0, 0, disc_t - 0.6))
    )
    body = disc.union(boss)

    top_z = disc_t + boss_h

    # Shank bore: straight through the whole stack, overshooting both faces.
    shank = (
        cq.Workplane("XY")
        .circle(stud_shank / 2.0)
        .extrude(top_z + 4.0)
        .translate((0, 0, -2.0))
    )
    body = body.cut(shank)

    # Flange counterbore, sunk from the boss top; overshoots the top face.
    cbore = (
        cq.Workplane("XY")
        .circle(stud_flange / 2.0)
        .extrude(cbore_depth + 2.0)
        .translate((0, 0, top_z - cbore_depth))
    )
    body = body.cut(cbore)

    # Underside fabric pocket: opens downward, drains, never a sealed void.
    pocket = (
        cq.Workplane("XY")
        .circle(pocket_dia / 2.0)
        .extrude(pocket_depth + 2.0)
        .translate((0, 0, -2.0))
    )
    body = body.cut(pocket)

    # Stitch holes: one pass from the underside, clean through both faces.
    body = (
        body.faces("<Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(x, -y) for (x, y) in _sew_points()])
        .circle(hole_dia / 2.0)
        .cutThruAll()
    )
    return body


def build_ring():
    """A flat annulus that traps the fabric patch edge inside the underside pocket."""
    outer = (
        cq.Workplane("XY")
        .circle(ring_od / 2.0)
        .extrude(ring_t)
        .edges(">Z")
        .chamfer(min(ring_t * 0.3, 0.4))
    )
    bore = (
        cq.Workplane("XY")
        .circle(ring_id / 2.0)
        .extrude(ring_t + 4.0)
        .translate((0, 0, -2.0))
    )
    return outer.cut(bore)


def _compound(*solids):
    """Separate bodies on one plate — a Compound, never a union of non-touching solids."""
    shapes = []
    for s in solids:
        shapes.extend(s.vals())
    return cq.Workplane(obj=cq.Compound.makeCompound(shapes))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "carrier":
    result = build_carrier()
elif target_part == "carrier_lid":
    # Ring stacked beside the carrier but close in: a compact two-body job.
    _off = disc_dia / 2.0 + ring_od / 2.0 + 3.0
    result = _compound(build_carrier(), build_ring().translate((_off, 0, 0)))
else:
    _off = disc_dia / 2.0 + ring_od / 2.0 + 3.0
    _gap = max(4.0, disc_dia * 0.2)
    result = _compound(
        build_carrier(),
        build_ring().translate((_off, 0, 0)),
        build_carrier().translate((0, disc_dia + _gap, 0)),
        build_ring().translate((_off, disc_dia + _gap, 0)),
    )
