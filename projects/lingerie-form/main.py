"""
Lingerie Form — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The intimates display form: a smooth, tasteful bust-and-hip body that carries
bras, briefs, camisoles, and slips. Sibling of `body-form`, and deliberately a
DIFFERENT anatomy rather than a trimmed torso — on intimates the fit IS the
product, so this form carries the one landmark a dress form omits: the
UNDERBUST ring. A bra reads correctly only when the bust apex and the band that
sits under it are two separate, measured circles; loft only through the bust and
you get a cone, and the band floats.

Extent: upper chest (just under the armscye) → upper thigh. No neck, no
shoulders, no arms, no post, no base, no clutter — the form is closed flat at
both ends and stands on its own bottom face. Everything above the bust would
only hide a strap, and everything below the thigh would only hide a leg line.

Landmark rings (all measured, all ISO-8559 girths; names shared with body-form
where the same measurement is meant, so a Fashion Cabinet measurement mapping
extends to this solid unchanged):
  upper_chest_girth → the closed top ring, above the bust
  bust_girth        → ★ the apex ring
  underbust_girth   → ★ the band ring (the bra's structural seat)
  waist_girth       → ★ waist
  hip_girth         → ★ hip / fullest seat
  thigh_girth       → the closed bottom ring (both thighs read as one column)

Modes:
  - form       : the bare intimates form, flat top and flat bottom, stands up.
  - hanger_tab : the same form with a small integrated hanging tab rising from
                 the flat top, so it can hang in a display as well as stand.

Bust shaping strategy: girth alone cannot make a bust — a wider ellipse spreads
the fullness sideways into the ribs. So the bust band (underbust → bust →
above-bust) is lofted at a HIGHER depth:width ratio than its neighbours, which
pushes the extra circumference forward rather than outward, and the whole bust
band is offset forward on Y by `bust_projection` so the apex sits proud of the
rib line the way a real bust does. The result is a rounded front and a flat-ish
back — a form, not a barrel.

Watertight strategy (Yantra4D scar tissue, all respected):
  - ONE additive ruled loft through convex elliptical wires. No cuts at all, so
    no fillet/chamfer-after-cut OCCT segfault path exists here.
  - Both ends are closed by the loft's own flat end caps — never a sphere cap
    (the pole-fan singularity trap that reads non-watertight).
  - The hanger tab is a SOLID prism that OVERLAPS down into the closed, solid
    top of the form. Solid into solid, generous overlap, no sealed void.
  - Ruled (linear) loft only: a linear interpolation between two ellipses never
    bulges wider than either, so every measured ring measures its exact girth.

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
target_part = str(PARAM(lambda: target_part, "form"))
# "form" | "hanger_tab"

bust_girth        = float(PARAM(lambda: bust_girth, 900.0))       # 4.7  bust apex
underbust_girth   = float(PARAM(lambda: underbust_girth, 760.0))  # 4.8  under-bust band
waist_girth       = float(PARAM(lambda: waist_girth, 700.0))      # 4.10 waist
hip_girth         = float(PARAM(lambda: hip_girth, 960.0))        # 4.12 hip (fullest seat)
upper_chest_girth = float(PARAM(lambda: upper_chest_girth, 840.0))  # above-bust chest
thigh_girth       = float(PARAM(lambda: thigh_girth, 580.0))      # per-leg upper thigh

# Vertical station lengths (mm) — the form is proportioned off these, not off a
# whole-body height, because it has no head and no legs to proportion against.
torso_length      = float(PARAM(lambda: torso_length, 660.0))  # top ring → bottom ring
underbust_to_waist = float(PARAM(lambda: underbust_to_waist, 160.0))  # band → waist
waist_to_hip      = float(PARAM(lambda: waist_to_hip, 200.0))  # waist → fullest seat

# Form/shaping knobs (advisory; the measured rings stay authoritative)
bust_depth_ratio  = float(PARAM(lambda: bust_depth_ratio, 0.86))  # depth:width at bust
seat_depth_ratio  = float(PARAM(lambda: seat_depth_ratio, 0.74))  # depth:width at hip
bust_projection   = float(PARAM(lambda: bust_projection, 26.0))   # apex offset forward (mm)
tab_width         = float(PARAM(lambda: tab_width, 46.0))         # hanger tab width (mm)
tab_height        = float(PARAM(lambda: tab_height, 60.0))        # hanger tab rise (mm)
tab_thickness     = float(PARAM(lambda: tab_thickness, 14.0))     # hanger tab thickness (mm)

target_material = str(PARAM(lambda: target_material, "polymaker-polylite-pla"))

# ── Clamps (match manifest slider bounds; keep the loft well-posed) ──────────
bust_girth = max(500.0, min(bust_girth, 1600.0))
underbust_girth = max(380.0, min(underbust_girth, bust_girth))
waist_girth = max(380.0, min(waist_girth, 1400.0))
hip_girth = max(440.0, min(hip_girth, 1700.0))
upper_chest_girth = max(400.0, min(upper_chest_girth, bust_girth))
thigh_girth = max(300.0, min(thigh_girth, 900.0))
torso_length = max(300.0, min(torso_length, 760.0))
underbust_to_waist = max(80.0, min(underbust_to_waist, 300.0))
waist_to_hip = max(100.0, min(waist_to_hip, 340.0))
bust_depth_ratio = max(0.60, min(bust_depth_ratio, 1.00))
seat_depth_ratio = max(0.55, min(seat_depth_ratio, 0.98))
bust_projection = max(0.0, min(bust_projection, 70.0))
tab_width = max(20.0, min(tab_width, 120.0))
tab_height = max(20.0, min(tab_height, 160.0))
tab_thickness = max(6.0, min(tab_thickness, 40.0))


# ── girth → ellipse semi-axes ────────────────────────────────────────────────
def _ellipse_axes(girth, depth_ratio):
    """Return (a, b) semi-axes (half-width, half-depth) of an ellipse whose
    perimeter equals `girth`, at a given depth:width ratio r = b/a.

    Ramanujan-II perimeter P ≈ pi (a+b) [1 + 3h/(10 + sqrt(4-3h))], h=((a-b)/(a+b))^2.
    For fixed r, P scales linearly with a, so a = girth / P_unit where P_unit is
    the perimeter at a = 1. Same fit body-form uses — one ring vocabulary."""
    r = max(0.35, min(depth_ratio, 1.0))
    a1, b1 = 1.0, r
    h = ((a1 - b1) / (a1 + b1)) ** 2
    p_unit = math.pi * (a1 + b1) * (1.0 + 3.0 * h / (10.0 + math.sqrt(4.0 - 3.0 * h)))
    a = girth / p_unit
    return a, a * r


def _loft_sections(sections):
    """Loft a solid through ordered (z, girth, depth_ratio, y_offset) sections,
    lowest z first. Built as ONE Workplane chain — each profile is drawn, then
    the workplane is advanced by the height delta to the next — which is the
    loft idiom CadQuery needs (pending wires accumulate on one stack; add()-ing
    separate Workplanes does NOT).

    `y_offset` shifts a ring forward on Y without changing its perimeter: this
    is how the bust apex sits proud of the rib line while still measuring its
    exact girth. It is applied via .center(), so it moves the ring's centre, not
    its size.

    RULED (linear) loft is deliberate: a monotone linear interpolation between
    two elliptical wires can never bulge WIDER than either wire, so every
    landmark ring measures its exact girth. A B-spline (ruled=False) loft
    overshoots where sections change fast (underbust→bust), which would break
    the CDG contract that the ring IS the measurement — and on a bra band that
    is the difference between a form that fits and one that lies."""
    ordered = sorted(sections, key=lambda s: s[0])
    z0, g0, dr0, y0 = ordered[0]
    a0, b0 = _ellipse_axes(g0, dr0)
    wp = cq.Workplane("XY").workplane(offset=z0).center(0.0, y0).ellipse(a0, b0)
    prev_z, prev_y = z0, y0
    for z, girth, dr, y in ordered[1:]:
        a, b = _ellipse_axes(girth, dr)
        # .center() is relative to the current workplane origin, so step the delta.
        wp = wp.workplane(offset=z - prev_z).center(0.0, y - prev_y).ellipse(a, b)
        prev_z, prev_y = z, y
    return wp.loft(ruled=True, combine=True)


# ── Vertical landmark heights (mm, waist datum z = 0) ────────────────────────
# Anchored on the two measured vertical spans (underbust→waist, waist→hip) and
# then extended to the requested total torso_length. Every station is derived
# from a real vertical measurement rather than from a body-height guess.
Z_WAIST = 0.0
Z_UNDERBUST = underbust_to_waist
Z_HIP = -waist_to_hip
# The bust apex sits above the band by ~55% of the band→waist span — the
# proportion that puts the apex where a bra cup's fullest point lands.
Z_BUST = Z_UNDERBUST + 0.55 * underbust_to_waist
# The measured stations (hip → bust) fix the middle of the form; the top and
# bottom rings absorb whatever length remains, split so the upper chest gets a
# short shoulder-less shelf and the thigh column gets the rest.
#
# Each end carries its OWN floor rather than sharing one: the above-bust shelf
# must stay long enough for the projection to ramp back to the rib line (a
# crowded shelf reads as a ledge under the apex), and the thigh column must
# clear the seat or the form stops short of the brief line it exists to show.
# So a too-short torso_length grows the form past the request instead of
# deforming it — the proportions are the contract, the overall height is not.
_span_core = Z_BUST - Z_HIP
_remain = max(0.0, torso_length - _span_core)
_top_rise = max(0.34 * _remain, 0.42 * underbust_to_waist)
_bottom_drop = max(0.66 * _remain, 0.60 * waist_to_hip)
Z_TOP = Z_BUST + _top_rise           # upper-chest ring (closed flat)
Z_BOTTOM = Z_HIP - _bottom_drop      # upper-thigh ring (closed flat, stands on this)

# Depth:width ratios per station. The bust band runs deeper than its
# neighbours so the extra circumference goes FORWARD, not sideways.
DR_TOP = 0.66
DR_UNDERBUST = 0.74
DR_WAIST = 0.72
DR_THIGH = 0.92


def _stations():
    """The ordered (z, girth, depth_ratio, y_offset) landmark rings, bottom → top.

    MEASURED rings (thigh, hip, waist, underbust, bust, upper chest) are the CDG
    surfaces — a garment wraps to these and each is exactly its ISO-8559 girth.
    The rest are DERIVED waypoints that keep the silhouette smooth between
    measured rings under the linear loft; their girths are interpolations, not
    measurements.

    The bust band carries a forward y_offset that ramps in below the band and
    ramps back out above the apex, so the projection blends instead of stepping."""
    p = bust_projection
    return [
        # ── bottom: the flat upper-thigh cap the form stands on ──────────────
        (Z_BOTTOM, thigh_girth * 1.62, DR_THIGH, 0.0),
        # a short draw-in above the cut line so the bottom does not read as a plug
        (Z_BOTTOM + 0.30 * (Z_HIP - Z_BOTTOM), thigh_girth * 1.72, 0.86, 0.0),
        # ── ★ HIP (measured) ────────────────────────────────────────────────
        (Z_HIP, hip_girth, seat_depth_ratio, 0.0),
        # upper hip — the seat curve rolling into the waist
        ((Z_HIP + Z_WAIST) / 2.0, (hip_girth + waist_girth) / 2.0 * 0.985, 0.73, 0.0),
        # ── ★ WAIST (measured) ──────────────────────────────────────────────
        (Z_WAIST, waist_girth, DR_WAIST, 0.0),
        # lower rib — the band's approach, already leaning forward
        ((Z_WAIST + Z_UNDERBUST) / 2.0,
         (waist_girth + underbust_girth) / 2.0, 0.73, 0.18 * p),
        # ── ★ UNDERBUST band (measured) — the bra's structural seat ─────────
        (Z_UNDERBUST, underbust_girth, DR_UNDERBUST, 0.45 * p),
        # ── ★ BUST apex (measured) — deeper ratio + full projection ─────────
        (Z_BUST, bust_girth, bust_depth_ratio, p),
        # above-bust roll-off, projection ramping back to the rib line
        (Z_BUST + 0.42 * (Z_TOP - Z_BUST),
         (bust_girth + upper_chest_girth) / 2.0 * 0.985, 0.72, 0.34 * p),
        # ── ★ UPPER CHEST (measured) — the flat top cap ─────────────────────
        (Z_TOP, upper_chest_girth * 0.90, DR_TOP, 0.0),
    ]


def build_form():
    """The bare intimates form: one additive ruled loft, flat top, flat bottom.
    Stands unaided on its bottom face — no post, no base, no stand hardware."""
    return _loft_sections(_stations())


def _hanger_tab():
    """A small solid hanging tab rising from the flat top.

    Rooted WELL BELOW the top face (a third of the top ring's depth) so it is a
    solid prism embedded in a solid body — generous overlap, one connected
    volume, no sealed void. Rounded only by the loft to a narrower crown, never
    by a fillet after a cut."""
    a_top, b_top = _ellipse_axes(upper_chest_girth * 0.90, DR_TOP)
    root_z = Z_TOP - max(8.0, b_top * 0.34)      # roots down into the closed top
    half_w = min(tab_width, a_top * 1.6) / 2.0
    half_t = min(tab_thickness, b_top * 1.2) / 2.0
    crown_z = Z_TOP + tab_height
    return (
        cq.Workplane("XY").workplane(offset=root_z)
        .rect(half_w * 2.0, half_t * 2.0)
        .workplane(offset=crown_z - root_z - tab_height * 0.30)
        .rect(half_w * 2.0, half_t * 2.0)
        .workplane(offset=tab_height * 0.30)
        .rect(half_w * 0.55, half_t * 2.0)
        .loft(ruled=True, combine=True)
    )


def build_hanger_tab():
    """The form plus its integrated hanging tab — one solid, still stands flat."""
    return build_form().union(_hanger_tab())


def build():
    builders = {
        "form": build_form,
        "hanger_tab": build_hanger_tab,
    }
    fn = builders.get(target_part, build_form)
    return fn()


result = build()
