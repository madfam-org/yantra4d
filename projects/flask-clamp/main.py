import cadquery as cq
import math


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part = PARAM(lambda: target_part, "ring_clamp")
vessel_diameter = float(PARAM(lambda: vessel_diameter, 84.0))
rod_diameter = float(PARAM(lambda: rod_diameter, 12.0))
neck_diameter = float(PARAM(lambda: neck_diameter, 34.0))
neck_holes = int(PARAM(lambda: neck_holes, 3))

# ─── Real-world reference dimensions (cited in manifest CDG standards) ─────────
# Erlenmeyer body Ø: 125 mL ~70 mm, 250 mL ~84 mm, 500 mL ~108 mm.
# Erlenmeyer neck OD: 34 mm (250/500 mL). Griffin beaker 250 mL OD ~70 mm.
# Ring-stand support rod: 12 mm dia (10x1.5 thread) / 1/2 in = 12.7 mm.
RING_WALL = 8.0            # mm, radial wall of the clamp ring
RING_HEIGHT = 14.0        # mm, axial height of the clamp ring


def _fillet_safe(wp, edges_selector, radius):
    """Fillet the blank BEFORE cutting features; fall back gracefully."""
    try:
        return wp.edges(edges_selector).fillet(radius)
    except Exception:
        return wp


def _polar(radius, angle_deg):
    a = math.radians(angle_deg)
    return radius * math.cos(a), radius * math.sin(a)


# ─── Mode 1: rod-mounted C-ring clamp ─────────────────────────────────────────
def build_ring_clamp():
    """Open C-ring that hugs a flask/beaker body and clamps onto a ring-stand rod.

    The ring is a C (a mouth wedge is cut OPEN to the exterior — never a closed
    torus), and the rod bore is a slit clamp open to a face, so no void is
    trapped and the mesh is one watertight body.
    """
    inner_r = vessel_diameter / 2.0 + 1.0     # slip clearance around the vessel
    outer_r = inner_r + RING_WALL

    # Ring blank: outer cylinder minus inner cylinder (annulus, both open axially).
    outer = cq.Workplane("XY").circle(outer_r).extrude(RING_HEIGHT)
    inner = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, RING_HEIGHT / 2.0))
        .cylinder(RING_HEIGHT + 2.0, inner_r)
    )
    ring = outer.cut(inner)

    # Mouth: a wedge box cut on -X, opening the C so the vessel slips in sideways.
    mouth = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(-outer_r, 0, RING_HEIGHT / 2.0))
        .box(RING_WALL * 3.0, inner_r * 0.9, RING_HEIGHT + 2.0)
    )
    ring = ring.cut(mouth)

    # Mounting arm to the rod, projecting on +X (union to the ring body).
    arm_len = rod_diameter + 26.0
    arm = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(outer_r + arm_len / 2.0 - 4.0, 0, RING_HEIGHT / 2.0))
        .box(arm_len, rod_diameter + 12.0, RING_HEIGHT)
    )
    arm = _fillet_safe(arm, "|Z", 3.0)
    ring = ring.union(arm)

    # Rod bore through the arm (vertical, open top & bottom → not sealed).
    rod_cx = outer_r + arm_len - 4.0 - (rod_diameter / 2.0 + 4.0)
    rod_bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(rod_cx, 0, RING_HEIGHT / 2.0))
        .cylinder(RING_HEIGHT + 2.0, rod_diameter / 2.0 + 0.4)
    )
    ring = ring.cut(rod_bore)

    # Clamp slit from the arm's outer edge into the rod bore (open to exterior).
    slit = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(rod_cx + arm_len / 2.0, 0, RING_HEIGHT / 2.0))
        .box(arm_len, 2.4, RING_HEIGHT + 2.0)
    )
    ring = ring.cut(slit)
    # Clamp-screw cross bore straddling the slit (open on both arm faces).
    screw = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(rod_cx + rod_diameter / 2.0 + 6.0, -RING_HEIGHT / 2.0, 0))
        .cylinder(rod_diameter + 20.0, 2.2)
    )
    ring = ring.cut(screw)
    return ring


# ─── Mode 2: inverted-neck drying holder ──────────────────────────────────────
def build_neck_holder():
    """A raised plate with keyed neck cutouts so flasks sit inverted to drain/dry;
    each cutout is a through-hole (open both faces) with a drainage relief."""
    n = max(1, neck_holes)
    hole_r = neck_diameter / 2.0 + 1.5
    pitch = 2 * hole_r + 14.0
    length = n * pitch + 12.0
    width = 2 * hole_r + 24.0
    plate_t = 8.0
    leg_h = 24.0

    plate = cq.Workplane("XY").box(length, width, plate_t, centered=(True, True, False))
    plate = _fillet_safe(plate, "|Z", 4.0)

    # Neck through-holes on the plate.
    x0 = -(n - 1) * pitch / 2.0
    hole_pts = [(x0 + i * pitch, 0.0) for i in range(n)]
    for (hx, hy) in hole_pts:
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(hx, hy, plate_t / 2.0))
            .cylinder(plate_t + 2.0, hole_r)
        )
        plate = plate.cut(hole)

    # Four corner legs (solid boxes unioned below the plate) to raise it for drainage.
    leg = 10.0
    lx = length / 2.0 - leg / 2.0 - 4.0
    ly = width / 2.0 - leg / 2.0 - 4.0
    for (sx, sy) in [(lx, ly), (-lx, ly), (lx, -ly), (-lx, -ly)]:
        post = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx, sy, -leg_h))
            .box(leg, leg, leg_h, centered=(True, True, False))
        )
        plate = plate.union(post)
    return plate


# ─── Mode 3: weighted rod-stand base ──────────────────────────────────────────
def build_rod_stand_base():
    """A heavy footed base with a vertical rod socket for the ring-stand rod; the
    socket is a blind bore open to the top face (no sealed cavity)."""
    base_w = 120.0
    base_d = 90.0
    base_t = 16.0
    boss_r = rod_diameter / 2.0 + 8.0
    boss_h = 26.0
    # Rod socket sits at the rear so glassware overhangs the front of the base.
    boss_y = -base_d / 2.0 + boss_r + 6.0

    base = cq.Workplane("XY").box(base_w, base_d, base_t, centered=(True, True, False))
    base = _fillet_safe(base, "|Z", 6.0)

    boss = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, boss_y, 0))
        .circle(boss_r).extrude(base_t + boss_h)
    )
    base = base.union(boss)

    # Rod socket: blind bore from the top of the boss (open top only).
    socket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, boss_y, base_t + boss_h - (boss_h + 4.0) / 2.0))
        .cylinder(boss_h + 4.0, rod_diameter / 2.0 + 0.4)
    )
    base = base.cut(socket)

    # Weight-saving pockets on the underside (open to the bottom face).
    for sx in (-base_w * 0.28, base_w * 0.28):
        pocket = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx, base_d * 0.18, base_t / 2.0 - base_t))
            .box(base_w * 0.34, base_d * 0.4, base_t * 0.6)
        )
        base = base.cut(pocket)
    return base


# ─── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "ring_clamp":
    result = build_ring_clamp()
elif target_part == "neck_holder":
    result = build_neck_holder()
elif target_part == "rod_stand_base":
    result = build_rod_stand_base()
else:
    result = build_ring_clamp()
