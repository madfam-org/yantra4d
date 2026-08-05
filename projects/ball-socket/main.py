"""
Ball-Socket / Articulated Arm — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A ball-and-socket joint for adjustable arms: phone, mic, camera, and light
mounts. A ball stud snaps into a socket cup whose opening is slightly smaller
than the ball, so friction holds any angle. Parts chain into arms of arbitrary
length. The 1/4-20 camera interface is modelled as its nominal clearance hole
(no slow helical thread).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `ball_dia`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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
ball_dia    = float(PARAM(lambda: ball_dia,    16.0))   # ball diameter (mm)
socket_grip = float(PARAM(lambda: socket_grip,  0.85))  # opening as fraction of ball_dia (<1 grips)
socket_clear = float(PARAM(lambda: socket_clear, 0.3))  # radial clearance socket sphere vs ball
stem_len    = float(PARAM(lambda: stem_len,    30.0))   # stem / arm length (mm)
stem_dia    = float(PARAM(lambda: stem_dia,     9.0))   # stem diameter (mm)
base_dia    = float(PARAM(lambda: base_dia,    22.0))   # base plate / cup outer diameter (mm)

end_type    = str(  PARAM(lambda: end_type,    "ball"))       # ball|socket|1/4-20|flat_mount
target_part = str(  PARAM(lambda: target_part, "ball_stud"))  # ball_stud|socket_cup|double_ball|arm_segment

# ── Derived + safe clamps ────────────────────────────────────────────────────
ball_r = max(2.0, ball_dia / 2.0)
# The socket cavity is a sphere slightly larger than the ball so it rotates
# freely; the RIM opening is smaller than the ball so the ball is captured.
socket_grip = max(0.55, min(socket_grip, 0.95))
socket_clear = max(0.1, min(socket_clear, 1.0))
socket_r = ball_r + socket_clear
opening_r = max(1.0, (ball_dia * socket_grip) / 2.0)   # < ball_r → captures ball
stem_dia = max(3.0, min(stem_dia, ball_dia - 1.0))
base_dia = max(ball_dia + 2.0, base_dia)
QUARTER20_HOLE = 5.5   # nominal 1/4-20 clearance bore (mm)


# ── Helpers ──────────────────────────────────────────────────────────────────
def make_ball(cz, r):
    """A watertight ball centered on the Z axis at height cz. A thin axial rod
    (fully interior, invisible) runs the full height through both poles: the
    boolean union re-tessellates the sphere poles, removing the degenerate
    pole-fan triangles that OCP's STL export otherwise leaves (which read as
    non-watertight). Purely a mesh-quality device — the rod never protrudes."""
    ball = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cz))
        .sphere(r)
    )
    rod = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cz))
        .cylinder(2.0 * r + 0.4, min(0.6, r * 0.15))
    )
    return ball.union(rod)


def ball_on_stem(z0):
    """A ball on a stem that rises from z0. Ball center at z0 + stem_len +
    0.55*ball_r so the stem buries into the ball for a solid neck."""
    stem = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0 + stem_len / 2.0))
        .cylinder(stem_len, stem_dia / 2.0)
    )
    ball = make_ball(z0 + stem_len + ball_r * 0.55, ball_r)
    return stem.union(ball)


def base_plate():
    """A short cylindrical base sitting on z=0 (thickness = base_dia * 0.28)."""
    t = max(4.0, base_dia * 0.28)
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, t / 2.0))
        .cylinder(t, base_dia / 2.0)
    )


def flat_mount_base():
    """A rectangular mounting plate with two screw holes, on z=0."""
    t = max(4.0, base_dia * 0.22)
    plate_w = base_dia * 1.6
    plate_d = base_dia
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, t / 2.0))
        .box(plate_w, plate_d, t)
    )
    hole_off = plate_w / 2.0 - max(5.0, base_dia * 0.22)
    for sx in (-1, 1):
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * hole_off, 0, t / 2.0))
            .cylinder(t + 2.0, 2.1)   # ~M4 clearance
        )
        plate = plate.cut(hole)
    return plate


def socket_cup_on(z0, flip=False):
    """A socket cup whose mouth captures a ball. Built as a thick-walled sphere
    shell: outer sphere (socket_r + wall) minus inner sphere (socket_r), then
    the mouth is opened by cutting a cylinder whose radius = opening_r (< ball_r)
    so the ball snaps past the rim and is held. Mouth faces +Z (or -Z if flip).
    Cup center sits at z0 + wall + socket_r."""
    wall = max(2.0, ball_r * 0.35)
    cz = z0 + wall + socket_r
    outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cz))
        .sphere(socket_r + wall)
    )
    inner = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cz))
        .sphere(socket_r)
    )
    cup = outer.cut(inner)

    # Open the mouth: remove the cap above the rim plane so the ball can enter.
    # The rim plane is where the sphere cross-section radius == opening_r.
    # Distance from center to that plane along the mouth axis:
    #   d = sqrt(socket_r^2 - opening_r^2)
    d = math.sqrt(max(0.0, socket_r * socket_r - opening_r * opening_r))
    mouth_dir = -1.0 if flip else 1.0
    # Cut everything beyond the rim plane on the mouth side (a big box).
    big = socket_r + wall + 10.0
    cut_center_z = cz + mouth_dir * (d + big)
    mouth_cut = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cut_center_z))
        .box(2.0 * big, 2.0 * big, 2.0 * big)
    )
    cup = cup.cut(mouth_cut)

    # A short access bore through the shell wall at the mouth so the opening is
    # a clean circular throat of radius opening_r (not just a sliced sphere cap).
    throat = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cz + mouth_dir * (d + wall)))
        .cylinder(2.0 * (wall + 1.0), opening_r)
    )
    cup = cup.cut(throat)

    # Pierce the closed (dome) pole with a thin axial rod inside the wall so the
    # shell's pole tessellation is regular and the mesh exports watertight (same
    # OCP pole-fan fix as make_ball; the rod lives in the solid wall material).
    dome_z = cz - mouth_dir * (socket_r + wall / 2.0)
    pole_rod = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, dome_z))
        .cylinder(wall + 1.0, min(0.5, wall * 0.4))
    )
    cup = cup.union(pole_rod)
    return cup


def end_feature(top):
    """Return the requested far-end feature as a solid, positioned with its root
    at height `top` (the stem top). Shared by arm_segment and any chainable end.
    end_type: 'ball' (default) | 'socket' | '1/4-20' | 'flat_mount'."""
    if end_type == "socket":
        return socket_cup_on(top, flip=False)
    if end_type == "flat_mount":
        t = 4.0
        tab = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, top + t / 2.0))
            .box(base_dia, base_dia * 0.6, t)
        )
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, top + t / 2.0))
            .cylinder(t + 2.0, 2.1)
        )
        return tab.cut(hole)
    if end_type == "1/4-20":
        boss = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, top + 5.0))
            .cylinder(10.0, stem_dia / 2.0 + 2.0)
        )
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, top + 5.0))
            .cylinder(12.0, QUARTER20_HOLE / 2.0)
        )
        return boss.cut(bore)
    return make_ball(top + ball_r * 0.55, ball_r)


# ── Part builders ────────────────────────────────────────────────────────────
def build_ball_stud():
    """A ball on a stem rising from a base. The base depends on end_type:
    flat_mount → rectangular screw plate, 1/4-20 → cylindrical boss with the
    camera bore, else a round base."""
    if end_type == "flat_mount":
        base = flat_mount_base()
        z0 = max(4.0, base_dia * 0.22)
    elif end_type == "1/4-20":
        base = base_plate()
        t = max(4.0, base_dia * 0.28)
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, t / 2.0))
            .cylinder(t + 2.0, QUARTER20_HOLE / 2.0)
        )
        base = base.cut(bore)
        z0 = t
    else:
        base = base_plate()
        z0 = max(4.0, base_dia * 0.28)
    return base.union(ball_on_stem(z0))


def build_socket_cup():
    """A socket cup on a base. The cup grips a ball of ball_dia; its mouth faces
    up. The base is a round plate (or screw plate for flat_mount end_type)."""
    if end_type == "flat_mount":
        base = flat_mount_base()
        z0 = max(4.0, base_dia * 0.22)
    else:
        base = base_plate()
        z0 = max(4.0, base_dia * 0.28)
    # Short neck between base and cup for clearance.
    neck_h = max(3.0, ball_r * 0.4)
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0 + neck_h / 2.0))
        .cylinder(neck_h, stem_dia / 2.0 + 1.0)
    )
    cup = socket_cup_on(z0 + neck_h, flip=False)
    return base.union(neck).union(cup)


def build_double_ball():
    """A link with a ball on both ends of a central stem — chains two sockets."""
    lower = make_ball(ball_r * 0.55, ball_r)
    stem = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, ball_r + stem_len / 2.0))
        .cylinder(stem_len, stem_dia / 2.0)
    )
    upper = make_ball(ball_r + stem_len + ball_r * 0.55, ball_r)
    return lower.union(stem).union(upper)


def build_arm_segment():
    """A chainable segment: a socket cup at the bottom (mouth down, grips a
    ball) and, on the far stem end, the feature chosen by end_type (default a
    ball). This is the repeatable unit of an articulated arm."""
    # Socket cup at the base, mouth facing DOWN to receive a ball from below.
    wall = max(2.0, ball_r * 0.35)
    cup = socket_cup_on(0.0, flip=True)
    # After flip, the cup body occupies roughly z:[0, 2*(wall+socket_r)] with the
    # mouth at the bottom; its top is a closed dome. Rise a stem from that top.
    cup_top = 2.0 * wall + 2.0 * socket_r
    stem = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cup_top + stem_len / 2.0))
        .cylinder(stem_len, stem_dia / 2.0)
    )
    body = cup.union(stem)

    # Far-end feature at the stem top (shared with any chainable end).
    top = cup_top + stem_len
    return body.union(end_feature(top))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "socket_cup":
    result = build_socket_cup()
elif target_part == "double_ball":
    result = build_double_ball()
elif target_part == "arm_segment":
    result = build_arm_segment()
else:
    result = build_ball_stud()
