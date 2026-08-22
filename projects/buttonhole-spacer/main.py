"""Buttonhole Spacer — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The buttonhole spacing gauge: the tool that divides a placket into equal button intervals
so a shirt front does not end up with a gap that gapes across the bust. The classic version
is a scissoring lazy-tongs expander — a joint-heavy mechanism that prints badly. This is the
printable equivalent: a graduated RAIL and a SLIDER that rides it, detented at the common
garment pitches, so the maker sets one interval and steps it down the placket.

Modes (dispatched via `target_part`):
  * "rail"   — the graduated rail alone.
  * "slider" — the sliding marker alone.
  * "set"    — rail and slider laid out together for one plate.

Geometry: the rail is a flat bar with a dovetailed track along its top and a row of detent
notches at `pitch` intervals; the slider is a C-shaped shuttle whose dovetail lips capture
the track, with a compliant detent tongue (generous land, no knife edges) and a marking
notch. Both print flat. The slider's throat is open at both ends, so it threads onto the
rail from either end — nothing is a sealed void.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `rail_len`).
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
rail_len   = float(PARAM(lambda: rail_len,   240.0))  # rail length (mm)
rail_w     = float(PARAM(lambda: rail_w,     20.0))   # rail width (mm)
rail_t     = float(PARAM(lambda: rail_t,     6.0))    # rail thickness (mm)
pitch      = float(PARAM(lambda: pitch,      20.0))   # detent pitch — the button interval (mm)
track_w    = float(PARAM(lambda: track_w,    9.0))    # dovetail track width at its throat (mm)
slide_clr  = float(PARAM(lambda: slide_clr,  0.35))   # running clearance, rail to slider (mm)
slider_len = float(PARAM(lambda: slider_len, 22.0))   # slider length along the rail (mm)

target_part = str(PARAM(lambda: target_part, "rail"))  # rail|slider|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
rail_len   = max(80.0, min(rail_len, 400.0))
rail_w     = max(12.0, min(rail_w, 40.0))
rail_t     = max(4.0, min(rail_t, 12.0))
pitch      = max(8.0, min(pitch, 60.0))
track_w    = max(5.0, min(track_w, rail_w - 6.0))
slide_clr  = max(0.15, min(slide_clr, 0.8))
slider_len = max(10.0, min(slider_len, 50.0))

TRACK_D = min(rail_t * 0.5, 3.5)          # dovetail depth
FLARE = TRACK_D * 0.55                    # dovetail flare per side (the undercut)
DETENT_R = 1.2                            # detent notch radius


def build_rail():
    """Flat bar, dovetail track cut along its length, detent notches at every `pitch`."""
    bar = cq.Workplane("XY").box(rail_w, rail_len, rail_t,
                                 centered=(True, True, False))

    # Dovetail track: a trapezoid cut, WIDER at depth than at the mouth, so the slider's
    # lips are captured. Cut as a prism swept the full length, overshooting both ends.
    half_mouth = track_w / 2.0
    half_deep = track_w / 2.0 + FLARE
    z0 = rail_t - TRACK_D
    prof = [
        (-half_mouth, rail_t + 1.0),
        (half_mouth, rail_t + 1.0),
        (half_mouth, rail_t),
        (half_deep, z0),
        (-half_deep, z0),
        (-half_mouth, rail_t),
    ]
    track = (
        cq.Workplane("XZ")
        .polyline(prof)
        .close()
        .extrude(rail_len + 4.0)
        .translate((0, rail_len / 2.0 + 2.0, 0))
    )
    bar = bar.cut(track)

    # Detent notches: shallow scallops down BOTH shoulders of the track, spaced at `pitch`.
    # These are the graduations the maker reads and the slider's tongue clicks into.
    n = int(rail_len / pitch)
    cutters = []
    for i in range(n + 1):
        y = -rail_len / 2.0 + pitch * i
        if abs(y) > rail_len / 2.0 - 2.0:
            continue
        for sx in (-1.0, 1.0):
            cutters.append(
                cq.Solid.makeCylinder(
                    DETENT_R, TRACK_D + 2.0,
                    cq.Vector(sx * (half_deep - DETENT_R * 0.35), y, z0 - 1.0),
                    cq.Vector(0, 0, 1)))
    if cutters:
        bar = bar.cut(cq.Workplane(obj=cq.Compound.makeCompound(cutters)))

    # Read-off window: a slot through the rail at the head end, so the maker can mark the
    # placket edge through the tool. Through-cut, opens on both faces.
    win = (
        cq.Workplane("XY")
        .box(2.4, 16.0, rail_t + 4.0, centered=(True, True, False))
        .translate((rail_w / 2.0 - 3.5, -rail_len / 2.0 + 14.0, -2.0))
    )
    bar = bar.cut(win)
    return bar


def build_slider():
    """A C-shaped shuttle: a body with a dovetail-shaped male key that rides the track,
    the throat open at both ends, plus a marking notch and a compliant detent tongue."""
    half_mouth = track_w / 2.0
    half_deep = track_w / 2.0 + FLARE
    body_w = rail_w + 5.0
    body_t = 5.0                                  # slider deck above the rail

    deck = cq.Workplane("XY").box(body_w, slider_len, body_t,
                                  centered=(True, True, False))

    # Male dovetail key hanging under the deck, a running fit inside the rail's track.
    key_h = TRACK_D - slide_clr
    prof = [
        (-(half_mouth - slide_clr), 0.02),        # 0.02 overlap into the deck — no seam
        ((half_mouth - slide_clr), 0.02),
        ((half_deep - slide_clr), -key_h),
        (-(half_deep - slide_clr), -key_h),
    ]
    key = (
        cq.Workplane("XZ")
        .polyline(prof)
        .close()
        .extrude(slider_len)
        .translate((0, slider_len / 2.0, 0))
    )
    slider = deck.union(key)

    # Detent tongue: a compliant finger cut free of the deck on three sides, carrying a
    # bump that drops into the rail's notches. Generous land — no knife edges.
    land = max(body_t * 0.45, 1.2)
    slot_w = 1.6
    arm_w = max(track_w * 0.55, 4.0)
    for sx in (-1.0, 1.0):
        relief = (
            cq.Workplane("XY")
            .box(slot_w, slider_len * 0.7, body_t + 2.0, centered=(True, True, False))
            .translate((sx * (arm_w / 2.0 + slot_w / 2.0), 0, -1.0))
        )
        slider = slider.cut(relief)
    # Thin the tongue to `land` from above so it can flex, opening upward (drains).
    thin = (
        cq.Workplane("XY")
        .box(arm_w, slider_len * 0.7, body_t + 2.0, centered=(True, True, False))
        .translate((0, 0, land))
    )
    slider = slider.cut(thin)

    # Marking notch: a V cut through the deck's front edge, the line the maker pencils.
    notch = (
        cq.Workplane("XY")
        .polyline([(-2.2, 0.0), (2.2, 0.0), (0.0, 5.0)])
        .close()
        .extrude(body_t + 4.0)
        .translate((0, -slider_len / 2.0 - 0.5, -2.0))
    )
    slider = slider.cut(notch)

    # Finger grips: shallow flutes on the deck sides, cut from a clean deck face.
    for sx in (-1.0, 1.0):
        flute = cq.Solid.makeCylinder(
            2.0, slider_len + 4.0,
            cq.Vector(sx * (body_w / 2.0 + 1.2), -slider_len / 2.0 - 2.0, body_t * 0.55),
            cq.Vector(0, 1, 0))
        slider = slider.cut(cq.Workplane(obj=flute))
    return slider


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "slider":
    result = build_slider()
elif target_part == "set":
    # Rail and slider are separate pieces — COMPOUND, never .union() across a gap.
    r = build_rail()
    s = build_slider().translate((rail_w + 12.0, 0, 0))
    result = cq.Workplane(obj=cq.Compound.makeCompound(
        r.solids().vals() + s.solids().vals()))
else:
    result = build_rail()
