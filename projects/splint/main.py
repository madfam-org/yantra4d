"""
Finger / Wrist Splint — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An adjustable immobilization splint that wraps a limb. Sized by the diameter it
wraps (finger or wrist). The body is an open-back contoured shell (a partial tube
with wall thickness) so it slips on and is secured with straps; ventilation holes
keep it breathable.

  * "finger_splint" — a near-full trough for a finger, open on top
                      (target_part == "finger_splint").
  * "wrist_brace"   — a longer, shallower curved brace with a ventilation pattern
                      and strap slots (target_part == "wrist_brace").
  * "mallet_splint" — a short fingertip splint, closed at the tip end, to hold a
                      mallet finger extended (target_part == "mallet_splint").

Watertight strategy: the shell is the region between two coaxial cylinders swept
through a partial arc — a C-channel cross-section that is a single manifold solid
(like a gutter). The mallet tip adds a solid domed cap. Ventilation holes are
radial through-cuts in the wall; strap slots are through-cuts near the edges.
Every result is one manifold solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
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
target_part = str(PARAM(lambda: target_part, "finger_splint"))
splint_type = str(PARAM(lambda: splint_type, "finger"))  # finger | wrist | mallet (mirror)

limb_dia   = float(PARAM(lambda: limb_dia,  18.0))    # finger/wrist diameter it wraps (mm)
length     = float(PARAM(lambda: length,    70.0))    # splint length along the limb (mm)
wall       = float(PARAM(lambda: wall,       3.0))    # shell wall thickness (mm)
clearance  = float(PARAM(lambda: clearance,  1.0))    # gap over the skin (mm)
wrap       = float(PARAM(lambda: wrap,     240.0))    # wrap angle of the shell (deg)
vents      = bool( PARAM(lambda: vents,     True))    # ventilation hole pattern
straps     = int(  PARAM(lambda: straps,       2))    # number of strap slot pairs

# ── Clamps ───────────────────────────────────────────────────────────────────
limb_dia   = max(8.0,   min(limb_dia, 90.0))
length     = max(20.0,  min(length, 220.0))
wall       = max(2.0,   min(wall, 6.0))
clearance  = max(0.3,   min(clearance, 3.0))
wrap       = max(160.0, min(wrap, 320.0))
straps     = max(0,     min(straps, 6))

R_IN = limb_dia / 2.0 + clearance     # inner shell radius
R_OUT = R_IN + wall                   # outer shell radius


# ── Core: a partial-arc C-channel shell along +Z ──────────────────────────────
def shell(wrap_deg, seg_len):
    """The solid between R_IN and R_OUT swept through wrap_deg degrees, extruded
    seg_len along Z. Opening faces +Y (up), centred so the gap is symmetric.

    Built as a full annulus minus a pie wedge for the open sector — robust and
    always watertight."""
    body = (
        cq.Workplane("XY")
        .circle(R_OUT)
        .circle(R_IN)
        .extrude(seg_len)
    )
    open_deg = 360.0 - wrap_deg
    if open_deg > 1.0:
        # Remove a wedge centred on +Y (90 deg) to open the top.
        half = math.radians(open_deg / 2.0)
        big = R_OUT + 10.0
        a0 = math.radians(90.0) - half
        a1 = math.radians(90.0) + half
        pts = [(0.0, 0.0)]
        steps = 24
        for i in range(steps + 1):
            a = a0 + (a1 - a0) * i / steps
            pts.append((big * math.cos(a), big * math.sin(a)))
        wedge = (
            cq.Workplane("XY")
            .polyline(pts)
            .close()
            .extrude(seg_len + 2.0)
            .translate((0, 0, -1.0))
        )
        body = body.cut(wedge)
    return body


def _vent_holes(seg_len):
    """Radial through-holes in the wall in a staggered pattern along the shell."""
    holes = None
    hole_r = min(2.6, wall * 1.4)
    rows = max(2, int(seg_len / 16.0))
    cols = 3
    for r in range(rows):
        z = 10.0 + (seg_len - 20.0) * (r / max(rows - 1, 1))
        stagger = (r % 2) * (0.5)
        for c in range(cols):
            # Spread holes across the closed part of the wrap (avoid the opening).
            frac = (c + 0.5 + stagger) / (cols + 1)
            ang = math.radians(90.0 + 180.0) + math.radians((frac - 0.5) * (wrap - 40.0))
            x = math.cos(ang)
            y = math.sin(ang)
            hole = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector((R_IN - 1.0) * x, (R_IN - 1.0) * y, z),
                             rotate=cq.Vector(90.0, 0.0, math.degrees(ang) + 90.0))
                .circle(hole_r)
                .extrude(wall + 2.0)
            )
            holes = hole if holes is None else holes.union(hole)
    return holes


def _strap_slots(seg_len, n):
    """Pairs of through-slots near the two open edges so a strap threads across."""
    if n <= 0:
        return None
    slots = None
    slot_w = 3.0
    slot_l = min(16.0, R_IN * 1.2)
    edge_ang = math.radians(90.0 + (wrap / 2.0) - 12.0)  # just inside one edge
    for side in (-1.0, 1.0):
        a = math.radians(90.0) + side * (edge_ang - math.radians(90.0))
        x = math.cos(a)
        y = math.sin(a)
        for i in range(n):
            z = seg_len * (i + 1) / (n + 1)
            slot = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector((R_IN + wall / 2.0) * x, (R_IN + wall / 2.0) * y, z),
                             rotate=cq.Vector(90.0, 0.0, math.degrees(a) + 90.0))
                .box(slot_w, slot_l, wall + 2.0, centered=(True, True, True))
            )
            slots = slot if slots is None else slots.union(slot)
    return slots


def build_finger():
    body = shell(wrap, length)
    if vents:
        v = _vent_holes(length)
        if v is not None:
            body = body.cut(v)
    s = _strap_slots(length, straps)
    if s is not None:
        body = body.cut(s)
    return body


def build_wrist():
    # Wrist brace: shallower wrap, longer, always ventilated, more straps.
    w = min(wrap, 220.0)
    body = shell(w, length)
    v = _vent_holes(length)
    if v is not None:
        body = body.cut(v)
    s = _strap_slots(length, max(straps, 2))
    if s is not None:
        body = body.cut(s)
    return body


def build_mallet():
    # Short, fuller wrap, closed tip to hold the fingertip extended.
    seg = min(length, 55.0)
    body = shell(max(wrap, 260.0), seg)
    try:
        body = body.union(_mallet_tip(seg))
    except Exception:
        # Fallback: a plain solid disc cap if the loft is degenerate.
        body = body.union(
            cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, seg)).circle(R_OUT).extrude(wall)
        )
    if vents:
        v = _vent_holes(seg)
        if v is not None:
            body = body.cut(v)
    return body


def _mallet_tip(seg):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, seg))
        .circle(R_OUT)
        .workplane(offset=R_OUT * 0.7)
        .circle(R_OUT * 0.3)
        .loft(combine=True)
    )


# ── Dispatch ─────────────────────────────────────────────────────────────────
_part = target_part
if _part == "finger_splint" and splint_type in ("wrist", "mallet"):
    _part = "wrist_brace" if splint_type == "wrist" else "mallet_splint"

if _part == "wrist_brace":
    result = build_wrist()
elif _part == "mallet_splint":
    result = build_mallet()
else:  # "finger_splint"
    result = build_finger()
