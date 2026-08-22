"""Trouser Hook & Bar — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The heavy waistband closure of tailored trousers, pencil skirts, culottes and suit
skirts: a flat hook plate whose tongue folds back on itself, and a flat bar plate
carrying a raised bridge the tongue drops behind. It is a different animal from the
bra-weight `hook-and-eye` — wider, thicker, and sewn flat inside a waistband so the
closure carries load without showing through. This is the rigid hard good the Fashion
Cabinet waistband notions place and bridge to here for their geometry; the garment
cartridge owns the waistband and placement math, this owns the hardware.

Modes (dispatched via `target_part`):
  * "set"  — hook plate and bar plate laid side by side, as sewn on a waistband.
  * "hook" — the hook plate alone (the tongue side, sewn to the overlap).
  * "bar"  — the bar plate alone (the catch side, sewn to the underlap).

Geometry: both parts start as a rounded flat plate (box + vertical-edge fillets) with
a single linear array of sew holes cut through in one pushPoints/cutThruAll pass. The
hook plate adds a folded-back tongue — a straight stub plus a quarter-arc bend trimmed
out of a full `cq.Solid.makeTorus` with oversized boxes (never a swept radiusArc). The
bar plate adds a raised bridge: two posts and a crossbar cylinder. The hook mouth
opening is held at `wire_d + gap` so the printed tongue clears the printed bar.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `hook_width`).
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
hook_width = float(PARAM(lambda: hook_width, 10.0))  # plate / hook width (mm)
plate_len  = float(PARAM(lambda: plate_len,  14.0))  # plate length along the band (mm)
plate_t    = float(PARAM(lambda: plate_t,    1.6))   # plate thickness (mm)
wire_d     = float(PARAM(lambda: wire_d,     1.6))   # tongue / crossbar stock diameter (mm)
sew_holes  = int(  PARAM(lambda: sew_holes,  4))     # sew holes per plate
gap        = float(PARAM(lambda: gap,        0.35))  # hook-to-bar print clearance (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|hook|bar

# ── Safe clamps ──────────────────────────────────────────────────────────────
hook_width = max(6.0, min(hook_width, 20.0))
plate_len  = max(8.0, min(plate_len, 25.0))
plate_t    = max(1.2, min(plate_t, 3.0))
wire_d     = max(1.0, min(wire_d, 3.0))
sew_holes  = max(2, min(sew_holes, 8))
gap        = max(0.2, min(gap, 0.8))

# Cross-parameter clamps — make invalid combinations impossible.
# Stock must stay slim relative to the plate it grows from.
wire_d = min(wire_d, hook_width * 0.35, plate_len * 0.25)
wire_d = max(0.8, wire_d)
# Sew holes: keep them small enough to leave material on a narrow plate.
_hole_r = max(0.5, min(wire_d * 0.5, hook_width * 0.16))
# Holes sit on a single row along X; the row must fit inside the plate length.
_row_len = max(2.0, plate_len - 2.0 * (_hole_r + 1.2))
if sew_holes > 1 and _row_len / (sew_holes - 1) < 2.2 * _hole_r:
    sew_holes = max(2, math.floor(_row_len / (2.2 * _hole_r)) + 1)

# Derived closure geometry.
MOUTH = wire_d + gap                 # clear opening the tongue leaves for the bar
# Bend centreline radius. The tongue leaves the plate on its mid-plane (z = plate_t/2),
# turns through a quarter arc and comes back over the plate with its underside at
# plate_t + MOUTH. That fixes the radius: plate_t/2 + 2*_bend_r - wire_d/2 = plate_t+MOUTH
# so the printed bar (wire_d) plus clearance (gap) always fits the hook mouth.
_bend_r = (plate_t / 2.0 + MOUTH + wire_d / 2.0) / 2.0
_bend_r = max(_bend_r, wire_d * 0.75)  # keep the arc printable, never degenerate
_tongue_w = max(2.0, hook_width * 0.55)  # width of the folded tongue across the plate (clamped below)
_stub = max(1.5, plate_len * 0.28)   # straight run before the bend
_pad = _hole_r + 1.2                 # margin from the plate end to the hole row

# Corner fillet radius of the plate. Anything fused ONTO the plate must stay clear of
# the filleted corners, or it meets the plate tangentially and the boolean produces a
# grazing near-coincident face (reads non-watertight).
_fillet_r = min(plate_len, hook_width) * 0.2
# The fillet must leave a flat core wide enough to stand the bridge posts and the tongue
# on. Shrink it (rather than letting features graze the rounded corners) on small plates.
_fillet_r = min(_fillet_r, (hook_width - wire_d * 2.0 - 1.6) / 2.0,
                (plate_len - wire_d * 2.0 - 1.6) / 2.0)
# A sliver fillet buys nothing visually but leaves a near-tangent sliver face for every
# feature standing near the corner to graze. Below this threshold, square the corners.
_fillet_r = _fillet_r if _fillet_r >= 0.4 else 0.0
# Safe inboard limits for features standing on the plate face.
_safe_x = plate_len / 2.0 - _fillet_r - wire_d / 2.0 - 0.3
_safe_y = hook_width / 2.0 - _fillet_r - wire_d / 2.0 - 0.3
# Tongue must also stay within the plate's flat core across Y.
_tongue_w = min(_tongue_w, max(1.6, hook_width - 2.0 * _fillet_r - 0.6))


def _plate():
    """A rounded flat sewing plate on XY, base z=0, centred in X and Y."""
    p = cq.Workplane("XY").box(plate_len, hook_width, plate_t, centered=(True, True, False))
    if _fillet_r > 0.0:
        try:
            p = p.edges("|Z").fillet(_fillet_r)
        except Exception:
            pass
    return p


def _sew_hole_points():
    """A single linear row of sew-hole centres along X near the sewing end (-X)."""
    if sew_holes <= 1:
        return [(-plate_len / 2.0 + _pad, 0.0)]
    # Row runs across the sewing half of the plate, offset toward -X.
    x0 = -plate_len / 2.0 + _pad
    x1 = min(plate_len / 2.0 - _pad, x0 + _row_len * 0.75)
    span = max(0.0, x1 - x0)
    n = sew_holes
    return [(x0 + span * i / (n - 1), 0.0) for i in range(n)]


def _drill(plate):
    """Cut the whole sew-hole row in ONE pushPoints/cutThruAll pass."""
    pts = _sew_hole_points()
    try:
        plate = (
            plate.faces(">Z")
            .workplane(centerOption="CenterOfBoundBox")
            .pushPoints(pts)
            .circle(_hole_r)
            .cutThruAll()
        )
    except Exception:
        pass
    return plate


def _tongue():
    """The folded-back tongue: a straight stub off the +X plate end, then a quarter-arc
    bend that turns it back over the plate, leaving a MOUTH-wide opening. The bend is a
    quarter cut out of a full makeTorus with oversized boxes (never a swept arc)."""
    tube_r = wire_d / 2.0
    x_end = plate_len / 2.0                     # plate end the tongue grows from
    # Centre the stub on the plate's mid-plane and keep its thickness strictly LESS than
    # the plate, so the embedded run is a true volumetric overlap. If the stub were as
    # thick as the plate its top and bottom faces would be coincident with the plate's
    # and the fuse would leave two disjoint bodies instead of one solid.
    stub_t = min(wire_d, max(0.6, plate_t - 0.5))
    z_low = plate_t / 2.0                       # centreline of the straight stub

    # Straight stub running +X out of the plate end. It must start far enough inboard to
    # bite the FLAT core of the plate (past the corner fillets), otherwise it only grazes
    # the rounded end and fuses as a separate body.
    stub_x0 = min(x_end - _fillet_r - 0.4, _safe_x)
    stub = (
        cq.Workplane("YZ")
        .center(0.0, z_low)
        .rect(_tongue_w, stub_t)
        # Run PAST the bend's start plane so the stub and the bend quarter share volume
        # rather than meeting on a single tangent face.
        .extrude(_stub + (x_end - stub_x0) + tube_r)
        .translate((stub_x0, 0, 0))
    )

    # Quarter-arc bend: torus axis along Y so the ring lies in the XZ plane.
    bend_cx = x_end + _stub
    bend_cz = z_low + _bend_r
    torus = cq.Solid.makeTorus(
        _bend_r, tube_r,
        pnt=cq.Vector(bend_cx, 0.0, bend_cz),
        dir=cq.Vector(0, 1, 0),
    )
    bend = cq.Workplane(obj=torus)
    big = (_bend_r + tube_r) * 4.0 + 4.0
    # Keep only the quarter with x >= bend_cx and z <= bend_cz (the fold-back turn).
    keep_cut_a = (
        cq.Workplane("XY")
        .box(big, big, big, centered=(True, True, True))
        .translate((bend_cx - big / 2.0, 0, bend_cz))
    )
    keep_cut_b = (
        cq.Workplane("XY")
        .box(big, big, big, centered=(True, True, True))
        .translate((bend_cx, 0, bend_cz + big / 2.0))
    )
    bend = bend.cut(keep_cut_a).cut(keep_cut_b)
    # The bend and return leg stay round stock (a real folded wire tongue); the flat
    # stub carries the tongue width. All three fuse by volumetric overlap.

    # Return leg: the quarter turn ends at the ring's side, where the centreline is at
    # x = bend_cx + _bend_r and z = bend_cz and the tangent is horizontal. The leg starts
    # there and heads back toward -X over the plate, forming the fold-back that leaves a
    # MOUTH-wide opening. It starts PAST that end face so the two share volume.
    ret_len = _stub + plate_len * 0.18
    ret_z = bend_cz
    ret = (
        cq.Workplane("YZ")
        .center(0.0, ret_z)
        .circle(tube_r)
        .extrude(-(ret_len + tube_r * 2.0))
        .translate((bend_cx + _bend_r + tube_r, 0, 0))
    )

    tongue = stub.union(bend).union(ret)
    return tongue


def build_hook():
    """Hook plate: rounded sewing plate + folded-back tongue."""
    plate = _drill(_plate())
    return plate.union(_tongue())


def _bridge():
    """The raised catch bridge: two posts at the plate's catch end and a crossbar
    cylinder spanning them, high enough to admit the tongue (MOUTH clearance)."""
    tube_r = wire_d / 2.0
    # Posts must land on the FLAT part of the plate, clear of the corner fillets, or the
    # union grazes the fillet surface tangentially and reads non-watertight.
    # `_safe_y` already accounts for the tube radius, so 2*_safe_y is the widest post
    # spacing whose OUTER edge still sits on the flat core. Never floor it above that:
    # a post tangent to the corner fillet grazes it and reads non-watertight.
    span = min(max(2.5, hook_width * 0.62), 2.0 * _safe_y)
    span = max(span, 0.0)
    bar_z = plate_t + MOUTH + tube_r
    cx = min(plate_len / 2.0 - max(_pad, wire_d * 1.4), _safe_x)

    posts = None
    for py in (-span / 2.0, span / 2.0):
        post = (
            cq.Workplane("XY")
            .center(cx, py)
            .circle(tube_r)
            # Stop the post below the crossbar's top tangent plane for the same reason.
            .extrude(bar_z + tube_r * 0.5)
            .translate((0, 0, -0.4))  # sink into the plate for a solid fuse
        )
        posts = post if posts is None else posts.union(post)

    # Stop the crossbar's end caps WELL INSIDE the posts. Running it to exactly
    # span/2 + tube_r puts each flat cap on the post's outer tangent plane — a
    # near-coincident surface that tessellates with cracks. Overlapping the posts by a
    # clear fraction of their radius keeps the fuse volumetric and the mesh closed.
    crossbar = (
        cq.Workplane("XZ")
        .center(cx, bar_z)
        .circle(tube_r)
        .extrude(span / 2.0 + tube_r * 0.5, both=True)
    )
    return posts.union(crossbar)


def build_bar():
    """Bar plate: rounded sewing plate + raised crossbar bridge."""
    plate = _drill(_plate())
    return plate.union(_bridge())


# ── Dispatch ─────────────────────────────────────────────────────────────────
# The platform renders PER PART: for every id in a mode's `parts[]` the worker
# injects that id as `target_part`. These branches must cover the manifest's part
# ids exactly — `hook_plate` and `bar_plate` — or a part falls through and renders
# the whole set instead of itself. The short names are kept as legacy aliases.
if target_part in ("hook_plate", "hook"):
    result = build_hook()
elif target_part in ("bar_plate", "bar"):
    result = build_bar()
else:
    set_gap = max(3.0, hook_width * 0.4)
    dy = hook_width + set_gap
    result = build_hook().translate((0, dy / 2.0, 0)).union(
        build_bar().rotate((0, 0, 0), (0, 0, 1), 180.0).translate((0, -dy / 2.0, 0)))
