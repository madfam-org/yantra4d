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
# ...but an INTEGER turn count degenerates the OCCT helical sweep (the profile
# closes on itself and the boolean yields a broken body) — the same trap the
# docstring names. At starts=3 the cap above lands on EXACTLY 1.0, so nudge any
# integer result off the whole number. A twentieth of a turn is visually nil and
# costs nothing, but it keeps the sweep non-degenerate.
if float(worm_turns).is_integer():
    worm_turns += 0.05
teeth = max(15, min(teeth, 80))
pressure_angle = max(14.5, min(pressure_angle, 25.0))
thickness = max(4.0, min(thickness, 20.0))
# The worm-bore is clamped against the thread root below, once r_root is known.
wheel_bore = max(0.0, min(wheel_bore, 16.0))
worm_bore = max(0.0, min(worm_bore, 12.0))
flank_pts = max(4, min(flank_pts, 14))
pa = math.radians(pressure_angle)

# Worm/wheel kinematics (shared)
rp_worm = worm_dia / 2.0

# DERIVED CLAMP — thread DEPTH against the worm's own radius (the kernel trap on
# this cartridge). The rib runs from the root radius (rp - ded) out to the tip
# (rp + m). With a textbook dedendum of 1.25m, a coarse module on a thin worm drives
# the root radius toward the axis; the swept rib then wraps back on itself and the
# STL tessellates cracked (or the solid exports empty).
#
# Rather than forbidding the coarse module outright — which silently rewrites the
# user's module and breaks the DIN 3975 mesh contract with the wheel — SHORTEN THE
# DEDENDUM so the root cylinder keeps at least 45% of the worm radius. The module,
# the pitch and the lead all stay exactly as asked, so the pair still meshes; only
# the depth of the thread's root relief is trimmed on the thinnest worms, which is
# what a machinist would do anyway.
ded_factor = min(1.25, 0.55 * rp_worm / m)

lead = math.pi * m * starts                            # axial advance per revolution
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
    ded = ded_factor * m                  # relieved on thin worms — see the clamp above
    r_out = rp_worm + add
    r_root = max(rp_worm - ded, 0.6 * m)
    # A worm shorter than a few axial pitches has almost no thread left after the
    # ends are squared off — at small module `lead * worm_turns` collapses to under
    # one pitch and the part came out as a BARE CYLINDER (a giveaway constant 1008
    # faces). Guarantee at least four axial pitches of real thread.
    length = max(lead * worm_turns, 4.0 * p)

    tan_pa = math.tan(pa)
    crest_half = max(p / 4.0 - add * tan_pa, 0.06 * p)
    root_half = p / 4.0 + ded * tan_pa

    # The swept profile must be given in ABSOLUTE radii on the XZ plane. Writing it
    # relative to rp_worm and then `.translate((rp_worm, 0, phase))` does not work:
    # `sweep(isFrenet=True)` re-frames the profile onto the helix's own moving frame,
    # which discards that translation, so the rib was swept at radius ~(r_out-rp_worm)
    # about the AXIS instead of about the pitch cylinder. The result was a thread
    # buried entirely inside the root cylinder — every worm rendered as a bare
    # cylinder (a constant 1008 faces regardless of module or starts), watertight but
    # completely unthreaded. Absolute radii, matching the proven thread helper used
    # elsewhere in the commons, put the rib where DIN 3975 wants it.
    #
    # The rib's inner edge is sunk WELL INSIDE the root cylinder (not a hair inside
    # it): a rib that merely touches the core wall is a tangency, and the fuse then
    # leaves core and thread as two separate bodies.
    r_in = max(0.35 * r_root, r_root - 0.5 * m)

    # Sweep each start over the full length plus a lead of run-out at both ends, then
    # CLIP THAT START to the finished length band BEFORE fusing it to the core.
    # Fusing the un-clipped ribs first and squaring the ends afterwards is what broke
    # multi-start worms: the overhanging run-out spirals hang outside the blank while
    # the union runs, and OCCT returns either a Null shape or a body per rib. Clipping
    # first means every fuse is core-plus-one-buried-rib, which is well conditioned.
    over = lead + p
    band = cq.Workplane("XY").circle(r_out + 1.0).extrude(length)
    worm = cq.Workplane("XY").circle(r_root).extrude(length)
    for s in range(starts):
        # Build the profile FRESH each pass: `sweep()` consumes the Workplane's
        # pending wires, so a profile hoisted out of the loop is empty on the second
        # start ("No pending wires present") and multi-start worms never built.
        prof = (cq.Workplane("XZ")
                .polyline([
                    (r_in, -root_half),
                    (r_out, -crest_half),
                    (r_out, crest_half),
                    (r_in, root_half),
                ]).close())
        helix = cq.Wire.makeHelix(pitch=lead, height=length + 2.0 * over,
                                  radius=rp_worm)
        thread = prof.sweep(cq.Workplane(obj=helix), isFrenet=True)
        thread = thread.translate((0, 0, -over))
        if s:
            # Multi-start: the starts are equally spaced around the circumference.
            thread = thread.rotate((0, 0, 0), (0, 0, 1), 360.0 * s / starts)
        worm = worm.union(thread.intersect(band))

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

    # Two support posts rising from the base to the worm, so the worm is joined to
    # the base by solid material (single body).
    #
    # The posts and the bridge MUST live at y = 0 — that is where the worm axis is.
    # Standing them off in +Y (at the plate edge) leaves them nowhere near the worm:
    # the bridge floats in space beside it and the worm comes out as a SECOND body,
    # which is exactly how this mode shipped. Because y = 0 also runs straight
    # through the wheel, the posts are pushed OUT past the wheel's tip circle in X,
    # so each post rises clear of the gear and only the bridge crosses over the top.
    wheel_tip_r = rp_wheel + m
    # The posts must stand entirely CLEAR of the wheel's tip circle. A post that
    # merely overlaps the tooth tips shears little crescents off them, and those
    # slivers survive as extra bodies (body_count 3 instead of 1). Size the post so
    # its inner face clears the tips, and widen the plate to carry it if need be.
    post_r = max(2.0, r_out * 0.5)
    post_x = wheel_tip_r + post_r + 1.5

    # Base plate the wheel sits on (overlaps the wheel bottom → fuses it in). It is
    # sized AFTER the posts so it always reaches under them.
    plate_r = rp_wheel + m + 3.0
    plate_t = 3.0
    plate_half_x = max(plate_r + w_len * 0.1, post_x + post_r + 1.0)
    base = (cq.Workplane("XY")
            .workplane(offset=-plate_t)
            .rect(2.0 * plate_half_x, 2.0 * plate_r)
            .extrude(plate_t + 0.5))
    combined = combined.union(base)
    # Sink the bridge's top face INTO the worm so the fuse is volumetric, not a
    # tangent kiss. Take the worm's UNDERSIDE from its actual bounding box rather
    # than deriving it from r_out: the worm is squared off by an end intersection
    # and its real radius is the thread ROOT, not the nominal tip, so a derived
    # estimate sits millimetres low and the bridge stops short in mid-air (which is
    # how this mode shipped — worm floating as a second body). Reach a full
    # millimetre past the measured underside so there is always real overlap.
    worm_bb = worm_pl.val().BoundingBox()
    bridge_top = worm_bb.zmin + 1.0
    for sx in (-1.0, 1.0):
        post = (cq.Workplane("XY")
                .transformed(offset=cq.Vector(sx * post_x, 0.0, -plate_t))
                .circle(post_r)
                .extrude(bridge_top + plate_t))
        combined = combined.union(post)

    # A bridge bar across the two post tops, at y = 0, carrying the worm along its
    # whole length. Spanning post-to-post it necessarily overlaps both posts, and
    # its top face is buried in the worm root, so worm + posts + plate fuse into one.
    bridge_h = max(1.5, post_r)
    bridge = (cq.Workplane("XY")
              .transformed(offset=cq.Vector(0.0, 0.0, bridge_top - bridge_h))
              .box(2.0 * post_x + 2.0 * post_r, 2.0 * post_r, bridge_h,
                   centered=(True, True, False)))
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
