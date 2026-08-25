import math

import cadquery as cq


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:  # noqa: BLE001 — NameError is absent from older
        # cq_runner sandbox builtin allowlists, so catching it by name raises
        # inside the sandbox; the broad catch is the portable probe.
        return default


target_part   = PARAM(lambda: target_part, "pin_vise_body")
collet_bore   = float(PARAM(lambda: collet_bore, 3.0))     # 0–3 mm collet capacity
body_dia      = float(PARAM(lambda: body_dia, 12.0))
body_length   = float(PARAM(lambda: body_length, 70.0))
flute_count   = int(float(PARAM(lambda: flute_count, 16)))    # axial grip flutes
handle_bore   = float(PARAM(lambda: handle_bore, 5.0))
jaw_opening   = float(PARAM(lambda: jaw_opening, 8.0))


# ─── Shared helper ────────────────────────────────────────────────────────────
def _flute_grip(body, dia, z_lo, z_hi, count, depth=0.7):
    """Cut `count` axial semicircular flutes around the wall between z_lo..z_hi.
    Each flute is open to the outer wall (no trapped void) and leaves the body a
    single manifold solid — a print-safe stand-in for a knurl."""
    n = max(6, count)
    r_at = dia / 2.0
    flute_r = max(0.5, (math.pi * dia / n) * 0.5 - 0.15)
    seg_h = z_hi - z_lo
    for k in range(n):
        ang = (360.0 / n) * k
        a = math.radians(ang)
        cx = r_at * math.cos(a)
        cy = r_at * math.sin(a)
        cutter = (
            cq.Workplane("XY")
            .workplane(offset=z_lo)
            .center(cx, cy)
            .circle(flute_r)
            .extrude(seg_h)
        )
        body = body.cut(cutter)
    return body


# ─── Mode 1: Pin Vise Body ────────────────────────────────────────────────────
def build_pin_vise_body():
    """The pin-vise body: a fluted grip cylinder with a collet bore open to the
    TOP face (holds the 0–3 mm tool) and a hollow handle cavity open to the BOTTOM
    face (clears long drills / stock). Two open bores => no trapped void."""
    body = cq.Workplane("XY").cylinder(body_length, body_dia / 2.0)
    # Fillet the ends of the plain blank BEFORE cutting features.
    body = body.edges("%CIRCLE").fillet(1.0)

    z_lo = -body_length / 2.0
    z_hi = body_length / 2.0

    # Collet bore — open to the top face, deep enough to seat a collet + tool.
    collet_seat = body_length * 0.45
    body = body.faces(">Z").workplane().hole(collet_bore + 3.0, collet_seat)

    # Handle pass-through cavity — open to the bottom face, clears long stock.
    handle_depth = body_length - collet_seat - 4.0
    body = body.faces("<Z").workplane().hole(handle_bore, handle_depth)

    # Fluted grip band on the middle of the body (manifold, open to the wall).
    band_lo = z_lo + body_length * 0.20
    band_hi = z_hi - body_length * 0.20
    body = _flute_grip(body, body_dia, band_lo, band_hi, flute_count)
    return body


# ─── Mode 2: Collet ───────────────────────────────────────────────────────────
def build_collet():
    """A split draw-in collet: a truncated cone with a central bore open on BOTH
    ends (a manifold tube) and three relief slots opening from the small end to
    let the jaws close. Slots are through the wall (open to bore + outer)."""
    big_r = body_dia / 2.0 - 1.0
    small_r = big_r * 0.6
    length = body_length * 0.42

    cone = (
        cq.Workplane("XY")
        .circle(big_r)
        .workplane(offset=length)
        .circle(small_r)
        .loft()
    )
    # Central bore — open both ends => manifold tube (never a trapped cavity).
    bore = (
        cq.Workplane("XY")
        .workplane(offset=-1.0)
        .circle(collet_bore / 2.0)
        .extrude(length + 2.0)
    )
    body = cone.cut(bore)

    # Three relief slots from the SMALL (top) end downward, cut through the wall.
    slot_w = 1.0
    slot_depth = length * 0.7
    for k in range(3):
        ang = 120.0 * k
        cutter = (
            cq.Workplane("XY")
            .workplane(offset=length - slot_depth)
            .center(0.0, 0.0)
            .slot2D(2.0 * big_r + 4.0, slot_w, ang)
            .extrude(slot_depth + 1.0)
        )
        body = body.cut(cutter)
    return body


# ─── Mode 3: Bench Block Vise ─────────────────────────────────────────────────
def build_bench_block_vise():
    """A small precision workholding block: a rectangular body with a top V-groove
    (a through prismatic notch, open at both ends and the top) to cradle round or
    square stock, plus a cross clamp screw hole. V-groove built as a triangular
    prism cut — never a revolve — so the mesh stays clean."""
    width = body_dia + 26.0
    depth = body_dia + 18.0
    height = body_dia + 10.0

    body = cq.Workplane("XY").box(width, depth, height)
    body = body.edges("|Z").fillet(3.0)
    body = body.edges("<Z").fillet(1.0)

    top_z = height / 2.0
    half = jaw_opening / 2.0 + 3.0
    # V-groove as a triangular prism swept the full depth (through slot).
    vgroove = (
        cq.Workplane("XZ")
        .workplane(offset=-(depth))
        .polyline([
            (-half, top_z + 1.0),
            (half, top_z + 1.0),
            (0.0, top_z - (half + 1.0)),
        ]).close()
        .extrude(2.0 * depth)
    )
    body = body.cut(vgroove)

    # Cross clamp screw hole (open on both faces => manifold), below the V.
    clamp = (
        cq.Workplane("YZ")
        .workplane(offset=-(width))
        .center(0.0, top_z - (half + 6.0))
        .circle(2.0)
        .extrude(2.0 * width)
    )
    body = body.cut(clamp)

    # Two base mounting holes through the block (open both faces => manifold).
    ox = width / 2.0 - 6.0
    oy = depth / 2.0 - 6.0
    body = (
        body.faces(">Z").workplane()
        .pushPoints([(ox, -oy), (-ox, -oy)])
        .hole(4.0)
    )
    return body


# ─── Dispatch ────────────────────────────────────────────────────────────────
_dispatch = {
    "pin_vise_body":    build_pin_vise_body,
    "collet":           build_collet,
    "bench_block_vise": build_bench_block_vise,
}

result = _dispatch.get(target_part, build_pin_vise_body)()
