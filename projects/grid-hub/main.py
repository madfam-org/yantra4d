"""Grid Hub — Modular Grid Interoperability Hub (Yantra4D Hyperobject, #300 capstone).

The Commons interoperability keystone: ONE hub that bridges the major shop /
desk organization grids so a bin, tool, or accessory built for one system mounts
on another. Real standard geometry for each:

  * Gridfinity — 42 mm grid. This hub carries a Gridfinity BASEPLATE socket: a
    42 mm cell whose top opening accepts a Gridfinity bin foot via the standard
    chamfer stack (0.8 mm @ 45 deg + 1.8 mm straight + 2.15 mm @ 45 deg), with a
    0.5 mm gap between cells.
  * Multiboard — 25 mm grid. Represented as a 25 mm-pitch tile with the board's
    cell bosses.
  * French cleat — a 45 deg interlocking wall rail; the hub's back carries the
    mating cleat hook (a 45 deg-bevelled rail that hangs on a wall cleat).
  * Pegboard — 1 in (25.4 mm) hole pitch, 1/4 in (~6.35 mm) holes; the hub's back
    carries two pegboard hook posts on that pitch.

Three distinct modes:
  * gridfinity_cleat — Gridfinity baseplate cell(s) on the front + a French-cleat
    hook on the back: hang Gridfinity bins on a cleat wall.
  * pegboard_grid    — pegboard hook posts on the back + a Gridfinity cell on the
    front: put Gridfinity on a pegboard.
  * multiboard_tile  — a Multiboard-pitch tile bridging to a Gridfinity cell:
    connect the 25 mm and 42 mm grids.

Watertightness: the Gridfinity socket chamfer stack is built as stacked lofted
frusta (a loft to a flat bottom, never a revolve of a cut profile); pegboard
posts and cleat rails are solid unions with overlap; every pocket / hole opens to
a face (no trapped void). Corners filleted before feature cuts.

Sandbox contract (cq_runner.py): `cq`+`math` pre-injected; params bare globals
via PARAM(lambda: name, default); final solid assigned to `result`.
"""

import cadquery as cq
import math


def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Standard grid geometry (nominal, mm) ─────────────────────────────────────
GRIDFINITY_PITCH = 42.0
GRIDFINITY_CLEAR = 0.5          # gap between grid cells
MULTIBOARD_PITCH = 25.0
PEG_PITCH = 25.4                # 1 inch
PEG_HOLE_D = 6.35               # 1/4 inch


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "gridfinity_cleat"))
gx          = int(PARAM(lambda: gx, 1))            # Gridfinity cells in X
gy          = int(PARAM(lambda: gy, 1))            # Gridfinity cells in Y
base_th     = float(PARAM(lambda: base_th, 5.0))  # baseplate floor thickness
back_th     = float(PARAM(lambda: back_th, 6.0))  # back plate thickness
cleat_ang   = float(PARAM(lambda: cleat_ang, 45.0))  # French-cleat bevel angle
wall        = float(PARAM(lambda: wall, 2.4))     # general wall

gx = max(1, min(gx, 4))
gy = max(1, min(gy, 4))
base_th = max(3.0, min(base_th, 10.0))
back_th = max(4.0, min(back_th, 12.0))
cleat_ang = max(30.0, min(cleat_ang, 60.0))
wall = max(1.6, min(wall, 5.0))


def _fillet_safe(wp, selector, radius):
    try:
        return wp.edges(selector).fillet(radius)
    except Exception:
        return wp


# ── Gridfinity baseplate socket (real chamfer stack) ─────────────────────────
def gridfinity_baseplate(nx, ny, floor_th):
    """A Gridfinity baseplate: an nx*ny grid of 42 mm cells, each with the
    standard stacked-chamfer socket that a bin foot drops into. Built as a solid
    slab with a lofted socket cut per cell (loft to a flat bottom → watertight,
    never a revolve of a groove). Returns (solid, total_w, total_h, height)."""
    cell = GRIDFINITY_PITCH
    total_w = nx * cell
    total_h = ny * cell
    # Socket profile (from the top down): the bin foot chamfer stack.
    c1 = 0.8    # top 45 deg lead-in
    s2 = 1.8    # straight
    c3 = 2.15   # lower 45 deg
    socket_h = c1 + s2 + c3
    slab_h = socket_h + floor_th

    slab = cq.Workplane("XY").box(total_w, total_h, slab_h, centered=(True, True, False))
    slab = _fillet_safe(slab, "|Z", 3.75)  # Gridfinity outer corner radius

    # Per-cell socket cut: a top opening ~ (42 - clearance) that steps inward.
    top_out = cell - GRIDFINITY_CLEAR      # 41.5 mm opening at the very top
    # radii/half-widths at each z level of the socket (square cross-section)
    hw_top = top_out / 2.0
    hw_mid = hw_top - c1                   # after 0.8 @ 45
    hw_bot = hw_mid                        # straight run keeps width
    hw_floor = hw_mid - c3                 # after 2.15 @ 45 at the bottom
    x0 = -(total_w - cell) / 2.0
    y0 = -(total_h - cell) / 2.0

    cutter = None
    for iy in range(ny):
        for ix in range(nx):
            cx = x0 + ix * cell
            cy = y0 + iy * cell
            # z of the socket bottom (floor top) and top (slab top)
            z_floor = slab_h - socket_h
            # Loft: floor square -> up c3 to mid -> straight s2 -> up c1 to top.
            prof = (
                cq.Workplane("XY").transformed(offset=cq.Vector(cx, cy, z_floor))
                .rect(2 * hw_floor, 2 * hw_floor)
                .workplane(offset=c3).rect(2 * hw_bot, 2 * hw_bot)
                .workplane(offset=s2).rect(2 * hw_mid, 2 * hw_mid)
                .workplane(offset=c1).rect(2 * hw_top, 2 * hw_top)
                .loft(combine=True)
            )
            # Extend the top opening up a hair so it cleanly breaks the top face.
            cap = (
                cq.Workplane("XY").transformed(offset=cq.Vector(cx, cy, slab_h - 0.01))
                .rect(2 * hw_top, 2 * hw_top).extrude(0.5)
            )
            piece = prof.union(cap)
            cutter = piece if cutter is None else cutter.union(piece)
    if cutter is not None:
        slab = slab.cut(cutter)
    return slab, total_w, total_h, slab_h


# ── Multiboard tile (25 mm pitch) ────────────────────────────────────────────
def multiboard_field(nx, ny, th):
    """A Multiboard-pitch tile: an nx*ny grid of 25 mm cells on a plate with a
    circular boss + hole per cell (the board's connection cell). Returns
    (solid, w, h)."""
    cell = MULTIBOARD_PITCH
    w = nx * cell
    h = ny * cell
    plate = cq.Workplane("XY").box(w, h, th, centered=(True, True, False))
    plate = _fillet_safe(plate, "|Z", 4.0)  # Multiboard corner radius

    x0 = -(w - cell) / 2.0
    y0 = -(h - cell) / 2.0
    holes = None
    for iy in range(ny):
        for ix in range(nx):
            cx = x0 + ix * cell
            cy = y0 + iy * cell
            hole = (
                cq.Workplane("XY").transformed(offset=cq.Vector(cx, cy, -1.0))
                .circle(6.2).extrude(th + 2.0)   # ~12.4 mm Multiboard core hole
            )
            holes = hole if holes is None else holes.union(hole)
    if holes is not None:
        plate = plate.cut(holes)
    return plate, w, h


# ── French cleat hook (45 deg) ───────────────────────────────────────────────
def cleat_hook(width, plate_th, ang):
    """A back-mounted French-cleat hook: a plate whose back face carries a
    downward-facing 45 deg bevel rail that hooks over a wall cleat. Returns
    (solid, height). Built from a swept/extruded triangular prism unioned onto
    the plate (solid → watertight)."""
    rail_h = 18.0
    plate_h = rail_h + 8.0
    plate = cq.Workplane("XY").box(width, plate_th, plate_h, centered=(True, True, False))
    plate = _fillet_safe(plate, "|Z", min(wall, width / 8.0))

    # Bevel rail: a right-triangle prism on the BACK (-Y) face. The hypotenuse
    # faces down-and-in at `ang`, so it drops onto a wall cleat's up-facing bevel.
    # Built as a triangular profile in the YZ plane, extruded along X across the
    # full plate width (robust solid → watertight).
    depth = min(rail_h / math.tan(math.radians(ang)), 14.0) + plate_th
    y_back = -plate_th / 2.0
    rail_prof = (
        cq.Workplane("YZ")
        .polyline([
            (y_back, plate_h - 2.0),
            (y_back - depth, plate_h - 2.0),
            (y_back, plate_h - 2.0 - rail_h),
        ]).close()
    )
    rail = rail_prof.extrude(width / 2.0, both=True)
    body = plate.union(rail)
    return body, plate_h


# ── Pegboard hook posts (1 in pitch) ─────────────────────────────────────────
def pegboard_posts(plate_th):
    """A back plate with two pegboard hook posts on the 1 in (25.4 mm) pitch that
    insert into standard pegboard and hook downward. Returns (solid, w, h)."""
    w = PEG_PITCH + 16.0
    h = 40.0
    plate = cq.Workplane("XY").box(w, plate_th, h, centered=(True, True, False))
    plate = _fillet_safe(plate, "|Z", min(wall, w / 8.0))

    # Two horizontal posts (into the board, -Y) + a small down hook at each tip.
    post_r = PEG_HOLE_D / 2.0 - 0.3
    post_len = 10.0
    posts = None
    for sx in (-1.0, 1.0):
        px = sx * PEG_PITCH / 2.0
        # Insert post: cylinder along -Y from the back face into the board.
        post = cq.Solid.makeCylinder(
            post_r, post_len + plate_th / 2.0,
            cq.Vector(px, plate_th / 2.0, h * 0.62), cq.Vector(0, -1, 0),
        )
        tip_y = plate_th / 2.0 - (post_len + plate_th / 2.0)  # = -post_len
        # Down hook at the tip: start ABOVE the axis (overlaps the post) and run
        # down, so it fuses to the post and cannot detach.
        hook = cq.Solid.makeCylinder(
            post_r, 6.0 + post_r,
            cq.Vector(px, tip_y, h * 0.62 + post_r), cq.Vector(0, 0, -1),
        )
        seg = cq.Workplane(obj=post).union(cq.Workplane(obj=hook))
        posts = seg if posts is None else posts.union(seg)
    body = plate.union(posts) if posts is not None else plate
    return body, w, h


# ── Mode builders ────────────────────────────────────────────────────────────
def build_gridfinity_cleat():
    """Gridfinity baseplate cell(s) facing up (front) + a French-cleat hook on
    the back. The baseplate slab is the front; the cleat plate stands behind it."""
    base, bw, bh, bslab = gridfinity_baseplate(gx, gy, base_th)
    hook, hook_h = cleat_hook(bw, back_th, cleat_ang)
    # Orient: baseplate lies flat (sockets open +Z). The cleat hangs it on a wall,
    # so rotate the baseplate to stand vertical and attach the cleat behind it.
    base = base.rotate((0, 0, 0), (1, 0, 0), -90).translate((0, back_th / 2.0, 0))
    # base now: sockets face -Y (out from wall); its slab spans Y and Z.
    hook = hook.translate((0, -0.0, 0))
    body = hook.union(base)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_pegboard_grid():
    """Pegboard hook posts on the back + a Gridfinity cell on the front."""
    base, bw, bh, bslab = gridfinity_baseplate(gx, gy, base_th)
    posts, pw, ph = pegboard_posts(back_th)
    # Stand the baseplate vertical (sockets face -Y) in front of the peg plate.
    base = base.rotate((0, 0, 0), (1, 0, 0), -90).translate((0, back_th / 2.0 + 0.0, 0))
    body = posts.union(base)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_multiboard_tile():
    """A Multiboard-pitch tile bridging to a Gridfinity cell: a Multiboard field
    on one face, a Gridfinity baseplate cell fused on the other."""
    mb, mw, mh = multiboard_field(max(1, gx * 2), max(1, gy * 2), back_th)
    base, bw, bh, bslab = gridfinity_baseplate(gx, gy, base_th)
    # Sit the Gridfinity baseplate on top of the Multiboard tile (fused stack).
    base = base.translate((0, 0, back_th - 0.5))
    body = mb.union(base)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pegboard_grid":
    result = build_pegboard_grid()
elif target_part == "multiboard_tile":
    result = build_multiboard_tile()
else:
    result = build_gridfinity_cleat()
