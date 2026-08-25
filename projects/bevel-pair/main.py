"""
Bevel Gear Pair — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A right-angle bevel gear set: a pinion, a matching gear (1:1 miter or 2:1
reduction), and a meshing demonstrator that fuses both onto a single printable
L-bracket. The tooth cross-section is generated from the TRUE involute of the
base circle P(t) = rb*(cos t + t sin t, sin t - t cos t) at the large (back) end
and LOFTED to a scaled copy toward the cone apex, so the teeth taper along the
pitch cone like a real bevel gear (ISO 23509 geometry).

The FUNCTIONAL interface is the ISO 23509 bevel pitch cone: module, pressure
angle, tooth count and shaft angle. A pinion from this cartridge meshes a gear
from the bevel-gear family (shared module + shaft angle) — it grows that family.

  - pinion    : the small bevel (drive) gear, solid back hub + axial bore.
  - gear      : the mating bevel — equal teeth for a 1:1 miter, or `ratio`× teeth
                for a reduction. Same module and shaft angle as the pinion.
  - mesh_demo : pinion + gear meshing at the shaft angle, both fused to one
                L-bracket base so the whole set prints as a SINGLE connected body
                (body_count == 1) — a desktop demonstrator of the right-angle roll.

APPROXIMATION NOTE: exact spherical-involute (octoid) flanks are not modelled.
Each tooth is the planar involute of the back cone, linearly lofted (scaled)
toward the apex — the classic Tredgold approximation. Pitch cone, module and
tooth count are dimensionally correct; adequate for maker-scale right-angle
drives, not precision spiral-bevel metrology.

Watertight strategy:
  Each bevel body is a single loft of the closed involute wire (large end →
  scaled small end), unioned with a back hub extruded from the SAME large-end
  wire (so the backing's outer boundary matches the loft exactly — a plain circle
  would leave a tangent seam that tessellates non-watertight at wide shaft
  angles). Bores are cut THROUGH so they vent both faces. In mesh_demo the two
  gears OVERLAP a solid bracket (volumetric union → one body); no floating
  meshing assembly. No revolve-of-cut profiles.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read each via PARAM(lambda: name, default); worker injects target_part.
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
target_part = str(PARAM(lambda: target_part, "pinion"))
# "pinion" | "gear" | "mesh_demo"

m = float(PARAM(lambda: m, 1.5))                       # module at large end (mm)
teeth = int(PARAM(lambda: teeth, 16))                  # pinion tooth count
ratio = float(PARAM(lambda: ratio, 1.0))              # gear:pinion ratio (1.0 miter, 2.0 reduction)
pressure_angle = float(PARAM(lambda: pressure_angle, 20.0))  # deg
shaft_angle = float(PARAM(lambda: shaft_angle, 90.0))  # deg between shafts
face_width = float(PARAM(lambda: face_width, 8.0))     # cone face width (mm)
bore = float(PARAM(lambda: bore, 4.0))                 # central bore (mm)
back_height = float(PARAM(lambda: back_height, 5.0))   # solid backing behind large end (mm)
flank_pts = int(PARAM(lambda: flank_pts, 7))           # involute samples / flank

# ── Clamp / normalise inputs ─────────────────────────────────────────────────
m = max(0.5, min(m, 3.0))
teeth = max(10, min(teeth, 40))
ratio = max(1.0, min(ratio, 3.0))
pressure_angle = max(14.5, min(pressure_angle, 25.0))
shaft_angle = max(60.0, min(shaft_angle, 120.0))
face_width = max(3.0, min(face_width, 20.0))
back_height = max(2.0, min(back_height, 14.0))
flank_pts = max(4, min(flank_pts, 12))
pa = math.radians(pressure_angle)


# ── Involute geometry (ISO 23509 back-cone profile) ──────────────────────────
def _involute_point(rb, t):
    return (rb * (math.cos(t) + t * math.sin(t)),
            rb * (math.sin(t) - t * math.cos(t)))


def _inv(angle):
    return math.tan(angle) - angle


def _roll_at_radius(rb, r):
    if r <= rb:
        return 0.0
    return math.sqrt((r / rb) ** 2 - 1.0)


def _one_tooth_profile(g_teeth, rb, ro, rr, n):
    """Outline of a SINGLE involute tooth centred on +X, root->tip->root."""
    half_pitch = math.pi / (2.0 * g_teeth)
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


def _gear_wire_scaled(g_teeth, rb, ro, rr, scale):
    """One tooth polar-patterned g_teeth times, uniformly scaled about origin."""
    tooth = _one_tooth_profile(g_teeth, rb, ro, rr, flank_pts)
    step = 2.0 * math.pi / g_teeth
    pts = []
    for k in range(g_teeth):
        a = k * step
        ca, sa = math.cos(a), math.sin(a)
        for (x, y) in tooth:
            xr = x * ca - y * sa
            yr = x * sa + y * ca
            pts.append((xr * scale, yr * scale))
    return pts


def _pitch_cone_half_angle(g_teeth, mate_teeth):
    """Pitch-cone half-angle γ for a gear of g_teeth meshing mate_teeth at the
    shaft angle Σ:  tan γ = sin Σ / (mate/g + cos Σ)  (ISO 23509)."""
    sigma = math.radians(shaft_angle)
    gamma = math.atan2(math.sin(sigma), (mate_teeth / g_teeth) + math.cos(sigma))
    return max(math.radians(8.0), min(gamma, math.radians(82.0)))


# ── Bevel body builder ───────────────────────────────────────────────────────
def _bevel_solid(g_teeth, mate_teeth, bore_d):
    """One bevel gear centred on Z, large (back) end at z=0, tapering toward +Z.
    Returns (solid, pitch_radius, gamma, total_height)."""
    rp = m * g_teeth / 2.0
    gamma = _pitch_cone_half_angle(g_teeth, mate_teeth)
    r_cone = rp / math.sin(gamma)                # apex-to-large-end distance
    fw = min(face_width, r_cone * 0.85)          # keep the small end off the apex
    inner_frac = (r_cone - fw) / r_cone

    rb = rp * math.cos(pa)
    ro = rp + m
    rr = max(rp - 1.25 * m, 0.5 * m)
    z_small = fw * math.cos(gamma)

    w_large = _gear_wire_scaled(g_teeth, rb, ro, rr, 1.0)
    w_small = _gear_wire_scaled(g_teeth, rb, ro, rr, inner_frac)

    solid = (cq.Workplane("XY")
             .workplane(offset=0.0).polyline(w_large).close()
             .workplane(offset=z_small).polyline(w_small).close()
             .loft(ruled=True))

    back = (cq.Workplane("XY")
            .workplane(offset=-back_height)
            .polyline(w_large).close()
            .extrude(back_height))
    solid = solid.union(back)

    total_h = z_small + back_height
    if bore_d > 0.05:
        br = min(bore_d / 2.0, inner_frac * rr - 0.4)
        br = max(br, 0.5)
        hole = (cq.Workplane("XY")
                .workplane(offset=-back_height - 1.0)
                .circle(br)
                .extrude(total_h + 2.0))
        solid = solid.cut(hole)
    return solid, rp, gamma, total_h


def build_pinion():
    return _bevel_solid(teeth, int(round(teeth * ratio)), bore)[0]


def build_gear():
    return _bevel_solid(int(round(teeth * ratio)), teeth, bore)[0]


def build_mesh_demo():
    """Pinion + gear meshing at the shaft angle, both fused to a single L-bracket
    base so the whole set is ONE connected body (body_count == 1). The pinion axis
    is vertical (on +Z); the gear axis is tilted by the shaft angle. A solid
    bracket wraps behind both back hubs and unions them into one printable solid.

    NOTE: the gears are printed pre-meshed as a static demonstrator of the pitch
    cones — a fused monolith, not a free-spinning pair (bores are kept for shafts,
    but the demo body itself is single-piece by design)."""
    g_teeth = int(round(teeth * ratio))
    pinion, rp_p, gamma_p, h_p = _bevel_solid(teeth, g_teeth, 0.0)
    gear, rp_g, gamma_g, h_g = _bevel_solid(g_teeth, teeth, 0.0)

    r_cone = rp_p / math.sin(gamma_p)
    apex_z = r_cone * math.cos(gamma_p)          # pinion apex on +Z

    # Pinion stands on +Z with back face at z=0. Tilt the gear about the shared
    # pitch apex by the shaft angle so the two pitch cones roll together.
    tilt = shaft_angle
    loc = (cq.Location(cq.Vector(0, 0, apex_z))
           * cq.Location(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), tilt)
           * cq.Location(cq.Vector(0, 0, -apex_z)))
    # `.located()` lives on Shape, not on Workplane — calling it on the Workplane
    # raises AttributeError, which is why this mode never rendered. Take the solid
    # out, relocate it, and wrap it back into a Workplane for the union.
    gear_m = cq.Workplane("XY").newObject([gear.val().located(loc)])

    combined = pinion.union(gear_m)

    # L-bracket base that both back hubs overlap → fuses the assembly into ONE body.
    max_r = max(rp_p, rp_g) + m + 2.0
    plate_t = max(3.0, back_height * 0.7)
    # Horizontal plate under the pinion back face (z <= 0 region).
    base_plate = (cq.Workplane("XY")
                  .workplane(offset=-plate_t)
                  .rect(2.2 * max_r, 2.2 * max_r)
                  .extrude(plate_t + 0.5))
    combined = combined.union(base_plate)

    # A vertical web rising at the far -Y edge to backstop the tilted gear hub.
    web = (cq.Workplane("XZ")
           .workplane(offset=-1.1 * max_r)
           .rect(2.2 * max_r, 2.2 * max_r)
           .extrude(plate_t)
           .translate((0, 0, 0)))
    # Only keep the web where it overlaps/joins — union is safe (overlaps base).
    combined = combined.union(web)

    try:
        combined = combined.clean()
    except Exception:
        pass
    return combined


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "gear":
    result = build_gear()
elif target_part == "mesh_demo":
    result = build_mesh_demo()
else:  # "pinion" (default)
    result = build_pinion()
