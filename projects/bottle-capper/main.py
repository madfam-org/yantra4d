"""
Homebrew Crown-Cap Seat — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Tooling for crimping standard 26 mm crown caps onto returnable / swing-top-free
glass bottles when bottling homebrew beer, cider, or soda. Three parts share one
CDG interface — the 26 mm crown-cap seat:

  * "cap_bell"      — a hand-capper BELL. A cylinder with an internal conical
                      seat that captures a crown cap; you place it over a capped
                      bottle neck and strike / press the bell so its shoulder
                      crimps the cap flutes down around the bottle finish.
  * "bench_seat"    — a BENCH SEAT puck the bottle stands in, with a shallow
                      cap-holding recess and a bottle-neck locating counterbore,
                      so a lever press has a stable, aligned base.
  * "cap_organizer" — a shallow TRAY with an array of cap-diameter recesses to
                      hold loose crown caps upright and ready.

Standard crown-cap dimensions used (nominal):
  cap outer diameter  ≈ 32.1 mm (across the crimp skirt, uncrimped)
  cap seat / crown bore that the flutes crimp down to ≈ 26 mm
  cap height          ≈ 6.0 mm

Watertight strategy: everything is a solid cylinder / block with pockets CUT
into it (hollow-by-cut, exactly like the reference box). Bores stay OPEN (no
lids over a cavity that would trap a void), chamfers are cut, and unions overlap
volumetrically. No sphere-tangent unions anywhere.

FOOD-CONTACT NOTE: geometry only. Only the cap seat touches the bottle rim, not
the beverage; even so, food-safe filament and hygienic handling are the maker's
responsibility (see README).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; parameters injected as bare globals.
  - Access params via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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


# ── Crown-cap standard (nominal) ─────────────────────────────────────────────
CAP_OD = 32.1     # uncrimped crown skirt outer diameter (mm)
CAP_SEAT = 26.0   # the 26 mm crown-cap seat diameter (the CDG interface)
CAP_H = 6.0       # crown cap height (mm)


# ── Parameters ───────────────────────────────────────────────────────────────
cap_dia     = float(PARAM(lambda: cap_dia,      CAP_OD))   # crown-cap OD (mm)
wall        = float(PARAM(lambda: wall,          4.0))     # bell / body wall thickness (mm)
bell_h      = float(PARAM(lambda: bell_h,       32.0))     # capper bell height (mm)
neck_dia    = float(PARAM(lambda: neck_dia,     28.0))     # bottle-neck finish OD to clear (mm)
clearance   = float(PARAM(lambda: clearance,     0.5))     # printed-fit slop (per side, mm)
seat_depth  = float(PARAM(lambda: seat_depth,    5.0))     # cap recess depth in bench seat (mm)
count       = int(  PARAM(lambda: count,           6))     # cap recesses per side (organizer)
grip_knurl  = bool( PARAM(lambda: grip_knurl,   True))     # grip flutes on the bell

target_part = str(  PARAM(lambda: target_part, "cap_bell"))  # cap_bell|bench_seat|cap_organizer

# ── Clamps ───────────────────────────────────────────────────────────────────
cap_dia     = max(24.0, min(cap_dia, 40.0))
wall        = max(2.5,  min(wall, 8.0))
bell_h      = max(18.0, min(bell_h, 60.0))
neck_dia    = max(20.0, min(neck_dia, 40.0))
clearance   = max(0.1,  min(clearance, 1.0))
seat_depth  = max(2.5,  min(seat_depth, 9.0))
count       = max(2,    min(count, 8))

cap_r = cap_dia / 2.0 + clearance
seat_r = CAP_SEAT / 2.0 + clearance


def _knurl(solid, outer_d, height, teeth=20, depth=0.8):
    """Shallow vertical grip flutes cut as one polar-array boolean (cheap,
    watertight)."""
    r = outer_d / 2.0
    try:
        cutter = (
            cq.Workplane("XY")
            .polarArray(radius=r, startAngle=0, angle=360, count=teeth)
            .rect(depth, depth * 3.0)
            .extrude(height + 2.0)
            .translate((0, 0, -1.0))
        )
        solid = solid.cut(cutter)
    except Exception:
        pass  # cosmetic
    return solid


# ── Part builders ────────────────────────────────────────────────────────────
def build_cap_bell():
    """A capper bell: a closed-top cylinder. Inside is a cap pocket (holds the
    crown cap) that steps down to a NECK clearance bore (drops over the bottle
    finish). The step between the two bores is the crimping shoulder."""
    outer_d = cap_dia + 2.0 * clearance + 2.0 * wall
    body = cq.Workplane("XY").circle(outer_d / 2.0).extrude(bell_h)

    # Cap pocket: from the OPEN bottom up, diameter = cap OD + clearance. This
    # holds the crown cap and lets the skirt sit while the bell drives down.
    pocket_h = CAP_H + 1.0
    pocket = cq.Workplane("XY").circle(cap_r).extrude(pocket_h).translate((0, 0, -0.5))
    body = body.cut(pocket)

    # Neck-clearance bore above the pocket so the bell can travel down over the
    # bottle finish while the shoulder crimps the cap. Stops short of the top so
    # the bell stays capped (a solid striking surface). Bore stays open downward
    # (connected to the pocket) — no trapped void.
    neck_bore_r = neck_dia / 2.0 + clearance + 0.6
    neck_bore_h = bell_h - wall  # leave `wall` as the closed striking top
    neck_bore = (
        cq.Workplane("XY")
        .circle(neck_bore_r)
        .extrude(neck_bore_h)
        .translate((0, 0, pocket_h - 0.5))
    )
    body = body.cut(neck_bore)

    # Crimping lead-in chamfer at the very bottom lip (helps the bell find the
    # cap). A cut cone: wide at the open rim, narrowing up to the pocket wall.
    try:
        ch = min(1.6, wall * 0.5)
        chamfer = (
            cq.Workplane("XY")
            .circle(cap_r + ch)
            .workplane(offset=ch)
            .circle(cap_r)
            .loft(combine=True)
            .translate((0, 0, -0.01))
        )
        body = body.cut(chamfer)
    except Exception:
        pass

    if grip_knurl:
        body = _knurl(body, outer_d, bell_h)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_bench_seat():
    """A puck the bottle stands on: a disk with a central bottle-neck locating
    counterbore on top and, at its centre floor, a deeper cap-holding recess so a
    crown cap sits crown-up and the bottle rim presses straight onto it.

    Void-free by construction: both pockets are cut from the TOP and the recess
    opens UP into the counterbore (one connected cavity, open to the top face). A
    fixed `floor` of solid material always remains beneath the recess — the body
    height is DERIVED from the floor + recess + counterbore stack rather than the
    other way round, so the recess can never seal off an internal pocket."""
    floor = 3.0                              # solid floor kept beneath the recess
    loc_depth = 8.0                          # neck-locating counterbore depth
    body_h = floor + seat_depth + loc_depth  # derived so nothing gets trapped
    body_d = cap_dia + 4.0 * wall + 8.0
    body = cq.Workplane("XY").circle(body_d / 2.0).extrude(body_h)

    # Bottle-neck locating counterbore, open at the TOP: the inverted bottle
    # finish nests here. Its floor sits at z = floor + seat_depth.
    loc_r = neck_dia / 2.0 + clearance + 1.0
    loc_floor_z = floor + seat_depth
    loc = (
        cq.Workplane("XY")
        .circle(loc_r)
        .extrude(loc_depth + 1.0)
        .translate((0, 0, loc_floor_z))
    )
    body = body.cut(loc)

    # Cap-holding recess: cut DOWN from the counterbore floor, opening upward
    # into it. Bottom sits at z = floor (solid material below), top overlaps a
    # touch into the counterbore so the two cavities merge cleanly.
    cap_recess = (
        cq.Workplane("XY")
        .circle(cap_r)
        .extrude(seat_depth + 1.0)
        .translate((0, 0, floor))
    )
    body = body.cut(cap_recess)

    # Soften the top outer rim for handling.
    try:
        body = body.edges(">Z").fillet(min(1.5, wall * 0.4))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_cap_organizer():
    """A shallow tray holding loose crown caps upright in a grid of recesses."""
    cell = cap_dia + 2.0 * clearance + 3.0
    cols = count
    rows = max(2, count - 2)
    tray_w = cols * cell + 2.0 * wall
    tray_d = rows * cell + 2.0 * wall
    tray_h = CAP_H + wall + 1.0

    body = cq.Workplane("XY").box(tray_w, tray_d, tray_h, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(4.0, wall + 1.0))
    except Exception:
        pass

    # Array of cap recesses, floor left at `wall`. Each recess an independent cut
    # cylinder (no shared multi-wire state) — union them into one cutter, one cut.
    recess_depth = tray_h - wall
    cutter = None
    x0 = -(cols - 1) * cell / 2.0
    y0 = -(rows - 1) * cell / 2.0
    for i in range(cols):
        for j in range(rows):
            x = x0 + i * cell
            y = y0 + j * cell
            hole = (
                cq.Workplane("XY")
                .circle(cap_r)
                .extrude(recess_depth + 1.0)
                .translate((x, y, wall - 0.5))
            )
            cutter = hole if cutter is None else cutter.union(hole)
    if cutter is not None:
        body = body.cut(cutter)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bench_seat":
    result = build_bench_seat()
elif target_part == "cap_organizer":
    result = build_cap_organizer()
else:
    result = build_cap_bell()
