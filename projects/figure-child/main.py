"""
Figure Child — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A parametric CHILD dress form — the small sibling of `body-form`, and the honest
way to stage the Fashion Cabinet `kids_baby` garments. Like its parent it is an
ABSTRACT form, not a figure: no head, no face, no arms beyond a shoulder shelf.
Its value is its INTERFACES — the neck / chest / waist / hip / crotch / knee /
ankle LANDMARK RINGS — and each ring's girth is an ISO-8559 body measurement, so
the same numbers that draft a flat pattern in Fashion Cabinet also size this
solid (see fashion-cabinet/packages/schemas/body-measurements.schema.json).

WHY A SEPARATE CARTRIDGE (not a small `body-form` preset)
---------------------------------------------------------
A child is not a scaled adult, and lofting `body-form` at child girths lies in
three specific ways this cartridge fixes:

  1. HEAD-TO-BODY RATIO. An adult stands ~7.5 head-lengths tall; a 1-year-old
     ~4, a 6-year-old ~5.7, a 10-year-old ~6.3. The form carries no head, but
     the ratio still governs everything below it: for a given stature the child's
     TORSO is proportionally LONGER and the LEGS proportionally SHORTER. Here
     leg length is a fraction of stature that GROWS with age (`_leg_fraction`),
     rather than the fixed adult value baked into `body-form`'s Z ladder.
  2. WAIST DEFINITION. Small children have essentially none — the toddler belly
     is at or wider than the chest, and the waist indent only appears around
     5-7y. `body-form` always cuts a waist. Here `_waist_indent` is age-driven
     and reaches ~0 under 2y, so the toddler silhouette is the correct barrel.
  3. BELLY PROJECTION. The infant abdomen projects forward; the depth:width
     ratio at the waist ring is therefore HIGHER (rounder section) in the young
     and falls toward the adult value with age (`_belly_ratio`).

Proportion model
----------------
One parameter, `size_age` (years, 0.5-10), drives a small age-response family.
The girth/length parameters remain independently settable ISO-8559 measurements
(the rings stay authoritative and are never overwritten by age); `size_age` only
sets the SHAPE responses above plus the derived vertical ladder, and supplies
the manifest presets' default values. Anthropometric anchors used for the age
responses are the standard growth-chart relations for stature-to-leg-length and
the classical head-count proportions; they are proportion ratios only, so no
population percentile is implied or claimed.

Modes (chosen from what the four kids_baby garments actually measure)
--------------------------------------------------------------------
  - torso       : neck ring down to the hip ring, capped. Serves `kids-t-shirt`
                  and `school-polo`, which measure only chest / neck / body
                  length / sleeve length.
  - bifurcated  : the torso continued past the hip through a crotch ring into two
                  upper-thigh stumps. Serves `baby-bodysuit`, whose snap crotch
                  measures `crotch_ext` and `crotch_width` and therefore needs a
                  real crotch surface to close under.
  - full_figure : the legs continued through knee and ankle rings to a flat foot
                  block. Serves `baby-sleeper`, which is FOOTED and measures
                  `inseam_length`, `ankle_girth` and `foot_length` — a footed
                  sleeper staged on thigh stumps has nowhere to put its feet.

Watertight strategy (Yantra4D scar tissue, all respected — same as `body-form`):
  - The body is ONE lofted solid through convex elliptical wires. The neck is
    closed by a short loft to a small flat ellipse (loft-to-flat frustum, NEVER a
    sphere pole — the pole-fan non-manifold trap); the hip/crotch is closed flat
    by the loft's end cap.
  - Legs are solid lofts that START ABOVE the hip ring, so they OVERLAP the seat
    solid generously before unioning — no coincident-face union, no sliver.
  - Feet are solid blocks overlapping the ankle loft on both faces.
  - No fillet/chamfer anywhere after a feature (the uncatchable-OCCT-segfault
    path). The form is purely additive: no cuts at all, so no sealed voids exist.

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


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "torso"))
# "torso" | "bifurcated" | "full_figure"

# The age driver — sets shape responses and the vertical ladder.
size_age = float(PARAM(lambda: size_age, 4.0))  # years, 0.5 = ~6 months

# ISO-8559 landmark GIRTHS (mm, full-body circumferences), at child defaults.
# Defaults are the ~4-year body implied by the Fashion Cabinet `kids-t-shirt`
# size-4 preset once its knit ease is removed (600 girth - 80 ease = 520 body).
neck_girth   = float(PARAM(lambda: neck_girth, 265.0))   # 4.4  neck base
chest_girth  = float(PARAM(lambda: chest_girth, 550.0))  # 4.6  chest girth
waist_girth  = float(PARAM(lambda: waist_girth, 530.0))  # 4.10 waist
hip_girth    = float(PARAM(lambda: hip_girth, 570.0))    # 4.12 hip (fullest seat)
thigh_girth  = float(PARAM(lambda: thigh_girth, 330.0))  # 4.14 per-leg thigh
knee_girth   = float(PARAM(lambda: knee_girth, 250.0))   # per-leg knee
ankle_girth  = float(PARAM(lambda: ankle_girth, 165.0))  # 4.17 per-leg ankle

# Vertical / linear landmarks (mm)
back_waist_length = float(PARAM(lambda: back_waist_length, 265.0))  # nape→waist
shoulder_width    = float(PARAM(lambda: shoulder_width, 275.0))     # point→point
crotch_height     = float(PARAM(lambda: crotch_height, 145.0))      # waist→crotch
inside_leg_length = float(PARAM(lambda: inside_leg_length, 430.0))  # crotch→ankle
foot_length       = float(PARAM(lambda: foot_length, 165.0))        # heel→toe

# Form shaping knobs (advisory; the measured rings stay authoritative).
# 0 = let the age model choose. Any positive value overrides it.
belly_depth_ratio = float(PARAM(lambda: belly_depth_ratio, 0.0))
seat_depth_ratio  = float(PARAM(lambda: seat_depth_ratio, 0.80))

target_material = str(PARAM(lambda: target_material, "polymaker-polylite-pla"))

# ── Clamps (match manifest slider bounds; keep the loft well-posed) ──────────
size_age = max(0.5, min(size_age, 10.0))
neck_girth = max(180.0, min(neck_girth, 380.0))
chest_girth = max(380.0, min(chest_girth, 820.0))
waist_girth = max(340.0, min(waist_girth, 780.0))
hip_girth = max(360.0, min(hip_girth, 860.0))
thigh_girth = max(180.0, min(thigh_girth, 520.0))
knee_girth = max(150.0, min(knee_girth, 400.0))
ankle_girth = max(90.0, min(ankle_girth, 280.0))
back_waist_length = max(150.0, min(back_waist_length, 400.0))
shoulder_width = max(160.0, min(shoulder_width, 400.0))
crotch_height = max(80.0, min(crotch_height, 260.0))
inside_leg_length = max(120.0, min(inside_leg_length, 700.0))
foot_length = max(70.0, min(foot_length, 260.0))
seat_depth_ratio = max(0.60, min(seat_depth_ratio, 0.98))
belly_depth_ratio = max(0.0, min(belly_depth_ratio, 0.98))


# ── Child age-response model ─────────────────────────────────────────────────
def _age_t():
    """Normalised age 0..1 across the served range (6 months → 10 years).
    Every age response below is a linear blend on this one variable, so the
    family is monotone and has no surprises between the presets."""
    return (size_age - 0.5) / 9.5


def _waist_indent():
    """How much the waist ring is allowed to pull IN relative to the chest, as a
    fraction of the chest→waist difference actually measured.

    An infant has no waist: the belly is as wide as (often wider than) the
    chest, so the form must not cut one even if the two girths differ slightly.
    Definition appears around 5-7y and is still gentler than an adult's at 10.
    0.0 at 0.5y → 0.85 at 10y."""
    return 0.85 * _age_t()


def _belly_ratio():
    """Depth:width at the waist ring. The infant abdomen projects forward, so the
    section is nearly round (0.92) and slims toward the adult-ish 0.72 by 10y.
    An explicit `belly_depth_ratio` overrides this."""
    if belly_depth_ratio > 0.0:
        return belly_depth_ratio
    return 0.92 - 0.20 * _age_t()


def _leg_fraction():
    """Leg length as a fraction of standing stature — the single number that most
    separates a child from a scaled adult. A 1-year-old is about 0.34 leg, a
    10-year-old about 0.47 (an adult is ~0.50). Used only to sanity-scale the
    default leg ladder when `inside_leg_length` is left at its default; an
    explicitly measured inside leg always wins."""
    return 0.34 + 0.13 * _age_t()


# ── girth → ellipse semi-axes ────────────────────────────────────────────────
def _ellipse_axes(girth, depth_ratio):
    """Return (a, b) semi-axes (half-width, half-depth) of an ellipse whose
    perimeter equals `girth`, at a given depth:width ratio r = b/a.

    Ramanujan-II perimeter P ≈ pi (a+b) [1 + 3h/(10 + sqrt(4-3h))], h=((a-b)/(a+b))^2.
    For fixed r, P scales linearly with a, so a = girth / P_unit where P_unit is
    the perimeter at a=1 — no iteration needed."""
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
    separate Workplanes does NOT).

    RULED (linear) loft is deliberate: a monotone linear interpolation between
    two elliptical wires can never bulge WIDER than either wire, so every
    landmark ring measures its exact girth. A B-spline loft overshoots where
    sections change fast, breaking the CDG contract that the ring IS the
    measurement."""
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


# ── Vertical landmark heights (mm from the waist datum z=0) ──────────────────
# Proportioned off back_waist_length (torso) and the measured crotch/inseam
# (below), NOT off a single adult stature ratio — that separation is what keeps
# the child's long torso and short legs honest.
BWL = back_waist_length
Z_WAIST = 0.0
Z_HIP = -0.42 * BWL          # child seat sits closer under the waist than an adult's
Z_CHEST = 0.60 * BWL
Z_SHOULDER = 0.97 * BWL
Z_NECK = 1.08 * BWL
Z_CROTCH = -crotch_height    # measured, not derived
DR_CHEST = 0.72              # child chest is rounder in section than an adult's
DR_NECK = 0.86


def _effective_inside_leg():
    """Inside leg used by the leg builders. The measurement is authoritative; the
    age model only sanity-bounds it against the stature its own proportion
    implies, so an unset/absurd value still yields a child-proportioned figure
    rather than an adult's leg on a toddler torso."""
    stature = (BWL + crotch_height) / (1.0 - _leg_fraction())
    implied = stature * _leg_fraction()
    return max(implied * 0.55, min(inside_leg_length, implied * 1.75))


def _effective_waist_girth():
    """The waist ring the form actually cuts, after the age-driven indent.
    Under ~2y this returns (essentially) the chest girth: the correct barrel."""
    if waist_girth >= chest_girth:
        return waist_girth
    return chest_girth - (chest_girth - waist_girth) * _waist_indent()


def _core_sections():
    """The ordered (z, girth, depth_ratio) landmark rings, hip → neck.

    The MEASURED rings (hip, waist, chest, neck) are the CDG surfaces a garment
    wraps to. The rest are DERIVED waypoints (upper hip, shoulder shelf, neck
    base) that shape a smooth silhouette between the measured rings under the
    linear loft; their girths are interpolations, not measurements."""
    w_eff = _effective_waist_girth()
    # A child's shoulders are narrow relative to the chest — no adult V.
    shoulder_girth = max(chest_girth * 0.86, neck_girth * 1.6)
    return [
        (Z_HIP - 0.12 * BWL, hip_girth * 0.985, seat_depth_ratio),     # below-seat taper
        (Z_HIP, hip_girth, seat_depth_ratio),                          # ★ HIP (measured)
        ((Z_HIP + Z_WAIST) / 2.0, (hip_girth + w_eff) / 2.0, 0.80),    # upper hip
        (Z_WAIST, w_eff, _belly_ratio()),                              # ★ WAIST (measured)
        (Z_CHEST, chest_girth, DR_CHEST),                              # ★ CHEST (measured)
        (Z_SHOULDER, shoulder_girth, 0.70),                            # shoulder shelf
        ((Z_SHOULDER + Z_NECK) / 2.0, (shoulder_girth + neck_girth) / 2.0, 0.78),
        (Z_NECK, neck_girth, DR_NECK),                                 # ★ NECK (measured)
    ]


def _neck_cap(top_z, top_girth):
    """Close the neck opening with a short loft to a small flat ellipse — a
    loft-to-flat frustum, never a sphere pole (the pole-fan non-manifold trap)."""
    a, b = _ellipse_axes(top_girth, DR_NECK)
    cap_h = max(8.0, top_girth * 0.02)
    return (
        cq.Workplane("XY").workplane(offset=top_z).ellipse(a, b)
        .workplane(offset=cap_h).ellipse(a * 0.42, b * 0.42)
        .loft(ruled=True, combine=True)
    )


def build_torso():
    """The bare child dress form: hip → neck loft, neck capped, hip closed by the
    loft end. One watertight solid. Serves kids-t-shirt and school-polo."""
    body = _loft_sections(_core_sections())
    return body.union(_neck_cap(Z_NECK, neck_girth))


def _leg_axis_offset():
    """Half the distance between the two leg centre-lines, from the CF axis."""
    a_hip, _b = _ellipse_axes(hip_girth, seat_depth_ratio)
    return a_hip * 0.46


def _build_leg(sx, to_ankle):
    """One leg as a single ruled loft, top → bottom.

    It STARTS ABOVE the hip ring (z_top) so it is buried inside the seat solid
    before the union — a generous overlap, never a coincident face. The top wire
    is oversized for the same reason: the union must bite, not kiss."""
    z_top = Z_HIP + 0.14 * BWL
    a_t, b_t = _ellipse_axes(thigh_girth, 0.94)
    wp = (
        cq.Workplane("XY").workplane(offset=z_top).center(sx, 0.0)
        .ellipse(a_t * 1.22, b_t * 1.22)
    )
    prev = z_top
    # crotch ring — where the thigh separates from the seat
    wp = wp.workplane(offset=Z_CROTCH - prev).ellipse(a_t, b_t)
    prev = Z_CROTCH

    leg_len = _effective_inside_leg()
    if not to_ankle:
        # bifurcated: a short upper-thigh stump, capped flat by the loft end.
        z_end = Z_CROTCH - leg_len * 0.32
        a_e, b_e = _ellipse_axes(thigh_girth * 0.86, 0.94)
        wp = wp.workplane(offset=z_end - prev).ellipse(a_e, b_e)
        return wp.loft(ruled=True, combine=True)

    # full figure: continue through the knee to the ankle.
    z_knee = Z_CROTCH - leg_len * 0.50
    a_k, b_k = _ellipse_axes(knee_girth, 0.96)
    wp = wp.workplane(offset=z_knee - prev).ellipse(a_k, b_k)
    prev = z_knee
    # calf waypoint (derived, not measured) so the shin is not a bare cone
    z_calf = Z_CROTCH - leg_len * 0.68
    a_c, b_c = _ellipse_axes((knee_girth + ankle_girth) / 2.0 * 1.06, 0.94)
    wp = wp.workplane(offset=z_calf - prev).ellipse(a_c, b_c)
    prev = z_calf
    z_ankle = Z_CROTCH - leg_len
    a_a, b_a = _ellipse_axes(ankle_girth, 0.86)
    wp = wp.workplane(offset=z_ankle - prev).ellipse(a_a, b_a)
    return wp.loft(ruled=True, combine=True)


def _build_foot(sx):
    """A flat foot block under one ankle — the surface a FOOTED sleeper closes
    over. A plain box: it overlaps the ankle loft well above the ankle ring, and
    the toe runs forward (+Y) from the leg axis. Deliberately blunt; a modelled
    toe would add nothing a sock-foot pattern can use."""
    leg_len = _effective_inside_leg()
    z_ankle = Z_CROTCH - leg_len
    a_a, _b_a = _ellipse_axes(ankle_girth, 0.86)
    foot_h = max(20.0, foot_length * 0.30)
    width = max(a_a * 2.0, foot_length * 0.42)
    # overlap: the block's top is BURIED inside the leg loft by foot_h*0.5
    z_bottom = z_ankle - foot_h * 0.5
    return (
        cq.Workplane("XY").workplane(offset=z_bottom)
        .center(sx, foot_length * 0.5 - width * 0.5)
        .rect(width, foot_length)
        .extrude(foot_h)
    )


def build_bifurcated():
    """Torso continued past the hip through the crotch into two upper-thigh
    stumps. Serves baby-bodysuit: a snap crotch needs a crotch to close under."""
    body = build_torso()
    x_off = _leg_axis_offset()
    legs = None
    for sx in (-x_off, x_off):
        leg = _build_leg(sx, to_ankle=False)
        legs = leg if legs is None else legs.union(leg)
    return body.union(legs)


def build_full_figure():
    """Torso + full legs to the ankle + flat foot blocks. Serves baby-sleeper,
    which is footed and measures inside leg, ankle girth and foot length."""
    body = build_torso()
    x_off = _leg_axis_offset()
    lower = None
    for sx in (-x_off, x_off):
        leg = _build_leg(sx, to_ankle=True).union(_build_foot(sx))
        lower = leg if lower is None else lower.union(leg)
    return body.union(lower)


def build():
    builders = {
        "torso": build_torso,
        "bifurcated": build_bifurcated,
        "full_figure": build_full_figure,
    }
    fn = builders.get(target_part, build_torso)
    return fn()


result = build()
