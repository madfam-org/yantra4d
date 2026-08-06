"""
Planetary Gearset — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A compact reduction stage: a central sun gear, orbiting planet gears, and a
surrounding internal ring gear, all involute and all sharing one module (ISO 53
/ DIN 867). Tooth flanks are sampled directly from the true involute of the base
circle P(t) = rb*(cos t + t sin t, sin t - t cos t), so any two members of the
set mesh correctly. The defining tooth-count relation of a planetary train,
ring = sun + 2*planet, is enforced by COMPUTING the ring count from sun+planet,
which also guarantees the planets sit on the carrier circle without interference.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` (cadquery) and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `sun_teeth`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
m            = float(PARAM(lambda: m,               2.0))   # module (mm), shared by all
sun_teeth    = int(  PARAM(lambda: sun_teeth,        12))   # sun tooth count
planet_teeth = int(  PARAM(lambda: planet_teeth,     12))   # planet tooth count
planets      = int(  PARAM(lambda: planets,           3))   # number of planets
pressure_angle = float(PARAM(lambda: pressure_angle, 20.0)) # pressure angle (deg)
thickness    = float(PARAM(lambda: thickness,        8.0))  # face width (mm)
sun_bore     = float(PARAM(lambda: sun_bore,         5.0))  # sun central bore (mm)
planet_bore  = float(PARAM(lambda: planet_bore,      4.0))  # planet central bore (mm)
rim_width    = float(PARAM(lambda: rim_width,        6.0))  # ring radial rim thickness (mm)
flank_pts    = int(  PARAM(lambda: flank_pts,         9))   # involute samples / flank

target_part  = str(  PARAM(lambda: target_part, "sun"))     # "sun"|"planet"|"ring"|"assembly"

# ── Clamp / normalise inputs ─────────────────────────────────────────────────
m = max(0.3, m)
sun_teeth = max(6, min(sun_teeth, 120))
planet_teeth = max(6, min(planet_teeth, 120))
planets = max(2, min(planets, 8))
pressure_angle = max(10.0, min(pressure_angle, 30.0))
thickness = max(1.0, thickness)
rim_width = max(2.0, rim_width)
flank_pts = max(4, min(flank_pts, 16))
pa = math.radians(pressure_angle)

# The defining relation — COMPUTED, never user-supplied, so it always holds.
ring_teeth = sun_teeth + 2 * planet_teeth
carrier_radius = (sun_teeth + planet_teeth) * m / 2.0   # sun-planet centre dist


# ── Involute geometry (the core value) ───────────────────────────────────────
def _involute_point(rb, t):
    """Point on the involute of a circle of radius `rb` at roll angle `t`."""
    return (rb * (math.cos(t) + t * math.sin(t)),
            rb * (math.sin(t) - t * math.cos(t)))


def _inv(angle):
    """Involute function inv(a) = tan(a) - a."""
    return math.tan(angle) - angle


def _roll_at_radius(rb, r):
    """Roll angle t so the involute point sits at radius r (r >= rb)."""
    if r <= rb:
        return 0.0
    return math.sqrt((r / rb) ** 2 - 1.0)


def _one_tooth_profile(teeth, rb, ro, rr, n):
    """Outline of a SINGLE involute tooth centred on +X, root->tip->root."""
    half_pitch = math.pi / (2.0 * teeth)
    beta0 = half_pitch + _inv(pa)
    r_start = max(rb, rr)
    t_end = _roll_at_radius(rb, ro)
    t_start = _roll_at_radius(rb, r_start)

    right = []
    for i in range(n):
        t = t_start + (t_end - t_start) * (i / (n - 1))
        x0, y0 = _involute_point(rb, t)
        phi = math.atan2(y0, x0)
        r = rb * math.sqrt(1.0 + t * t)
        ang = phi - beta0
        right.append((r * math.cos(ang), r * math.sin(ang)))

    root_r = []
    if rr < r_start - 1e-6:
        fx, fy = right[0]
        fang = math.atan2(fy, fx)
        root_r.append((rr * math.cos(fang), rr * math.sin(fang)))

    left = [(x, -y) for (x, y) in reversed(right)]
    root_l = [(x, -y) for (x, y) in reversed(root_r)]

    pts = []
    pts.extend(root_r)
    pts.extend(right)
    pts.extend(left)
    pts.extend(root_l)
    return pts


def _gear_wire(teeth, rb, ro, rr):
    """Full closed spur cross-section: one tooth polar-patterned `teeth` times."""
    tooth = _one_tooth_profile(teeth, rb, ro, rr, flank_pts)
    step = 2.0 * math.pi / teeth
    all_pts = []
    for k in range(teeth):
        a = k * step
        ca, sa = math.cos(a), math.sin(a)
        for (x, y) in tooth:
            all_pts.append((x * ca - y * sa, x * sa + y * ca))
    return all_pts


def _spur_solid(teeth, bore):
    """External involute spur gear as a watertight solid, with optional bore."""
    rp = m * teeth / 2.0
    rb = rp * math.cos(pa)
    ro = rp + m
    rr = max(rp - 1.25 * m, 0.5 * m)
    wire = _gear_wire(teeth, rb, ro, rr)
    solid = cq.Workplane("XY").polyline(wire).close().extrude(thickness)
    if bore > 0.05:
        br = min(bore / 2.0, rr - 0.5)
        if br > 0.4:
            through = (cq.Workplane("XY")
                       .transformed(offset=cq.Vector(0, 0, -1.0))
                       .circle(br)
                       .extrude(thickness + 2.0))
            solid = solid.cut(through)
    return solid


def _ring_solid():
    """Internal (annular) ring gear: teeth point INWARD. Built by cutting an
    external-gear-shaped cavity from a plain cylindrical rim. Internal tooth tips
    reach inward to rp - m; roots sit at rp + 1.25*m."""
    rp = m * ring_teeth / 2.0
    rb = rp * math.cos(pa)
    ro = rp + 1.25 * m           # outer extent of the cutter (ring roots)
    rr = max(rp - m, 0.4 * m)    # inner extent (ring tips)
    wire = _gear_wire(ring_teeth, rb, ro, rr)
    cutter = cq.Workplane("XY").polyline(wire).close().extrude(thickness + 2.0)
    cutter = cutter.translate((0, 0, -1.0))
    rim_outer = ro + rim_width
    rim = cq.Workplane("XY").circle(rim_outer).extrude(thickness)
    return rim.cut(cutter)


# ── Part builders ────────────────────────────────────────────────────────────
def build_sun():
    return _spur_solid(sun_teeth, sun_bore)


def build_planet():
    return _spur_solid(planet_teeth, planet_bore)


def build_ring():
    return _ring_solid()


def build_assembly():
    """All members positioned: sun at centre, planets on the carrier circle,
    ring outside. A multi-body compound for visualisation of the train."""
    asm = cq.Assembly()
    asm.add(build_sun(), name="sun", color=cq.Color(0.85, 0.65, 0.30))
    ring = build_ring()
    asm.add(ring, name="ring", color=cq.Color(0.42, 0.56, 0.69))
    planet = build_planet()
    step = 2.0 * math.pi / planets
    for i in range(planets):
        a = i * step
        px = carrier_radius * math.cos(a)
        py = carrier_radius * math.sin(a)
        asm.add(planet, name=f"planet_{i}", loc=cq.Location(cq.Vector(px, py, 0)),
                color=cq.Color(0.55, 0.71, 0.80))
    return asm


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "assembly":
    result = build_assembly()
elif target_part == "ring":
    result = build_ring()
elif target_part == "planet":
    result = build_planet()
else:  # "sun" (default)
    result = build_sun()
