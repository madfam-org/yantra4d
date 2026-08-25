"""
Zipper Pull Assist Lever — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A RIGID LEVER adaptive aid for zippers. This is deliberately the other half of a
pair the commons already started: `zipper-loop-aid` clips a finger RING onto the
pull TAB, which helps when the problem is grip area. This cartridge helps when the
problem is FORCE — arthritic hands, weak pinch, one-handed dressing — by clamping
the zipper SLIDER BODY itself and giving the user a lever arm, so the same hand
force produces several times the pull.

The two cartridges therefore take different interfaces on purpose:
  * zipper-loop-aid  → pull-tab C-clip (2 mm slip of metal, `tab_t`/`tab_w`).
  * this cartridge   → slider-BODY clamp (the moulded slider casting, `body_l` ×
                       `body_w` × `body_h`), which is far stiffer than the tab and
                       is the only place a lever can be anchored without bending
                       the tab flat.

Modes are dispatched via `target_part`:
  * "lever"      — the slider-body clamp with a straight lever arm. The workhorse.
  * "t_handle"   — the same clamp under a cross T bar, for a whole-hand grasp when
                   the user cannot close a finger around a lever at all.
  * "tab_shim"   — a shim that fills a slider whose tab has broken off entirely,
                   restoring a pull point on the same body clamp.

Watertightness strategy: every part is one blank with box and cylinder cuts. The
clamp pocket is cut fully through the clamp in Y (opening onto both side faces) so
it traps no void, and its retaining mouth is cut by a box that fully breaches the
outer face. The lever/T/shim are UNIONED onto the clamp with real volumetric
overlap (`WELD` mm buried), never a tangent kiss. Every derived dimension is
clamped so a min-wall / max-body extreme cannot cut the clamp into two arms.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.

CadQuery axis note: an "XZ" workplane extrudes toward -Y, so a length-L extrusion
occupies Y in [-L, 0]. Centring it on Y=0 means translating by +L/2. Getting this
backwards turns a through-bore into a blind pocket that still passes every
watertight and body-count check.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Standard dimensions (mm) ─────────────────────────────────────────────────
# A #5 coil zipper slider body — the common jacket/bag size — measures roughly
# 22 mm long, 11 mm wide and 6 mm tall over the casting. #3 (garment) is smaller,
# #10 (heavy outerwear, luggage) larger; the ranges span that series.
SLIDER_L = 22.0
SLIDER_W = 11.0
SLIDER_H = 6.0


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "lever"))
body_l = float(PARAM(lambda: body_l, SLIDER_L))     # slider body length (mm)
body_w = float(PARAM(lambda: body_w, SLIDER_W))     # slider body width (mm)
body_h = float(PARAM(lambda: body_h, SLIDER_H))     # slider body height (mm)
clamp_clear = float(PARAM(lambda: clamp_clear, 0.4))  # clamp clearance per side (mm)
wall = float(PARAM(lambda: wall, 3.0))              # clamp wall (mm)
retain = float(PARAM(lambda: retain, 0.55))         # retaining mouth, fraction of body_w
lever_len = float(PARAM(lambda: lever_len, 55.0))   # lever arm length (mm)
lever_w = float(PARAM(lambda: lever_w, 9.0))        # lever arm width (mm)
lever_t = float(PARAM(lambda: lever_t, 6.0))        # lever arm thickness (mm)
bar_len = float(PARAM(lambda: bar_len, 42.0))       # T cross-bar length (mm)
bar_dia = float(PARAM(lambda: bar_dia, 12.0))       # T cross-bar Ø (mm)

# ── Clamps: extreme UI values must still build one watertight body ───────────
body_l = max(10.0, min(body_l, 40.0))
body_w = max(5.0, min(body_w, 22.0))
body_h = max(3.0, min(body_h, 14.0))
clamp_clear = max(0.1, min(clamp_clear, 1.0))
wall = max(2.0, min(wall, 6.0))
# Below ~0.30 the mouth is too tight to snap the clamp on at all; above ~0.85
# nothing retains it and the aid falls off the slider in use.
retain = max(0.30, min(retain, 0.85))
lever_len = max(20.0, min(lever_len, 120.0))
lever_w = max(5.0, min(lever_w, 22.0))
lever_t = max(3.0, min(lever_t, 12.0))
bar_len = max(20.0, min(bar_len, 90.0))
bar_dia = max(7.0, min(bar_dia, 25.0))

# ── Derived, clamped ─────────────────────────────────────────────────────────
POCK_L = body_l + 2.0 * clamp_clear       # clamp pocket, along X (slider length)
POCK_W = body_w + 2.0 * clamp_clear       # clamp pocket, along Z (slider width)
CLAMP_X = POCK_L + 2.0 * wall             # clamp outer, X
CLAMP_Z = POCK_W + 2.0 * wall             # clamp outer, Z
CLAMP_Y = max(body_h + 2.0 * clamp_clear, 4.0)   # clamp depth across the slider
MOUTH = max(2.0, min(POCK_W * retain, POCK_W - 1.2))  # retaining mouth opening
WELD = 1.2                                # union overlap so nothing is tangent
OV = 1.0                                  # cutter overshoot past every face


def _clamp():
    """The slider-body clamp: a rounded block with a through pocket in Y and a
    retaining mouth opening toward -X.

    The pocket runs the full Y depth and overshoots both faces, so the slider
    slides in from either side and no void is trapped. The mouth is cut by a box
    that starts outside the -X face, so it always breaches the wall rather than
    stopping flush against it.
    """
    body = cq.Workplane("XY").box(CLAMP_X, CLAMP_Y, CLAMP_Z, centered=(True, True, True))
    try:
        body = body.edges("|Y").fillet(min(wall * 0.7, CLAMP_Z * 0.18, 2.5))
    except Exception:
        pass

    # Pocket for the slider body: through in Y.
    pocket = cq.Workplane("XY").box(
        POCK_L, CLAMP_Y + 2.0 * OV, POCK_W, centered=(True, True, True)
    )
    body = body.cut(pocket)

    # Retaining mouth: opens the pocket to the -X face, narrower than the pocket so
    # a lip survives on both sides and the clamp snaps on rather than falling off.
    mouth = cq.Workplane("XY").box(
        wall + 2.0 * OV, CLAMP_Y + 2.0 * OV, MOUTH, centered=(True, True, True)
    ).translate((-(POCK_L / 2.0 + wall / 2.0), 0, 0))
    body = body.cut(mouth)
    return body


# ── Part builders ─────────────────────────────────────────────────────────────
def build_lever():
    """Slider-body clamp plus a straight lever arm.

    The arm leaves the clamp at +X (opposite the mouth, so pulling the lever seats
    the clamp harder rather than prying it off) and tapers slightly to a rounded
    tip. Mechanical advantage is roughly lever_len / (body_l/2) over pinching the
    tab directly — which is the entire point of the part.
    """
    body = _clamp()

    # Arm: a rounded slab running +X, buried WELD mm into the clamp.
    arm_x0 = CLAMP_X / 2.0 - WELD
    arm = (
        cq.Workplane("XY")
        .box(lever_len + WELD, lever_t, lever_w, centered=(True, True, True))
        .translate((arm_x0 + (lever_len + WELD) / 2.0, 0, 0))
    )
    try:
        arm = arm.edges("|Y").fillet(min(lever_w * 0.3, lever_t * 0.4, 2.0))
    except Exception:
        pass
    body = body.union(arm)

    # Rounded tip so the lever does not dig into a palm.
    tip = (
        cq.Workplane("XZ")
        .center(arm_x0 + lever_len, 0)
        .circle(lever_w / 2.0)
        .extrude(lever_t)
        .translate((0, lever_t / 2.0, 0))
    )
    body = body.union(tip)

    # A finger hole near the tip, but ONLY when the arm is wide enough to keep a
    # real rim on both sides — otherwise the hole would sever the arm.
    hole_r = lever_w * 0.26
    if hole_r >= 2.0 and lever_w - 2.0 * hole_r >= 3.0:
        hole = (
            cq.Workplane("XZ")
            .center(arm_x0 + lever_len - lever_w * 0.15, 0)
            .circle(hole_r)
            .extrude(lever_t + 2.0 * OV)
            .translate((0, lever_t / 2.0 + OV, 0))
        )
        body = body.cut(hole)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_t_handle():
    """Slider-body clamp under a cross T bar, for a whole-hand grasp.

    For a user who cannot close a finger around a lever at all, a T bar can be
    driven with a closed fist or the heel of the hand. The stem is short: the bar
    itself provides the purchase, so a long stem would only add bending moment.
    """
    body = _clamp()

    stem_len = max(6.0, bar_dia * 0.8)
    stem_x0 = CLAMP_X / 2.0 - WELD
    stem_w = max(lever_w, bar_dia * 0.75)
    stem = (
        cq.Workplane("XY")
        .box(stem_len + WELD, min(lever_t, bar_dia), stem_w, centered=(True, True, True))
        .translate((stem_x0 + (stem_len + WELD) / 2.0, 0, 0))
    )
    body = body.union(stem)

    # Cross bar: a cylinder along Z, centred on the stem tip and buried into it,
    # with its two end edges FILLETED to round them off.
    #
    # The ends are deliberately NOT spheres and NOT a revolved capsule profile.
    # Both of those close the surface to a point on the axis — a pole singularity —
    # and OCC tessellates that pole into zero-area facets. The solid still reports
    # as one solid in OCC, and `is_watertight` still passes at the B-Rep level, but
    # the exported mesh carries two degenerate zero-volume shells that trimesh
    # splits off, so `body_count` comes back as 3. Filleting a cylinder's end edge
    # produces the same rounded end with no pole and no degenerate facets.
    bar_cx = stem_x0 + stem_len - WELD * 0.5
    cap_r = bar_dia / 2.0
    bar = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(bar_cx, 0.0, -bar_len / 2.0))
        .circle(cap_r)
        .extrude(bar_len)
    )
    # Fillet radius is capped below the bar radius and below half its length so a
    # degenerate fillet can never consume the whole end face.
    end_r = min(cap_r * 0.85, bar_len * 0.45)
    try:
        bar = bar.edges(">Z or <Z").fillet(end_r)
    except Exception:
        pass
    body = body.union(bar)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_tab_shim():
    """A pull point for a slider whose tab has broken off entirely.

    Same body clamp, but instead of a lever it carries a flat blade with a
    generous eye, so a cord, split ring or the zipper-loop-aid ring can be
    attached. This is the repair case rather than the leverage case.
    """
    body = _clamp()

    blade_len = max(12.0, min(lever_len * 0.45, 40.0))
    blade_w = max(lever_w, 8.0)
    blade_t = max(lever_t * 0.6, 2.5)
    blade_x0 = CLAMP_X / 2.0 - WELD
    blade = (
        cq.Workplane("XY")
        .box(blade_len + WELD, blade_t, blade_w, centered=(True, True, True))
        .translate((blade_x0 + (blade_len + WELD) / 2.0, 0, 0))
    )
    try:
        blade = blade.edges("|Y").fillet(min(blade_w * 0.3, blade_t * 0.4, 2.0))
    except Exception:
        pass
    body = body.union(blade)

    # Rounded end.
    end = (
        cq.Workplane("XZ")
        .center(blade_x0 + blade_len, 0)
        .circle(blade_w / 2.0)
        .extrude(blade_t)
        .translate((0, blade_t / 2.0, 0))
    )
    body = body.union(end)

    # The eye. Radius is chosen so a real rim survives on every side; if the blade
    # is too narrow for that, the eye is simply omitted rather than severing it.
    eye_r = blade_w * 0.24
    if eye_r >= 1.6 and blade_w - 2.0 * eye_r >= 3.0:
        eye = (
            cq.Workplane("XZ")
            .center(blade_x0 + blade_len - blade_w * 0.1, 0)
            .circle(eye_r)
            .extrude(blade_t + 2.0 * OV)
            .translate((0, blade_t / 2.0 + OV, 0))
        )
        body = body.cut(eye)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "t_handle":
    result = build_t_handle()
elif target_part == "tab_shim":
    result = build_tab_shim()
else:
    result = build_lever()
