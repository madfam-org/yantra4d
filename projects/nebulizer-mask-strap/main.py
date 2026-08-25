"""
Nebulizer Mask Strap Buckle — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Head-strap hardware for a nebulizer or aerosol mask. A nebulizer mask ships with a
thin elastic loop swaged into two staples; when the elastic perishes (and it does,
because it lives in a warm humid airstream and gets washed) the mask is usually
thrown away with it. These parts let a carer re-strap the same mask with ordinary
webbing and adjust it without re-tying a knot behind a patient's head.

The webbing interface is deliberately NOT new. It is the same 20/25 mm nominal
webbing slot the wearables closures wave published (strap-buckle, tri-glide-slider,
ladder-lock): slot width = webbing nominal + clearance, slot height = webbing
thickness + clearance, and a rail bar the strap wraps. Anything that already fits
those cartridges fits these.

Modes are dispatched via `target_part`:
  * "tri_slide"  — a three-bar length adjuster: the strap goes over the first bar,
                   under the centre bar, back over the third, and friction on the
                   centre bar holds the setting. This is the adjuster.
  * "mask_hook"  — a hook that captures the mask's moulded strap staple on one end
                   and carries a webbing slot on the other, so webbing replaces the
                   original elastic without modifying the mask.
  * "split_yoke" — a Y yoke that takes one webbing tail at the back of the head and
                   splits it into two, so a single adjuster drives both mask ears.

Watertightness strategy: every part is a rounded slab with rectangular slots cut
straight through. Slots are cut with oversized cutters that pass fully through both
faces (never stopping flush) so no cut ever leaves a coplanar zero-thickness face.
Bars between slots are floored at a real minimum so a wide-webbing / thick-webbing
extreme cannot thin a bar to nothing and split the frame into two bodies.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Published webbing interface (mm) ─────────────────────────────────────────
# Same nominal series as the wearables closures wave. Nominal webbing is woven a
# little narrow, so a slot at nominal + clearance is the correct fit, not tight.
WEBBING = {"20mm": 20.0, "25mm": 25.0}


def webbing_mm(name):
    return WEBBING.get(name, WEBBING["25mm"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "tri_slide"))
webbing = str(PARAM(lambda: webbing, "25mm"))          # nominal webbing width
web_t = float(PARAM(lambda: web_t, 1.6))               # webbing thickness (mm)
slot_clear = float(PARAM(lambda: slot_clear, 0.6))     # slot clearance per axis (mm)
bar_w = float(PARAM(lambda: bar_w, 4.0))               # bar width between slots (mm)
frame_t = float(PARAM(lambda: frame_t, 4.0))           # frame slab thickness (mm)
rail_t = float(PARAM(lambda: rail_t, 3.2))             # outer rail thickness (mm)
staple_w = float(PARAM(lambda: staple_w, 12.0))        # mask strap staple width (mm)
staple_t = float(PARAM(lambda: staple_t, 3.0))         # mask strap staple bar thickness (mm)
yoke_angle = float(PARAM(lambda: yoke_angle, 35.0))    # yoke split half-angle (deg)

# ── Clamps: extreme UI values must still build one watertight body ───────────
web_t = max(0.8, min(web_t, 4.0))
slot_clear = max(0.2, min(slot_clear, 1.2))
# A bar thinner than ~2 mm is two perimeters of plastic across a strap that
# carries a mask against a face; it snaps. A bar wider than the strap is not a
# bar any more. Both ends clamped.
bar_w = max(2.0, min(bar_w, 10.0))
frame_t = max(2.5, min(frame_t, 9.0))
rail_t = max(2.0, min(rail_t, 7.0))
staple_w = max(6.0, min(staple_w, 26.0))
staple_t = max(1.5, min(staple_t, 8.0))
yoke_angle = max(15.0, min(yoke_angle, 60.0))

# ── Derived, clamped ─────────────────────────────────────────────────────────
WEB_W = webbing_mm(webbing)
slot_w = WEB_W + slot_clear              # slot width, along the bar
slot_h = web_t + slot_clear              # slot height, through the frame
# The frame must be thicker than the slot it carries or the slot severs the slab.
frame_t = max(frame_t, slot_h + 1.6)
rail_t = max(rail_t, 1.6)
OV = 1.0                                 # cutter overshoot past every face


def _rounded_slab(x, y, z, rad):
    """Rounded-rect slab centred on the origin in XY, sitting on z=0.

    Fillet radius is floored and capped against the slab so a degenerate radius
    never throws (a thrown fillet would leave the caller with a half-built shape).
    """
    r = max(0.4, min(rad, min(x, y) / 2.0 - 0.4))
    w = cq.Workplane("XY").box(x, y, z, centered=(True, True, False))
    try:
        w = w.edges("|Z").fillet(r)
    except Exception:
        pass
    return w


def _through_slot(cx, cy, w, h, span):
    """A rectangular cutter of w (X) by h (Z), running the full `span` in Y and
    overshooting both Y faces, centred at (cx, cy) with its Z centre at cy_z=h/2
    handled by the caller's translate. Used to cut strap slots clean through."""
    return (
        cq.Workplane("XY")
        .box(w, span + 2.0 * OV, h, centered=(True, True, False))
        .translate((cx, 0, cy))
    )


# ── Part builders ─────────────────────────────────────────────────────────────
def build_tri_slide():
    """Three-bar friction adjuster.

    Layout along X: rail | slot | bar | slot | rail. The strap passes over the
    first rail, down through slot 1, under the centre bar, up through slot 2 and
    back over the far rail; the load pinches it against the centre bar.
    """
    # Overall X = two outer rails + two slots + one centre bar.
    x = 2.0 * rail_t + 2.0 * slot_w + bar_w
    y = WEB_W + 2.0 * rail_t          # frame depth across the strap
    z = frame_t

    body = _rounded_slab(x, y, z, min(rail_t, frame_t) * 0.8)

    # Slot centres: symmetric about X=0, one on each side of the centre bar.
    off = (bar_w + slot_w) / 2.0
    for cx in (-off, off):
        body = body.cut(_through_slot(cx, (z - slot_h) / 2.0, slot_w, slot_h, y))

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_mask_hook():
    """Mask-staple hook + webbing slot.

    One end is a C hook whose throat clears the mask's moulded strap staple bar;
    the other end is the published webbing slot. The hook opening faces -X so the
    part is pushed onto the staple and the strap tension pulls it closed.
    """
    # Hook throat must clear the staple bar in both directions.
    throat_w = staple_w + slot_clear
    throat_h = staple_t + slot_clear
    hook_len = throat_w + 2.0 * rail_t
    slot_len = slot_w + 2.0 * rail_t

    x = hook_len + slot_len
    y = max(WEB_W, staple_w) + 2.0 * rail_t
    z = max(frame_t, throat_h + 2.0 * rail_t)

    body = _rounded_slab(x, y, z, min(rail_t, z) * 0.8)

    # Webbing slot at the +X end.
    slot_cx = x / 2.0 - slot_len / 2.0
    body = body.cut(_through_slot(slot_cx, (z - slot_h) / 2.0, slot_w, slot_h, y))

    # Staple throat at the -X end: a through pocket …
    throat_cx = -x / 2.0 + hook_len / 2.0
    body = body.cut(_through_slot(throat_cx, (z - throat_h) / 2.0, throat_w, throat_h, y))
    # … opened to the -X face by a mouth narrower than the throat, so the staple
    # snaps in and is retained. The mouth is floored so it never closes to zero
    # (a zero mouth is just a closed pocket, still watertight but not a hook) and
    # capped below the throat so a retaining lip always survives.
    mouth_h = max(1.2, min(throat_h * 0.62, throat_h - 0.8))
    # The mouth spans from OV outside the -X face to the throat centre, so it
    # definitely breaches the outer wall and definitely lands inside the pocket.
    mouth_x0 = -x / 2.0 - OV
    mouth_x1 = throat_cx
    mouth_len = mouth_x1 - mouth_x0
    mouth = (
        cq.Workplane("XY")
        .box(mouth_len, y + 2.0 * OV, mouth_h, centered=(True, True, False))
        .translate(((mouth_x0 + mouth_x1) / 2.0, 0, (z - mouth_h) / 2.0))
    )
    body = body.cut(mouth)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_split_yoke():
    """Y yoke: one webbing slot at the stem, two at the arms.

    A single adjuster at the back of the head drives one strap into the stem slot;
    the two arm slots feed the left and right mask ears. Built as a union of three
    overlapping rounded slabs (never tangent) so it is one solid.
    """
    ang = math.radians(yoke_angle)
    slot_len = slot_w + 2.0 * rail_t
    arm_len = slot_len + 2.0 * rail_t + WEB_W * 0.5
    stem_len = slot_len + 2.0 * rail_t
    y_body = WEB_W + 2.0 * rail_t
    z = frame_t

    # Hub: a slab large enough that both arm roots and the stem root are buried
    # inside it, so the union has real volumetric overlap everywhere.
    hub_x = y_body * 1.15 + WEB_W * math.sin(ang)
    hub_y = y_body * 1.15 + WEB_W * math.sin(ang)
    body = _rounded_slab(hub_x, hub_y, z, min(rail_t, z) * 0.8)

    # Stem runs -X from the hub and carries the single (input) slot.
    stem = _rounded_slab(stem_len + hub_x * 0.6, y_body, z, min(rail_t, z) * 0.8)
    stem_cx = -(stem_len + hub_x * 0.6) / 2.0 + hub_x * 0.30
    stem = stem.translate((stem_cx, 0, 0))
    body = body.union(stem)
    stem_slot_cx = stem_cx - (stem_len + hub_x * 0.6) / 2.0 + slot_len / 2.0 + rail_t
    body = body.cut(_through_slot(stem_slot_cx, (z - slot_h) / 2.0, slot_w, slot_h, y_body))

    # Two arms fan out toward +X at ±yoke_angle.
    for sign in (1.0, -1.0):
        arm = _rounded_slab(arm_len + hub_x * 0.6, y_body, z, min(rail_t, z) * 0.8)
        arm = arm.translate(((arm_len + hub_x * 0.6) / 2.0 - hub_x * 0.30, 0, 0))
        arm = arm.rotate((0, 0, 0), (0, 0, 1), sign * yoke_angle)
        body = body.union(arm)

        # Slot near the arm tip, cut in the ARM's own frame then rotated with it.
        sx = (arm_len + hub_x * 0.6) - hub_x * 0.30 - slot_len / 2.0 - rail_t
        cutter = _through_slot(sx, (z - slot_h) / 2.0, slot_w, slot_h, y_body)
        cutter = cutter.rotate((0, 0, 0), (0, 0, 1), sign * yoke_angle)
        body = body.cut(cutter)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "mask_hook":
    result = build_mask_hook()
elif target_part == "split_yoke":
    result = build_split_yoke()
else:
    result = build_tri_slide()
