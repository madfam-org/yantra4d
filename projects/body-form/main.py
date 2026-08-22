"""
Body Form — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A parametric dress form (tailor's torso) — the mannequin the Fashion Cabinet
commons drapes its patterns onto. Deliberately an ABSTRACT form, not a figure:
its whole value is its INTERFACES — the neck / shoulder / bust / waist / hip
LANDMARK RINGS. Those rings are the CDG (Common Denominator Geometry) surfaces
a garment wraps to, and each ring's girth is an ISO-8559 body measurement, so
the same numbers that draft a flat pattern in Fashion Cabinet also size this
solid. One shared measurement contract, two commons (see the Fashion Cabinet
schema packages/schemas/body-measurements.schema.json).

The form is built as a LOFT through named elliptical cross-sections stacked by
height. Each section's circumference equals its landmark girth: girth →
ellipse (width, depth) via a per-landmark depth:width ratio, and the ellipse
perimeter is fitted (Ramanujan) so the ring is dimensionally the measurement.

Modes:
  - torso        : the bare dress form, neck ring down to the hip ring, capped.
  - torso_stand  : the torso on a neck post + weighted round base (a usable
                   dress-form stand).
  - bifurcated   : the torso continued past the hip into two upper-thigh stumps
                   (a "trouser form") so bottoms/one-pieces have legs to fit.
  - figure       : the full figure, shoulders to floor — the torso with a
                   shoulder cap + short upper-arm stub each side, and the hip
                   continued through thigh / knee / ankle rings to close at the
                   ankles. Serves dresses, heritage robes, outerwear, tailoring.
  - legs         : the lower body alone, waist ring through hip / thigh / knee /
                   ankle — a trouser/skirt form for bottoms, skirts and denim.

Watertight strategy (Yantra4D scar tissue, all respected):
  - The body is ONE lofted solid through convex elliptical wires — no boolean of
    a post onto a sphere (the pole-fan non-manifold trap). The neck is closed by
    a short loft to a small flat ellipse (loft-to-flat frustum, NO sphere pole
    singularity); the hip/crotch is closed flat by the loft's end cap.
  - The stand post is a SOLID cylinder embedded into the (closed, solid) neck and
    into the base — a solid post on a solid base, no trapped cavity.
  - Thigh stumps are solid lofts continued from the hip wire, capped flat.
  - Full legs are solid lofts whose TOP wire starts well ABOVE the crotch, inside
    the seat solid, so the leg/torso junction is a deep volumetric OVERLAP, never
    a coplanar touch (coplanar-touch unions crack). The ankle is closed flat by
    the loft's own end cap — no sphere pole.
  - Arm stubs are lofted cones whose ROOT wire sits inside the shoulder shelf
    (again an overlap, not a touch); the outboard end is a flat elliptical cap.
  - No fillet/chamfer after feature cuts (the uncatchable-OCCT-segfault path);
    the form has no cuts at all — it is a pure additive loft.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as bare globals.
  - Read each via PARAM(lambda: name, default). No globals()/eval/getattr.
  - Assign the final solid to a top-level `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default. `except Exception`
    catches the NameError the sandbox raises for an unbound param (globals()/
    NameError are not exposed)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters — ISO-8559 landmark GIRTHS (mm), full-body circumferences ─────
target_part = str(PARAM(lambda: target_part, "torso"))
# "torso" | "torso_stand" | "bifurcated" | "figure" | "legs"

neck_girth   = float(PARAM(lambda: neck_girth, 360.0))    # 4.4  neck base
chest_girth  = float(PARAM(lambda: chest_girth, 900.0))   # 4.6  chest/bust girth
bust_girth   = float(PARAM(lambda: bust_girth, 920.0))    # 4.7  bust apex (>= chest)
waist_girth  = float(PARAM(lambda: waist_girth, 720.0))   # 4.10 waist
hip_girth    = float(PARAM(lambda: hip_girth, 980.0))     # 4.12 hip (fullest seat)
back_waist_length = float(PARAM(lambda: back_waist_length, 410.0))  # nape→waist
shoulder_width    = float(PARAM(lambda: shoulder_width, 400.0))     # point→point
thigh_girth  = float(PARAM(lambda: thigh_girth, 580.0))   # per-leg thigh (bifurcated)
knee_girth   = float(PARAM(lambda: knee_girth, 380.0))    # 4.17 per-leg knee
ankle_girth  = float(PARAM(lambda: ankle_girth, 240.0))   # 4.19 per-leg ankle
inside_leg_length = float(PARAM(lambda: inside_leg_length, 780.0))  # 4.26 crotch→floor
upper_arm_girth   = float(PARAM(lambda: upper_arm_girth, 300.0))    # 4.14 upper arm
arm_stub_length   = float(PARAM(lambda: arm_stub_length, 120.0))    # shoulder→stub end

# Form/pose knobs (advisory; the rings stay authoritative)
bust_depth_ratio  = float(PARAM(lambda: bust_depth_ratio, 0.72))  # depth:width at bust
seat_depth_ratio  = float(PARAM(lambda: seat_depth_ratio, 0.74))  # depth:width at hip
wall              = float(PARAM(lambda: wall, 0.0))       # 0 = solid form; >0 = shelled (advisory)
post_dia          = float(PARAM(lambda: post_dia, 32.0))  # stand neck-post Ø
base_dia          = float(PARAM(lambda: base_dia, 340.0)) # stand base Ø
base_th           = float(PARAM(lambda: base_th, 18.0))   # stand base thickness

target_material = str(PARAM(lambda: target_material, "polymaker-polylite-pla"))

# ── Clamps (match manifest slider bounds; keep the loft well-posed) ──────────
neck_girth = max(240.0, min(neck_girth, 560.0))
chest_girth = max(460.0, min(chest_girth, 1900.0))
bust_girth = max(chest_girth, min(bust_girth, chest_girth + 260.0))
waist_girth = max(380.0, min(waist_girth, 1600.0))
hip_girth = max(440.0, min(hip_girth, 1800.0))
back_waist_length = max(200.0, min(back_waist_length, 620.0))
shoulder_width = max(240.0, min(shoulder_width, 620.0))
thigh_girth = max(300.0, min(thigh_girth, 900.0))
knee_girth = max(220.0, min(knee_girth, 620.0))
ankle_girth = max(150.0, min(ankle_girth, 420.0))
inside_leg_length = max(400.0, min(inside_leg_length, 1000.0))
upper_arm_girth = max(180.0, min(upper_arm_girth, 560.0))
arm_stub_length = max(40.0, min(arm_stub_length, 320.0))
# The leg lofts stay well-posed only if each ring is smaller than the one above.
knee_girth = min(knee_girth, thigh_girth * 0.92)
ankle_girth = min(ankle_girth, knee_girth * 0.92)
bust_depth_ratio = max(0.55, min(bust_depth_ratio, 0.98))
seat_depth_ratio = max(0.55, min(seat_depth_ratio, 0.98))
post_dia = max(16.0, min(post_dia, 80.0))
base_dia = max(180.0, min(base_dia, 600.0))
base_th = max(8.0, min(base_th, 60.0))


# ── girth → ellipse semi-axes ────────────────────────────────────────────────
def _ellipse_axes(girth, depth_ratio):
    """Return (a, b) semi-axes (half-width, half-depth) of an ellipse whose
    perimeter equals `girth`, at a given depth:width ratio r = b/a.

    Ramanujan-II perimeter P ≈ pi (a+b) [1 + 3h/(10 + sqrt(4-3h))], h=((a-b)/(a+b))^2.
    Solve the scale by one Newton-free ratio: for fixed r, P scales linearly with a,
    so a = girth / P_unit where P_unit is the perimeter at a=1."""
    r = max(0.35, min(depth_ratio, 1.0))
    a1, b1 = 1.0, r
    h = ((a1 - b1) / (a1 + b1)) ** 2
    p_unit = math.pi * (a1 + b1) * (1.0 + 3.0 * h / (10.0 + math.sqrt(4.0 - 3.0 * h)))
    a = girth / p_unit
    return a, a * r


def _loft_sections(sections, cx=0.0):
    """Loft a solid through ordered (z, girth, depth_ratio) sections, lowest z
    first. Built as ONE Workplane chain — each profile is drawn, then the
    workplane is advanced by the height delta to the next — which is the loft
    idiom CadQuery needs (pending wires accumulate on one stack; add()-ing
    separate Workplanes does NOT). Sections must be sorted by z ascending.

    RULED (linear) loft is deliberate: a monotone linear interpolation between
    two elliptical wires can never bulge WIDER than either wire, so every
    landmark ring measures its exact girth. A B-spline (ruled=False) loft
    overshoots where sections change fast (shoulder→neck), breaking the CDG
    contract that the ring IS the measurement. Intermediate rings keep the
    silhouette smooth despite the linear segments."""
    ordered = sorted(sections, key=lambda s: s[0])
    z0 = ordered[0][0]
    a0, b0 = _ellipse_axes(ordered[0][1], ordered[0][2])
    wp = cq.Workplane("XY").workplane(offset=z0).center(cx, 0.0).ellipse(a0, b0)
    prev_z = z0
    for z, girth, dr in ordered[1:]:
        a, b = _ellipse_axes(girth, dr)
        wp = wp.workplane(offset=z - prev_z).ellipse(a, b)
        prev_z = z
    return wp.loft(ruled=True, combine=True)


# ── Vertical landmark heights (mm from waist datum z=0) ───────────────────────
# Proportioned off back_waist_length so the form scales with the person.
BWL = back_waist_length
Z_WAIST = 0.0
Z_HIP = -0.55 * BWL          # seat sits below the waist
Z_CHEST = 0.62 * BWL         # chest line above the waist
Z_BUST = 0.50 * BWL          # bust apex just below the chest line
Z_SHOULDER = 0.98 * BWL      # shoulder/HPS level
Z_NECK = 1.06 * BWL          # neck base ring
Z_CROTCH = -0.92 * BWL       # bifurcated split
DR_WAIST = 0.70
DR_CHEST = 0.62
DR_NECK = 0.82

# Full-leg stations (figure / legs). Unlike the torso rings these are NOT scaled
# off BWL: inside_leg_length is itself a measurement (crotch → floor), so the
# knee and ankle hang off it directly and the figure grows exactly as tall as
# the wearer's leg says it should.
ILL = inside_leg_length
Z_ANKLE = Z_CROTCH - ILL * 0.94      # ankle ring (floor is ILL below the crotch)
Z_FLOOR = Z_CROTCH - ILL             # notional floor; the form closes at the ankle
Z_KNEE = Z_CROTCH - ILL * 0.47       # knee ≈ mid inside-leg
Z_THIGH = Z_CROTCH - ILL * 0.10      # thigh ring, just below the crotch
DR_LEG = 0.92                        # legs are near-round in section


def _core_sections():
    """The ordered (z, girth, depth_ratio) landmark rings, hip → neck.

    The MEASURED rings (hip, waist, bust, chest, neck) are the CDG surfaces — a
    garment wraps to these and each is exactly its ISO-8559 girth. The rest are
    DERIVED waypoints (upper-hip, lower-chest, shoulder shelf, neck base) that
    shape a smooth silhouette between the measured rings under the linear loft;
    their girths are interpolations, not measurements."""
    shoulder_girth = max(chest_girth * 0.82, neck_girth * 1.7)
    return [
        (Z_HIP - 0.12 * BWL, hip_girth * 0.985, seat_depth_ratio),   # below-seat taper
        (Z_HIP, hip_girth, seat_depth_ratio),                        # ★ HIP (measured)
        ((Z_HIP + Z_WAIST) / 2.0, (hip_girth + waist_girth) / 2.0 * 0.99, 0.72),  # upper hip
        (Z_WAIST, waist_girth, DR_WAIST),                            # ★ WAIST (measured)
        (Z_BUST, bust_girth, bust_depth_ratio),                      # ★ BUST (measured)
        (Z_CHEST, chest_girth, DR_CHEST),                            # ★ CHEST (measured)
        (Z_SHOULDER, shoulder_girth, 0.66),                          # shoulder shelf
        ((Z_SHOULDER + Z_NECK) / 2.0, (shoulder_girth + neck_girth) / 2.0, 0.74),  # neck base
        (Z_NECK, neck_girth, DR_NECK),                               # ★ NECK (measured)
    ]


def _neck_cap(top_z, top_girth):
    """Close the neck opening with a short loft to a small flat ellipse — a
    loft-to-flat frustum, never a sphere pole (the pole-fan non-manifold trap)."""
    a, b = _ellipse_axes(top_girth, DR_NECK)
    cap_h = max(10.0, top_girth * 0.02)
    return (
        cq.Workplane("XY").workplane(offset=top_z).ellipse(a, b)
        .workplane(offset=cap_h).ellipse(a * 0.42, b * 0.42)
        .loft(ruled=True, combine=True)
    )


def build_torso():
    """The bare dress form: hip → neck loft, neck capped, hip closed by the
    loft end. One watertight solid."""
    body = _loft_sections(_core_sections())
    body = body.union(_neck_cap(Z_NECK, neck_girth))
    return body


def build_bifurcated():
    """Torso continued below the hip into two upper-thigh stumps (a trouser
    form). Each stump is a solid loft from a half-hip ellipse down to a capped
    thigh ellipse, unioned to the torso where they overlap the seat."""
    body = build_torso()
    a_hip, _b_hip = _ellipse_axes(hip_girth, seat_depth_ratio)
    x_off = a_hip * 0.48                     # leg centre offset from CF axis
    z_top = Z_HIP + 0.10 * BWL
    stump_bottom = Z_CROTCH - 0.5 * BWL
    legs = None
    for sx in (-x_off, x_off):
        a_t, b_t = _ellipse_axes(thigh_girth, 0.92)
        leg = (
            cq.Workplane("XY").workplane(offset=z_top).center(sx, 0.0)
            .ellipse(a_t * 1.15, b_t * 1.15)
            .workplane(offset=Z_CROTCH - z_top).ellipse(a_t, b_t)
            .workplane(offset=stump_bottom - Z_CROTCH).ellipse(a_t * 0.94, b_t * 0.94)
            .loft(ruled=False, combine=True)
        )
        legs = leg if legs is None else legs.union(leg)
    return body.union(legs)


def _leg_offset():
    """Half the leg-centre spacing: how far each leg axis sits from the centre
    front/back plane. Derived from the hip ellipse so a wider seat puts the legs
    correspondingly further apart."""
    a_hip, _b = _ellipse_axes(hip_girth, seat_depth_ratio)
    return a_hip * 0.44


def _leg(sx):
    """ONE full leg, thigh through knee to a flat-capped ankle.

    The TOP wire sits at Z_HIP — well ABOVE the crotch and therefore deep INSIDE
    the seat solid — so the leg/torso union is a volumetric overlap, never the
    coplanar touch that cracks a boolean. It starts at a generous ellipse
    (roughly the half-seat the leg occupies) and necks down to the measured
    thigh ring below the crotch, which is what gives the form its inner-thigh
    line without any cut.

    The ankle is closed by the loft's own flat end cap — no sphere pole, no
    fillet. RULED loft everywhere, so no ring bulges past its girth."""
    a_t, b_t = _ellipse_axes(thigh_girth, DR_LEG)
    a_k, b_k = _ellipse_axes(knee_girth, DR_LEG)
    a_a, b_a = _ellipse_axes(ankle_girth, DR_LEG)
    # root wire: sized to fill its half of the seat so the overlap is generous
    a_r, b_r = a_t * 1.30, b_t * 1.22
    stations = [
        (Z_HIP, a_r, b_r),                                 # root, inside the seat
        (Z_CROTCH, a_t * 1.06, b_t * 1.04),                # crotch level
        (Z_THIGH, a_t, b_t),                               # ★ THIGH (measured)
        ((Z_THIGH + Z_KNEE) / 2.0,
         (a_t + a_k) / 2.0 * 0.98, (b_t + b_k) / 2.0 * 0.98),   # mid-thigh taper
        (Z_KNEE, a_k, b_k),                                # ★ KNEE (measured)
        ((Z_KNEE + Z_ANKLE) / 2.0,
         (a_k + a_a) / 2.0 * 1.04, (b_k + b_a) / 2.0 * 1.04),   # calf swell
        (Z_ANKLE, a_a, b_a),                               # ★ ANKLE (measured)
    ]
    ordered = sorted(stations, key=lambda s: s[0])
    z0, a0, b0 = ordered[0]
    wp = cq.Workplane("XY").workplane(offset=z0).center(sx, 0.0).ellipse(a0, b0)
    prev_z = z0
    for z, a, b in ordered[1:]:
        wp = wp.workplane(offset=z - prev_z).ellipse(a, b)
        prev_z = z
    return wp.loft(ruled=True, combine=True)


def _legs():
    """Both legs as one shape. They are unioned to the torso/hip solid, which is
    what connects them into a single printable body through the seat."""
    x_off = _leg_offset()
    left = _leg(-x_off)
    right = _leg(x_off)
    return left.union(right)


def _arm_stub(sx):
    """A short upper-arm stub for one side, so a tailored shoulder hangs.

    Built as a loft along the vertical axis in a LOCAL frame and then rotated
    outboard, which keeps every wire an ordinary planar ellipse (the well-posed
    case) instead of a swept path. The ROOT wire is deliberately placed inboard
    of the shoulder shelf so the stub starts INSIDE the torso solid — an
    overlap, not a touch — and the outboard end is a flat elliptical cap, never
    a sphere."""
    a_u, b_u = _ellipse_axes(upper_arm_girth, 0.86)
    root_r = a_u * 1.16
    # Build along +Z at the origin: root disc → armhole ring → stub end cap.
    stub = (
        cq.Workplane("XY").ellipse(root_r, root_r * 0.86)
        .workplane(offset=arm_stub_length * 0.30).ellipse(a_u * 1.04, b_u * 1.04)
        .workplane(offset=arm_stub_length * 0.70).ellipse(a_u * 0.94, b_u * 0.94)
        .loft(ruled=True, combine=True)
    )
    # Point it outboard and tilt it down: shoulders slope, so does the stub.
    side = 1.0 if sx >= 0 else -1.0
    stub = stub.rotate((0, 0, 0), (0, 1, 0), 90.0 * side)
    stub = stub.rotate((0, 0, 0), (0, 1, 0), 14.0 * side)   # ~14° shoulder slope
    # Seat the root inside the shoulder shelf: start inboard of the shelf edge.
    a_sh, _b_sh = _ellipse_axes(max(chest_girth * 0.82, neck_girth * 1.7), 0.66)
    x_root = side * max(a_sh * 0.55, shoulder_width / 2.0 - a_u * 1.5)
    return stub.translate((x_root, 0.0, Z_SHOULDER - a_u * 0.10))


def _shoulder_cap():
    """The shoulder shelf + both arm stubs.

    The torso loft already carries a shoulder shelf ring; the cap widens it to
    the measured shoulder_width with a shallow loft between two ellipses so a
    jacket's shoulder line has somewhere real to sit, and the stubs then root
    into that widened shelf."""
    a_sh, b_sh = _ellipse_axes(max(chest_girth * 0.82, neck_girth * 1.7), 0.66)
    half_w = max(shoulder_width / 2.0, a_sh)
    shelf_h = max(16.0, 0.05 * BWL)
    shelf = (
        cq.Workplane("XY").workplane(offset=Z_SHOULDER - shelf_h)
        .ellipse(a_sh * 0.98, b_sh * 0.98)
        .workplane(offset=shelf_h * 0.55).ellipse(half_w, b_sh)
        .workplane(offset=shelf_h * 0.45).ellipse(half_w * 0.94, b_sh * 0.96)
        .loft(ruled=True, combine=True)
    )
    return shelf.union(_arm_stub(-1.0)).union(_arm_stub(1.0))


def build_figure():
    """Full figure, shoulders to floor: the torso, a shoulder cap + upper-arm
    stubs, and both full legs closed at the ankle. One watertight solid — the
    legs meet the torso through a deep seat overlap and the stubs root inside
    the shoulder shelf, so every union is volumetric."""
    body = build_torso()
    body = body.union(_shoulder_cap())
    return body.union(_legs())


def _lower_sections():
    """Waist → hip rings for the `legs` mode: the trouser block starts at the
    measured waist and runs to the seat, where the legs take over."""
    return [
        (Z_HIP, hip_girth, seat_depth_ratio),                        # ★ HIP (measured)
        ((Z_HIP + Z_WAIST) / 2.0, (hip_girth + waist_girth) / 2.0 * 0.99, 0.72),
        (Z_WAIST, waist_girth, DR_WAIST),                            # ★ WAIST (measured)
    ]


def build_legs():
    """Lower body, waist to ankle — the trouser/skirt form. A waist→hip block
    closed flat at the waist by the loft's end cap, with both full legs unioned
    into it through the seat. The two legs are connected through that block, so
    the result is ONE printable solid, not two."""
    block = _loft_sections(_lower_sections())
    return block.union(_legs())


def _stand():
    """Neck post + weighted round base. ONE solid: the post spans from inside the
    base (overlapping it) up through the form and above the neck, so post∪base∪
    torso is a single connected body — no floating base, no trapped cavity."""
    base_z = Z_HIP - 0.5 * BWL - base_th          # base underside
    base_top = base_z + base_th
    post_top = Z_NECK + max(10.0, neck_girth * 0.02) + 90.0   # rises above the neck
    post_bottom = base_z + base_th * 0.4          # post roots INTO the base
    base = (cq.Workplane("XY").workplane(offset=base_z)
            .circle(base_dia / 2.0)
            .extrude(base_th))
    post = (cq.Workplane("XY").workplane(offset=post_bottom)
            .circle(post_dia / 2.0)
            .extrude(post_top - post_bottom))
    # a short neck knob so the post reads as a dress-form finial
    knob = (cq.Workplane("XY").workplane(offset=post_top - 6.0)
            .circle(post_dia * 0.7)
            .extrude(18.0))
    _ = base_top
    return post.union(base).union(knob)


def build_torso_stand():
    """Torso on a stand — the usable dress form."""
    return build_torso().union(_stand())


def build():
    builders = {
        "torso": build_torso,
        "torso_stand": build_torso_stand,
        "bifurcated": build_bifurcated,
        "figure": build_figure,
        "legs": build_legs,
    }
    fn = builders.get(target_part, build_torso)
    return fn()


result = build()
