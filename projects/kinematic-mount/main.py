"""
Kinematic Mount 3-Ball — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A repeatable 3-ball kinematic coupling: two plates that mate on exactly six
points of contact, so they separate and re-seat to the same position every time
(sub-micron repeatability in metal; excellent in print for optics, fixtures and
tool changers).

Two established seat geometries are provided:
  - Kelvin coupling (cone / vee / flat) — three DIFFERENT seats: a trihedral
    cone (3 contacts), a radial vee groove (2 contacts) and a flat land (1
    contact) = 6 constraints, statically determinate.
  - Maxwell coupling (three identical radial vees at 120°) — six contacts from
    three symmetric vees; lower thermal sensitivity because the vees radiate
    from the common centre.

Real design figures (precision-kinematics convention):
  - three seats / balls at 120° on a bolt-circle
  - ball diameter 6–10 mm (steel spheres, NOT printed) — default 8 mm
  - ball centre seats ~0.5 mm proud of the flat land; seats are cut pockets so
    the ball contacts the seat walls, never the pocket floor.

Watertight strategy (the load-bearing detail):
  Every seat is a CUT POCKET removed from a clean plate blank — a cone tool
  (makeCone), a triangular-prism vee tool (extruded triangle), a flat counterbore
  (cylinder), and, on the top plate, a spherical ball cup (sphere tool whose
  centre sits above the surface → leaves a clean spherical dimple). NO tangent
  sphere unions (they leave zero-volume seams). Fillet the blank BEFORE cutting;
  the centre bore and mount holes are through-holes vented to faces.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected; params arrive as BARE globals.
  - Read every param via PARAM(lambda: <name>, <default>).
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters (Maxwell/Kelvin 3-ball kinematic coupling) ────────────────────
target_part = str(PARAM(lambda: target_part, "base_plate"))
# "base_plate" (Kelvin cone/vee/flat) | "top_plate" (ball cups) | "base_vee3" (Maxwell)

plate_dia = float(PARAM(lambda: plate_dia, 60.0))     # plate diameter, mm
plate_thick = float(PARAM(lambda: plate_thick, 10.0))  # plate thickness, mm
ball_dia = float(PARAM(lambda: ball_dia, 8.0))        # steel ball diameter, mm
bolt_circle = float(PARAM(lambda: bolt_circle, 40.0))  # seat/ball circle diameter, mm
center_bore = float(PARAM(lambda: center_bore, 10.0))  # central through-bore, mm
mount_bolt_d = float(PARAM(lambda: mount_bolt_d, 4.3))  # mount bolt clearance (M4)

# Clamp to sane ranges so extreme UI values never crash the kernel.
plate_dia = max(36.0, min(plate_dia, 120.0))
plate_thick = max(6.0, min(plate_thick, 24.0))
ball_dia = max(6.0, min(ball_dia, 12.0))
bolt_circle = max(20.0, min(bolt_circle, plate_dia - 12.0))
center_bore = max(0.0, min(center_bore, bolt_circle - ball_dia - 4.0))
mount_bolt_d = max(2.5, min(mount_bolt_d, 8.0))

_ball_r = ball_dia / 2.0
_seat_r = bolt_circle / 2.0


def _polar(radius, ang_deg):
    a = math.radians(ang_deg)
    return radius * math.cos(a), radius * math.sin(a)


# ── Plate blank ──────────────────────────────────────────────────────────────
def _plate_blank():
    """A clean cylindrical plate, base at z=0, top at z=plate_thick, with a
    filleted top rim (done on the clean blank, before any seat cuts)."""
    blank = (
        cq.Workplane("XY")
        .circle(plate_dia / 2.0)
        .extrude(plate_thick)
    )
    try:
        blank = blank.edges(">Z").fillet(min(1.5, plate_thick * 0.15))
    except Exception:
        pass
    return blank


def _center_and_mounts(body):
    """Central through-bore (if any) + three mount through-holes on a wider
    circle, all vented top↔bottom. Mount holes sit between the seats (at 60°
    offset) so they never intersect a seat."""
    if center_bore > 0.5:
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -0.5))
            .circle(center_bore / 2.0)
            .extrude(plate_thick + 1.0)
        )
        body = body.cut(bore)
    mr = min((plate_dia / 2.0) - 5.0, _seat_r + _ball_r + 4.0)
    if mr > center_bore / 2.0 + mount_bolt_d:
        for i in range(3):
            mx, my = _polar(mr, 60.0 + i * 120.0)
            hole = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(mx, my, -0.5))
                .circle(max(0.6, mount_bolt_d / 2.0))
                .extrude(plate_thick + 1.0)
            )
            body = body.cut(hole)
    return body


# ── Seat tools (all CUT, never unioned spheres) ──────────────────────────────
def _cone_seat_tool(cx, cy):
    """A downward conical pocket (trihedral cone seat). A 90° included cone,
    deep enough that an 8 mm ball contacts the cone WALL (3-line contact) well
    above the apex. makeCone(r_bottom=apex, r_top=mouth) built pointing down."""
    depth = _ball_r * 0.9
    mouth_r = depth  # 90° included cone → mouth radius == depth
    apex = cq.Vector(cx, cy, plate_thick - depth)
    # Cone with apex (r≈0) at the bottom, mouth (r=mouth_r) at the top surface.
    cone = cq.Solid.makeCone(0.15, mouth_r, depth, apex, cq.Vector(0, 0, 1))
    # extend the mouth slightly above the surface so the cut face is clean
    lip = cq.Solid.makeCone(mouth_r, mouth_r + 0.6, 0.6,
                            cq.Vector(cx, cy, plate_thick), cq.Vector(0, 0, 1))
    return cq.Workplane("XY").add(cone).add(lip)


def _vee_seat_tool(cx, cy, ang_deg):
    """A radial V-groove pocket: a triangular prism whose apex points DOWN,
    oriented so the groove runs radially (a ball drops in and touches the two
    flanks — 2-point contact). Built by extruding a downward V triangle, then
    rotating it to the radial direction and translating to (cx, cy)."""
    depth = _ball_r * 0.9
    halfw = depth  # 90° V
    length = ball_dia + 4.0
    # Triangle in XZ: apex at bottom centre, opening up to the surface. Extrude
    # along Y to make the groove; groove axis = world Y before rotation.
    tri = (
        cq.Workplane("XZ")
        .polyline([(-halfw, plate_thick + 0.3),
                   (halfw, plate_thick + 0.3),
                   (0.0, plate_thick - depth)])
        .close()
        .extrude(length / 2.0, both=True)
    )
    # tri groove axis currently along Y. Rotate about Z so it points radially.
    tri = tri.rotate((0, 0, 0), (0, 0, 1), ang_deg - 90.0)
    tri = tri.translate((cx, cy, 0))
    return tri


def _flat_seat_tool(cx, cy):
    """A flat land seat: a shallow flat-bottomed counterbore. The ball rests on
    the flat floor (1-point contact). A plain cylinder pocket."""
    depth = min(1.2, plate_thick * 0.2)
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, plate_thick - depth))
        .circle(_ball_r + 1.5)
        .extrude(depth + 0.3)
    )
    return pocket


def _ball_cup_tool(cx, cy):
    """A spherical ball cup for the TOP plate: a sphere tool whose centre sits
    ABOVE the surface by (ball_r - seat_depth), so cutting it leaves a spherical
    cap dimple that cradles the lower hemisphere of a glued/pressed steel ball.
    A single sphere cut → clean watertight dimple (no tangent union)."""
    seat_depth = _ball_r * 0.6
    cz = plate_thick - seat_depth + _ball_r
    sph = cq.Solid.makeSphere(_ball_r, cq.Vector(cx, cy, cz))
    return cq.Workplane("XY").add(sph)


# ── Part builders ────────────────────────────────────────────────────────────
def build_base_plate():
    """Kelvin coupling base: cone + vee + flat seats at 0°, 120°, 240°."""
    body = _plate_blank()
    c0x, c0y = _polar(_seat_r, 0.0)
    c1x, c1y = _polar(_seat_r, 120.0)
    c2x, c2y = _polar(_seat_r, 240.0)
    body = body.cut(_cone_seat_tool(c0x, c0y))
    body = body.cut(_vee_seat_tool(c1x, c1y, 120.0))
    body = body.cut(_flat_seat_tool(c2x, c2y))
    body = _center_and_mounts(body)
    return body


def build_base_vee3():
    """Maxwell coupling base: three identical radial V-grooves at 120°."""
    body = _plate_blank()
    for i in range(3):
        ang = i * 120.0
        cx, cy = _polar(_seat_r, ang)
        body = body.cut(_vee_seat_tool(cx, cy, ang))
    body = _center_and_mounts(body)
    return body


def build_top_plate():
    """The moving plate: three spherical ball cups at 120° to seat pressed/glued
    steel balls that mate into the base seats. Distinct from either base."""
    body = _plate_blank()
    for i in range(3):
        cx, cy = _polar(_seat_r, i * 120.0)
        body = body.cut(_ball_cup_tool(cx, cy))
    body = _center_and_mounts(body)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "top_plate":
    result = build_top_plate()
elif target_part == "base_vee3":
    result = build_base_vee3()
else:
    result = build_base_plate()
