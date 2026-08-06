"""
Guitar Pick Holder & Punch — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Keeps guitar picks where you need them and lets you make your own. The shared
geometric denominator is the classic 351 pick outline (a rounded equilateral
triangle) so every part references the same real pick footprint.

Three parts (dispatched by `target_part`):
  * "pick_clip"           — a slim pocket clip that holds a stack of picks and
                            slides onto a strap, pocket, or headstock.
  * "wall_holder"         — a small wall tray with N pick slots.
  * "pick_punch_template" — a flat plate with the 351 pick outline cut clean
                            through it: lay a plastic sheet under it and trace /
                            cut your own picks to the standard shape.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `pick_count`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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
target_part = str(PARAM(lambda: target_part, "pick_clip"))  # clip|wall|punch

pick_size   = float(PARAM(lambda: pick_size,   31.0))  # pick tip-to-edge span (mm, 351≈31)
pick_count  = int(  PARAM(lambda: pick_count,     6))  # picks held (clip stack / wall slots)
pick_th     = float(PARAM(lambda: pick_th,      1.0))  # single pick thickness (mm)
wall        = float(PARAM(lambda: wall,         2.4))  # body wall thickness (mm)
mount       = str(  PARAM(lambda: mount,   "screw"))   # wall mount style: screw|adhesive
screw_dia   = float(PARAM(lambda: screw_dia,    4.0))  # wall screw clearance (mm)
plate_t     = float(PARAM(lambda: plate_t,      3.0))  # punch template plate thickness (mm)

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
pick_size  = max(18.0, min(pick_size, 45.0))
pick_count = max(1, min(pick_count, 30))
pick_th    = max(0.5, min(pick_th, 2.0))
wall       = max(1.6, min(wall, 5.0))
screw_dia  = max(2.5, min(screw_dia, 8.0))
plate_t    = max(2.0, min(plate_t, 8.0))


# ── 351 pick outline ─────────────────────────────────────────────────────────
def pick_outline(size):
    """A 2D wire of the classic 351 pick: a rounded equilateral triangle.

    `size` is the overall height (playing-tip to opposite rounded shoulder).
    Three vertices on a circle of radius R, connected by tangent arcs (the two
    shoulders are broadly rounded; the playing tip is a tighter radius). Returns
    a closed cq.Workplane sketch on XY ready to `.extrude`."""
    R = size / 2.0
    # Three corner points (tip pointing -Y so the pick "plays" downward).
    tip = (0.0, -R)
    left = (-R * math.sin(math.radians(120)), -R * math.cos(math.radians(120)))
    right = (R * math.sin(math.radians(120)), -R * math.cos(math.radians(120)))
    # Midpoints bulge outward to make the rounded-triangle sides convex.
    def mid(a, b, bulge):
        mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
        # push midpoint away from centroid
        d = math.hypot(mx, my) or 1.0
        return (mx + mx / d * bulge, my + my / d * bulge)

    bulge = R * 0.28
    m_lr = mid(left, right, bulge)   # top shoulder side
    m_rt = mid(right, tip, bulge)    # right side toward tip
    m_lt = mid(left, tip, bulge)     # left side toward tip

    wp = (
        cq.Workplane("XY")
        .moveTo(*tip)
        .threePointArc(m_rt, right)
        .threePointArc(m_lr, left)
        .threePointArc(m_lt, tip)
        .close()
    )
    return wp


def pick_solid(size, thickness):
    """A single solid pick (for the clip's holding cavity reference)."""
    return pick_outline(size).extrude(thickness)


# ── Part builders ────────────────────────────────────────────────────────────
def build_pick_clip():
    """A slim clip: a shallow rectangular pocket sized to a stack of `pick_count`
    picks, backed by a sprung tongue so it slides onto a strap or pocket edge."""
    stack = pick_count * pick_th + 0.6
    body_w = pick_size + 2.0 * wall
    body_h = pick_size * 0.92 + 2.0 * wall
    body_d = stack + 2.0 * wall

    body = cq.Workplane("XY").box(body_w, body_d, body_h, centered=(True, True, False))
    # Hollow the pick pocket from the top, open at the top so picks drop in.
    pocket = (
        cq.Workplane("XY")
        .box(pick_size, stack, body_h, centered=(True, True, False))
        .translate((0, 0, wall))
    )
    body = body.cut(pocket)
    # A thumb scallop on the front so a pick can be pushed out.
    scallop = (
        cq.Workplane("XZ")
        .circle(pick_size * 0.32)
        .extrude(body_d + 2.0)
        .translate((0, body_d / 2.0 + 1.0, body_h))
    )
    body = body.cut(scallop)
    # Sprung tongue on the back: a thin plate standing off the body with a gap,
    # gripping a strap/pocket edge of ~ (2*pick_th..) thick.
    tongue_gap = 3.0
    tongue_t = wall
    tongue = (
        cq.Workplane("XY")
        .box(body_w * 0.7, tongue_t, body_h * 1.15, centered=(True, True, False))
        .translate((0, -body_d / 2.0 - tongue_gap - tongue_t / 2.0, 0))
    )
    bridge = (
        cq.Workplane("XY")
        .box(body_w * 0.7, tongue_gap + tongue_t, wall, centered=(True, False, False))
        .translate((0, -body_d / 2.0 - tongue_gap - tongue_t, body_h - wall))
    )
    body = body.union(bridge).union(tongue)
    try:
        body = body.edges("|Y and >Z").fillet(min(1.5, wall * 0.4))
    except Exception:
        pass
    return body


def build_wall_holder():
    """A wall tray with `pick_count` angled slots; each slot holds one pick edge-up
    so you can pluck it. Screw or adhesive back."""
    slot_pitch = max(pick_th + 3.0, 5.0)
    tray_w = pick_count * slot_pitch + 2.0 * wall
    tray_d = pick_size * 0.7 + 2.0 * wall
    tray_h = pick_size * 0.55 + wall

    body = cq.Workplane("XY").box(tray_w, tray_d, tray_h, centered=(True, True, False))
    # Cut vertical pick slots across the tray.
    for i in range(pick_count):
        x = -tray_w / 2.0 + wall + slot_pitch * (i + 0.5)
        slot = (
            cq.Workplane("XY")
            .box(pick_th + 0.4, pick_size * 0.6, tray_h, centered=(True, True, False))
            .translate((x, 0, wall))
        )
        body = body.cut(slot)
    # Back wall raised for mounting.
    back = (
        cq.Workplane("XY")
        .box(tray_w, wall, tray_h + pick_size * 0.35, centered=(True, True, False))
        .translate((0, -tray_d / 2.0 + wall / 2.0, 0))
    )
    body = body.union(back)
    if mount == "screw":
        r = screw_dia / 2.0
        dx = tray_w / 2.0 - max(8.0, screw_dia + 5.0)
        for xc in [-dx, dx]:
            cutter = (
                cq.Workplane("XZ")
                .circle(r)
                .extrude(wall + 4.0)
                .translate((xc, -tray_d / 2.0 + wall + 2.0, tray_h + pick_size * 0.18))
            )
            body = body.cut(cutter)
    return body


def build_pick_punch_template():
    """A flat plate with the 351 pick outline cut clean through — a stencil /
    punch guide for cutting your own picks from sheet plastic."""
    margin = max(8.0, wall * 3.0)
    plate_w = pick_size + 2.0 * margin
    plate_d = pick_size + 2.0 * margin

    plate = cq.Workplane("XY").box(plate_w, plate_d, plate_t, centered=(True, True, False))
    # Cut the pick outline straight through the plate.
    cutter = pick_outline(pick_size).extrude(plate_t + 2.0).translate((0, 0, -1.0))
    plate = plate.cut(cutter)
    # A finger notch at the plate edge to lift the cut pick out.
    notch = (
        cq.Workplane("XY")
        .circle(margin * 0.5)
        .extrude(plate_t + 2.0)
        .translate((0, plate_d / 2.0, -1.0))
    )
    plate = plate.cut(notch)
    # Round the plate corners.
    try:
        plate = plate.edges("|Z").fillet(min(4.0, margin * 0.5))
    except Exception:
        pass
    return plate


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "wall_holder":
    result = build_wall_holder()
elif target_part == "pick_punch_template":
    result = build_pick_punch_template()
else:
    result = build_pick_clip()
