"""
GoPro Ball-Head Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An angle-adjustable base for the GoPro-style action-cam mount: a ball-and-socket
lets the camera tilt to any angle, then a pinch bolt locks it. The ball stud
carries a GoPro finger bank so it seats into a GoPro accessory; the socket clamp
grips the ball and carries its own GoPro fingers, so a whole articulating mount
drops into any GoPro ecosystem. A 1/4-20 variant screws a ball to a tripod.

Two standards, encoded dimensionally:
  GoPro finger clevis — finger thickness ~3.0 mm, gap ~3.2 mm (pitch ~6.2 mm),
    knuckle diameter ~15 mm, M5 axle bolt ~5.0 mm.
  1/4-20 UNC tripod screw — ~5.5 mm tapping/clearance socket.

Three modes (each geometrically distinct):
  - ball_stud     : a ball on a stem on a puck, GoPro 3-prong fingers underneath.
  - socket_clamp  : a cup with a ball cavity, compression slit + pinch bolt, GoPro
                    2-prong fingers underneath — grips a ball_stud.
  - ball_to_quarter : a ball on a stem on a puck with a 1/4-20 socket underneath.

Watertight strategy (ball joints are the trap here):
  The ball is a TRUNCATED sphere built by revolving a TRUE circular arc
  (threePointArc) with a straight axis segment giving small FLAT poles — this
  avoids the pole apex singularity that makes a naive .sphere() non-watertight
  (its tessellated poles leave open edges). The socket cavity is the same
  truncated ball subtracted, opened to the top by a cylindrical mouth (vents to
  outside). The slit and bolt are through-cuts. Fingers overlap into their base.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
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
target_part = str(PARAM(lambda: target_part, "ball_stud"))
# "ball_stud" | "socket_clamp" | "ball_to_quarter"

ball_d = float(PARAM(lambda: ball_d, 12.0))         # ball diameter
stem_d = float(PARAM(lambda: stem_d, 6.0))          # ball stem diameter
wall = float(PARAM(lambda: wall, 4.0))              # socket wall thickness
grip_clear = float(PARAM(lambda: grip_clear, 0.4))  # socket cavity per-side clearance

# GoPro finger clevis
finger_thick = float(PARAM(lambda: finger_thick, 3.0))
finger_gap = float(PARAM(lambda: finger_gap, 3.2))
knuckle_d = float(PARAM(lambda: knuckle_d, 15.0))
bolt_hole_d = float(PARAM(lambda: bolt_hole_d, 5.0))
reach = float(PARAM(lambda: reach, 10.0))

quarter20_d = float(PARAM(lambda: quarter20_d, 5.5))    # 1/4-20 socket dia
quarter20_depth = float(PARAM(lambda: quarter20_depth, 8.0))  # 1/4-20 socket depth

# Clamp to sane ranges so extreme UI values never crash the kernel.
ball_d = max(8.0, min(ball_d, 24.0))
stem_d = max(3.0, min(stem_d, ball_d - 2.0))
wall = max(3.0, min(wall, 8.0))
grip_clear = max(0.1, min(grip_clear, 0.8))
finger_thick = max(2.0, min(finger_thick, 6.0))
finger_gap = max(2.2, min(finger_gap, 8.0))
knuckle_d = max(9.0, min(knuckle_d, 26.0))
bolt_hole_d = max(3.0, min(bolt_hole_d, 8.0))
reach = max(6.0, min(reach, 30.0))
quarter20_d = max(3.0, min(quarter20_d, 9.0))
quarter20_depth = max(4.0, min(quarter20_depth, 14.0))

_knuckle_r = max(1.0, knuckle_d / 2.0)
_bolt_r = min(max(0.5, bolt_hole_d / 2.0), _knuckle_r - 1.2)
_pitch = finger_thick + finger_gap
_shaft_w = knuckle_d * 0.92


# ── Truncated ball (flat poles → watertight surface of revolution) ───────────
def _trunc_ball(r, flat_frac=0.16):
    """A near-sphere of radius r with small flat discs at both poles, built by
    revolving a TRUE circular arc with a straight axis segment. No pole apex →
    watertight (unlike a naive .sphere(), whose tessellated poles leave gaps)."""
    flat_frac = max(0.08, min(flat_frac, 0.4))
    th = math.asin(flat_frac)
    z_top = r * math.cos(th)
    flat_r = r * math.sin(th)
    prof = (
        cq.Workplane("XZ")
        .moveTo(0.0, z_top)
        .lineTo(0.0, -z_top)
        .lineTo(flat_r, -z_top)
        .threePointArc((r, 0.0), (flat_r, z_top))
        .close()
    )
    return prof.revolve(360, (0, 0, 0), (0, 1, 0))


# ── GoPro finger primitive ────────────────────────────────────────────────────
def _finger(x_center, base_top_z):
    knuckle = cq.Workplane("YZ").circle(_knuckle_r).extrude(finger_thick / 2.0, both=True)
    shaft_h = reach + 4.0
    shaft = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -shaft_h / 2.0))
        .box(finger_thick, _shaft_w, shaft_h, centered=(True, True, True))
    )
    finger = knuckle.union(shaft)
    hole = cq.Workplane("YZ").circle(_bolt_r).extrude(finger_thick, both=True)
    finger = finger.cut(hole)
    return finger.translate((x_center, 0, base_top_z + reach))


def _bank_down(filled):
    """A finger bank facing DOWN (knuckles below Z=0), for mounting under a puck."""
    x0 = -_pitch
    bank = None
    for i in filled:
        f = _finger(x0 + i * _pitch, 0.0)
        bank = f if bank is None else bank.union(f)
    bank = bank.rotate((0, 0, 0), (1, 0, 0), 180)  # point -Z
    return bank


def _puck(diameter, height):
    puck = cq.Workplane("XY").circle(diameter / 2.0).extrude(height)
    try:
        puck = puck.edges("|Z").fillet(min(2.0, diameter / 2.0 - 0.5))
    except Exception:
        pass
    return puck


# ── Part builders ────────────────────────────────────────────────────────────
def _ball_on_puck(puck_d, puck_h):
    """A ball on a stem rising from a puck (puck top at Z=puck_h). Returns the
    fused solid; ball centre sits above the stem."""
    r = ball_d / 2.0
    stem_h = max(4.0, r * 0.9)
    puck = _puck(puck_d, puck_h)
    stem = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, puck_h - 0.01))
        .circle(stem_d / 2.0)
        .extrude(stem_h + 0.01)
    )
    ball = _trunc_ball(r).translate((0, 0, puck_h + stem_h + r * 0.72))
    return puck.union(stem).union(ball)


def build_ball_stud():
    """A ball stud with GoPro 3-prong fingers underneath — insert the ball into a
    socket_clamp, and the fingers into a GoPro accessory."""
    puck_d = max(knuckle_d * 1.5, ball_d + 8.0)
    puck_h = 5.0
    body = _ball_on_puck(puck_d, puck_h)
    return body.union(_bank_down([0, 1, 2]))


def build_ball_to_quarter():
    """A ball stud on a puck with a 1/4-20 socket bored into the underside —
    screws a ball onto any tripod / 1/4-20 stud."""
    puck_d = max(ball_d + 12.0, quarter20_d + 2.0 * wall + 6.0)
    puck_h = max(6.0, quarter20_depth + 2.5)
    body = _ball_on_puck(puck_d, puck_h)
    # 1/4-20 socket up from the underside (vented at the bottom face).
    q_r = max(0.5, quarter20_d / 2.0)
    q_depth = min(quarter20_depth, puck_h - 1.5)
    socket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.01))
        .circle(q_r)
        .extrude(q_depth + 0.01)
    )
    return body.cut(socket)


def build_socket_clamp():
    """A cup that grips a ball: a ball-shaped cavity opening up, a compression
    slit and a cross pinch bolt, with GoPro 2-prong fingers underneath. Tighten
    the bolt to lock the ball at any angle."""
    r = ball_d / 2.0
    cav_r = r + grip_clear
    cup_od = ball_d + 2.0 * wall
    cup_h = ball_d * 0.85 + 3.0
    cup = _puck(cup_od, cup_h)

    # Ball cavity: cavity centre set so the ball's equator sits inside and the
    # cavity opens toward the top.
    cav = _trunc_ball(cav_r).translate((0, 0, cup_h - ball_d * 0.30))
    cup = cup.cut(cav)

    # Cylindrical mouth from the top down into the cavity so it vents (no trapped
    # void) and the ball can enter.
    mouth = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cup_h - 2.0))
        .circle(ball_d * 0.42)
        .extrude(4.0)
    )
    cup = cup.cut(mouth)

    # Compression slit from the top on one side into the cavity (lets the jaw
    # pinch). Through-cut → vented.
    slit = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cup_od / 2.0 - wall * 0.5, 0, cup_h - ball_d * 0.5))
        .box(1.6, cup_od + 2.0, ball_d, centered=(True, True, False))
    )
    cup = cup.cut(slit)

    # Cross pinch bolt near the top (through-hole along X).
    bolt = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, cup_h - 2.5, 0))
        .circle(max(0.5, min(2.6, wall)))
        .extrude(cup_od / 2.0 + 1.0, both=True)
    )
    cup = cup.cut(bolt)

    return cup.union(_bank_down([0, 2]))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "socket_clamp":
    result = build_socket_clamp()
elif target_part == "ball_to_quarter":
    result = build_ball_to_quarter()
else:  # "ball_stud"
    result = build_ball_stud()
