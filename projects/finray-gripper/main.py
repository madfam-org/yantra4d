"""
Fin-Ray Gripper Jaw — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A compliant Fin-Ray-effect gripper finger. The Fin Ray Effect: a triangular
finger whose two long flanks are joined by angled cross-ribs; when the front
flank is pushed, the finger wraps TOWARD the load instead of away — passive
form-fitting compliance with no actuator. Here the whole finger is a PRINTABLE
SINGLE-BODY solid (a ribbed wedge); print it in PLA/PETG for a lightly compliant
jaw or in TPU for a soft, fully-wrapping one.

This cartridge bridges soft-robotics to the servo family: one mode carries a real
24T/25T servo output spline (the same negative-tooth bore used by `servo-horn`),
so a Fin-Ray jaw can bolt straight onto a hobby servo.

Modes:
  - finray_jaw    : the compliant Fin-Ray wedge finger with cross-ribs and a
                    bolt-through root tab.
  - finray_servo_mount : a Fin-Ray finger whose root is a splined servo boss
                    (24T Futaba / 25T Spektrum) — drives directly off a servo.
  - finray_finger : a slimmer single Fin-Ray blade (a modular jaw element for a
                    multi-finger hand) with a dovetail-free pin root.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
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


# ── Servo spline standards (shared with servo-horn) ──────────────────────────
# (teeth count, nominal pitch diameter mm). 24T Futaba/Savox, 25T Spektrum/Hitec.
SPLINE_TABLE = {"24T": (24, 5.8), "25T": (25, 6.0)}


def spline_spec(kind):
    return SPLINE_TABLE.get(kind, (24, 5.8))


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "finray_jaw"))
# "finray_jaw" | "finray_servo_mount" | "finray_finger"

fin_len = float(PARAM(lambda: fin_len, 70.0))     # finger length (tip travel, Y)
fin_base = float(PARAM(lambda: fin_base, 34.0))   # base width of the wedge (X at root)
fin_th = float(PARAM(lambda: fin_th, 16.0))       # finger thickness (Z)
rib_count = int(PARAM(lambda: rib_count, 6))      # number of cross-ribs
rib_w = float(PARAM(lambda: rib_w, 2.4))          # rib / flank wall thickness
spline = str(PARAM(lambda: spline, "24T"))        # servo spline (servo_mount mode)
hub_d = float(PARAM(lambda: hub_d, 12.0))         # servo boss outer diameter
tooth_h = float(PARAM(lambda: tooth_h, 0.35))     # spline tooth ridge depth
pin_d = float(PARAM(lambda: pin_d, 4.0))          # root pivot pin bore (finger mode)

# ── Clamp to sane ranges ─────────────────────────────────────────────────────
fin_len = max(40.0, min(fin_len, 120.0))
fin_base = max(18.0, min(fin_base, 60.0))
fin_th = max(8.0, min(fin_th, 28.0))
rib_count = max(3, min(rib_count, 12))
rib_w = max(1.5, min(rib_w, 5.0))
hub_d = max(8.0, min(hub_d, 20.0))
tooth_h = max(0.15, min(tooth_h, 0.8))
pin_d = max(2.0, min(pin_d, 8.0))

n_teeth, pitch_d = spline_spec(spline)
pitch_r = pitch_d / 2.0


# ── Fin-Ray wedge (the core compliant structure) ─────────────────────────────
def _finray_solid(length, base_w, thickness, ribs, wall):
    """Build the Fin-Ray finger as a single solid: a triangular wedge (wide at the
    root, meeting at the tip) whose interior is filled by a run of angled
    cross-ribs joining the two flanks. Built by UNIONING overlapping solids so the
    result is one watertight body. Root sits on XZ at y=0; tip at y=length.

    Geometry: the two flanks are the left/right edges of an isosceles triangle in
    the XY plane, extruded up Z by `thickness`. The front flank (the working face)
    is the +X edge; the back flank the -X edge; they converge at the tip."""
    half = base_w / 2.0
    # Outer triangular wedge (solid) — this alone is the finger blank.
    tri = (
        cq.Workplane("XY")
        .polyline([(-half, 0.0), (half, 0.0), (0.0, length)])
        .close()
        .extrude(thickness)
    )
    # Hollow the middle to leave two flank walls + ribs. Inner (smaller) triangle
    # cut, then ribs unioned back in. Inner triangle inset by `wall` on each edge.
    inset = wall
    # inner apex pulled back from the tip so the tip stays solid
    inner = (
        cq.Workplane("XY")
        .polyline([
            (-half + inset * 1.6, inset),
            (half - inset * 1.6, inset),
            (0.0, length - inset * 2.2),
        ])
        .close()
        .extrude(thickness)
    )
    body = tri.cut(inner)

    # Cross-ribs: bars spanning between the two flanks at rising heights along the
    # finger, each angled toward the tip (the Fin-Ray signature). Union them in.
    for i in range(ribs):
        t = (i + 1) / (ribs + 1)
        y = t * (length - inset * 2.0) + inset
        # width available between flanks at this y (linear taper to the tip)
        w_here = base_w * (1.0 - t) * 0.9
        if w_here < wall * 1.5:
            continue
        rib = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, y, 0.0),
                         rotate=cq.Vector(0, 0, 18.0 if i % 2 == 0 else -18.0))
            .box(w_here, wall, thickness, centered=(True, True, False))
        )
        body = body.union(rib)
    return body


def _root_slab(base_w, thickness, depth):
    """A solid mounting slab across the root, centred so it spans y in
    [-depth, +2] — overlapping the wedge base (y >= 0) so the weld is solid."""
    return (
        cq.Workplane("XY")
        .center(0.0, -depth / 2.0 + 1.0)
        .box(base_w, depth + 2.0, thickness, centered=(True, True, False))
    )


def build_finray_jaw():
    """The compliant Fin-Ray wedge with a bolt-through root slab (two M4 holes)."""
    root_depth = 12.0
    body = _finray_solid(fin_len, fin_base, fin_th, rib_count, rib_w)
    root = _root_slab(fin_base, fin_th, root_depth)
    body = body.union(root)
    # Two mounting holes through the root slab (through Z, vented both faces).
    for sx in (-1, 1):
        hx = sx * (fin_base / 2.0 - 5.0)
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(hx, -root_depth / 2.0 + 1.0, -1.0))
            .circle(2.2)   # M4 clearance
            .extrude(fin_th + 2.0)
        )
        body = body.cut(hole)
    return body


def _spline_cutter(height, hub_r):
    """The negative of a servo output spline: base cylinder (radius pitch_r -
    tooth_h) unioned with N rim teeth, so the bore left behind has N internal
    ridges that mesh with the servo shaft. Centred on origin, z 0..height. Same
    idiom as the `servo-horn` cartridge so the two genuinely interoperate."""
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


def build_finray_servo_mount():
    """A Fin-Ray finger whose root is a splined servo boss — the jaw drives
    directly off a 24T/25T hobby servo. The boss carries the internal spline bore
    and a central retaining-screw clearance; the wedge grows out of it."""
    hub_r = max(pitch_r + 2.0, hub_d / 2.0)
    boss_h = fin_th
    # Servo boss cylinder centred at the root (y ~ 0).
    boss = (
        cq.Workplane("XY")
        .center(0.0, -hub_r + 3.0)
        .circle(hub_r)
        .extrude(boss_h)
    )
    # Fin-Ray wedge overlapping the boss.
    wedge = _finray_solid(fin_len, fin_base, fin_th, rib_count, rib_w)
    body = boss.union(wedge)
    # Splined bore through the boss (from below, vented through the top too).
    cutter = _spline_cutter(boss_h + 2.0, hub_r).translate((0.0, -hub_r + 3.0, -1.0))
    body = body.cut(cutter)
    # Central retaining-screw clearance from the top down (vented to outside).
    screw = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, -hub_r + 3.0, boss_h - min(2.0, boss_h * 0.4)))
        .circle(1.6)
        .extrude(min(2.0, boss_h * 0.4) + 1.0)
    )
    body = body.cut(screw)
    return body


def build_finray_finger():
    """A slimmer single Fin-Ray blade — a modular jaw element with a pin-hinge
    root (one cross bore for a pivot pin). Thinner than the jaw so several stack
    on a hand."""
    slim_th = max(6.0, fin_th * 0.6)
    root_depth = 10.0
    body = _finray_solid(fin_len, fin_base * 0.8, slim_th, rib_count, rib_w)
    root = _root_slab(fin_base * 0.8, slim_th, root_depth)
    body = body.union(root)
    # Cross pivot bore through X (a hinge pin) near the root, vented both sides.
    bore = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(-root_depth / 2.0 + 1.0, slim_th / 2.0, 0))
        .circle(pin_d / 2.0)
        .extrude(fin_base * 0.8 / 2.0 + 2.0, both=True)
    )
    body = body.cut(bore)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "finray_servo_mount":
    result = build_finray_servo_mount()
elif target_part == "finray_finger":
    result = build_finray_finger()
else:
    result = build_finray_jaw()
