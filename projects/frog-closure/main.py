"""Frog Closure 盤扣 — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The Chinese knotted frog (盤扣 pánkòu): a knot-button on one side of a closure and a
loop on the other, each carried on a sewn tail. It is the closure of the changpao, the
qipao, the magua and the tangzhuang — the heritage lane's defining fastener, and the
one Fashion Cabinet bridge claim (`changpao`, FC-300 rank 299) that the y4d commons
had no solid for. Fashion Cabinet owns the fashion semantics — where the frogs sit
along the measured 大襟 dajin curve, spaced by ARC LENGTH, and how much bias strip each
one eats; this cartridge owns the hardware: the physical knot, loop and sew tails.

In cloth a pánkòu is a single bias strip hand-knotted into a ball at one end and bent
into a loop at the other. Printed rigid it becomes a two-part finding: the KNOT half
(ball + neck + sew tail) and the LOOP half (an open ring + sew tail). The pair spans
`span` millimetres knot-centre to loop-centre — the same span Fashion Cabinet's
`frog_width` measures, so a robe's finished frog drives this solid directly.

Modes (dispatched via `target_part`):
  * "pair"  — knot half + loop half, laid out as one closure at its finished span.
  * "knot"  — the knot-button half alone (ball + neck + tail).
  * "loop"  — the loop half alone (open ring + tail).

Geometry notes — the house lessons are load-bearing here:
  * The knot ball is a LOFT to flat top and bottom caps, never a sphere: a sphere's
    poles are a singularity that turns a boolean into a non-manifold shell
    (feedback_cadquery_sphere_pole_singularity). A flat-capped barrel also prints
    without support and reads as the flattened ball a real pánkòu actually is.
  * The loop is a `makeTorus` half-ring box-cut to an open C, never a swept
    `radiusArc` — swept arcs degenerate ("Arc radius is not large enough") at the
    small radii a garment frog uses (feedback_cadquery_swept_arc_use_maketorus).
  * Every union overlaps volumetrically (stems sink into their neighbours) so the
    fuse is a solid, not a coincident-face kiss.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `span`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
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
span      = float(PARAM(lambda: span,      56.0))  # knot centre to loop centre (mm)
knots     = int(  PARAM(lambda: knots,      1))    # knot/loop pairs on one tail run
knot_dia  = float(PARAM(lambda: knot_dia,  11.0))  # knot-ball diameter (mm)
tail_w    = float(PARAM(lambda: tail_w,     7.0))  # sew-tail width (mm)
tail_t    = float(PARAM(lambda: tail_t,     2.0))  # tail / cord thickness (mm)
loop_id   = float(PARAM(lambda: loop_id,   12.0))  # loop inner diameter (mm)
gap       = float(PARAM(lambda: gap,        0.4))  # knot-to-loop clearance (mm)

target_part = str(PARAM(lambda: target_part, "pair"))  # pair|knot|loop

# ── Safe clamps ──────────────────────────────────────────────────────────────
# Every clamp is two-sided and expressed against the manifest's own min/max, so a
# render at either extreme of any slider lands inside a buildable envelope.
span     = max(30.0, min(span, 110.0))
knots    = max(1, min(knots, 5))
knot_dia = max(5.0, min(knot_dia, 24.0))
tail_w   = max(3.0, min(tail_w, 16.0))
tail_t   = max(1.0, min(tail_t, 5.0))
loop_id  = max(4.0, min(loop_id, 30.0))
gap      = max(0.1, min(gap, 1.5))

# The loop must admit the knot: a loop narrower than the ball cannot close. Widen the
# ring's inner diameter rather than shrinking the knot, so the user's knot size — the
# visible feature — is always the one honoured.
loop_id = max(loop_id, knot_dia + 2.0 * gap)

# The tail must be at least as wide as the cord it carries, else the ring would stand
# proud of its own mount.
tail_w = max(tail_w, tail_t + 1.0)

# The pair's two halves each occupy roughly half the span; keep the ball and ring from
# colliding at the shortest span the manifest allows.
_half = span / 2.0
knot_dia = min(knot_dia, max(5.0, _half - 2.0))
loop_id = max(loop_id, knot_dia + 2.0 * gap)
loop_id = min(loop_id, max(knot_dia + 2.0 * gap, span - knot_dia - 4.0))

# Ring wall: the printed stand-in for the bias cord. Scaled off the tail thickness so
# it never vanishes at thin settings nor swamps a small loop.
ring_w = max(1.2, min(tail_t, loop_id / 3.0))

# LAST, because it depends on the final loop_id and ring_w: the tail must be no wider
# than the ring it mounts. A tail wider than the ring's OUTER diameter has its side
# walls land outside the ring entirely while its top face stays flush with the ring's
# flank — a tangential meeting rather than an overlap, which fuses into an open shell.
# This is how tail_w=max(16.0) first failed against a 16mm-outer ring. Capped here
# rather than inside the loop builder so the knot half, the loop half and the pair all
# share one tail width and the closure stays visually coherent.
tail_w = min(tail_w, (loop_id + 2.0 * ring_w) * 0.8)
tail_w = max(tail_w, 3.0)

# Tail run length — how far the sewn strip extends behind each half.
tail_len = max(6.0, min(span * 0.45, 40.0))


# Flat-cap radius as a fraction of the ball radius. Shared by `_ball` (which builds the
# cap) and `build_knot` (which must keep the neck stem strictly inside it) — a single
# constant so the two can never drift apart and silently re-open the non-manifold seam.
CAP_FRAC = 0.42


def _ball(dia, z0):
    """A knot ball as a flat-capped loft, centred on the origin in XY, sitting on z0.

    Deliberately NOT `cq.Workplane.sphere`: a sphere meets the stem at a pole, and a
    pole is a degenerate vertex that turns the union into a non-manifold shell
    (feedback_cadquery_sphere_pole_singularity). Three ruled sections — a flat base,
    a full-diameter equator, a flat top — give a watertight barrel with printable
    flat caps, which is also closer to a real knotted pánkòu than a true sphere.
    """
    r = dia / 2.0
    cap_r = r * CAP_FRAC      # flat cap: wide enough to print, small enough to read as a ball
    return (
        cq.Workplane("XY")
        .workplane(offset=z0)
        .circle(cap_r)
        .workplane(offset=r)
        .circle(r)
        .workplane(offset=r)
        .circle(cap_r)
        .loft(ruled=True)
    )


def _tail(length, y0):
    """The sewn tail: a flat strip lying along +Y from y0, centred on X.

    Straight segments only — an extruded rectangle. This is the surface the garment
    is stitched through, and the `sew_tail` CDG interface's geometry.
    """
    return (
        cq.Workplane("XY")
        .box(tail_w, length, tail_t, centered=(True, False, False))
        .translate((0.0, y0, 0.0))
    )


def build_knot():
    """The knot half: sew tail → neck stem → knot ball, fused with real overlap.

    Built at the origin with the tail running -Y and the ball centred on (0, 0).
    """
    ball_r = knot_dia / 2.0

    # Tail runs backwards (-Y) from just under the ball, overlapping it so the fuse
    # is volumetric rather than a coincident face.
    tail = _tail(tail_len + ball_r, -(tail_len + ball_r))

    # Neck stem: a short cylinder from the tail up into the ball. It overlaps BOTH
    # neighbours, which is what makes the three-way union a single watertight body.
    #
    # The neck must be strictly NARROWER than the ball's flat bottom cap. If it is
    # wider, its wall exits through the loft's base rim and meets the loft's flank
    # tangentially — a non-manifold kiss, not an overlap, and the union comes back as
    # an open shell. That is precisely how knot_dia=min(5.0) first failed: cap_r was
    # 1.05mm while the neck wanted 1.5mm. Bounding the neck by the cap keeps the stem
    # buried inside the ball at every knot size the manifest allows.
    cap_r = ball_r * CAP_FRAC
    neck_r = min(tail_w * 0.35, ball_r * 0.6, cap_r * 0.8)
    neck_r = max(0.5, neck_r)
    neck = (
        cq.Workplane("XY")
        .circle(neck_r)
        .extrude(tail_t + ball_r)
    )

    ball = _ball(knot_dia, tail_t * 0.5)

    return tail.union(neck).union(ball)


def build_loop():
    """The loop half: sew tail → open C ring the knot passes through.

    The ring is a makeTorus box-cut to a C, NOT a swept arc: at garment radii a
    swept `radiusArc` degenerates outright (feedback_cadquery_swept_arc_use_maketorus).
    The C opens toward -Y so the knot enters from the tail side.
    """
    r_mid = (loop_id + ring_w) / 2.0        # torus centreline radius
    z_mid = tail_t / 2.0                    # ring lies in the plane of the tail
    r_out = r_mid + ring_w / 2.0            # ring outer radius

    torus = cq.Solid.makeTorus(
        r_mid, ring_w / 2.0,
        pnt=cq.Vector(0.0, 0.0, z_mid),
        dir=cq.Vector(0, 0, 1),             # axis along Z → ring lies flat in XY
    )
    ring = cq.Workplane(obj=torus)

    # Open the C: cut a notch out of the ring's -Y side so the knot can enter. The notch
    # is a mouth, not a bisection — it leaves two horns still joined through the ring's
    # +Y arc.
    #
    # Its width is bounded on BOTH sides, and both bounds were found by the extremes
    # sweep rather than by inspection:
    #   * too wide  → the cut severs the ring into two arcs (the original 2-body fail);
    #   * too close to the bore → the cut's side walls land tangent to the ring's own
    #     inner wall, shaving a zero-thickness sliver that opens the mesh. That is how
    #     knot_dia=min(5.0) failed, where a 4.5mm mouth met a ~5.4mm bore.
    # Holding the mouth to a fraction of the BORE (not of the knot) keeps a real wall on
    # each horn at every combination the manifest allows.
    mouth_w = min(loop_id * 0.62, knot_dia * 0.9, loop_id - 1.2)
    mouth_w = max(mouth_w, min(1.0, loop_id * 0.3))
    mouth = (
        cq.Workplane("XY")
        .box(mouth_w, r_out * 2.0, ring_w * 4.0, centered=(True, False, True))
        .translate((0.0, -r_out * 2.0, z_mid))
    )
    ring = ring.cut(mouth)

    # Tail runs -Y, starting INSIDE the ring's solid material rather than at its rim:
    # it begins at +r_mid (the ring's far/+Y arc, which the mouth never touches) and
    # runs back past the horns. That single strip therefore overlaps the +Y arc and
    # both horns at once, fusing the C into one watertight body no matter how wide
    # the mouth is cut. Starting it at the -Y rim instead leaves the horns joined only
    # through the arc and the tail bridging nothing — the 2-body failure.
    tail = _tail(tail_len + r_mid * 2.0, -(tail_len + r_mid))

    return ring.union(tail)


def build_pair():
    """One complete closure: the knot half and the loop half at their finished span.

    The two halves are placed `span` apart along X — knot centre to loop centre, the
    exact quantity Fashion Cabinet's `frog_width` measures — and their tails run away
    from each other, as a frog sits on a garment: each tail sews to its own side of
    the opening. `knots` repeats the closure down the placket.

    Returned as a single fused Workplane rather than an Assembly, because the halves
    of one printed frog share a print bed and the platform's mesh bar reads one body
    per part. Halves are joined by a thin sprue at the tail ends — the same way a
    printed findings card holds its pieces until they are cut apart — so the part is
    one watertight solid, and snips into a working two-part closure.
    """
    knot = build_knot().translate((-span / 2.0, 0.0, 0.0))
    loop = build_loop().rotate((0, 0, 0), (0, 0, 1), 180.0).translate((span / 2.0, 0.0, 0.0))

    body = knot.union(loop)

    # Sprue: a thin rail joining the two tail ends so one part prints as one body.
    # Its thickness is deliberately a fraction of the tail so it snips cleanly.
    sprue_t = max(0.6, tail_t * 0.4)
    sprue = (
        cq.Workplane("XY")
        .box(span, tail_w * 0.5, sprue_t, centered=(True, True, False))
    )
    body = body.union(sprue)

    if knots > 1:
        # Repeat the closure down the placket. Pitch is set by the closure's own
        # footprint so repeats never intersect, and the run is joined by a spine rail
        # for the same one-body reason as the sprue.
        pitch = max(tail_w * 2.0, knot_dia * 1.6)
        run = body
        for i in range(1, knots):
            run = run.union(body.translate((0.0, -pitch * i, 0.0)))
        spine = (
            cq.Workplane("XY")
            .box(tail_w * 0.5, pitch * (knots - 1) + tail_w * 0.5, sprue_t,
                 centered=(True, True, False))
            .translate((0.0, -pitch * (knots - 1) / 2.0, 0.0))
        )
        body = run.union(spine)

    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "knot":
    result = build_knot()
elif target_part == "loop":
    result = build_loop()
else:
    result = build_pair()
