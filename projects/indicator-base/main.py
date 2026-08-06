import cadquery as cq


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part   = PARAM(lambda: target_part, "stem_base")
stem_dia      = float(PARAM(lambda: stem_dia, 8.0))    # Mitutoyo Series-2 stem = 8 mm
post_height   = float(PARAM(lambda: post_height, 60.0))
base_width    = float(PARAM(lambda: base_width, 60.0))
base_depth    = float(PARAM(lambda: base_depth, 45.0))
base_thick    = float(PARAM(lambda: base_thick, 14.0))
column_dia    = float(PARAM(lambda: column_dia, 16.0))


# ─── Shared helpers ───────────────────────────────────────────────────────────
def _base_block():
    """Filleted rectangular base plate. Fillet the blank BEFORE any feature cut."""
    body = cq.Workplane("XY").box(base_width, base_depth, base_thick)
    body = body.edges("|Z").fillet(6.0)
    body = body.edges(">Z").fillet(1.5)
    # Two counterbored fixing holes to bolt the base to a plate — open to both faces
    # through the plate (manifold), counterbore open to the top face.
    off_x = base_width / 2.0 - 9.0
    off_y = base_depth / 2.0 - 9.0
    pts = [(off_x, off_y), (-off_x, off_y)]
    body = (
        body.faces(">Z").workplane()
        .pushPoints(pts)
        .cboreHole(5.5, 10.0, 5.0)
    )
    return body


# ─── Mode 1: Stem Base (horizontal cross-bore) ────────────────────────────────
def build_stem_base():
    """Column base that grips the 8 mm indicator stem in a horizontal cross-bore
    at the top of a vertical column. A saw-cut clamp slot + a cross clamp screw
    close the bore onto the stem. Every cut opens to a face — no trapped void."""
    body = _base_block()

    # Vertical column, unioned (overlapping, not tangent) into the base.
    col_h = post_height
    column = (
        cq.Workplane("XY")
        .workplane(offset=base_thick / 2.0 - 2.0)
        .circle(column_dia / 2.0)
        .extrude(col_h)
    )
    body = body.union(column)

    # Clamp head block at the top of the column (gives material around the bore).
    head_z = base_thick / 2.0 - 2.0 + col_h
    head = (
        cq.Workplane("XY")
        .workplane(offset=head_z - 14.0)
        .box(column_dia + 8.0, column_dia + 8.0, 20.0, centered=(True, True, False))
    )
    body = body.union(head)
    body = body.edges("|Z").fillet(2.0)

    # Horizontal stem bore through the clamp head (open both sides => manifold tube).
    bore_z = head_z - 6.0
    stem_bore = (
        cq.Workplane("XZ")
        .workplane(offset=-(base_depth))
        .center(0.0, bore_z)
        .circle(stem_dia / 2.0 + 0.1)
        .extrude(2.0 * base_depth)
    )
    body = body.cut(stem_bore)

    # Saw-cut clamp slot from the top face down to the bore (open to top + slot walls).
    slot = (
        cq.Workplane("XY")
        .workplane(offset=bore_z)
        .box(2.0, column_dia + 10.0, 30.0, centered=(True, True, False))
    )
    body = body.cut(slot)

    # Cross clamp screw: a hole perpendicular to both the bore and the slot
    # (open on both outer faces => manifold), so tightening pinches the slot.
    clamp = (
        cq.Workplane("YZ")
        .workplane(offset=-(column_dia + 10.0))
        .center(0.0, bore_z + 8.0)
        .circle(1.6)
        .extrude(2.0 * (column_dia + 10.0))
    )
    body = body.cut(clamp)
    return body


# ─── Mode 2: Lug Base (flat vertical post + lug pad) ──────────────────────────
def build_lug_base():
    """Low base carrying a flat-faced post with a lug-mount pad: a flat vertical
    face and a tapped-style through hole for lug-back indicators (the lug bolts
    flat to the pad). The hole opens on both faces of the pad — manifold."""
    body = _base_block()

    # Flat post rising from the base — a slab, distinct from the round column.
    post = (
        cq.Workplane("XY")
        .workplane(offset=base_thick / 2.0 - 2.0)
        .box(column_dia + 14.0, 10.0, post_height, centered=(True, True, False))
    )
    post = post.edges("|Z").fillet(3.0)
    body = body.union(post)

    # Lug-mount pad: a boss on the front flat face, fully seated into the post so
    # it is not a half-embedded boss. Union of overlapping solids.
    pad_z = base_thick / 2.0 - 2.0 + post_height - 22.0
    pad = (
        cq.Workplane("XZ")
        .workplane(offset=-5.0)
        .center(0.0, pad_z)
        .circle(11.0)
        .extrude(12.0)
    )
    body = body.union(pad)

    # Lug fastening hole through the pad+post (open both front and back => manifold).
    lug_hole = (
        cq.Workplane("XZ")
        .workplane(offset=-20.0)
        .center(0.0, pad_z)
        .circle(2.5)
        .extrude(40.0)
    )
    body = body.cut(lug_hole)
    return body


# ─── Mode 3: Dovetail Holder (for test / finger indicators) ───────────────────
def build_dovetail_holder():
    """Bench block with a standard dovetail slot for lever/test indicators plus a
    cross clamp for the 8 mm stem accessory. The dovetail is a trapezoidal groove
    open to the top and both ends (a through slot) — never a trapped pocket."""
    body = _base_block()

    # Tower to carry the dovetail high enough to clear work.
    tower_h = post_height * 0.55
    tower = (
        cq.Workplane("XY")
        .workplane(offset=base_thick / 2.0 - 2.0)
        .box(base_width * 0.5, base_depth * 0.55, tower_h, centered=(True, True, False))
    )
    tower = tower.edges("|Z").fillet(3.0)
    body = body.union(tower)

    top_z = base_thick / 2.0 - 2.0 + tower_h

    # Dovetail groove: trapezoid wider at the bottom, swept the full depth (through
    # slot, open at both ends and the top face). Standard ~ 9.5 mm nominal, 60°.
    dt_top = 8.0
    dt_bot = 11.0
    dt_h = 7.0
    groove = (
        cq.Workplane("XZ")
        .workplane(offset=-(base_depth))
        .polyline([
            (-dt_top / 2.0, top_z + 1.0),
            (dt_top / 2.0, top_z + 1.0),
            (dt_bot / 2.0, top_z - dt_h),
            (-dt_bot / 2.0, top_z - dt_h),
        ]).close()
        .extrude(2.0 * base_depth)
    )
    body = body.cut(groove)

    # Cross clamp screw that pinches the dovetail (open on both faces => manifold).
    clamp = (
        cq.Workplane("YZ")
        .workplane(offset=-(base_width))
        .center(0.0, top_z - dt_h / 2.0)
        .circle(1.6)
        .extrude(2.0 * base_width)
    )
    body = body.cut(clamp)
    return body


# ─── Dispatch ────────────────────────────────────────────────────────────────
_dispatch = {
    "stem_base":       build_stem_base,
    "lug_base":        build_lug_base,
    "dovetail_holder": build_dovetail_holder,
}

result = _dispatch.get(target_part, build_stem_base)()
