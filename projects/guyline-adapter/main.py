"""
Guy-Line Adapter Set — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Lightweight tent and tarp hardware sized to the guy-line cord diameter. A 3-hole
line tensioner (the friction adjuster that replaces a metal cam), a tarp edge
clip that grips a tarp without a grommet, and a pole tip that caps an improvised
pole. The cord-hole geometry is the shared interface across the set.

Three parts (dispatched by `target_part`):
  * "line_tensioner" — a flat 3-hole tensioner; the cord threads through the holes
                       and friction holds the set length (adjust by squeezing).
  * "tarp_clip"      — a jaw that pinches a tarp edge and offers a cord hole, so
                       any point on a tarp becomes a tie-out.
  * "pole_tip"       — a cone tip with a cord notch that caps a stick/pole and
                       gives the guy-line something to hook onto.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cord_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
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
target_part = str(PARAM(lambda: target_part, "line_tensioner"))  # tensioner|clip|tip

cord_dia   = float(PARAM(lambda: cord_dia,   3.0))   # guy-line cord diameter (mm)
thick      = float(PARAM(lambda: thick,      5.0))   # body thickness (mm)
holes      = int(  PARAM(lambda: holes,        3))   # tensioner cord holes (2 or 3)
tarp_gap   = float(PARAM(lambda: tarp_gap,   2.0))   # tarp thickness the clip grips (mm)
pole_dia   = float(PARAM(lambda: pole_dia,  16.0))   # pole/stick diameter for the tip (mm)

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
cord_dia = max(1.5, min(cord_dia, 8.0))
thick    = max(3.0, min(thick, 10.0))
holes    = max(2, min(holes, 4))
tarp_gap = max(0.5, min(tarp_gap, 8.0))
pole_dia = max(8.0, min(pole_dia, 40.0))

hole_r = cord_dia / 2.0 + 0.3     # cord clearance
rim = max(3.0, cord_dia * 1.6)    # material around each hole


# ── Part builders ────────────────────────────────────────────────────────────
def build_line_tensioner():
    """A flat plate with `holes` cord holes in a triangle/line; the cord weaves
    through and friction on the bends holds the tension. Rounded outline so it
    won't chafe the line."""
    pitch = 2.0 * rim + 2.0 * hole_r
    if holes <= 2:
        # Two holes in a line.
        length = pitch + 2.0 * rim
        width = 2.0 * rim + 2.0 * hole_r
        plate = (
            cq.Workplane("XY")
            .box(length, width, thick, centered=(True, True, False))
        )
        pts = [(-pitch / 2.0, 0.0), (pitch / 2.0, 0.0)]
    else:
        # Triangle arrangement (classic 3-hole tensioner) for holes==3, plus one
        # extra centre hole when holes==4.
        length = pitch + 2.0 * rim
        width = pitch + 2.0 * rim
        plate = (
            cq.Workplane("XY")
            .box(length, width, thick, centered=(True, True, False))
        )
        pts = [
            (-pitch / 2.0, -pitch / 3.0),
            (pitch / 2.0, -pitch / 3.0),
            (0.0, pitch / 2.0),
        ]
        if holes >= 4:
            pts.append((0.0, -pitch / 12.0))

    # Round the plate outline.
    try:
        plate = plate.edges("|Z").fillet(min(rim * 0.9, hole_r + rim - 0.5))
    except Exception:
        pass
    # Bore the cord holes.
    for (x, y) in pts:
        cutter = (
            cq.Workplane("XY")
            .circle(hole_r)
            .extrude(thick + 2.0)
            .translate((x, y, -1.0))
        )
        plate = plate.cut(cutter)
    # Chamfer the hole mouths so the cord runs smoothly (non-fatal).
    try:
        plate = plate.faces(">Z").edges("%CIRCLE").chamfer(min(0.8, thick * 0.2))
    except Exception:
        pass
    return plate


def build_tarp_clip():
    """A C-jaw that pinches a tarp edge of `tarp_gap` thickness and offers a cord
    hole on its stem, turning any tarp point into a tie-out."""
    jaw_len = max(16.0, cord_dia * 5.0)
    jaw_w = 2.0 * rim + 2.0 * hole_r
    grip = thick

    total_h = tarp_gap + 2.0 * grip
    # Solid C, then cut the tarp slot from +X.
    outer = (
        cq.Workplane("XY")
        .box(jaw_len, jaw_w, total_h, centered=(False, True, False))
    )
    slot = (
        cq.Workplane("XY")
        .box(jaw_len - grip, jaw_w + 2.0, tarp_gap, centered=(False, True, False))
        .translate((grip, 0, grip))
    )
    body = outer.cut(slot)
    # Internal grip nub so the tarp is pinched (a small ridge into the slot).
    nub = (
        cq.Workplane("XY")
        .box(2.0, jaw_w, 1.2, centered=(False, True, False))
        .translate((jaw_len - grip - 3.0, 0, grip + tarp_gap - 1.2))
    )
    body = body.union(nub)
    # Cord hole through the closed back (bored along Z).
    cutter = (
        cq.Workplane("XY")
        .circle(hole_r)
        .extrude(total_h + 2.0)
        .translate((grip * 0.5, 0, -1.0))
    )
    body = body.cut(cutter)
    # Lead-in chamfers at the +X slot mouth so the tarp slides in (boolean
    # triangle cuts on both jaw corners — always watertight).
    lead = min(2.0, grip * 0.5)
    if lead > 0.2:
        wide = jaw_w + 4.0
        tri_low = (
            cq.Workplane("XZ")
            .polyline([(0, 0), (-lead, 0), (0, lead)]).close()
            .extrude(wide).translate((jaw_len, wide / 2.0, grip))
        )
        tri_high = (
            cq.Workplane("XZ")
            .polyline([(0, 0), (-lead, 0), (0, -lead)]).close()
            .extrude(wide).translate((jaw_len, wide / 2.0, grip + tarp_gap))
        )
        body = body.cut(tri_low).cut(tri_high)
    return body


def build_pole_tip():
    """A cone cap for a stick/pole of `pole_dia`, with a cord notch near the tip so
    a guy-line can be hitched to it. A socket cup with an external cone + notch."""
    sock_r = pole_dia / 2.0 + 0.4
    wall = max(2.5, thick * 0.6)
    outer_r = sock_r + wall
    sock_depth = pole_dia * 1.2
    cone_h = pole_dia * 0.9

    # Socket cup (open at bottom to receive the pole).
    cup = cq.Workplane("XY").circle(outer_r).extrude(sock_depth)
    bore = (
        cq.Workplane("XY")
        .circle(sock_r)
        .extrude(sock_depth - wall)
    )
    cup = cup.cut(bore)
    # Cone tip on top.
    cone = (
        cq.Workplane("XY")
        .circle(outer_r)
        .workplane(offset=cone_h)
        .circle(max(1.5, outer_r * 0.25))
        .loft(combine=True)
        .translate((0, 0, sock_depth))
    )
    body = cup.union(cone)
    # Cord notch: a horizontal hole through the cone base for the guy-line.
    notch = (
        cq.Workplane("XY")
        .transformed(rotate=cq.Vector(90, 0, 0))
        .circle(hole_r)
        .extrude(outer_r * 3.0)
        .translate((0, outer_r * 1.5, sock_depth + cone_h * 0.35))
    )
    body = body.cut(notch)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tarp_clip":
    result = build_tarp_clip()
elif target_part == "pole_tip":
    result = build_pole_tip()
else:
    result = build_line_tensioner()
