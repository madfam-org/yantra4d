"""
Bevel / Miter Gear — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A conical bevel gear for right-angle drives. The tooth cross-section is generated
from the true involute of the base circle P(t) = rb*(cos t + t sin t,
sin t - t cos t) at the large (back) end, then LOFTED to a scaled copy toward the
cone apex, so the teeth taper along the pitch cone like a real bevel gear. When
the two mating gears have equal tooth counts and a 90 deg shaft angle the result
is a miter pair.

APPROXIMATION NOTE: exact spherical-involute bevel teeth (octoid flanks) are not
modelled. Instead each tooth is the planar involute profile of the back cone,
linearly lofted (scaled) toward the apex. This yields a dimensionally-correct
pitch cone, module, and tooth count with a recognizable, printable, watertight
bevel — the standard Tredgold-style approximation, adequate for maker-scale
right-angle drives but not for precision spiral-bevel metrology.

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
m            = float(PARAM(lambda: m,               3.0))   # module at large end (mm)
teeth        = int(  PARAM(lambda: teeth,            20))   # tooth count
pressure_angle = float(PARAM(lambda: pressure_angle, 20.0)) # pressure angle (deg)
shaft_angle  = float(PARAM(lambda: shaft_angle,     90.0))  # shaft angle (deg)
face_width   = float(PARAM(lambda: face_width,      12.0))  # cone face width (mm)
bore         = float(PARAM(lambda: bore,             6.0))  # central bore (mm)
back_height  = float(PARAM(lambda: back_height,      6.0))  # solid backing behind large end
flank_pts    = int(  PARAM(lambda: flank_pts,         7))   # involute samples / flank

target_part  = str(  PARAM(lambda: target_part, "bevel"))   # "bevel" | "miter_pair"

# ── Clamp / normalise inputs ─────────────────────────────────────────────────
m = max(0.5, m)
teeth = max(8, min(teeth, 80))
pressure_angle = max(10.0, min(pressure_angle, 30.0))
shaft_angle = max(30.0, min(shaft_angle, 150.0))
face_width = max(2.0, face_width)
back_height = max(1.0, back_height)
flank_pts = max(4, min(flank_pts, 14))
pa = math.radians(pressure_angle)


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
    return root_r + right + left + root_l


def _gear_wire_scaled(teeth, rb, ro, rr, scale):
    """One tooth polar-patterned `teeth` times, uniformly scaled about origin."""
    tooth = _one_tooth_profile(teeth, rb, ro, rr, flank_pts)
    step = 2.0 * math.pi / teeth
    pts = []
    for k in range(teeth):
        a = k * step
        ca, sa = math.cos(a), math.sin(a)
        for (x, y) in tooth:
            xr = x * ca - y * sa
            yr = x * sa + y * ca
            pts.append((xr * scale, yr * scale))
    return pts


# ── Bevel body builder ───────────────────────────────────────────────────────
def _bevel_solid(g_teeth):
    """Build one bevel gear centred on Z, large (back) end at z=0, tapering to the
    small end toward +Z (apex direction). Returns the solid and its pitch radius
    so the pair builder can position two of them."""
    rp = m * g_teeth / 2.0
    gamma = math.radians(shaft_angle / 2.0)      # pitch-cone half-angle
    gamma = max(math.radians(10.0), min(gamma, math.radians(80.0)))
    r_cone = rp / math.sin(gamma)                # apex-to-large-end distance
    fw = min(face_width, r_cone * 0.85)          # keep the small end off the apex
    inner_frac = (r_cone - fw) / r_cone          # scale of small end vs large end

    rb = rp * math.cos(pa)
    ro = rp + m
    rr = max(rp - 1.25 * m, 0.5 * m)

    z_small = fw * math.cos(gamma)               # axial rise from large to small end

    w_large = _gear_wire_scaled(g_teeth, rb, ro, rr, 1.0)
    w_small = _gear_wire_scaled(g_teeth, rb, ro, rr, inner_frac)

    solid = (cq.Workplane("XY")
             .workplane(offset=0.0).polyline(w_large).close()
             .workplane(offset=z_small).polyline(w_small).close()
             .loft(ruled=True))

    # Solid backing behind the large end so there is hub material for the bore
    # and a flat mounting face. Extrude the SAME large-end tooth wire downward so
    # the backing's outer boundary matches the loft exactly (teeth run straight
    # through it) — a plain circle would leave a tangent seam that tessellates
    # into a non-watertight mesh at wide shaft angles.
    back = (cq.Workplane("XY")
            .workplane(offset=-back_height)
            .polyline(w_large).close()
            .extrude(back_height))
    solid = solid.union(back)

    total_h = z_small + back_height
    if bore > 0.05:
        br = min(bore / 2.0, inner_frac * rr - 0.4)
        br = max(br, 0.5)
        hole = (cq.Workplane("XY")
                .workplane(offset=-back_height - 1.0)
                .circle(br)
                .extrude(total_h + 2.0))
        solid = solid.cut(hole)
    return solid, rp, gamma


def build_bevel():
    return _bevel_solid(teeth)[0]


def build_miter_pair():
    """Two bevel gears meshing at the shaft angle. The first sits on +Z; the
    second is rotated by the shaft angle about a line through the common pitch
    apex so their pitch cones share an apex and roll on each other."""
    g1, rp, gamma = _bevel_solid(teeth)
    g2, _, _ = _bevel_solid(teeth)

    r_cone = rp / math.sin(gamma)
    # Gear 1: back face at z=0, apex on +Z at z = r_cone*cos(gamma).
    apex_z = r_cone * math.cos(gamma)
    # Move gear 2 so its own apex coincides with gear 1's apex, then tilt by the
    # shaft angle so the two pitch cones roll together.
    asm = cq.Assembly()
    asm.add(g1, name="gear_a", color=cq.Color(0.42, 0.56, 0.69))
    loc = (cq.Location(cq.Vector(0, 0, apex_z))                 # to shared apex
           * cq.Location(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), shaft_angle)
           * cq.Location(cq.Vector(0, 0, -apex_z)))             # bring its back out
    asm.add(g2, name="gear_b", loc=loc, color=cq.Color(0.55, 0.71, 0.80))
    return asm


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "miter_pair":
    result = build_miter_pair()
else:  # "bevel" (default)
    result = build_bevel()
