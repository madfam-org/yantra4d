"""Shoe Tree — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A one-piece compliant shoe tree: a toe form that fills the vamp, a flat-spring shank that
flexes along its length, and a heel pad that presses back into the counter. Commercial
cedar trees are a two-piece toe block on a sprung spindle; that assembly cannot print as
one solid, so this cartridge does what a printed part does well instead — the spring IS
the shank, a wide thin ribbon of material that stores the preload.

Modes (dispatched via `target_part`):
  * "solid"  — the plain one-piece tree.
  * "vented" — the same with a lattice of through-vents in the toe form, so a damp shoe
               dries through the tree rather than around it.
  * "pair"   — a left and a right laid out side by side on one plate.

Geometry: the toe form is a single lofted chain of rounded-rect sections following a real
last's taper (widest at the ball, narrowing and rising to the toe spring). The shank is a
tapered ribbon, and the heel pad another short loft. Everything is one continuous loft
chain plus overlapping unions — no coplanar touches, no sealed voids, no fillets after
the cuts.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `shoe_len`).
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
shoe_len   = float(PARAM(lambda: shoe_len,   270.0))  # inside length of the shoe (mm)
ball_w     = float(PARAM(lambda: ball_w,     98.0))   # width across the ball of the foot (mm)
toe_h      = float(PARAM(lambda: toe_h,      40.0))   # toe-box internal height (mm)
shank_t    = float(PARAM(lambda: shank_t,    4.0))    # spring shank thickness (mm)
heel_h     = float(PARAM(lambda: heel_h,     52.0))   # heel counter height (mm)
vent_rows  = int(  PARAM(lambda: vent_rows,  3))      # vent rows in the toe form

target_part = str(PARAM(lambda: target_part, "solid"))


# ── Safe clamps ──────────────────────────────────────────────────────────────
# EU 34 (~215 mm) to EU 50 (~330 mm) covers every wearable shoe.
shoe_len  = max(200.0, min(shoe_len, 340.0))
ball_w    = max(60.0,  min(ball_w, 135.0))
# A last is never wider than about half its length; clamp so no combination inverts.
ball_w    = min(ball_w, shoe_len * 0.48)
toe_h     = max(20.0,  min(toe_h, 70.0))
shank_t   = max(2.4,   min(shank_t, 9.0))
heel_h    = max(28.0,  min(heel_h, 90.0))
vent_rows = max(1,     min(vent_rows, 5))

# ── Last proportions (fractions of shoe_len, measured from the toe at x = 0) ──
TOE_END   = 0.00
BALL_X    = 0.30    # widest point of a last sits at ~30 % back from the toe
WAIST_X   = 0.58    # the shank waist
HEEL_X    = 1.00

toe_len   = shoe_len * 0.42        # length of the solid toe form
shank_len = shoe_len * 0.36        # the compliant ribbon between form and heel
heel_len  = shoe_len - toe_len - shank_len
# The shank is a WIDE, THIN ribbon: wide so it does not twist, thin so it flexes, and
# never a knife edge — the land is at least 2.4 mm everywhere.
shank_w   = max(shank_t * 3.0, ball_w * 0.30)
heel_w    = max(shank_w + 6.0, ball_w * 0.62)


def _sec(width, height):
    """A safe (width, height) pair — never zero, never inverted."""
    return max(2.0, width), max(2.0, height)


def _toe_form():
    """The toe block: one lofted chain of rounded-rect sections along +X.

    Section 0 is the toe tip (small, and lifted for toe spring), the widest section is
    at the ball, and the last section hands off to the shank. Built on ONE workplane
    chain closed by a single `loft`, so the block is a single solid with no internal
    seams to crack.
    """
    # (x fraction of toe_len, width fraction of ball_w, height fraction of toe_h, z lift)
    stations = [
        (0.00, 0.34, 0.42, toe_h * 0.16),   # toe tip, sprung up off the bed
        (0.14, 0.60, 0.68, toe_h * 0.07),
        (0.32, 0.84, 0.88, toe_h * 0.01),
        (0.55, 1.00, 1.00, 0.0),            # the ball: widest and tallest
        (0.78, 0.94, 0.90, 0.0),
        (1.00, 0.80, 0.74, 0.0),            # hand-off to the shank
    ]
    lofter = cq.Workplane("YZ")
    last_x = 0.0
    last_z = 0.0
    for (fx, fw, fh, lift) in stations:
        x = fx * toe_len
        w, h = _sec(ball_w * fw, toe_h * fh)
        z = lift + h / 2.0
        lofter = (
            lofter.workplane(offset=x - last_x)
            .center(0, z - last_z)
            .rect(w, h)
        )
        last_x = x
        last_z = z
    return lofter.loft(ruled=True)


def _shank():
    """The compliant spring: a wide thin ribbon narrowing to the waist and back out.

    One loft chain again. The ribbon's neutral axis sits at the toe form's mid-height
    so the flex is pure bending, and it OVERLAPS both the toe form and the heel pad by
    a real length rather than butting against them.
    """
    over = max(6.0, shoe_len * 0.03)   # overlap into the neighbouring solids
    z_mid = toe_h * 0.5
    stations = [
        (-over,                 1.00, 1.35),
        (shank_len * 0.28,      0.78, 1.00),
        (shank_len * 0.50,      0.70, 1.00),   # the waist: thinnest and narrowest
        (shank_len * 0.74,      0.82, 1.10),
        (shank_len + over,      1.15, 1.45),
    ]
    lofter = cq.Workplane("YZ")
    last_x = 0.0
    for (x, fw, ft) in stations:
        w, t = _sec(shank_w * fw, shank_t * ft)
        lofter = (
            lofter.workplane(offset=x - last_x)
            .center(0, 0)
            .rect(w, t)
        )
        last_x = x
    return lofter.loft(ruled=True).translate((toe_len, 0, z_mid))


def _heel_pad():
    """The heel pad: a short loft that fills the counter and presses on the back seam."""
    over = max(6.0, shoe_len * 0.03)
    z_mid = toe_h * 0.5
    stations = [
        (-over,             0.55, 0.45),
        (heel_len * 0.35,   0.86, 0.86),
        (heel_len * 0.72,   1.00, 1.00),
        (heel_len,          0.88, 0.92),   # the back face, still a real flat section
    ]
    lofter = cq.Workplane("YZ")
    last_x = 0.0
    last_z = 0.0
    for (x, fw, fh) in stations:
        w, h = _sec(heel_w * fw, heel_h * fh)
        # The pad grows downward and upward about the shank's neutral axis.
        z = 0.0
        lofter = (
            lofter.workplane(offset=x - last_x)
            .center(0, z - last_z)
            .rect(w, h)
        )
        last_x = x
        last_z = z
    x0 = toe_len + shank_len
    return lofter.loft(ruled=True).translate((x0, 0, z_mid))


def _vent_cutters():
    """Through-vents in the toe form, so a damp shoe dries through the tree.

    Every cutter overshoots BOTH faces of the block in Z, so no cut surface is ever
    coincident with the loft skin.
    """
    cutters = None
    vent_d = max(4.0, min(ball_w * 0.12, 14.0))
    over = toe_h * 2.0 + 20.0
    cols = 3
    for r in range(vent_rows):
        fx = 0.28 + 0.52 * (r + 0.5) / float(vent_rows)
        x = fx * toe_len
        # Width available at this station, from the toe-form taper.
        avail = ball_w * (0.84 + 0.16 * math.sin(math.pi * fx))
        span = avail - vent_d - 6.0
        if span <= vent_d:
            continue
        n = cols if span > vent_d * 2.6 else 1
        for c in range(n):
            fy = 0.0 if n == 1 else (c / float(n - 1)) - 0.5
            y = fy * span * 0.5
            cut = (
                cq.Workplane("XY")
                .circle(vent_d / 2.0)
                .extrude(over)
                .translate((x, y, -over / 2.0 + toe_h * 0.5))
            )
            cutters = cut if cutters is None else cutters.union(cut)
    return cutters


def build_solid():
    """The plain one-piece tree: toe form + spring shank + heel pad, unioned in order.

    Folded in one at a time rather than pre-fusing the shank to the heel — OCCT's fuse
    is order-sensitive on chained lofts, and the sequential form is the one that comes
    out watertight.
    """
    return _toe_form().union(_shank()).union(_heel_pad())


def build_vented():
    """The same tree with drying vents bored through the toe form.

    The vents are cut AFTER the three solids are fused, so a vent that happens to graze
    the shank overlap still cuts a clean through-hole rather than a blind pocket.
    """
    body = build_solid()
    cutters = _vent_cutters()
    if cutters is not None:
        body = body.cut(cutters)
    return body


def build_pair():
    """A left and a right side by side on one plate.

    The two are genuinely separate solids — mirrored, translated well apart, and
    combined as a compound rather than a union of non-touching bodies.
    """
    right = build_vented()
    left = right.mirror(mirrorPlane="XZ")
    gap = max(ball_w * 0.35, 24.0)
    off = ball_w / 2.0 + gap / 2.0
    a = right.translate((0, off, 0))
    b = left.translate((0, -off, 0))
    solids = []
    for wp in (a, b):
        for s in wp.vals():
            solids.append(s)
    return cq.Workplane(obj=cq.Compound.makeCompound(solids))


# ── Dispatch ─────────────────────────────────────────────────────────────────
# Mode ids and part ids match the manifest exactly:
#   solid  -> parts ["solid"]
#   vented -> parts ["vented"]
#   pair   -> parts ["pair"]
if target_part == "vented":
    result = build_vented()
elif target_part == "pair":
    result = build_pair()
else:
    result = build_solid()
