"""
Self-Watering Planter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A pot with a water reservoir in the base and a wicking path up to the soil, so
plants draw water on their own between fillings. The pot has a false floor above a
reservoir; wick holes let potting mix reach down and pull water up; an overflow hole
at the top of the reservoir stops over-filling. A matching saucer and a lift-out
inner pot (with wick legs) complete the set.

Design idiom (watertight pot shell + false floor):
  The pot is a SOLID outer body with the soil cavity cut from the top; the false
  floor is left as a slab of material at reservoir height, then wick holes and one
  overflow hole are drilled. Because the pot is one closed solid minus interior
  volumes, it exports watertight. Round or square footprints share the same
  build via a `_body(w, d, h, r)` block helper.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `wall`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(  PARAM(lambda: target_part, "planter"))  # planter | saucer | insert
shape       = str(  PARAM(lambda: shape,       "round"))     # round | square
pot_dia     = float(PARAM(lambda: pot_dia,    120.0))        # pot diameter / width (mm)
height      = float(PARAM(lambda: height,     130.0))        # overall pot height (mm)
wall        = float(PARAM(lambda: wall,         3.0))        # wall thickness (mm)
reservoir_h = float(PARAM(lambda: reservoir_h, 35.0))        # reservoir height at the base (mm)
wick_count  = int(  PARAM(lambda: wick_count,     4))        # wicking holes in the false floor
wick_dia    = float(PARAM(lambda: wick_dia,    16.0))        # wicking hole diameter (mm)
drainage    = bool( PARAM(lambda: drainage,    True))        # overflow hole at reservoir top

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
pot_dia = max(40.0, min(pot_dia, 400.0))
height = max(50.0, min(height, 500.0))
wall = max(1.6, min(wall, 8.0))
reservoir_h = max(10.0, min(reservoir_h, height - 20.0))
wick_count = max(1, min(wick_count, 8))
wick_dia = max(4.0, min(wick_dia, min(pot_dia * 0.25, 40.0)))

is_round = shape != "square"
floor_th = max(2.5, wall)                     # bottom floor thickness
false_th = max(2.5, wall)                     # false-floor slab thickness
outer_r = pot_dia / 2.0
inner_r = outer_r - wall


# ── Block helper (round or square footprint) ──────────────────────────────────
def _block(w, h, r, hollow_r=None):
    """A vertical prism, base at z=0. Round → cylinder of radius w/2. Square →
    box of side w with filleted vertical edges (r). Returns a Workplane solid."""
    if is_round:
        wp = cq.Workplane("XY").circle(w / 2.0).extrude(h)
    else:
        wp = cq.Workplane("XY").box(w, w, h, centered=(True, True, False))
        rr = max(0.0, min(r, w / 2.0 - 0.5))
        if rr > 0.4:
            try:
                wp = wp.edges("|Z").fillet(rr)
            except Exception:
                pass
    return wp


def _cavity(w, base_z, h):
    """An interior cavity prism (round or square) inset by `wall`, base at base_z."""
    inner_w = w - 2.0 * wall
    if is_round:
        c = cq.Workplane("XY").circle(inner_w / 2.0).extrude(h)
    else:
        c = cq.Workplane("XY").box(inner_w, inner_w, h, centered=(True, True, False))
        rr = max(0.0, min(pot_dia * 0.1 - wall, inner_w / 2.0 - 0.5))
        if rr > 0.4:
            try:
                c = c.edges("|Z").fillet(rr)
            except Exception:
                pass
    return c.translate((0, 0, base_z))


def _wick_ring_positions():
    """Positions for the wick holes, on a circle inside the false floor."""
    rad = min(inner_r, outer_r - wall) * 0.55
    pts = []
    for k in range(wick_count):
        ang = math.radians(360.0 / wick_count * k)
        pts.append((rad * math.cos(ang), rad * math.sin(ang)))
    return pts


# ── Part builders ─────────────────────────────────────────────────────────────
def build_planter():
    """The pot: solid outer body, soil cavity cut from the top down to the false
    floor, wick holes through the false floor, and an overflow hole at reservoir top."""
    corner_r = pot_dia * 0.1
    body = _block(pot_dia, height, corner_r)

    # Soil cavity: from the top of the false floor up to the rim.
    false_top = floor_th + reservoir_h + false_th
    soil_h = height - false_top + 1.0
    soil = _cavity(pot_dia, false_top, soil_h)
    body = body.cut(soil)

    # Reservoir cavity: hollow the space between the bottom floor and the false
    # floor, leaving side walls. This creates the water chamber under the slab.
    res = _cavity(pot_dia, floor_th, reservoir_h)
    body = body.cut(res)

    # Wick holes through the false floor (soil dips down to touch water).
    for (hx, hy) in _wick_ring_positions():
        hole = (
            cq.Workplane("XY")
            .center(hx, hy)
            .circle(wick_dia / 2.0)
            .extrude(false_th + 2.0)
            .translate((0, 0, floor_th + reservoir_h - 1.0))
        )
        try:
            body = body.cut(hole)
        except Exception:
            pass

    # Central fill/wick tube: a small open column linking soil to reservoir so it
    # can be top-filled. (One extra wick hole in the middle.)
    fill = (
        cq.Workplane("XY")
        .circle(wick_dia / 2.0)
        .extrude(false_th + 2.0)
        .translate((0, 0, floor_th + reservoir_h - 1.0))
    )
    try:
        body = body.cut(fill)
    except Exception:
        pass

    # Overflow hole through the side wall at the top of the reservoir.
    if drainage:
        of_z = floor_th + reservoir_h - max(4.0, wick_dia * 0.4)
        of = (
            cq.Workplane("YZ")
            .workplane(offset=outer_r - wall - 1.0)
            .center(0.0, of_z)
            .circle(3.0)
            .extrude(wall + 3.0)
        )
        try:
            body = body.cut(of)
        except Exception:
            pass

    # Soften the rim.
    try:
        body = body.edges(">Z").fillet(min(wall * 0.4, 1.2))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_saucer():
    """A shallow drip tray sized a touch larger than the pot footprint."""
    saucer_w = pot_dia + 2.0 * wall + 8.0
    s_h = max(14.0, reservoir_h * 0.35)
    corner_r = saucer_w * 0.08
    body = _block(saucer_w, s_h, corner_r)
    # Hollow the tray, leaving a floor.
    cav_h = s_h - floor_th + 1.0
    if is_round:
        cav = cq.Workplane("XY").circle((saucer_w - 2.0 * wall) / 2.0).extrude(cav_h).translate((0, 0, floor_th))
    else:
        cav = cq.Workplane("XY").box(
            saucer_w - 2.0 * wall, saucer_w - 2.0 * wall, cav_h, centered=(True, True, False)
        ).translate((0, 0, floor_th))
        try:
            cav = cav.edges("|Z").fillet(max(0.0, corner_r - wall))
        except Exception:
            pass
    body = body.cut(cav)
    try:
        body = body.edges(">Z").fillet(min(wall * 0.4, 1.0))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_insert():
    """A lift-out inner pot: an open-top cup that nests in the planter, with legs
    (a stepped ring at the base) that stand it on the false floor and act as wicks,
    plus drainage holes in its floor."""
    ins_w = pot_dia - 2.0 * wall - 4.0        # clears the pot interior
    ins_h = height - (floor_th + reservoir_h + false_th) + reservoir_h * 0.6
    ins_h = max(40.0, ins_h)
    leg_h = max(12.0, reservoir_h * 0.6)
    corner_r = ins_w * 0.1

    body = _block(ins_w, ins_h, corner_r)
    # Hollow the cup.
    cav_h = ins_h - floor_th + 1.0
    if is_round:
        cav = cq.Workplane("XY").circle((ins_w - 2.0 * wall) / 2.0).extrude(cav_h).translate((0, 0, floor_th))
    else:
        cav = cq.Workplane("XY").box(
            ins_w - 2.0 * wall, ins_w - 2.0 * wall, cav_h, centered=(True, True, False)
        ).translate((0, 0, floor_th))
    body = body.cut(cav)

    # Wick legs: a downward ring skirt with slots, standing the cup in the reservoir.
    skirt_ro = ins_w / 2.0 - 1.0
    skirt_ri = skirt_ro - wall
    if is_round:
        skirt = (
            cq.Workplane("XY").circle(skirt_ro).circle(skirt_ri).extrude(-leg_h)
        )
    else:
        so = cq.Workplane("XY").box(2.0 * skirt_ro, 2.0 * skirt_ro, leg_h, centered=(True, True, False))
        si = cq.Workplane("XY").box(2.0 * skirt_ri, 2.0 * skirt_ri, leg_h + 1.0, centered=(True, True, False))
        skirt = so.cut(si).translate((0, 0, -leg_h))
    body = body.union(skirt)
    # Slots in the skirt so water wicks up (cut a few gaps).
    for k in range(4):
        ang = math.radians(90.0 * k)
        gx = math.cos(ang) * skirt_ro
        gy = math.sin(ang) * skirt_ro
        slot = (
            cq.Workplane("XY")
            .center(gx, gy)
            .rect(wall * 3.0, wall * 3.0)
            .extrude(leg_h)
            .translate((0, 0, -leg_h))
        )
        try:
            body = body.cut(slot)
        except Exception:
            pass

    # Drainage / wick holes in the cup floor.
    for (hx, hy) in _wick_ring_positions():
        hx *= ins_w / pot_dia
        hy *= ins_w / pot_dia
        hole = cq.Workplane("XY").center(hx, hy).circle(wick_dia / 2.5).extrude(floor_th + 2.0).translate((0, 0, -1.0))
        try:
            body = body.cut(hole)
        except Exception:
            pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "saucer":
    result = build_saucer()
elif target_part == "insert":
    result = build_insert()
else:
    result = build_planter()
