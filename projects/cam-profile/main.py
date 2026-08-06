"""
Cam / Eccentric — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A rotating cam that converts rotation into linear follower motion — the heart of
timers, automatons, indexers, engines, and clamping fixtures. Choose a motion law
(`cam_type`); the profile is built as a polar radius function r(θ) sampled into a
closed polyline and extruded, so the follower's displacement curve IS the printed
edge.

Interface (Cam Rise Profile, `spline`, internal):
  The working surface is defined by `base_radius` (the dwell/low radius) and `lift`
  (the peak rise above base). A follower tuned to that base + lift tracks the cam;
  swapping `cam_type` changes the timing law without changing the interface.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `base_radius`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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
cam_type    = str(  PARAM(lambda: cam_type, "eccentric"))  # eccentric | snail | harmonic
base_radius = float(PARAM(lambda: base_radius, 15.0))  # low/dwell radius (mm)
lift        = float(PARAM(lambda: lift,        10.0))  # peak rise above base (mm)
bore        = float(PARAM(lambda: bore,         6.0))  # shaft bore diameter (mm)
thickness   = float(PARAM(lambda: thickness,    8.0))  # cam thickness (Z, mm)
dwell_angle = float(PARAM(lambda: dwell_angle, 90.0))  # low-dwell span for harmonic (deg)
hub         = bool( PARAM(lambda: hub,        True))   # add a raised hub around the bore

target_part = str(PARAM(lambda: target_part, "eccentric"))  # mirrors cam_type

# `target_part` (the mode dispatcher) also selects the cam law, so either the mode
# or the explicit cam_type param can drive the shape; the mode wins if it names a
# known law.
if target_part in ("eccentric", "snail_cam", "harmonic_cam"):
    cam_type = {"eccentric": "eccentric", "snail_cam": "snail",
                "harmonic_cam": "harmonic"}[target_part]

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
base_radius = max(5.0, min(base_radius, 120.0))
lift = max(1.0, min(lift, base_radius * 2.5))
thickness = max(2.0, min(thickness, 40.0))
bore = max(2.0, min(bore, base_radius * 1.2))
dwell_angle = max(0.0, min(dwell_angle, 300.0))

_STEPS = 240  # angular samples around the profile (smooth but light)


# ── Radius laws r(θ), θ in radians over [0, 2π) ──────────────────────────────
def _r_eccentric(t):
    """Circle of radius base_radius whose center is offset by `lift/2` along +X.
    r(θ) = e·cosθ + sqrt(R² − e²·sin²θ), giving a smooth once-per-rev rise; the
    follower sees a near-sinusoidal lift of ~`lift`."""
    e = lift / 2.0
    R = base_radius
    s = e * math.sin(t)
    return e * math.cos(t) + math.sqrt(max(0.0, R * R - s * s))


def _r_snail(t):
    """Archimedean snail: radius rises linearly from base to base+lift over almost
    the whole turn, then drops sharply back (the return). Classic escapement /
    indexing cam."""
    rise_span = 2.0 * math.pi * 0.85  # 85% of the turn rises, 15% returns
    if t <= rise_span:
        return base_radius + lift * (t / rise_span)
    # Sharp linear return over the last 15%.
    frac = (t - rise_span) / (2.0 * math.pi - rise_span)
    return base_radius + lift * (1.0 - frac)


def _r_harmonic(t):
    """Rise–dwell–fall via cycloidal-ish halves. A low dwell of `dwell_angle`, then
    a smooth (1−cos) rise to peak over the next quarter-ish, a high dwell, and a
    smooth fall back — a gentle, low-shock motion law."""
    d = math.radians(dwell_angle)
    remaining = 2.0 * math.pi - d
    rise = remaining * 0.35
    high = remaining * 0.30
    fall = remaining - rise - high
    if t < d:
        return base_radius
    t2 = t - d
    if t2 < rise:
        return base_radius + lift * 0.5 * (1.0 - math.cos(math.pi * (t2 / rise)))
    t3 = t2 - rise
    if t3 < high:
        return base_radius + lift
    t4 = t3 - high
    return base_radius + lift * 0.5 * (1.0 + math.cos(math.pi * (t4 / max(1e-6, fall))))


_LAWS = {"eccentric": _r_eccentric, "snail": _r_snail, "harmonic": _r_harmonic}


def build_cam():
    """Sample the selected radius law into a closed polyline and extrude. Drill the
    bore; optionally add a raised hub for set-screw grip."""
    law = _LAWS.get(cam_type, _r_eccentric)
    pts = []
    for i in range(_STEPS):
        t = 2.0 * math.pi * i / _STEPS
        r = max(1.0, law(t))
        pts.append((r * math.cos(t), r * math.sin(t)))

    cam = cq.Workplane("XY").polyline(pts).close().extrude(thickness)

    if hub:
        hub_r = min(base_radius * 0.6, bore / 2.0 + 4.0)
        hub_h = min(thickness * 0.6, 5.0)
        hub_solid = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, thickness))
            .circle(hub_r)
            .extrude(hub_h)
        )
        cam = cam.union(hub_solid)
        total_h = thickness + hub_h
    else:
        total_h = thickness

    # Shaft bore through cam (+ hub).
    hole = cq.Workplane("XY").circle(bore / 2.0).extrude(total_h + 2.0).translate((0, 0, -1.0))
    cam = cam.cut(hole)

    # A small flat on the bore (set-screw key) for anti-slip mounting.
    try:
        flat_w = bore * 0.9
        flat = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(bore / 2.0 - flat_w * 0.12, 0, -1.0))
            .box(flat_w * 0.25, flat_w, total_h + 2.0, centered=(True, True, False))
        )
        cam = cam.cut(flat)
    except Exception:
        pass

    try:
        cam = cam.clean()
    except Exception:
        pass
    return cam


# ── Dispatch ─────────────────────────────────────────────────────────────────
result = build_cam()
