import cadquery as cq
import math


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part = PARAM(lambda: target_part, "wheel")
optic_diameter = float(PARAM(lambda: optic_diameter, 25.4))
positions = int(PARAM(lambda: positions, 6))
wheel_thickness = float(PARAM(lambda: wheel_thickness, 8.0))
bore_diameter = float(PARAM(lambda: bore_diameter, 6.0))
cuvette_wells = int(PARAM(lambda: cuvette_wells, 4))

# ─── Real-world reference dimensions (cited in manifest CDG standards) ─────────
# Optics: Ø1 in = 25.4 mm, Ø25 mm metric, Ø1/2 in = 12.7 mm.
# Standard 10 mm path-length cuvette: 12.5 mm square external footprint.
CUVETTE_SQ = 12.5           # mm, external square of a 10 mm cuvette
CUVETTE_H = 45.0            # mm, typical cuvette body height
DETENT_COUNT_MULT = 1       # one detent notch per optic position


def _fillet_safe(wp, edges_selector, radius):
    """Fillet the blank BEFORE cutting features; fall back gracefully."""
    try:
        return wp.edges(edges_selector).fillet(radius)
    except Exception:
        return wp


def _polar(radius, angle_deg):
    a = math.radians(angle_deg)
    return radius * math.cos(a), radius * math.sin(a)


# ─── Mode 1: rotating filter / optic wheel ────────────────────────────────────
def build_wheel():
    """Detented filter wheel: a disc with N optic pockets and a central bore.

    Optic pockets are blind bores OPEN to the top face (no trapped voids). Rim
    detents are notches CUT from the outer edge (never tangent-sphere unions),
    so the mesh stays a single watertight body.
    """
    n = max(3, positions)
    optic_r = optic_diameter / 2.0
    # Pocket-centre radius: clear the central bore and leave rim material.
    pocket_ring_r = optic_r + max(6.0, bore_diameter) + 4.0
    disc_r = pocket_ring_r + optic_r + 6.0
    t = max(4.0, wheel_thickness)

    disc = cq.Workplane("XY").circle(disc_r).extrude(t)
    disc = _fillet_safe(disc, "|Z", 1.5)

    # Central mounting bore (through — open to both faces, not a sealed cavity).
    # Cut on an explicit Z-plane workplane so face selection can't go void after
    # subsequent pockets remove the ">Z" reference face.
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, t / 2.0))
        .cylinder(t + 2.0, bore_diameter / 2.0)
    )
    disc = disc.cut(bore)

    # Optic seat pockets: blind counterbores open to the top, with a light-pass
    # through-hole at each seat floor so beams pass and no void is trapped.
    seat_depth = t * 0.6
    light_d = optic_diameter * 0.7
    seat_pts = [_polar(pocket_ring_r, i * 360.0 / n) for i in range(n)]
    for (sx, sy) in seat_pts:
        seat = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx, sy, t - seat_depth / 2.0))
            .cylinder(seat_depth, optic_r + 0.2)
        )
        light = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx, sy, t / 2.0))
            .cylinder(t + 2.0, light_d / 2.0)
        )
        disc = disc.cut(seat).cut(light)

    # Rim detent notches: cylinders cut at the outer edge between optic stations.
    detent_r = 2.2
    for i in range(n):
        ang = (i + 0.5) * 360.0 / n
        dx, dy = _polar(disc_r, ang)
        notch = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(dx, dy, t / 2.0))
            .cylinder(t + 2.0, detent_r)
        )
        disc = disc.cut(notch)

    # Finger grip: a shallow relief slot cut into the top face near the rim.
    grip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(disc_r - 4.0, 0, t))
        .box(6.0, 18.0, t * 0.5)
    )
    return disc.cut(grip)


# ─── Mode 2: benchtop cuvette holder block ────────────────────────────────────
def build_cuvette_block():
    """A block with square cuvette wells (12.5 mm, standard 10 mm path) and a
    beam-access slot cut through the side so light reaches each cell."""
    n = max(1, cuvette_wells)
    well = CUVETTE_SQ + 0.4          # slip clearance around the cuvette
    wall = 4.0
    pitch = well + wall
    length = n * pitch + wall
    width = well + 2 * wall
    height = CUVETTE_H * 0.55

    block = (
        cq.Workplane("XY")
        .box(length, width, height, centered=(True, True, False))
    )
    block = _fillet_safe(block, "|Z", 3.0)

    # Cuvette wells: square blind pockets open to the top face.
    well_depth = height * 0.8
    well_floor = height - well_depth
    x0 = -(n - 1) * pitch / 2.0
    well_pts = [(x0 + i * pitch, 0.0) for i in range(n)]
    for (wx, wy) in well_pts:
        pocket = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(wx, wy, height - well_depth / 2.0))
            .box(well, well, well_depth)
        )
        block = block.cut(pocket)

    # Beam-access windows: one per well, cut from BOTH long side faces into the
    # well. Each window removes only wall material between the outer face and the
    # well cavity (open to both → no trapped void), and sits above the well floor
    # so the base bridge stays intact and the block remains a single body.
    win_z = well_floor + well_depth * 0.45
    win_h = min(well * 0.6, well_depth * 0.5)
    for (wx, wy) in well_pts:
        window = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(wx, 0.0, win_z))
            .box(well * 0.7, width + 2.0, win_h)
        )
        block = block.cut(window)
    return block


# ─── Mode 3: retaining hub cap ────────────────────────────────────────────────
def build_hub_cap():
    """Knurled-style hub cap that pins the wheel to its shaft: a stepped disc with
    a shaft bore and radial finger flutes cut into the rim."""
    cap_r = max(9.0, bore_diameter) + 8.0
    boss_r = max(6.0, bore_diameter / 2.0 + 3.0)
    cap_t = 5.0
    boss_h = 4.0

    cap = cq.Workplane("XY").circle(cap_r).extrude(cap_t)
    # Locating boss on the underside seats into the wheel's central bore.
    boss = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -boss_h))
        .circle(boss_r).extrude(boss_h)
    )
    cap = cap.union(boss)
    cap = _fillet_safe(cap, ">Z", 1.0)

    # Shaft bore straight through the cap and boss (open both ends).
    cap = cap.faces(">Z").workplane().circle(bore_diameter / 2.0).cutThruAll()

    # Radial finger flutes: cylinders cut around the rim for grip.
    flutes = 10
    flute_r = 1.6
    for i in range(flutes):
        ang = i * 360.0 / flutes
        fx, fy = _polar(cap_r, ang)
        flute = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(fx, fy, cap_t / 2.0))
            .cylinder(cap_t + 2.0, flute_r)
        )
        cap = cap.cut(flute)
    return cap


# ─── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "wheel":
    result = build_wheel()
elif target_part == "cuvette_block":
    result = build_cuvette_block()
elif target_part == "hub_cap":
    result = build_hub_cap()
else:
    result = build_wheel()
