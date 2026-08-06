import cadquery as cq
import math


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part   = PARAM(lambda: target_part, "angled_stand")
slot_count    = int(str(PARAM(lambda: slot_count, 6)))
slot_length   = float(PARAM(lambda: slot_length, 10.0))
slot_width    = float(PARAM(lambda: slot_width, 3.0))
slot_pitch    = float(PARAM(lambda: slot_pitch, 14.0))
body_height   = float(PARAM(lambda: body_height, 40.0))
wall          = float(PARAM(lambda: wall, 5.0))
rake_angle    = float(PARAM(lambda: rake_angle, 20.0))


# ─── Mode 1: Angled Stand (raked slots on a wedge) ────────────────────────────
def build_angled_stand():
    """A wedge block whose top face is raked back, carrying a row of obround tool
    slots so tweezers/probes rest tip-up. Slots are pockets open to the top face
    (no trapped void). The rake is a single angled cut on the blank."""
    n = max(2, slot_count)
    length = slot_pitch * n + 2.0 * wall
    depth = slot_length + 2.0 * wall + 6.0

    body = cq.Workplane("XY").box(length, depth, body_height)
    body = body.edges("|Z").fillet(4.0)

    # Rake the top: subtract a plane tilted about X by rake_angle so the top face
    # climbs from front to back, and tweezers seated in the slots point tip-up.
    ang = max(5.0, min(40.0, rake_angle))
    top_z = body_height / 2.0
    cutter = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, top_z), rotate=cq.Vector(ang, 0, 0))
        .box(length * 2.0, depth * 2.0, body_height, centered=(True, True, False))
    )
    body = body.cut(cutter)

    slot_depth = slot_length
    x0 = -slot_pitch * (n - 1) / 2.0
    # Place slots along a line; cut each straight down from well above the surface
    # so the obround fully breaches the raked face and opens to it.
    for i in range(n):
        x = x0 + i * slot_pitch
        cutter2 = (
            cq.Workplane("XY")
            .workplane(offset=top_z - slot_depth)
            .center(x, 0.0)
            .slot2D(slot_length, slot_width, 90)
            .extrude(body_height)  # tall enough to pierce the raked face
        )
        body = body.cut(cutter2)
    return body


# ─── Mode 2: Carousel (radial slots on a round base) ──────────────────────────
def build_carousel():
    """A round base with tool slots arranged radially around the perimeter, each a
    vertical obround pocket open to the top face. Distinct round silhouette."""
    n = max(3, slot_count)
    rim = max(wall, 4.0)          # solid outer rim, never near-tangent to the wall
    # Radius so slots at the given pitch fit around the circle, with a solid rim
    # outboard and a solid hub inboard of the slot ring.
    circ_needed = slot_pitch * n
    radius = max(circ_needed / (2.0 * math.pi) + slot_length / 2.0 + rim,
                 slot_length + wall + 12.0)
    height = body_height * 0.7

    body = cq.Workplane("XY").cylinder(height, radius)
    body = body.edges("%CIRCLE").fillet(2.0)

    slot_depth = height * 0.6
    top_z = height / 2.0
    # Place the slot centre so its OUTER tip sits a full rim inside the wall
    # (outer tip = slot_r + slot_length/2 = radius - rim) — no near-tangency.
    slot_r = radius - rim - slot_length / 2.0
    for k in range(n):
        ang = (360.0 / n) * k
        a = math.radians(ang)
        cx = slot_r * math.cos(a)
        cy = slot_r * math.sin(a)
        cutter = (
            cq.Workplane("XY")
            .workplane(offset=top_z - slot_depth)
            .center(cx, cy)
            .slot2D(slot_length, slot_width, ang)  # obround aligned radially
            .extrude(slot_depth + 1.0)
        )
        body = body.cut(cutter)

    # Central finger well to lift the whole carousel — open to the top face, kept
    # shallower than the body and clear of the slot ring.
    well_r = min(radius * 0.35, slot_r - slot_length / 2.0 - 4.0)
    if well_r > 3.0:
        body = body.faces(">Z").workplane().hole(2.0 * well_r, slot_depth)
    return body


# ─── Mode 3: Probe Rail (row of upright slots + base) ─────────────────────────
def build_probe_rail():
    """A vertical rail on a foot, with a row of upright slots to stand probes and
    fine screwdrivers. Slots are obround pockets open to the top of the rail; the
    foot has mounting holes. All cuts open to a face."""
    n = max(2, slot_count)
    rail_len = slot_pitch * n + 2.0 * wall
    rail_thick = slot_width + 2.0 * wall
    rail_h = body_height

    # Foot
    foot_depth = rail_thick + 24.0
    foot_h = 8.0
    foot = cq.Workplane("XY").box(rail_len, foot_depth, foot_h)
    foot = foot.edges("|Z").fillet(4.0)

    # Rail rising from the foot (union of overlapping solids).
    rail = (
        cq.Workplane("XY")
        .workplane(offset=foot_h / 2.0 - 2.0)
        .box(rail_len, rail_thick, rail_h, centered=(True, True, False))
    )
    rail = rail.edges("|Z").fillet(2.0)
    body = foot.union(rail)

    # Row of upright bores from the top of the rail downward (open to the top
    # face). A drilled round pocket per tool — guaranteed manifold, sized to the
    # tool girth (slot_width). Depth from slot_length.
    bore_depth = slot_length
    x0 = -slot_pitch * (n - 1) / 2.0
    pts = [(x0 + i * slot_pitch, 0.0) for i in range(n)]
    body = (
        body.faces(">Z").workplane()
        .pushPoints(pts)
        .hole(slot_width, bore_depth)
    )

    # Foot mounting holes (open both faces => manifold).
    ox = rail_len / 2.0 - 6.0
    oy = foot_depth / 2.0 - 5.0
    body = (
        body.faces("<Z").workplane()
        .pushPoints([(ox, oy), (-ox, oy)])
        .hole(4.0)
    )
    return body


# ─── Dispatch ────────────────────────────────────────────────────────────────
_dispatch = {
    "angled_stand": build_angled_stand,
    "carousel":     build_carousel,
    "probe_rail":   build_probe_rail,
}

result = _dispatch.get(target_part, build_angled_stand)()
