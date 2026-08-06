"""
Servo Horn — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A replacement servo arm with a real splined bore. The bore is cut with N internal
teeth matching the servo output spline standard: 24T (~5.8 mm, Futaba / Savox) or
25T (~6.0 mm, Spektrum / Hitec). Linkage holes sit at a chosen radius along the
arm. Three modes: a single arm, a double (two-sided) arm, and a round wheel horn
with holes around a disc.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `spline`).
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


# ── Servo spline standards ────────────────────────────────────────────────────
# (teeth count, nominal pitch diameter mm). 24T Futaba/Savox, 25T Spektrum/Hitec.
SPLINE_TABLE = {"24T": (24, 5.8), "25T": (25, 6.0)}


def spline_spec(kind):
    """Return (n_teeth, pitch_diameter_mm) for the spline standard."""
    return SPLINE_TABLE.get(kind, (24, 5.8))


# ── Parameters ───────────────────────────────────────────────────────────────
spline      = str(  PARAM(lambda: spline, "24T"))    # 24T | 25T
hub_d       = float(PARAM(lambda: hub_d,     10.0))  # boss/hub outer diameter around the spline
horn_t      = float(PARAM(lambda: horn_t,     4.0))  # horn thickness (Z)
arm_len     = float(PARAM(lambda: arm_len,   22.0))  # arm length from centre to tip
arm_w       = float(PARAM(lambda: arm_w,      7.0))  # arm width at the tip
hole_d      = float(PARAM(lambda: hole_d,     2.0))  # linkage hole diameter (1.5 M / clevis)
hole_count  = int(  PARAM(lambda: hole_count,   4))  # linkage holes along the arm
hole_pitch  = float(PARAM(lambda: hole_pitch, 3.0))  # spacing between linkage holes
screw_d     = float(PARAM(lambda: screw_d,    2.5))  # central retaining screw clearance
tooth_h     = float(PARAM(lambda: tooth_h,   0.35))  # spline tooth height (ridge depth)
wheel_d     = float(PARAM(lambda: wheel_d,   32.0))  # wheel-horn disc diameter (wheel mode)

target_part = str(PARAM(lambda: target_part, "single_arm"))
# "single_arm" | "double_arm" | "wheel_horn"


# ── Derived / clamped geometry ───────────────────────────────────────────────
n_teeth, pitch_d = spline_spec(spline)
pitch_r = pitch_d / 2.0
hub_r = max(pitch_r + 1.6, hub_d / 2.0)
hole_r = max(0.5, hole_d / 2.0)
screw_r = max(0.6, min(screw_d / 2.0, pitch_r - 0.4))
tooth_h = max(0.15, min(tooth_h, 0.8))
hole_count = max(1, min(hole_count, 10))


def _spline_cutter(height):
    """The negative of the servo output spline: a base cylinder (radius
    pitch_r - tooth_h) unioned with N small teeth at the rim, so the bore left in
    the horn has N internal ridges that mesh with the shaft's N teeth. Centred on
    the origin, from z=0 to z=height."""
    base = cq.Workplane("XY").circle(max(0.6, pitch_r - tooth_h)).extrude(height)
    tooth_w = (2.0 * math.pi * pitch_r / n_teeth) * 0.5
    teeth = None
    for i in range(n_teeth):
        a = 360.0 * i / n_teeth
        rad = math.radians(a)
        cx = (pitch_r - tooth_h / 2.0) * math.cos(rad)
        cy = (pitch_r - tooth_h / 2.0) * math.sin(rad)
        t = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, 0), rotate=cq.Vector(0, 0, a))
            .box(tooth_h + 0.4, tooth_w, height, centered=(True, True, False))
        )
        teeth = t if teeth is None else teeth.union(t)
    return base.union(teeth)


def _hub():
    """The central boss carrying the splined bore + a counterbore for the servo
    retaining screw head. Base at z=0, up to z=horn_t."""
    boss = cq.Workplane("XY").circle(hub_r).extrude(horn_t)
    # Splined bore through the boss.
    boss = boss.cut(_spline_cutter(horn_t + 2.0).translate((0, 0, -1.0)))
    # Central screw clearance up top (so the horn screw passes to the shaft).
    boss = (
        boss.faces(">Z").workplane()
        .circle(screw_r).cutBlind(-min(horn_t - 1.0, horn_t * 0.6))
    )
    return boss


def _arm_bar(length, width, thickness):
    """A tapered arm bar from the hub (X=0) out to +X `length`, `width` at the
    tip, blending into the hub. Base at z=0, up `thickness`."""
    root_w = max(width, hub_r * 1.4)
    bar = (
        cq.Workplane("XY")
        .polyline([
            (0.0, -root_w / 2.0),
            (length, -width / 2.0),
            (length, width / 2.0),
            (0.0, root_w / 2.0),
        ])
        .close()
        .extrude(thickness)
    )
    # Round the tip.
    tip = cq.Workplane("XY").transformed(offset=cq.Vector(length, 0, 0)).circle(width / 2.0).extrude(thickness)
    return bar.union(tip)


def _arm_holes(bar, length):
    """Cut `hole_count` linkage holes along the arm, spaced `hole_pitch`, ending
    near the tip."""
    # Outermost hole sits `hole_r + 1` from the tip; work inward.
    x_out = length - (hole_r + 1.0)
    for i in range(hole_count):
        x = x_out - i * hole_pitch
        if x < hub_r + hole_r:
            break
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, 0, -1.0))
            .circle(hole_r).extrude(horn_t + 2.0)
        )
        bar = bar.cut(hole)
    return bar


def build_single_arm():
    """One arm off the splined hub with a row of linkage holes."""
    hub = _hub()
    arm = _arm_bar(arm_len, arm_w, horn_t)
    arm = _arm_holes(arm, arm_len)
    return hub.union(arm)


def build_double_arm():
    """Two opposed arms (a 180-degree bar) off the splined hub — the classic
    two-sided horn for pull-pull or balanced linkages."""
    hub = _hub()
    arm_a = _arm_holes(_arm_bar(arm_len, arm_w, horn_t), arm_len)
    arm_b = arm_a.rotate((0, 0, 0), (0, 0, 1), 180.0)
    return hub.union(arm_a).union(arm_b)


def build_wheel_horn():
    """A round wheel horn: a disc on the splined hub with linkage holes arranged
    around a bolt circle — used for steering / heavy pulls."""
    hub = _hub()
    disc = cq.Workplane("XY").circle(max(hub_r + 3.0, wheel_d / 2.0)).extrude(horn_t)
    body = hub.union(disc)
    # Holes on a bolt circle near the rim.
    bc_r = max(hub_r + 2.0, wheel_d / 2.0 - (hole_r + 2.0))
    n = max(4, hole_count * 2)
    for i in range(n):
        a = math.radians(360.0 * i / n)
        x = bc_r * math.cos(a)
        y = bc_r * math.sin(a)
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, -1.0))
            .circle(hole_r).extrude(horn_t + 2.0)
        )
        body = body.cut(hole)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "double_arm":
    result = build_double_arm()
elif target_part == "wheel_horn":
    result = build_wheel_horn()
else:  # "single_arm"
    result = build_single_arm()
