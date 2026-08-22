"""Garment Hanger — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The parametric shoulder-profile clothes hanger: a curved shoulder bar that carries a
garment's shoulder line without creasing it, and a rod hook that hangs it on a closet
rail. This is the display hard good the Fashion Cabinet garment record bridges to when it
needs a hanger cut to a specific finished shoulder width — a 46 cm menswear jacket and a
28 cm child's shirt want genuinely different shoulder spans, and the shop-bought hanger
comes in two sizes.

Modes (dispatched via `target_part`):
  * "standard"    — curved shoulder bar + hook. The plain hanger.
  * "notched"     — the same, with lingerie/camisole strap notches cut into the shoulder.
  * "trouser_bar" — a two-part assembly: the notched shoulder body plus a separate lower
                    bar that snaps between the two shoulder tips. Parts: `body`, `bar`.

Geometry: the shoulder bar is a lofted swept-ish blank built from stacked rounded-rect
sections mirrored about X, so the shoulder line drops away from the neck the way a real
hanger's does. The hook is composed from `cq.Solid.makeTorus` sections wrapped in
`cq.Workplane(obj=...)` and trimmed with oversized box cuts — never a swept radiusArc
path, which degenerates. Every union overlaps; every cutter overshoots both faces.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `shoulder_w`).
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
shoulder_w  = float(PARAM(lambda: shoulder_w,  420.0))  # tip-to-tip shoulder span (mm)
shoulder_t  = float(PARAM(lambda: shoulder_t,  12.0))   # shoulder bar section thickness (mm)
shoulder_h  = float(PARAM(lambda: shoulder_h,  16.0))   # shoulder bar section height (mm)
slope       = float(PARAM(lambda: slope,       38.0))   # neck-to-tip drop (mm)
hook_rod    = float(PARAM(lambda: hook_rod,    32.0))   # closet rod diameter the hook clears (mm)
hook_wire   = float(PARAM(lambda: hook_wire,   6.0))    # hook wire section diameter (mm)
notch_count = int(  PARAM(lambda: notch_count, 2))      # strap notches per shoulder
bar_drop    = float(PARAM(lambda: bar_drop,    120.0))  # trouser bar drop below the tips (mm)

target_part = str(PARAM(lambda: target_part, "standard"))


# ── Safe clamps ──────────────────────────────────────────────────────────────
# 250 mm is a child size 4; 500 mm is a heavy-coat hanger. Nothing outside is a hanger.
shoulder_w  = max(250.0, min(shoulder_w, 500.0))
shoulder_t  = max(6.0,  min(shoulder_t, 22.0))
shoulder_h  = max(10.0, min(shoulder_h, 30.0))
slope       = max(10.0, min(slope, shoulder_w * 0.16))
hook_rod    = max(18.0, min(hook_rod, 45.0))
hook_wire   = max(3.5,  min(hook_wire, 10.0))
notch_count = max(1,    min(notch_count, 3))
bar_drop    = max(50.0, min(bar_drop, 220.0))

half_w   = shoulder_w / 2.0
# Neck platform: where the hook root fuses into the shoulder bar. Wide enough that the
# hook root never sits on a knife edge.
neck_w   = max(shoulder_t * 2.2, hook_wire * 3.0)
# Shoulder bar centreline: flat across the neck, then dropping to the tips.
tip_h    = shoulder_h * 0.68           # tips taper down: real hangers thin toward the ends
# Hook geometry, all torus-based.
hook_ri  = hook_rod / 2.0 + 1.2        # inside radius: rod diameter + running clearance
hook_rc  = hook_ri + hook_wire / 2.0   # torus centreline radius
stem_len = max(28.0, hook_rc * 1.6)    # straight stem between the neck and the hook curl


# ── Shoulder bar ─────────────────────────────────────────────────────────────
def _drop_at(f):
    """Shoulder-line drop (mm) at fraction `f` from the neck out to the tip.

    A shallow cosine: flat at the neck, steepest mid-shoulder, easing at the tip —
    the shoulder line a jacket actually wants."""
    return slope * (1.0 - math.cos(math.pi * f)) / 2.0


def _sec_at(f):
    """(thickness, height) of the shoulder bar section at fraction `f`."""
    return (
        shoulder_t + (shoulder_t * 0.72 - shoulder_t) * f,
        shoulder_h + (tip_h - shoulder_h) * f,
    )


def _shoulder_half():
    """One half of the shoulder bar, from the neck centre out to the +X tip.

    A chain of rounded-rect sections pushed onto a single Workplane along X and closed
    with one `loft` — a single solid, so there are no coplanar unions to crack open.
    """
    steps = 7
    lofter = cq.Workplane("YZ")
    last_x = 0.0
    last_drop = 0.0
    for i in range(steps + 1):
        f = i / float(steps)
        x = f * half_w
        drop = _drop_at(f)
        t, h = _sec_at(f)
        lofter = (
            lofter.workplane(offset=x - last_x)
            .center(0, -(drop - last_drop))
            .rect(t, h)
        )
        last_x = x
        last_drop = drop
    return lofter.loft(ruled=True)


def _shoulder_bar():
    """Full shoulder bar: the +X half mirrored to -X, fused across an overlapping neck
    block so the two halves are one solid rather than two tangent lofts."""
    right = _shoulder_half()
    left = right.mirror(mirrorPlane="YZ")
    # Neck block spans the seam with real overlap on both sides — never a coplanar touch.
    neck = (
        cq.Workplane("XY")
        .box(neck_w, shoulder_t, shoulder_h)
        .translate((0, 0, 0))
    )
    body = right.union(left).union(neck)
    return body


def _strap_notches():
    """Cutters for lingerie/camisole strap notches, mirrored on both shoulders.

    A notch is a rounded slot cut down into the top face of the shoulder bar at the
    point the strap naturally sits. Cutters overshoot the bar in Y and in +Z so no
    coincident faces survive.
    """
    cutters = None
    notch_w = max(3.0, min(hook_wire * 0.9, 6.0))
    over = shoulder_t + 8.0
    for i in range(notch_count):
        # Space notches across the outer half of each shoulder — where a strap lands.
        f = 0.45 + 0.22 * (i + 1) / float(notch_count)
        f = min(f, 0.86)
        x = f * half_w
        h = _sec_at(f)[1]
        # The bar SLOPES across the notch's own width, so a Z-aligned cutter bites
        # deeper on its outboard side. Measure the bar top at both edges of the notch
        # and hang the cutter from the LOWER of the two, then cap the depth to a
        # fraction of the thinnest section under it — the notch must never sever the
        # shoulder, which is exactly how a steep-slope hanger split into two bodies.
        f_lo = max(0.0, (x - notch_w / 2.0) / half_w)
        f_hi = min(1.0, (x + notch_w / 2.0) / half_w)
        tops = []
        for ff in (f_lo, f, f_hi):
            tops.append(-_drop_at(ff) + _sec_at(ff)[1] / 2.0)
        bottoms = []
        for ff in (f_lo, f, f_hi):
            bottoms.append(-_drop_at(ff) - _sec_at(ff)[1] / 2.0)
        z_top = min(tops)
        # Leave at least 45 % of the local section as an unbroken land under the notch.
        land = max(2.0, h * 0.45)
        room = z_top - max(bottoms) - land
        if room < 1.0:
            # No safe notch depth at this station on this slope — omit it rather than
            # cut through. A hanger with fewer notches still hangs a garment.
            continue
        notch_d = min(shoulder_h * 0.42, 7.0, room)
        cut = (
            cq.Workplane("XY")
            .box(notch_w, over, notch_d + 6.0)
            .translate((x, 0, z_top - notch_d + (notch_d + 6.0) / 2.0))
        )
        try:
            cut = cut.edges("|Y").fillet(notch_w * 0.35)
        except Exception:
            pass
        mirror = cut.mirror(mirrorPlane="YZ")
        cutters = cut if cutters is None else cutters.union(cut)
        cutters = cutters.union(mirror)
    return cutters


# ── Hook (torus composition, never a swept arc) ──────────────────────────────
def _curl(rc, wire_d):
    """A three-quarter arc of `cq.Solid.makeTorus`, wrapped in a Workplane.

    A swept `radiusArc` path degenerates here, so the curl is a torus with ONE
    quadrant removed. Cutting a single quadrant (rather than assembling several) is
    deliberate: two abutting quadrants meet along a single tangent circle, which is a
    coincident surface, not an overlap — the union then reads as two detached bodies
    at larger wire diameters (observed at `hook_wire` 9.5). One cut, one solid.

    Result: a ring open at the +X/-Z quadrant, lying in the XZ plane, tube radius
    `wire_d / 2`, centred on the origin.
    """
    tor = cq.Workplane(obj=cq.Solid.makeTorus(rc, wire_d / 2.0))
    # makeTorus is centred at the origin in XY with its axis along Z. Rotate about X
    # so the ring lies in XZ — the plane the hook curls in.
    tor = tor.rotate((0, 0, 0), (1, 0, 0), 90)
    big = rc * 2.0 + wire_d * 4.0 + 20.0
    # One oversized box removes the +X/-Z quadrant, opening the hook mouth. Oversized
    # in every direction so no cut face is ever coincident with the torus surface.
    opener = (
        cq.Workplane("XY")
        .box(big, big, big)
        .translate((big / 2.0, 0, -big / 2.0))
    )
    return tor.cut(opener)


def _hook_pieces():
    """The rod hook as (stem, curl) — deliberately NOT pre-unioned.

    The curl is placed so the stem cylinder passes through REAL torus material rather
    than sitting coincident with the tube's -X extreme (which is what a naive
    placement does, and reads non-watertight).

    They are returned separately because OCCT's fuse is order-sensitive here:
    `bar.union(stem).union(curl)` is watertight while `bar.union(stem.union(curl))` —
    same geometry, pre-fused hook — is not. Callers must fold them in one at a time.
    """
    r = hook_wire / 2.0
    # `bite` shifts the curl inboard so the stem axis lands inside the tube wall
    # instead of exactly on its centreline extreme.
    cx = hook_rc - r * 0.8
    z0 = shoulder_h / 2.0 - r          # bury the stem root inside the shoulder bar
    z_curl = z0 + stem_len             # centre height of the curl torus
    # Run the stem past the curl centre height, so its overlap with the torus is a
    # volume rather than a tangency.
    stem = (
        cq.Workplane("XY")
        .circle(r)
        .extrude(stem_len + r * 1.2)
        .translate((0, 0, z0))
    )
    curl = _curl(hook_rc, hook_wire).translate((cx, 0, z_curl))
    return stem, curl


def _add_hook(body):
    """Fold the hook into `body` one piece at a time (see `_hook_pieces`)."""
    stem, curl = _hook_pieces()
    return body.union(stem).union(curl)


# ── Trouser bar (the second part of the trouser_bar mode) ────────────────────
def _bar_tip_z(f=1.0):
    """Z of the shoulder-bar centreline at fraction `f` out toward the tip."""
    return -slope * (1.0 - math.cos(math.pi * f)) / 2.0


bar_len = shoulder_w * 0.80          # the bar spans most of the shoulder, inset from tips
bar_dia = max(6.0, min(shoulder_t * 0.85, 14.0))
post_d = max(4.0, min(shoulder_t * 0.6, 8.0))   # the vertical posts that carry the bar


def build_bar():
    """The separate trouser bar: a horizontal rod between two vertical posts, with a
    seating boss at the top of each post that drops into the shoulder tip socket."""
    z_top = _bar_tip_z(0.80) - shoulder_h * 0.3
    z_bar = z_top - bar_drop
    x = bar_len / 2.0
    # Horizontal rod along X, running past both post centres so the union overlaps.
    rod = (
        cq.Workplane("YZ")
        .circle(bar_dia / 2.0)
        .extrude(bar_len + post_d)
        .translate((-(bar_len + post_d) / 2.0, 0, z_bar))
    )
    body = rod
    for sx in (-1.0, 1.0):
        post_h = z_top - z_bar + bar_dia
        post = (
            cq.Workplane("XY")
            .circle(post_d / 2.0)
            .extrude(post_h)
            .translate((sx * x, 0, z_bar - bar_dia / 2.0))
        )
        body = body.union(post)
        # Seating boss: a stubby pin that plugs into the shoulder tip socket.
        pin = (
            cq.Workplane("XY")
            .circle(post_d / 2.0 - 0.25)
            .extrude(post_d * 1.2)
            .translate((sx * x, 0, z_bar - bar_dia / 2.0 + post_h - 0.4))
        )
        body = body.union(pin)
    return body


def _bar_sockets(solid):
    """Cut the two pin sockets into the underside of the shoulder tips."""
    z_top = _bar_tip_z(0.80) - shoulder_h * 0.3
    x = bar_len / 2.0
    depth = post_d * 1.2
    for sx in (-1.0, 1.0):
        bore = (
            cq.Workplane("XY")
            .circle(post_d / 2.0 + 0.2)
            .extrude(depth + 2.0)
            .translate((sx * x, 0, z_top - 1.0))
        )
        solid = solid.cut(bore)
    return solid


# ── Part builders ────────────────────────────────────────────────────────────
def build_standard():
    """Plain hanger: shoulder bar + hook, one solid."""
    return _add_hook(_shoulder_bar())


def build_notched():
    """Hanger with strap notches cut into both shoulders."""
    body = _shoulder_bar()
    cutters = _strap_notches()
    if cutters is not None:
        body = body.cut(cutters)
    return _add_hook(body)


def build_body():
    """The trouser_bar mode's upper part: a notched hanger with tip sockets bored."""
    return _bar_sockets(build_notched())


# ── Dispatch ─────────────────────────────────────────────────────────────────
# Mode ids and part ids match the manifest exactly:
#   standard    -> parts ["standard"]
#   notched     -> parts ["notched"]
#   trouser_bar -> parts ["body", "bar"]
if target_part == "notched":
    result = build_notched()
elif target_part == "body":
    result = build_body()
elif target_part == "bar":
    result = build_bar()
else:
    result = build_standard()
