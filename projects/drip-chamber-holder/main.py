"""
Drip Chamber Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A real ward-workflow gap. The drip chamber of a gravity infusion set has to
hang VERTICAL and STILL for the drop count to mean anything — a chamber swinging
on its tubing gives a false rate, and a chamber tilted past a few degrees runs
dry or floods. This holder clips the chamber upright and rides the dovetail
accessory face of `iv-pole-clamp`, so the whole stack is one printed assembly
on any pole.

The chamber bore follows ISO 8536 gravity infusion sets: the drip chamber body
is nominally 15–22 mm across depending on the set, so the bore is a published
parameter with a real range rather than one hard-coded set.

Modes:
  - dovetail_holder : C-clip chamber cradle on a dovetail tongue (rides an
                      `iv-pole-clamp` dovetail face).
  - twin_holder     : two cradles on one tongue, for a piggyback / dual-line set.
  - tube_guide      : a small dovetail-mounted guide that routes the downstream
                      tubing so it does not tug the chamber out of vertical.

Watertight strategy: every body is ONE solid. The cradle is a full ring first,
then the mouth is cut once; the dovetail tongue is unioned with a 0.2 mm
overlap; every cut is full-depth. The mouth width is clamped to stay strictly
less than the bore diameter so the C never opens into two arcs, and the tongue
is clamped inside the body width so the union can never leave a floating stub.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

A printable ward convenience, not a certified medical device. It holds the
chamber; it does not regulate flow. Nothing here replaces a clinician reading
the actual drip rate, and it must not be used with a device whose fall or
mis-rate could harm a patient.
"""

import math

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
target_part = str(PARAM(lambda: target_part, "dovetail_holder"))
# "dovetail_holder" | "twin_holder" | "tube_guide"

chamber_dia = float(PARAM(lambda: chamber_dia, 18.0))  # drip chamber body dia (ISO 8536)
chamber_fit = float(PARAM(lambda: chamber_fit,  0.4))  # per-side cradle clearance
cradle_h    = float(PARAM(lambda: cradle_h,    24.0))  # cradle height along the chamber
wall        = float(PARAM(lambda: wall,         3.4))  # cradle wall thickness
mouth_frac  = float(PARAM(lambda: mouth_frac,   0.72)) # mouth width / bore dia — the snap
dove_w      = float(PARAM(lambda: dove_w,      18.0))  # dovetail width (matches iv-pole-clamp)
dove_h      = float(PARAM(lambda: dove_h,       8.0))  # dovetail projection depth
dove_angle  = float(PARAM(lambda: dove_angle,  60.0))  # dovetail flank angle
stack_gap   = float(PARAM(lambda: stack_gap,   30.0))  # centre spacing (twin_holder)
tube_dia    = float(PARAM(lambda: tube_dia,     4.4))  # infusion tubing OD (tube_guide)

# ── Clamps ───────────────────────────────────────────────────────────────────
chamber_dia = max(8.0,  min(chamber_dia, 60.0))
chamber_fit = max(0.0,  min(chamber_fit, 2.5))
cradle_h    = max(6.0,  min(cradle_h, 90.0))
wall        = max(2.0,  min(wall, 12.0))
mouth_frac  = max(0.35, min(mouth_frac, 0.95))
dove_w      = max(6.0,  min(dove_w, 80.0))
dove_h      = max(2.0,  min(dove_h, 40.0))
dove_angle  = max(40.0, min(dove_angle, 80.0))
stack_gap   = max(10.0, min(stack_gap, 200.0))
tube_dia    = max(1.5,  min(tube_dia, 20.0))

# ── Derived, clamped so the C-ring can never be severed ──────────────────────
R_BORE = chamber_dia / 2.0 + chamber_fit
R_OUT = R_BORE + wall
# The mouth must be strictly narrower than the bore, or the ring opens into two
# free arcs (two bodies). Hard-capped at 0.95 of the bore diameter.
MOUTH = min(mouth_frac * 2.0 * R_BORE, 2.0 * R_BORE - 0.6)
MOUTH = max(0.8, MOUTH)

# Dovetail tongue on the -Y face.
DOVE_W = min(dove_w, 2.0 * R_OUT * 0.9)
DOVE_W = max(3.0, DOVE_W)
DOVE_H = min(dove_h, R_OUT * 1.5)
DOVE_H = max(1.0, DOVE_H)
FLANK = math.radians(90.0 - dove_angle)
DOVE_NARROW = max(1.5, DOVE_W - 2.0 * DOVE_H * math.tan(FLANK))
DOVE_NARROW = min(DOVE_NARROW, DOVE_W - 0.4)

# Twin spacing must be at least enough that the two cradles do not fully merge
# into an unrecognisable blob; they may touch (that is fine — still one body).
GAP = max(stack_gap, 2.0 * R_OUT * 0.55)

# Tube guide.
R_TUBE = tube_dia / 2.0
GUIDE_R = R_TUBE + max(1.6, wall * 0.5)
GUIDE_MOUTH = min(2.0 * R_TUBE * 0.7, 2.0 * R_TUBE - 0.4)
GUIDE_MOUTH = max(0.5, GUIDE_MOUTH)


# ── Helpers ──────────────────────────────────────────────────────────────────
def cradle(y_off=0.0, h=None):
    """A C-shaped cradle: full ring first, ONE mouth cut. The mouth opens on
    +Y (away from the pole) so the chamber snaps in from the front."""
    hh = cradle_h if h is None else h
    ring = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, y_off, 0))
        .circle(R_OUT)
        .extrude(hh)
    )
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, y_off, -1.0))
        .circle(R_BORE)
        .extrude(hh + 2.0)
    )
    ring = ring.cut(bore)
    mouth = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, y_off, -1.0))
        .box(MOUTH, R_OUT * 2.2, hh + 2.0, centered=(True, False, False))
    )
    return ring.cut(mouth)


def dovetail(y_face, h, z0=0.0):
    """Trapezoid tongue on the -Y side: narrow at the body, wide at the tip.
    Sketched flat on XY and extruded up Z, so the slide axis is vertical — the
    holder drops onto the clamp's dovetail from above and gravity seats it."""
    prof = (
        cq.Workplane("XY")
        .polyline(
            [
                (-DOVE_NARROW / 2.0, 0.0),
                (DOVE_NARROW / 2.0, 0.0),
                (DOVE_W / 2.0, -DOVE_H),
                (-DOVE_W / 2.0, -DOVE_H),
            ]
        )
        .close()
        .extrude(h)
    )
    # y_face is already 0.2 mm INSIDE the body, so the union always overlaps.
    return prof.translate((0, y_face, z0))


# ── Part builders ────────────────────────────────────────────────────────────
def build_dovetail_holder():
    body = cradle()
    body = body.union(dovetail(-R_OUT + 0.2, cradle_h))
    return body


def build_twin_holder():
    """Two cradles stacked along Z on one continuous tongue — a piggyback set.

    Stacking vertically (not side by side) keeps both chambers on the pole
    centreline, which is what actually matters for the drop count."""
    total_h = cradle_h * 2.0 + GAP
    a = cradle()
    b = cradle().translate((0, 0, cradle_h + GAP))
    # The tongue runs the FULL height, so it physically bridges both cradles —
    # they are never two floating rings.
    tongue = dovetail(-R_OUT + 0.2, total_h)
    # A spine on the back ties the cradles together even where the tongue is
    # narrower than the ring: a slab from the tongue root into both rings.
    spine_w = min(DOVE_NARROW, 2.0 * R_OUT * 0.7)
    spine_w = max(2.0, spine_w)
    spine_d = max(1.5, wall * 0.8)
    spine = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -R_OUT + 0.2 - spine_d / 2.0, 0))
        .box(spine_w, spine_d + 0.4, total_h, centered=(True, True, False))
    )
    return a.union(b).union(spine).union(tongue)


def build_tube_guide():
    """A small snap guide that routes the downstream tubing so it cannot tug
    the chamber off vertical. Same dovetail, much smaller ring."""
    h = max(6.0, cradle_h * 0.35)
    ring = cq.Workplane("XY").circle(GUIDE_R).extrude(h)
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(R_TUBE)
        .extrude(h + 2.0)
    )
    ring = ring.cut(bore)
    mouth = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .box(GUIDE_MOUTH, GUIDE_R * 2.2, h + 2.0, centered=(True, False, False))
    )
    ring = ring.cut(mouth)
    # Dovetail sized to the guide, never wider than the guide body.
    gw = min(DOVE_W, 2.0 * GUIDE_R * 0.9)
    gw = max(2.5, gw)
    gh = min(DOVE_H, GUIDE_R * 1.5)
    gh = max(1.0, gh)
    gn = max(1.2, gw - 2.0 * gh * math.tan(FLANK))
    gn = min(gn, gw - 0.3)
    tongue = (
        cq.Workplane("XY")
        .polyline(
            [
                (-gn / 2.0, 0.0),
                (gn / 2.0, 0.0),
                (gw / 2.0, -gh),
                (-gw / 2.0, -gh),
            ]
        )
        .close()
        .extrude(h)
        .translate((0, -GUIDE_R + 0.2, 0))
    )
    return ring.union(tongue)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "twin_holder":
    result = build_twin_holder()
elif target_part == "tube_guide":
    result = build_tube_guide()
else:  # "dovetail_holder"
    result = build_dovetail_holder()
