import cadquery as cq
import math


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part = PARAM(lambda: target_part, "carousel")
pipette_slots = int(PARAM(lambda: pipette_slots, 6))
body_diameter = float(PARAM(lambda: body_diameter, 22.0))
tip_cols = int(PARAM(lambda: tip_cols, 8))
tip_rows = int(PARAM(lambda: tip_rows, 6))
tip_hole = float(PARAM(lambda: tip_hole, 6.5))

# ─── Real-world reference dimensions (cited in manifest CDG standards) ─────────
# Single-channel micropipette shaft: 6.0 mm (20-1000 µL), 3.8 mm (2-10 µL).
# SBS / ANSI-SLAS microplate: 9 mm well pitch, Ø6.4 mm wells, 127.76 x 85.48 mm.
SBS_PITCH = 9.0             # mm, ANSI-SLAS microplate well pitch
SBS_BORDER = 7.0           # mm, tray edge margin


def _fillet_safe(wp, edges_selector, radius):
    """Fillet the blank BEFORE cutting features; fall back gracefully."""
    try:
        return wp.edges(edges_selector).fillet(radius)
    except Exception:
        return wp


def _polar(radius, angle_deg):
    a = math.radians(angle_deg)
    return radius * math.cos(a), radius * math.sin(a)


# ─── Mode 1: pipette carousel stand ───────────────────────────────────────────
def build_carousel():
    """Round bench stand that cradles N single-channel pipettes upright.

    Each cradle is a blind bore OPEN to the top face (no trapped void). A slim
    finger-relief slot is cut from the outer rim into each cradle so the pipette
    can be grasped, staying open to the exterior.
    """
    n = max(2, pipette_slots)
    cradle_r = body_diameter / 2.0 + 0.6      # slip clearance around the body
    ring_r = cradle_r + max(8.0, n * 1.5)
    base_r = ring_r + cradle_r + 6.0
    base_h = 14.0
    cradle_depth = base_h * 0.75

    base = cq.Workplane("XY").circle(base_r).extrude(base_h)
    base = _fillet_safe(base, "|Z", 4.0)

    cradle_pts = [_polar(ring_r, i * 360.0 / n) for i in range(n)]
    for (cx, cy) in cradle_pts:
        cradle = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, base_h - cradle_depth / 2.0))
            .cylinder(cradle_depth, cradle_r)
        )
        base = base.cut(cradle)
        # Finger-relief slot from rim into the cradle (open to outside + cradle).
        ang = math.degrees(math.atan2(cy, cx))
        mx, my = _polar((ring_r + base_r) / 2.0, ang)
        relief = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(mx, my, base_h - cradle_depth / 2.0))
            .transformed(rotate=cq.Vector(0, 0, ang))
            .box(base_r, cradle_r * 0.8, cradle_depth)
        )
        base = base.cut(relief)

    # Central boss with a hollow-free label post kept SOLID (no sealed cavity).
    boss = cq.Workplane("XY").circle(cradle_r * 0.8).extrude(base_h + 6.0)
    base = base.union(boss)
    return base


# ─── Mode 2: pipette-tip rack tray ────────────────────────────────────────────
def build_tip_rack():
    """A tray drilled with a grid of tip holes on the real 9 mm SBS pitch, with a
    raised lip and open drainage so tips seat and no cavity is trapped."""
    cols = max(2, tip_cols)
    rows = max(2, tip_rows)
    hole_d = max(3.0, tip_hole)

    width = (cols - 1) * SBS_PITCH + 2 * SBS_BORDER
    depth = (rows - 1) * SBS_PITCH + 2 * SBS_BORDER
    tray_h = 12.0
    wall = 2.4

    tray = cq.Workplane("XY").box(width, depth, tray_h, centered=(True, True, False))
    tray = _fillet_safe(tray, "|Z", 3.0)

    # Hollow the tray to a shelf, open to the top (drainage/air gap under tips).
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, tray_h - (tray_h - wall) / 2.0))
        .box(width - 2 * wall, depth - 2 * wall, tray_h - wall)
    )
    tray = tray.cut(cavity)

    # Grid of tip holes through the top shelf (open top + into the cavity below).
    x0 = -(cols - 1) * SBS_PITCH / 2.0
    y0 = -(rows - 1) * SBS_PITCH / 2.0
    for i in range(cols):
        for j in range(rows):
            hx = x0 + i * SBS_PITCH
            hy = y0 + j * SBS_PITCH
            hole = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(hx, hy, tray_h))
                .cylinder(wall * 4.0, hole_d / 2.0)
            )
            tray = tray.cut(hole)
    return tray


# ─── Mode 3: wall-mount single pipette hook ───────────────────────────────────
def build_wall_hook():
    """A wall plate with a keyhole mounting slot and a C-cradle that holds one
    pipette by its body; all openings vent to a face (no trapped void)."""
    plate_w = body_diameter + 16.0
    plate_h = 70.0
    plate_t = 5.0
    cradle_r = body_diameter / 2.0 + 0.8

    plate = cq.Workplane("XY").box(plate_w, plate_t, plate_h, centered=(True, True, False))
    plate = _fillet_safe(plate, "|Y", 3.0)

    # Keyhole mounting slot near the top: a circle + a slot, cut through the plate.
    key_c = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, -plate_h * 0.82, 0))
        .cylinder(plate_t + 2.0, 4.5)
    )
    key_slot = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, -plate_h * 0.76, 0))
        .box(5.0, 10.0, plate_t + 2.0)
    )
    plate = plate.cut(key_c).cut(key_slot)

    # C-cradle arm projecting forward, holding the pipette body horizontally.
    arm_y = 20.0
    arm = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_t / 2.0 + arm_y / 2.0, plate_h * 0.30))
        .box(plate_w, arm_y, cradle_r * 2.0 + 6.0)
    )
    arm = _fillet_safe(arm, "|Z", 3.0)
    plate = plate.union(arm)

    # Cradle bore through the arm (open front + back → not sealed).
    bore = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, -plate_h * 0.30, plate_t / 2.0 + arm_y / 2.0))
        .cylinder(arm_y + 4.0, cradle_r)
    )
    plate = plate.cut(bore)
    # Open the cradle bottom into a U so a pipette drops in from the front.
    mouth = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_t / 2.0 + arm_y / 2.0, plate_h * 0.30 - cradle_r))
        .box(cradle_r * 1.2, arm_y + 4.0, cradle_r * 2.0)
    )
    plate = plate.cut(mouth)
    return plate


# ─── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "carousel":
    result = build_carousel()
elif target_part == "tip_rack":
    result = build_tip_rack()
elif target_part == "wall_hook":
    result = build_wall_hook()
else:
    result = build_carousel()
