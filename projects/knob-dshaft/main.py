"""
D-Shaft Replacement Knob — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A right-to-repair replacement knob for a drawer, cabinet, appliance, or dial. The
user measures the broken shaft and picks the matching bore: a round hole, a
single D-flat, a double-D (two flats), or a splined bore. The knob body can be a
plain cylinder, a knurled-style grippy barrel, or a fluted (scalloped) barrel.

Modes (dispatched via `target_part`):
  * "knob"         — the plain replacement knob.
  * "pointer_knob" — adds a raised indicator line up the side + across the top so
                     it reads as a dial pointer (volume / temperature / mode).

Bore geometry:
  * round      — a plain circular bore of `shaft_dia`.
  * D-flat     — a circle with ONE flat chord cut at `flat_depth` from the wall
                 (the classic potentiometer / appliance D-shaft).
  * double-D   — two opposing flats (a shaft flatted on both sides).
  * splined    — a ring of small teeth (knurled/serrated insert shaft); the
                 nominal diameter matches `shaft_dia` so it press-fits a splined
                 post. Real spline counts vary; 20 teeth suits common 6 mm posts.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `shaft_dia`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
knob_dia    = float(PARAM(lambda: knob_dia,     30.0))   # knob outer diameter (mm)
knob_height = float(PARAM(lambda: knob_height,  18.0))   # knob height (mm)
style       = str(  PARAM(lambda: style, "cylindrical")) # "cylindrical"|"knurled"|"fluted"
bore_type   = str(  PARAM(lambda: bore_type,  "D-flat")) # round|D-flat|double-D|splined
shaft_dia   = float(PARAM(lambda: shaft_dia,     6.0))   # measured shaft diameter (mm)
flat_depth  = float(PARAM(lambda: flat_depth,    0.5))   # depth of the D flat from the wall
bore_depth  = float(PARAM(lambda: bore_depth,   14.0))   # how deep the bore goes (mm)
setscrew    = bool( PARAM(lambda: setscrew,    False))   # radial set-screw hole
setscrew_dia = float(PARAM(lambda: setscrew_dia, 3.2))   # set-screw clearance (≈ M3)
top_round   = bool( PARAM(lambda: top_round,    True))   # dome / round the top edge

target_part = str(  PARAM(lambda: target_part, "knob"))  # "knob" | "pointer_knob"


# ── Derived / clamped geometry ───────────────────────────────────────────────
knob_dia = max(10.0, knob_dia)
knob_height = max(6.0, knob_height)
shaft_dia = max(2.0, min(shaft_dia, knob_dia - 4.0))  # leave a wall around the bore
shaft_r = shaft_dia / 2.0
bore_depth = max(3.0, min(bore_depth, knob_height - 1.5))  # keep a closed top cap
# A D-flat can't cut past the shaft centre; clamp it under the radius.
flat_depth = max(0.0, min(flat_depth, shaft_r - 0.6))
CLR = 0.2  # print clearance added to the bore so it slips onto the shaft


# ── Bore cutter ──────────────────────────────────────────────────────────────
def round_cutter(length):
    """A plain cylindrical bore cutter of the (clearance-adjusted) shaft radius."""
    return cq.Workplane("XY").circle(shaft_r + CLR).extrude(length)


def splined_cutter(length):
    """A gear-like ring of teeth. Nominal (tooth-tip) diameter == shaft_dia so it
    grips a serrated insert post. Built as a star polygon of 2*n points."""
    r = shaft_r + CLR
    n = 20
    tip = r
    root = r - min(0.6, shaft_r * 0.18)
    pts = []
    for i in range(2 * n):
        ang = math.pi * i / n
        rad = tip if (i % 2 == 0) else root
        pts.append((rad * math.cos(ang), rad * math.sin(ang)))
    return cq.Workplane("XY").polyline(pts).close().extrude(length)


def flatted_cutter(length):
    """Cylindrical bore with one (D-flat) or two opposing (double-D) flats cut in.
    The flat sits `flat_depth` in from the wall on the +X side (and −X for a
    double-D), modelling a real flatted shaft as a circle with a chord."""
    r = shaft_r + CLR
    cutter = round_cutter(length)
    # Keep x <= r - flat_depth on the +X side: subtract the outboard sliver.
    sliver = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector((r - flat_depth) + r, 0, length / 2.0))
        .box(2.0 * r, 2.2 * r + 2.0, length + 2.0, centered=(True, True, True))
    )
    cutter = cutter.cut(sliver)
    if bore_type == "double-D":
        sliver2 = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(-((r - flat_depth) + r), 0, length / 2.0))
            .box(2.0 * r, 2.2 * r + 2.0, length + 2.0, centered=(True, True, True))
        )
        cutter = cutter.cut(sliver2)
    return cutter


# ── Body builders ────────────────────────────────────────────────────────────
def knob_body():
    """The outer barrel per `style`, base at z=0."""
    body = cq.Workplane("XY").circle(knob_dia / 2.0).extrude(knob_height)

    if style == "fluted":
        # Scallop the sides with a ring of vertical cylindrical flutes.
        n = max(6, int(round(knob_dia / 4.0)))
        flute_r = max(1.2, knob_dia * 0.06)
        ring_r = knob_dia / 2.0
        cutter = None
        for i in range(n):
            ang = 2.0 * math.pi * i / n
            cx = ring_r * math.cos(ang)
            cy = ring_r * math.sin(ang)
            f = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(cx, cy, -0.5))
                .circle(flute_r)
                .extrude(knob_height + 1.0)
            )
            cutter = f if cutter is None else cutter.union(f)
        if cutter is not None:
            body = body.cut(cutter)

    elif style == "knurled":
        # Grippy barrel: a ring of shallow flats (a coarse knurl) via a polygon
        # column slightly larger than the core, unioned so it stays watertight.
        n = max(10, int(round(knob_dia / 2.5)))
        core_r = knob_dia / 2.0
        # Rebuild the barrel as an n-gon prism (coarse knurl facets).
        pts = []
        for i in range(n):
            ang = 2.0 * math.pi * i / n
            pts.append((core_r * math.cos(ang), core_r * math.sin(ang)))
        body = cq.Workplane("XY").polyline(pts).close().extrude(knob_height)

    # Round / dome the top edge for a finished feel.
    if top_round:
        rr = min(knob_dia * 0.12, knob_height * 0.4, 3.0)
        if rr >= 0.3:
            try:
                body = body.edges(">Z").fillet(rr)
            except Exception:
                pass  # knurl/flute intersections can resist filleting — non-fatal
    return body


def bore_cutter():
    """Solid cutter for the bore, from z=-0.5 up through bore_depth (extended
    below the base so the bottom opening is clean)."""
    length = bore_depth + 0.5
    if bore_type == "splined":
        base = splined_cutter(length)
    elif bore_type in ("D-flat", "double-D") and flat_depth > 0.02:
        base = flatted_cutter(length)
    else:
        base = round_cutter(length)
    return base.translate((0, 0, -0.5))


def add_setscrew(body):
    """Radial set-screw hole through the wall into the bore, near the base."""
    if not setscrew:
        return body
    d = max(1.5, min(setscrew_dia, knob_dia * 0.25))
    z = min(bore_depth * 0.5, knob_height - 3.0)
    z = max(2.0, z)
    hole = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, z, 0))
        .circle(d / 2.0)
        .extrude(knob_dia)  # from centre outward through the +X wall
    )
    return body.cut(hole)


def add_pointer(body):
    """Raised indicator: a rib up the +X side and a line across the top so the
    knob reads as a dial pointer."""
    r = knob_dia / 2.0
    w = max(1.5, knob_dia * 0.06)
    # Side rib (a thin box hugging the +X wall, unioned so it protrudes slightly).
    rib = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(r - 0.4, 0, 0))
        .box(1.6, w, knob_height, centered=(True, True, False))
    )
    body = body.union(rib)
    # Top line from centre to the +X rim.
    line = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(r / 2.0, 0, knob_height - 0.1))
        .box(r, w, 1.2, centered=(True, True, False))
    )
    body = body.union(line)
    return body


# ── Assemble ─────────────────────────────────────────────────────────────────
def build():
    body = knob_body()
    body = body.cut(bore_cutter())
    body = add_setscrew(body)
    if target_part == "pointer_knob":
        body = add_pointer(body)
    return body


result = build()
