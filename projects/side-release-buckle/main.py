"""Side-Release Buckle — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The two-part snap buckle every pack strap, sternum strap, dog collar and duffel closure
uses: a male half whose pair of sprung cantilever prongs slide into a female housing and
click out through its side windows when you squeeze them. Sized for the nominal webbing
widths the trade actually sells — 20, 25, 38 and 50 mm. This is the rigid hard good the
Fashion Cabinet `side-release-buckle` notion places and bridges to here for its geometry.

Modes (dispatched via `target_part`):
  * "set"    — male and female halves laid out side by side on one plate.
  * "male"   — the pronged half with its webbing bar.
  * "female" — the housing half with side windows and its webbing bar.

Geometry: both halves start from a rounded slab. The webbing channel is a single slot cut
(the flange edge the tape threads over) with an overshooting cutter. The male prongs are
straight cantilever arms with a lofted catch ramp — flat-topped lofts, never points — and
a generous root land so they flex without a knife edge. The female is a slab hollowed by
one oversized pocket cut opening out the mating end, so no sealed void exists; its side
windows are cut clean through both walls. Every union overlaps; every cutter overshoots.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `webbing_w`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
webbing_w  = float(PARAM(lambda: webbing_w,  25.0))  # nominal webbing width (mm)
webbing_t  = float(PARAM(lambda: webbing_t,  1.6))   # webbing thickness (mm)
body_t     = float(PARAM(lambda: body_t,     8.0))   # buckle body thickness (mm)
wall_t     = float(PARAM(lambda: wall_t,     2.2))   # housing / prong wall thickness (mm)
prong_len  = float(PARAM(lambda: prong_len,  20.0))  # cantilever prong length (mm)
snap_clear = float(PARAM(lambda: snap_clear, 0.35))  # sliding clearance male/female (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|male|female

# ── Safe clamps ──────────────────────────────────────────────────────────────
webbing_w  = max(15.0, min(webbing_w, 50.0))
webbing_t  = max(0.8, min(webbing_t, 4.0))
body_t     = max(5.0, min(body_t, 14.0))
wall_t     = max(1.4, min(wall_t, 4.0))
prong_len  = max(10.0, min(prong_len, 40.0))
snap_clear = max(0.15, min(snap_clear, 0.8))

# The channel must fit inside the body with a floor and a ceiling of real material.
slot_t = min(webbing_t + 0.4, body_t - 2.0 * wall_t)
slot_t = max(0.7, slot_t)

# ── Derived geometry ─────────────────────────────────────────────────────────
# Trade buckles run roughly 1.55x the webbing width across the flats.
outer_w   = webbing_w + 2.0 * wall_t + 4.0        # overall width (Y) of both halves
bar_len   = max(6.0, wall_t * 2.2)                # length (X) of the webbing bar zone
tail_len  = bar_len + 2.0 * wall_t + 2.0          # webbing end block length (X)
corner_r  = min(2.5, wall_t * 1.2)

# Male prong geometry: two arms hugging the outside, a spine down the middle.
prong_w   = max(1.6, wall_t)                      # prong arm thickness in Y
prong_t   = max(1.8, min(wall_t * 1.3, body_t * 0.45))   # prong arm thickness in Z
catch_h   = max(0.9, min(prong_w * 0.9, 2.2))     # how far the catch bump stands proud
catch_len = max(3.0, prong_len * 0.22)            # ramp length along X
gap_y     = prong_w + 1.2                         # squeeze gap each prong needs

# Female housing: interior must swallow the male nose plus running clearance.
nose_w    = outer_w - 2.0 * (wall_t + 0.6)        # male nose width across the arms
cav_w     = nose_w + 2.0 * snap_clear
cav_t     = prong_t + 2.0 * snap_clear
cav_len   = prong_len + 3.0
house_len = cav_len + tail_len


def _rounded_slab(length, width, thick, rad):
    """Rounded-rectangle slab, X = length, Y = width, resting on Z = 0."""
    r = max(0.3, min(rad, min(length, width) / 2.0 - 0.3))
    return (
        cq.Workplane("XY")
        .rect(length, width)
        .extrude(thick)
        .edges("|Z")
        .fillet(r)
    )


def _webbing_slot(x_center, length, thick):
    """The tape channel cutter: overshoots both Y faces so no coincident surfaces."""
    return (
        cq.Workplane("XY")
        .box(length, webbing_w + 20.0, thick)
        .translate((x_center, 0.0, thick / 2.0 + (body_t - thick) / 2.0))
    )


def _tail_block(x0):
    """The webbing end of either half: a rounded slab with the tape slot cut through.

    `x0` is the X coordinate of the block's outboard (far) face; the block runs
    inboard from there toward the mating end.
    """
    blk = _rounded_slab(tail_len, outer_w, body_t, corner_r).translate(
        (x0 - tail_len / 2.0, 0.0, 0.0))
    # One slot, cut clean across the full width: the flange edge the tape threads over.
    slot = _webbing_slot(x0 - tail_len / 2.0, bar_len, slot_t)
    return blk.cut(slot)


def _prong(y_sign):
    """One sprung cantilever arm running +X from the male body's mating face.

    The arm sits on the outside of the nose, and carries a lofted catch ramp near
    its free end. Built from clean blanks only — no fillets after the loft.
    """
    y_out = nose_w / 2.0 - prong_w / 2.0
    z0 = (body_t - prong_t) / 2.0
    arm = (
        cq.Workplane("XY")
        .box(prong_len, prong_w, prong_t)
        .translate((prong_len / 2.0, y_sign * y_out, z0 + prong_t / 2.0))
    )
    # Catch: a loft from the arm's flank out to a proud flat pad and back down, so the
    # ramp leads in on assembly and the square shoulder locks on release.
    cx = prong_len - catch_len - max(1.5, prong_len * 0.10)
    cx = max(catch_len, cx)
    face = "YZ"
    ramp = (
        cq.Workplane(face)
        .workplane(offset=cx)
        .rect(prong_w * 0.5, prong_t * 0.6)
        .workplane(offset=catch_len)
        .rect(prong_w + 2.0 * catch_h, prong_t * 0.95)
        .loft(ruled=True)
        .translate((0.0, y_sign * y_out, z0 + prong_t / 2.0))
    )
    # Square back shoulder behind the ramp so the catch cannot simply slide back out.
    shoulder = (
        cq.Workplane("XY")
        .box(max(1.2, catch_len * 0.35), prong_w + 2.0 * catch_h, prong_t * 0.95)
        .translate((cx + catch_len - 0.3, y_sign * y_out, z0 + prong_t / 2.0))
    )
    return arm.union(ramp).union(shoulder)


def build_male():
    """Webbing tail block + a solid nose plate + two sprung cantilever prongs."""
    # The tail block's inboard face sits at X = 0; the nose grows in +X.
    body = _tail_block(0.0)
    # Nose plate: a flat tongue the female swallows, thinner than the body so it
    # slides inside the cavity. It overlaps the tail block in X for a solid union.
    nose_len = prong_len * 0.55
    z0 = (body_t - prong_t) / 2.0
    nose = (
        cq.Workplane("XY")
        .box(nose_len + 2.0, nose_w - 2.0 * gap_y, prong_t)
        .translate(((nose_len + 2.0) / 2.0 - 2.0, 0.0, z0 + prong_t / 2.0))
    )
    body = body.union(nose)
    # Prong roots overlap the tail block by 2 mm so there is a generous land, not a
    # knife edge, where the arm meets the body.
    root_l = 2.5
    for s in (1.0, -1.0):
        root = (
            cq.Workplane("XY")
            .box(root_l + 2.0, prong_w + 1.0, prong_t + 1.0)
            .translate(((root_l + 2.0) / 2.0 - 2.0,
                        s * (nose_w / 2.0 - prong_w / 2.0),
                        (body_t - (prong_t + 1.0)) / 2.0 + (prong_t + 1.0) / 2.0))
        )
        body = body.union(root).union(_prong(s))
    return body


def build_female():
    """Hollow housing: one open-ended pocket, two side windows, a webbing tail."""
    # The housing runs from X = 0 (mating mouth) to X = house_len (webbing end).
    body = _rounded_slab(house_len, outer_w, body_t, corner_r).translate(
        (house_len / 2.0, 0.0, 0.0))

    # Cavity: opens out through the mouth at X = 0, so it is never a sealed void.
    z0 = (body_t - cav_t) / 2.0
    cavity = (
        cq.Workplane("XY")
        .box(cav_len + 10.0, cav_w, cav_t)
        .translate(((cav_len + 10.0) / 2.0 - 10.0, 0.0, z0 + cav_t / 2.0))
    )
    body = body.cut(cavity)

    # Side windows: the prong catches pop out here. Cut through both side walls,
    # overshooting in Y so nothing is coincident.
    win_len = max(catch_len + 2.0, prong_len * 0.30)
    win_x = prong_len - catch_len - max(1.5, prong_len * 0.10) + catch_len * 0.5
    win_x = max(win_len / 2.0 + 1.0, min(win_x, cav_len - win_len / 2.0 - 1.0))
    for s in (1.0, -1.0):
        win = (
            cq.Workplane("XY")
            .box(win_len, wall_t * 4.0 + 8.0, cav_t + 1.2)
            .translate((win_x, s * (cav_w / 2.0 + wall_t / 2.0 + 2.0),
                        z0 + cav_t / 2.0))
        )
        body = body.cut(win)

    # Webbing slot at the far end.
    tail_center = house_len - tail_len / 2.0
    body = body.cut(_webbing_slot(tail_center, bar_len, slot_t))
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "male":
    result = build_male()
elif target_part == "female":
    result = build_female()
else:
    gap = max(6.0, outer_w * 0.25)
    male = build_male().translate((0.0, outer_w / 2.0 + gap / 2.0, 0.0))
    female = build_female().translate((0.0, -(outer_w / 2.0 + gap / 2.0), 0.0))
    result = cq.Workplane("XY").add(male).add(female)
