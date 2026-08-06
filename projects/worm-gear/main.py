"""
Worm & Worm-Wheel — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A high-reduction, potentially self-locking right-angle drive in two parts:

  - The WORM: a screw — a helical thread (single- or multi-start) of a
    trapezoidal (Acme-style) profile swept along a true helix on a cylinder
    (DIN 3975). Turns are kept modest for fast, watertight geometry.
  - The WORM-WHEEL: a gear whose teeth are angled to mesh the worm. Its involute
    flanks are sampled from the true involute of the base circle P(t) =
    rb*(cos t + t sin t, sin t - t cos t) and twist-extruded at the worm's lead
    angle (a helical spur gear), so the module and mesh geometry are real.

APPROXIMATION NOTE: a truly THROATED wheel (concave rim hugging the worm) is not
modelled — that requires a globoid enveloping cut and is very heavy. The wheel
here is a helical spur gear set to the worm's lead angle: correct pitch, module,
and hand of helix, meshing on a line rather than wrapped around the worm. This is
the standard maker-scale approximation, adequate for light-duty drives.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` (cadquery) and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `teeth`).
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


# ── Parameters ───────────────────────────────────────────────────────────────
m            = float(PARAM(lambda: m,               2.0))   # module (mm)
starts       = int(  PARAM(lambda: starts,            1))   # worm thread starts
worm_dia     = float(PARAM(lambda: worm_dia,        16.0))  # worm pitch diameter (mm)
worm_turns   = float(PARAM(lambda: worm_turns,       2.5))  # visible worm turns
teeth        = int(  PARAM(lambda: teeth,            30))   # worm-wheel tooth count
pressure_angle = float(PARAM(lambda: pressure_angle, 20.0)) # pressure angle (deg)
thickness    = float(PARAM(lambda: thickness,       10.0))  # wheel face width (mm)
worm_bore    = float(PARAM(lambda: worm_bore,        5.0))  # worm shaft bore (mm)
wheel_bore   = float(PARAM(lambda: wheel_bore,       6.0))  # wheel shaft bore (mm)
flank_pts    = int(  PARAM(lambda: flank_pts,         9))   # involute samples / flank

target_part  = str(  PARAM(lambda: target_part, "worm"))    # "worm" | "wheel" | "pair"

# ── Clamp / normalise inputs ─────────────────────────────────────────────────
m = max(0.3, m)
starts = max(1, min(starts, 3))
worm_dia = max(4.0, worm_dia)
worm_turns = max(1.0, min(worm_turns, 4.0))
# The helical sweep self-intersects (and tessellates non-watertight) once the
# TOTAL swept revolutions grow large, so cap starts*turns at 3. This keeps every
# start count watertight while still showing multiple visible turns.
if starts * worm_turns > 3.0:
    worm_turns = max(1.0, 3.0 / starts)
teeth = max(10, min(teeth, 120))
pressure_angle = max(10.0, min(pressure_angle, 30.0))
thickness = max(2.0, thickness)
flank_pts = max(4, min(flank_pts, 16))
pa = math.radians(pressure_angle)

# Worm/wheel kinematics (shared)
rp_worm = worm_dia / 2.0
lead = math.pi * m * starts               # axial advance per revolution
lead_angle = math.degrees(math.atan(lead / (2.0 * math.pi * rp_worm)))


# ── Involute geometry (wheel flanks) ─────────────────────────────────────────
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
    return root_r + right + left + root_l


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


# ── Part builders ────────────────────────────────────────────────────────────
def build_worm():
    """Single- or multi-start worm: a trapezoidal thread swept along a true helix
    on a root cylinder. Multi-start worms union `starts` helices phase-shifted by
    the axial pitch. Ends are squared off by intersecting with a bounding
    cylinder so the exported solid is watertight."""
    p = math.pi * m                       # axial pitch between adjacent threads
    add = m
    ded = 1.25 * m
    r_out = rp_worm + add
    r_root = rp_worm - ded
    r_root = max(r_root, 0.6 * m)
    length = lead * worm_turns

    tan_pa = math.tan(pa)
    crest_half = p / 4.0 - add * tan_pa
    root_half = p / 4.0 + ded * tan_pa
    crest_half = max(crest_half, 0.06 * p)

    worm = cq.Workplane("XY").circle(r_root).extrude(length)

    for s in range(starts):
        phase = s * p                     # axial offset of this start
        helix = cq.Wire.makeHelix(pitch=lead, height=length + phase, radius=rp_worm)
        prof = (cq.Workplane("XZ")
                .polyline([
                    (r_root - rp_worm, -root_half),
                    (r_out - rp_worm, -crest_half),
                    (r_out - rp_worm, crest_half),
                    (r_root - rp_worm, root_half),
                ]).close())
        prof = prof.translate((rp_worm, 0, phase))
        thread = prof.sweep(cq.Workplane(obj=helix), isFrenet=True)
        worm = worm.union(thread)

    # Square the ends (the helical sweep overshoots the nominal length).
    bound = cq.Workplane("XY").circle(r_out + 1.0).extrude(length)
    worm = worm.intersect(bound)

    if worm_bore > 0.05:
        br = min(worm_bore / 2.0, r_root - 0.5)
        if br > 0.4:
            hole = (cq.Workplane("XY").workplane(offset=-1.0)
                    .circle(br).extrude(length + 2.0))
            worm = worm.cut(hole)
    return worm, length, r_out


def build_wheel():
    """Worm-wheel as a helical spur gear at the worm's lead angle (hand set so it
    conjugates the worm). Twist over the face width = thickness*tan(helix)/rp."""
    rp = m * teeth / 2.0
    rb = rp * math.cos(pa)
    ro = rp + m
    rr = max(rp - 1.25 * m, 0.5 * m)
    wire = _gear_wire(teeth, rb, ro, rr)
    twist_deg = math.degrees(thickness * math.tan(math.radians(lead_angle)) / rp)
    solid = cq.Workplane("XY").polyline(wire).close().twistExtrude(thickness, twist_deg)
    if wheel_bore > 0.05:
        br = min(wheel_bore / 2.0, rr - 0.5)
        if br > 0.4:
            hole = (cq.Workplane("XY").workplane(offset=-1.0)
                    .circle(br).extrude(thickness + 2.0))
            solid = solid.cut(hole)
    return solid, rp


def build_pair():
    """Worm meshing with the wheel at 90 deg. The worm lies along X above the
    wheel; centre distance = worm pitch radius + wheel pitch radius. The worm is
    rotated to lie horizontally and lifted to the mesh line."""
    worm, w_len, r_out = build_worm()
    wheel, rp_wheel = build_wheel()

    centre_dist = rp_worm + rp_wheel
    # Wheel sits at the origin, axis along Z. Worm axis along X, tangent to the
    # wheel pitch circle at the top, one centre-distance above the wheel centre.
    worm_pl = (worm
               .rotate((0, 0, 0), (0, 1, 0), 90)     # worm axis X
               .translate((-w_len / 2.0, 0, centre_dist)))
    asm = cq.Assembly()
    asm.add(wheel, name="wheel", color=cq.Color(0.42, 0.56, 0.69))
    asm.add(worm_pl, name="worm", color=cq.Color(0.85, 0.65, 0.30))
    return asm


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pair":
    result = build_pair()
elif target_part == "wheel":
    result = build_wheel()[0]
else:  # "worm" (default)
    result = build_worm()[0]
