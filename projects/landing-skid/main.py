"""
Landing Skid — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Printable landing gear for FPV & RC multirotors. A leg drops from the frame to a
splayed foot, protecting the belly, camera and gimbal on landing. It attaches
either by clamping around a round arm/boom, or by bolting to a flat frame plate
using the standard square motor bolt pattern. Three modes: a boom-clamp skid, a
bolt-on skid, and a tall gear that lifts the craft for camera / cargo clearance.

Reuses the shared `motor_bolt_points()` / `motor_screw_d()` helper for the
bolt-on mode — the same motor bolt-pattern interface used across the drone
Commons.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `boom_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use
    globals()/eval/getattr — they are not in the sandbox's allowed builtins.
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


# ── Shared motor bolt-pattern interface (reused across the drone Commons) ─────
MOTOR_PATTERNS = {"16x16": 16.0, "19x19": 19.0, "9x9": 9.0}


def motor_bolt_points(pattern):
    """Return the 4 (x,y) motor-screw centres for a square NxN mount pattern."""
    s = MOTOR_PATTERNS.get(pattern, 16.0)
    h = s / 2.0
    return [(h, h), (h, -h), (-h, h), (-h, -h)]


def motor_screw_d(pattern):
    """Screw clearance diameter: 9x9 boards use M2, 16/19 use M3."""
    return 2.4 if pattern == "9x9" else 3.4


# ── Parameters ───────────────────────────────────────────────────────────────
boom_dia    = float(PARAM(lambda: boom_dia,    12.0))   # arm/boom diameter to clamp (clamp mode)
skid_h      = float(PARAM(lambda: skid_h,      45.0))   # skid height (frame down to foot)
leg_w       = float(PARAM(lambda: leg_w,        8.0))   # leg width
leg_t       = float(PARAM(lambda: leg_t,        5.0))   # leg thickness
foot_len    = float(PARAM(lambda: foot_len,    40.0))   # foot length (fore-aft skid)
foot_w      = float(PARAM(lambda: foot_w,      10.0))   # foot width
splay       = float(PARAM(lambda: splay,       12.0))   # outward splay of the foot (deg)
clamp_wall  = float(PARAM(lambda: clamp_wall,   3.0))   # wall around the boom (clamp mode)
motor_pattern = str(PARAM(lambda: motor_pattern, "16x16"))  # bolt mode plate pattern
tall_extra  = float(PARAM(lambda: tall_extra,  35.0))   # extra height for the tall gear mode

target_part = str(PARAM(lambda: target_part, "clamp_skid"))
# "clamp_skid" | "bolt_skid" | "tall_gear"


# ── Derived / clamped geometry ───────────────────────────────────────────────
boom_r = max(2.0, boom_dia / 2.0)
splay = max(0.0, min(splay, 30.0))
screw_r = max(0.8, motor_screw_d(motor_pattern) / 2.0)
plate_w = MOTOR_PATTERNS.get(motor_pattern, 16.0) + 10.0


def _foot(z_bottom, f_len, f_w):
    """A splayed skid foot: a rounded bar running fore-aft (Y), sitting at
    z=z_bottom, with rounded ends so it slides on landing."""
    foot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_bottom + leg_t / 2.0))
        .box(f_w, f_len, leg_t, centered=(True, True, True))
    )
    # Rounded caps at both ends.
    for sy in (-1.0, 1.0):
        cap = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, sy * f_len / 2.0, z_bottom + leg_t / 2.0))
            .cylinder(leg_t, f_w / 2.0)
        )
        foot = foot.union(cap)
    try:
        foot = foot.edges("|Z").fillet(min(1.5, f_w / 4.0))
    except Exception:
        pass
    return foot


def _leg(height):
    """A vertical leg from z=0 (top) down to z=-height, splayed outward at the
    bottom so the foot sits wider than the mount. Built as a leaning box."""
    # Leg leans out in +Y by `splay` about the top (z=0) so the foot moves to +Y.
    leg = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -height / 2.0))
        .box(leg_w, leg_t, height, centered=(True, True, True))
    )
    if splay > 0.1:
        leg = leg.rotate((0, 0, 0), (1, 0, 0), splay)
    return leg


def _leg_and_foot(height, f_len, f_w):
    """A splayed leg with a foot at its bottom. Returns the union positioned with
    the leg top at z=0. The foot is placed where the leg bottom lands after the
    splay rotation about the top (z=0)."""
    leg = _leg(height)
    ang = math.radians(splay)
    z0 = -height
    # Rotate the leg-bottom centre (0, 0, z0) about X by +splay: y and z map to
    #   y' = -z0*sin(ang),  z' = z0*cos(ang).
    y_b = -z0 * math.sin(ang)
    z_b = z0 * math.cos(ang)
    foot = _foot(z_b - leg_t / 2.0, f_len, f_w).translate((0, y_b, 0))
    return leg.union(foot)


def _boom_clamp():
    """A clamp collar that wraps a round boom (axis along X) with a split so it
    can be pinched onto the arm. Centred at the frame level (z=0), boom axis
    along X."""
    outer_r = boom_r + max(1.5, clamp_wall)
    collar = (
        cq.Workplane("YZ")
        .circle(outer_r)
        .extrude(leg_w, both=True)
    )
    bore = (
        cq.Workplane("YZ")
        .circle(boom_r)
        .extrude(leg_w + 2.0, both=True)
    )
    collar = collar.cut(bore)
    # Split kerf from the bottom so it clamps (a thin slot up to the bore).
    kerf = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -outer_r / 2.0))
        .box(leg_w * 2.0 + 2.0, 1.2, outer_r, centered=(True, True, True))
    )
    collar = collar.cut(kerf)
    return collar


def _bolt_plate():
    """A flat mounting plate carrying the square motor bolt pattern. Top at
    z=leg_t, so a splayed leg can grow from its underside."""
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, leg_t / 2.0))
        .box(plate_w, plate_w, leg_t, centered=(True, True, True))
    )
    try:
        plate = plate.edges("|Z").fillet(min(3.0, plate_w / 2.0 - 0.6))
    except Exception:
        pass
    plate = (
        plate.faces(">Z").workplane()
        .pushPoints(motor_bolt_points(motor_pattern))
        .circle(screw_r).cutThruAll()
    )
    return plate


def build_clamp_skid():
    """Boom-clamp skid: a clamp collar around the arm, a splayed leg, and a foot."""
    collar = _boom_clamp()
    leg_foot = _leg_and_foot(skid_h, foot_len, foot_w)
    # Connect the collar (centred at z=0) to the leg top (z=0). A small bridge
    # block fuses the round collar to the rectangular leg.
    bridge = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -boom_r / 2.0))
        .box(leg_w, leg_t, boom_r + 1.0, centered=(True, True, True))
    )
    return collar.union(bridge).union(leg_foot)


def build_bolt_skid():
    """Bolt-on skid: a flat plate carrying the square motor bolt pattern, a
    splayed leg, and a foot — bolts under an arm's motor mount or a frame plate."""
    return _bolt_plate().union(_leg_and_foot(skid_h, foot_len, foot_w))


def build_tall_gear():
    """Tall landing gear: like the bolt-on skid but taller (adds `tall_extra`) to
    lift the belly for a camera / gimbal / cargo, with a wider foot for stability."""
    return _bolt_plate().union(
        _leg_and_foot(skid_h + tall_extra, foot_len * 1.3, foot_w * 1.2)
    )


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bolt_skid":
    result = build_bolt_skid()
elif target_part == "tall_gear":
    result = build_tall_gear()
else:  # "clamp_skid"
    result = build_clamp_skid()
