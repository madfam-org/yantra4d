"""
Golf Accessory Set — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Small course accessories sized to a standard golf ball (42.7 mm) and tee. A tee
holder that carries a row of tees, a ball marker disc, and an alignment tool that
cradles the ball so you can draw a straight putting line. The ball/tee dimensions
are the shared interface.

Three parts (dispatched by `target_part`):
  * "tee_holder"     — a slim block/clip with a row of tee sockets, clips to a bag
                       or belt.
  * "ball_marker"    — a flat disc marker with a grip rim (and a small locating
                       stub underneath), the size of a coin marker.
  * "alignment_tool" — a partial ring the ball nests in with a straight slot on
                       top; run a pen through the slot to draw a line on the ball.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `ball_dia`).
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
target_part = str(PARAM(lambda: target_part, "tee_holder"))  # tee|marker|alignment

ball_dia   = float(PARAM(lambda: ball_dia,  42.7))  # golf ball diameter (mm, std 42.67)
tee_dia    = float(PARAM(lambda: tee_dia,    5.5))  # tee shaft diameter (mm)
tee_count  = int(  PARAM(lambda: tee_count,    5))  # tees the holder carries
wall       = float(PARAM(lambda: wall,       3.0))  # body wall thickness (mm)
marker_dia = float(PARAM(lambda: marker_dia,24.0))  # ball marker disc diameter (mm)
slot_w     = float(PARAM(lambda: slot_w,     2.2))  # alignment pen-slot width (mm)

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
ball_dia   = max(38.0, min(ball_dia, 46.0))
tee_dia    = max(3.0, min(tee_dia, 9.0))
tee_count  = max(2, min(tee_count, 12))
wall       = max(2.0, min(wall, 6.0))
marker_dia = max(18.0, min(marker_dia, 36.0))
slot_w     = max(1.2, min(slot_w, 4.0))


# ── Part builders ────────────────────────────────────────────────────────────
def build_tee_holder():
    """A slim block with a row of `tee_count` tee sockets and a belt/bag clip."""
    socket_r = tee_dia / 2.0 + 0.4
    pitch = 2.0 * socket_r + wall
    length = tee_count * pitch + wall
    width = 2.0 * socket_r + 2.0 * wall
    depth = max(18.0, tee_dia * 3.0)          # how deep tees seat (z)

    body = cq.Workplane("XY").box(length, width, depth, centered=(True, True, False))
    # Bore the tee sockets from the top (open up), leaving a floor.
    for i in range(tee_count):
        x = -length / 2.0 + wall + pitch * (i + 0.5)
        cutter = (
            cq.Workplane("XY")
            .circle(socket_r)
            .extrude(depth - wall)
            .translate((x, 0, wall))
        )
        body = body.cut(cutter)
    # Belt/bag spring clip on the back (−Y): a tongue standing off with a gap.
    clip_gap = 4.0
    clip_t = wall
    tongue = (
        cq.Workplane("XY")
        .box(length * 0.7, clip_t, depth * 1.1, centered=(True, True, False))
        .translate((0, -width / 2.0 - clip_gap - clip_t / 2.0, 0))
    )
    bridge = (
        cq.Workplane("XY")
        .box(length * 0.7, clip_gap + clip_t, wall, centered=(True, False, False))
        .translate((0, -width / 2.0 - clip_gap - clip_t, depth - wall))
    )
    body = body.union(bridge).union(tongue)
    try:
        body = body.edges("|X and >Z").fillet(min(1.5, wall * 0.4))
    except Exception:
        pass
    return body


def build_ball_marker():
    """A flat disc ball marker with a knurled grip rim and a small locating stub
    underneath so it stays put on the green."""
    r = marker_dia / 2.0
    disc_h = max(2.0, wall * 0.8)
    disc = cq.Workplane("XY").circle(r).extrude(disc_h)
    # Grip flutes around the rim (a single polar-array cutter — cheap, watertight).
    try:
        teeth = max(12, int(marker_dia))
        cutter = (
            cq.Workplane("XY")
            .polarArray(radius=r, startAngle=0, angle=360, count=teeth)
            .rect(0.8, 2.4)
            .extrude(disc_h + 1.0)
            .translate((0, 0, -0.5))
        )
        disc = disc.cut(cutter)
    except Exception:
        pass
    # A shallow raised centre ring so a logo/coin could sit, and a locating stub.
    ringlet = (
        cq.Workplane("XY")
        .circle(r * 0.55).circle(r * 0.42)
        .extrude(disc_h + 0.6)
    )
    disc = disc.union(ringlet)
    stub = (
        cq.Workplane("XY")
        .circle(max(1.2, r * 0.14))
        .extrude(2.5)
        .translate((0, 0, -2.5))
    )
    disc = disc.union(stub)
    return disc


def build_alignment_tool():
    """A partial ring the ball nests in with a straight slot across the top; run a
    pen through the slot to draw a putting alignment line on the ball."""
    R = ball_dia / 2.0
    cradle_r = R * 0.92          # the ring cups the ball just below its equator
    ro = cradle_r + wall
    ring_h = ball_dia * 0.42

    # Ring cradle (annulus) with the top open so the ball drops in.
    ring = cq.Workplane("XY").circle(ro).circle(cradle_r).extrude(ring_h)
    # Two alignment fins across the top forming a straight channel for the pen.
    fin_h = wall + 3.0
    fin_len = ro * 2.0
    gap = slot_w
    for sy in [-(gap / 2.0 + wall / 2.0), (gap / 2.0 + wall / 2.0)]:
        fin = (
            cq.Workplane("XY")
            .box(fin_len, wall, fin_h, centered=(True, True, False))
            .translate((0, sy, ring_h))
        )
        ring = ring.union(fin)
    # A base tab so the tool sits flat while marking.
    tab = (
        cq.Workplane("XY")
        .box(ro * 2.0, ro * 0.5, wall, centered=(True, True, False))
        .translate((0, ro * 0.9, 0))
    )
    ring = ring.union(tab)
    return ring


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "ball_marker":
    result = build_ball_marker()
elif target_part == "alignment_tool":
    result = build_alignment_tool()
else:
    result = build_tee_holder()
