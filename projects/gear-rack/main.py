"""
Involute Gear Rack — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A linear rack that meshes with an involute spur pinion. The rack tooth is the
exact conjugate of an involute gear: a straight-sided trapezoid whose flanks are
inclined at the pressure angle (ISO 53 / DIN 867). Because the rack and any
pinion share the same module and pressure angle, they engage correctly. When the
matching pinion is included, its flanks are sampled directly from the true
involute of the base circle P(t) = rb*(cos t + t sin t, sin t - t cos t), so the
pair is a dimensionally-real rack-and-pinion set.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` (cadquery) and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `m`).
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
m            = float(PARAM(lambda: m,               2.0))   # module (mm)
pressure_angle = float(PARAM(lambda: pressure_angle, 20.0)) # pressure angle (deg)
rack_teeth   = int(  PARAM(lambda: rack_teeth,       12))   # teeth along the rack
width        = float(PARAM(lambda: width,           12.0))  # face width (Z depth, mm)
height       = float(PARAM(lambda: height,          10.0))  # solid backing below roots
mount_holes  = bool( PARAM(lambda: mount_holes,    False))  # mounting holes in the back
hole_dia     = float(PARAM(lambda: hole_dia,         4.0))  # mounting-hole diameter (mm)
hole_count   = int(  PARAM(lambda: hole_count,        3))   # number of mounting holes
include_pinion = bool(PARAM(lambda: include_pinion, False)) # add a matching pinion
pinion_teeth = int(  PARAM(lambda: pinion_teeth,     16))   # pinion tooth count
bore         = float(PARAM(lambda: bore,             6.0))  # pinion central bore (mm)
flank_pts    = int(  PARAM(lambda: flank_pts,         9))   # involute samples / flank

target_part  = str(  PARAM(lambda: target_part, "rack"))    # "rack"|"rack_with_holes"|"rack_and_pinion"

# ── Clamp / normalise inputs ─────────────────────────────────────────────────
m = max(0.3, m)
pressure_angle = max(10.0, min(pressure_angle, 30.0))
rack_teeth = max(2, min(rack_teeth, 60))
width = max(2.0, width)
height = max(2.0, height)
pinion_teeth = max(6, min(pinion_teeth, 120))
flank_pts = max(4, min(flank_pts, 16))
pa = math.radians(pressure_angle)

# A rack_with_holes mode implies mount_holes on; rack_and_pinion implies pinion.
if target_part == "rack_with_holes":
    mount_holes = True
if target_part == "rack_and_pinion":
    include_pinion = True


# ── Involute geometry (shared with the pinion) ───────────────────────────────
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


# ── Part builders ────────────────────────────────────────────────────────────
def build_rack():
    """Straight involute-conjugate rack teeth on a solid bar.

    Pitch line: tooth thickness == space == p/2 (circular pitch p = pi*m).
    Addendum = m above the pitch line, dedendum = 1.25*m below. Flanks inclined
    at the pressure angle so the tip land = p/4 - add*tan(pa) and the root width
    = p/4 + ded*tan(pa). Teeth run along +X; bar extruded `width` in Z."""
    n = rack_teeth
    p = math.pi * m
    add = m
    ded = 1.25 * m
    tan_pa = math.tan(pa)
    top_half = p / 4.0 - add * tan_pa
    bot_half = p / 4.0 + ded * tan_pa
    top_half = max(top_half, 0.05 * m)

    length = n * p
    x0 = -length / 2.0
    back = height
    y_root = -ded
    y_tip = add
    y_back = -ded - back

    pts = [(x0, y_back), (x0, y_root)]
    for i in range(n):
        cx = x0 + (i + 0.5) * p
        pts.append((cx - bot_half, y_root))
        pts.append((cx - top_half, y_tip))
        pts.append((cx + top_half, y_tip))
        pts.append((cx + bot_half, y_root))
    pts.append((x0 + length, y_root))
    pts.append((x0 + length, y_back))

    solid = cq.Workplane("XY").polyline(pts).close().extrude(width)

    if mount_holes and hole_count > 0 and hole_dia > 0.05:
        hr = min(hole_dia / 2.0, back / 2.0 - 0.5, width / 2.0 - 0.5)
        if hr > 0.3:
            z_mid = width / 2.0
            y_mid = y_back + back / 2.0
            nh = max(1, min(hole_count, n))
            margin = length / (nh + 1)
            for i in range(1, nh + 1):
                cx = x0 + i * margin
                hole = (cq.Workplane("XZ")
                        .transformed(offset=cq.Vector(cx, z_mid, -y_mid))
                        .circle(hr)
                        .extrude(back + 2.0))
                try:
                    solid = solid.cut(hole)
                except Exception:
                    pass
    return solid, length, y_tip


def build_pinion(teeth):
    """External involute spur gear meshing with the rack (same m, pa)."""
    rp = m * teeth / 2.0
    rb = rp * math.cos(pa)
    ro = rp + m
    rr = rp - 1.25 * m
    rr = max(rr, 0.5 * m)
    wire = _gear_wire(teeth, rb, ro, rr)
    solid = cq.Workplane("XY").polyline(wire).close().extrude(width)
    if bore > 0.05:
        br = min(bore / 2.0, rr - 0.5)
        if br > 0.4:
            through = (cq.Workplane("XY")
                       .transformed(offset=cq.Vector(0, 0, -1.0))
                       .circle(br)
                       .extrude(width + 2.0))
            solid = solid.cut(through)
    return solid, rp


def build_rack_and_pinion():
    """Rack plus a pinion positioned so its pitch circle rolls on the rack pitch
    line (pinion centre one pitch-radius above the rack tip - addendum)."""
    rack, length, y_tip = build_rack()
    pinion, rp = build_pinion(pinion_teeth)
    # Rack pitch line sits at y=0 in rack coords; pinion centre one pitch radius
    # above it, offset in X to the rack's right end for a clear meshing pose.
    px = length / 2.0 - rp
    py = rp
    pinion = pinion.translate((px, py, 0))
    asm = cq.Assembly()
    asm.add(rack, name="rack", color=cq.Color(0.42, 0.56, 0.69))
    asm.add(pinion, name="pinion", color=cq.Color(0.55, 0.71, 0.80))
    return asm


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "rack_and_pinion":
    result = build_rack_and_pinion()
else:  # "rack" and "rack_with_holes"
    result = build_rack()[0]
