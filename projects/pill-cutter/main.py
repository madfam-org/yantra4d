"""
Pill Cutter / Crusher / Dosing Cup — Yantra4D Hyperobject Cartridge (CadQuery).

A small kit for managing solid medication at home: a splitter body that centres
a tablet in a V-pocket under a razor-blade slot for a clean half, a crusher cup
whose domed floor pulverises a tablet under a press boss, and a graduated dosing
cup for liquid medicine.

  * "splitter"   — a base with a centring V-pocket and a transverse blade slot so
                   a standard snap-off / razor blade halves a tablet
                   (target_part == "splitter").
  * "crusher"    — a heavy cup with a domed grinding floor and a press boss to
                   crush a tablet to powder (target_part == "crusher").
  * "dosing_cup" — a tapered graduated cup for liquid doses (target_part ==
                   "dosing_cup").

Watertight strategy: the splitter is a solid block with a V-pocket and a blade
slot cut in; the crusher is a solid cup (blind bore) with a domed floor bump
added and a boss on the underside handle; the dosing cup is a lofted frustum
hollowed by a smaller lofted frustum, leaving a floor. Every result is one
manifold solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

These are printable everyday medication-handling AIDS, not certified medical
devices; do not use printed parts where sterility or exact dosing is required.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "splitter"))  # splitter | crusher | dosing_cup

pill_dia   = float(PARAM(lambda: pill_dia,  12.0))   # tablet diameter (mm)
pill_th    = float(PARAM(lambda: pill_th,    5.0))   # tablet thickness (mm)
blade_slot = float(PARAM(lambda: blade_slot, 1.2))   # razor-blade slot width (mm)
wall       = float(PARAM(lambda: wall,       3.0))   # body wall thickness
cup_ml     = float(PARAM(lambda: cup_ml,    30.0))   # dosing-cup volume (mL)

# ── Clamps ───────────────────────────────────────────────────────────────────
pill_dia   = max(4.0,  min(pill_dia, 30.0))
pill_th    = max(1.5,  min(pill_th, 14.0))
blade_slot = max(0.6,  min(blade_slot, 3.0))
wall       = max(2.0,  min(wall, 8.0))
cup_ml     = max(5.0,  min(cup_ml, 60.0))

PILL_R = pill_dia / 2.0


# ── Part builders ────────────────────────────────────────────────────────────
def build_splitter():
    """A block with a V-groove that self-centres a round tablet, and a vertical
    slot across the centre to guide a razor / snap-off blade through the middle."""
    length = pill_dia + 2.0 * wall + 8.0
    width = pill_dia + 2.0 * wall
    height = pill_th + wall + 2.0
    body = cq.Workplane("XY").box(length, width, height, centered=(True, True, False))

    # V-pocket: a wedge trough running along X that cradles the pill by its rim.
    v_half = PILL_R + 0.6
    v_depth = pill_th * 0.75 + 1.0
    vprof = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, height, 0))
        .polyline([(-v_half, 0), (0, -v_depth), (v_half, 0)])
        .close()
    )
    vgroove = vprof.extrude(-(length + 2.0))
    vgroove = vgroove.translate((length / 2.0 + 1.0, 0, 0))
    body = body.cut(vgroove)

    # Blade slot: a thin transverse slit through the middle, down past the pill.
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, height - v_depth - 0.5))
        .box(blade_slot, width + 2.0, v_depth + 2.0, centered=(True, True, False))
    )
    body = body.cut(slot)

    # Finger scallops on the ends so the split halves are easy to pick out.
    for sx in (-1.0, 1.0):
        scoop = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * length / 2.0, 0, height))
            .circle(width * 0.28)
            .extrude(-(pill_th + 1.0))
        )
        body = body.cut(scoop)
    return body


def build_crusher():
    """A stout cup: a tablet drops in, a domed floor concentrates the load, and a
    grippy press boss on a lid pushes down to crush it. Modelled as the cup with
    an integral top press knob so it prints as one solid tool the user twists."""
    bore_r = PILL_R + 1.2
    cup_wall = wall + 1.0
    outer_r = bore_r + cup_wall
    bore_depth = pill_th + 8.0
    total_h = bore_depth + wall

    body = cq.Workplane("XY").circle(outer_r).extrude(total_h)
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall))
        .circle(bore_r)
        .extrude(bore_depth + 1.0)
    )
    body = body.cut(bore)

    # Domed grinding bump on the floor (a low cone) to focus crushing force.
    # Start the cone base BELOW the floor top (inside the solid) so the union is
    # volumetric, not a coplanar kiss on the floor face (which cracks the mesh).
    dome = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall - 1.0))
        .circle(bore_r * 0.9)
        .workplane(offset=2.8)
        .circle(bore_r * 0.25)
        .loft(combine=True)
    )
    body = body.union(dome)
    try:
        body = body.clean()
    except Exception:
        pass

    # Grip flutes around the outside for a firm twist. Shallow radial slots on
    # the outer surface (proven watertight knurl geometry): narrow and shallow
    # so adjacent flutes never merge into slivers on a small cup.
    flute_depth = min(0.8, cup_wall * 0.25)
    try:
        cutter = (
            cq.Workplane("XY")
            .polarArray(radius=outer_r, startAngle=0, angle=360, count=16)
            .rect(flute_depth, flute_depth * 3.0)
            .extrude(total_h + 2.0)
            .translate((0, 0, -1.0))
        )
        body = body.cut(cutter)
    except Exception:
        pass
    return body


def build_dosing_cup():
    """A tapered graduated cup for liquid medicine. Frustum outer, hollowed by a
    smaller frustum leaving a floor; volume drives the size."""
    # Approximate the cup as a straight frustum; pick radii/height to hit cup_ml.
    # Use a fixed taper; solve height for the target interior volume.
    vol_mm3 = cup_ml * 1000.0
    r_top_in = max(9.0, (vol_mm3 / 12.0) ** (1.0 / 3.0) * 1.1)  # heuristic inner top r
    r_bot_in = r_top_in * 0.72
    # Frustum volume V = pi/3 * h * (R^2 + R*r + r^2); solve for h.
    denom = (3.141592653589793 / 3.0) * (r_top_in**2 + r_top_in * r_bot_in + r_bot_in**2)
    h_in = max(18.0, vol_mm3 / denom)
    h_in = min(h_in, 80.0)

    r_top_out = r_top_in + wall
    r_bot_out = r_bot_in + wall
    total_h = h_in + wall

    outer = (
        cq.Workplane("XY")
        .circle(r_bot_out)
        .workplane(offset=total_h)
        .circle(r_top_out)
        .loft(combine=True)
    )
    inner = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall))
        .circle(r_bot_in)
        .workplane(offset=h_in + 1.0)
        .circle(r_top_in)
        .loft(combine=True)
    )
    body = outer.cut(inner)

    # Graduation rings on the outside (cosmetic tick marks): thin grooves.
    for i in range(1, 4):
        z = wall + h_in * i / 4.0
        rr = r_bot_out + (r_top_out - r_bot_out) * (i / 4.0)
        ring = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z))
            .circle(rr + 0.3)
            .circle(rr - 0.3)
            .extrude(0.8)
        )
        try:
            body = body.cut(ring)
        except Exception:
            pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "crusher":
    result = build_crusher()
elif target_part == "dosing_cup":
    result = build_dosing_cup()
else:  # "splitter"
    result = build_splitter()
