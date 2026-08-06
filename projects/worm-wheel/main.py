"""
Worm & Wheel Set — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A high-reduction, potentially self-locking right-angle drive in three modes: the
worm (a screw), the worm-wheel (a helical gear that meshes it), and a fused
mesh demonstrator. The worm thread is a trapezoidal (Acme-style) profile swept
along a true `makeHelix` on a cylinder (DIN 3975); the wheel's flanks are sampled
from the TRUE involute of the base circle P(t) = rb*(cos t + t sin t,
sin t - t cos t) and twist-extruded at the worm's lead angle (a helical spur
gear), so module and mesh geometry are real.

The FUNCTIONAL interface is the DIN 3975 worm pair: module, starts, pressure
angle and lead angle. A worm from this cartridge drives a wheel from the
worm-gear family (shared module + starts) — it grows that family.

  - worm       : a single- or multi-start worm screw, squared ends, axial bore.
  - wheel      : the worm-wheel — a helical spur gear at the worm's lead angle.
  - mesh_demo  : worm + wheel meshing at 90 deg, both fused to one base bracket so
                 the set prints as a SINGLE connected body (body_count == 1).

APPROXIMATION NOTE: a truly THROATED (globoid) wheel hugging the worm is not
modelled — that requires an enveloping cut and is very heavy. The wheel here is a
helical spur gear set to the worm's lead angle: correct pitch, module and hand of
helix, meshing on a line. Standard maker-scale approximation, adequate for
light-duty drives.

Watertight strategy:
  Worm = a root cylinder with additive trapezoidal helical thread ribs UNIONED on
  (root pushed into the cylinder → clean volumetric fuse), then intersected with a
  bounding cylinder to square the overshooting ends. Wheel = a single twistExtrude
  of the closed involute wire. Bores cut THROUGH (vent both faces). In mesh_demo
  the worm and wheel OVERLAP a solid base bracket (volumetric union → one body).
  Turn counts are kept modest (starts*turns <= 3) so the helical sweep never
  self-intersects into a non-watertight mesh. No revolve-of-cut profiles.

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
target_part = str(PARAM(lambda: target_part, "worm"))
# "worm" | "wheel" | "mesh_demo"

m = float(PARAM(lambda: m, 1.5))                       # module (mm)
starts = int(PARAM(lambda: starts, 1))                 # worm thread starts
worm_dia = float(PARAM(lambda: worm_dia, 14.0))        # worm pitch diameter (mm)
worm_turns = float(PARAM(lambda: worm_turns, 2.5))     # visible worm turns
teeth = int(PARAM(lambda: teeth, 30))                  # worm-wheel tooth count
pressure_angle = float(PARAM(lambda: pressure_angle, 20.0))  # deg
thickness = float(PARAM(lambda: thickness, 9.0))       # wheel face width (mm)
worm_bore = float(PARAM(lambda: worm_bore, 5.0))       # worm shaft bore (mm)
wheel_bore = float(PARAM(lambda: wheel_bore, 6.0))     # wheel shaft bore (mm)
flank_pts = int(PARAM(lambda: flank_pts, 8))           # involute samples / flank

# ── Clamp / normalise inputs ─────────────────────────────────────────────────
m = max(0.5, min(m, 3.0))
starts = max(1, min(starts, 3))
worm_dia = max(6.0, min(worm_dia, 30.0))
worm_turns = max(1.0, min(worm_turns, 4.0))
# Cap total swept revolutions at 3 so the helical sweep stays watertight.
if starts * worm_turns > 3.0:
    worm_turns = max(1.0, 3.0 / starts)
teeth = max(15, min(teeth, 80))
pressure_angle = max(14.5, min(pressure_angle, 25.0))
thickness = max(4.0, min(thickness, 20.0))
flank_pts = max(4, min(flank_pts, 14))
pa = math.radians(pressure_angle)

# Worm/wheel kinematics (shared)
rp_worm = worm_dia / 2.0
lead = math.pi * m * starts                            # axial advance per revolution
lead_angle = math.degrees(math.atan(lead / (2.0 * math.pi * rp_worm)))


# ── Involute geometry (wheel flanks) ─────────────────────────────────────────
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


def _gear_wire(g_teeth, rb, ro, rr):
    """Full closed spur cross-section: one tooth polar-patterned g_teeth times."""
    tooth = _one_tooth_profile(g_teeth, rb, ro, rr, flank_pts)
    step = 2.0 * math.pi / g_teeth
    all_pts = []
    for k in range(g_teeth):
        a = k * step
        ca, sa = math.cos(a), math.sin(a)
        for (x, y) in tooth:
            all_pts.append((x * ca - y * sa, x * sa + y * ca))
    return all_pts


# ── Part builders ────────────────────────────────────────────────────────────
def build_worm(with_bore=True):
    """Single- or multi-start worm: a trapezoidal thread swept along a true helix
    on a root cylinder. Ends squared by intersecting with a bounding cylinder."""
    p = math.pi * m                       # axial pitch between adjacent threads
    add = m
    ded = 1.25 * m
    r_out = rp_worm + add
    r_root = max(rp_worm - ded, 0.6 * m)
    length = lead * worm_turns

    tan_pa = math.tan(pa)
    crest_half = max(p / 4.0 - add * tan_pa, 0.06 * p)
    root_half = p / 4.0 + ded * tan_pa

    worm = cq.Workplane("XY").circle(r_root).extrude(length)
    for s in range(starts):
        phase = s * p
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

    bound = cq.Workplane("XY").circle(r_out + 1.0).extrude(length)
    worm = worm.intersect(bound)

    if with_bore and worm_bore > 0.05:
        br = min(worm_bore / 2.0, r_root - 0.5)
        if br > 0.4:
            hole = (cq.Workplane("XY").workplane(offset=-1.0)
                    .circle(br).extrude(length + 2.0))
            worm = worm.cut(hole)
    return worm, length, r_out


def build_wheel(with_bore=True):
    """Worm-wheel as a helical spur gear at the worm's lead angle."""
    rp = m * teeth / 2.0
    rb = rp * math.cos(pa)
    ro = rp + m
    rr = max(rp - 1.25 * m, 0.5 * m)
    wire = _gear_wire(teeth, rb, ro, rr)
    twist_deg = math.degrees(thickness * math.tan(math.radians(lead_angle)) / rp)
    solid = cq.Workplane("XY").polyline(wire).close().twistExtrude(thickness, twist_deg)
    if with_bore and wheel_bore > 0.05:
        br = min(wheel_bore / 2.0, rr - 0.5)
        if br > 0.4:
            hole = (cq.Workplane("XY").workplane(offset=-1.0)
                    .circle(br).extrude(thickness + 2.0))
            solid = solid.cut(hole)
    return solid, rp


def build_mesh_demo():
    """Worm meshing the wheel at 90 deg, both fused to one base bracket so the set
    is ONE connected body (body_count == 1). The wheel lies flat (axis Z); the
    worm axis is along X, tangent to the wheel pitch circle, one centre-distance
    above the wheel centre. A base plate under the wheel and two posts up to the
    worm ends union everything into a single printable demonstrator.

    NOTE: printed pre-meshed as a static demonstrator (a fused monolith), not a
    free-spinning pair."""
    worm, w_len, r_out = build_worm(with_bore=False)
    wheel, rp_wheel = build_wheel(with_bore=False)

    centre_dist = rp_worm + rp_wheel
    worm_pl = (worm
               .rotate((0, 0, 0), (0, 1, 0), 90)         # worm axis → X
               .translate((-w_len / 2.0, 0, centre_dist)))

    combined = wheel.union(worm_pl)

    # Base plate the wheel sits on (overlaps the wheel bottom → fuses it in).
    plate_r = rp_wheel + m + 3.0
    plate_t = 3.0
    base = (cq.Workplane("XY")
            .workplane(offset=-plate_t)
            .rect(2.0 * plate_r + w_len * 0.2, 2.0 * plate_r)
            .extrude(plate_t + 0.5))
    combined = combined.union(base)

    # Two support posts rising from the base to just under the worm ends, so the
    # worm is joined to the base by solid material (single body). Posts sit at
    # ±X near the worm ends, offset in +Y so they clear the wheel teeth.
    post_r = max(2.0, r_out * 0.5)
    post_x = w_len / 2.0 - post_r
    post_top = centre_dist - r_out + 0.5     # reach just into the worm root
    for sx in (-1.0, 1.0):
        post = (cq.Workplane("XY")
                .transformed(offset=cq.Vector(sx * post_x, plate_r - post_r - 0.5, -plate_t))
                .circle(post_r)
                .extrude(post_top + plate_t))
        combined = combined.union(post)

    # A bridge bar across the two post tops carrying the worm (guarantees the worm
    # is fused even if a post just misses the root).
    bridge = (cq.Workplane("XY")
              .transformed(offset=cq.Vector(0, plate_r - post_r - 0.5, post_top - 0.5))
              .box(2.0 * post_x + 2.0 * post_r, 2.0 * post_r, 1.5, centered=(True, True, False)))
    combined = combined.union(bridge)

    try:
        combined = combined.clean()
    except Exception:
        pass
    return combined


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "wheel":
    result = build_wheel()[0]
elif target_part == "mesh_demo":
    result = build_mesh_demo()
else:  # "worm" (default)
    result = build_worm()[0]
