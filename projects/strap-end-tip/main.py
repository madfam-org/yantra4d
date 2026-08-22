"""Strap End Tip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The metal cap crimped or riveted onto the raw end of a leather strap or a length of
webbing: it stops the end fraying, gives the strap a finished silhouette, and on a belt it
is the piece that leads the tongue through the keeper. This is the rigid hard good the
Fashion Cabinet `strap-end-tip` notion places and bridges to here for its geometry.

The strap slides into a channel that runs the full width of the tip — a flange-style edge
interface, sized directly by `strap_w` and `strap_t`, which is why Fashion Cabinet can
couple a garment's finished strap dimension straight to this object.

Modes (dispatched via `target_part`):
  * "rounded"  — a semicircular nose (the belt-tip standard).
  * "pointed"  — a V nose (English point, the dress-belt standard).
  * "square"   — a square nose with softened corners (webbing / utility strap).

Geometry: a rounded slab body, the nose profile swept as a plan outline, the strap channel
cut as an oversized slot open at the back face (never a sealed void), and the rivet bores
cut clean through in one pushPoints operation. No fillet or chamfer follows any cut.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `strap_w`).
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
strap_w    = float(PARAM(lambda: strap_w,    25.0))  # finished strap / webbing width (mm)
strap_t    = float(PARAM(lambda: strap_t,     3.0))  # strap thickness the channel takes (mm)
wall_t     = float(PARAM(lambda: wall_t,      1.6))  # tip wall around the channel (mm)
tip_len    = float(PARAM(lambda: tip_len,    26.0))  # overall tip length (mm)
nose_len   = float(PARAM(lambda: nose_len,   14.0))  # how much of that length is the nose (mm)
rivet_dia  = float(PARAM(lambda: rivet_dia,   3.0))  # rivet bore diameter (mm)
rivets     = int(  PARAM(lambda: rivets,      2))    # rivet bores across the strap

target_part = str(PARAM(lambda: target_part, "rounded"))  # rounded|pointed|square

# ── Safe clamps ──────────────────────────────────────────────────────────────
# Webbing is sold in nominal 20 / 25 / 38 / 50 mm widths; belt leather runs 25-45 mm.
strap_w   = max(10.0, min(strap_w, 75.0))
# Garment leather 1.2-2 mm, belt veg-tan 3-4.5 mm, seatbelt webbing about 1.2 mm.
strap_t   = max(0.8, min(strap_t, 8.0))
wall_t    = max(1.0, min(wall_t, 4.0))
tip_len   = max(strap_w * 0.5, min(tip_len, strap_w * 3.0))
# The nose can never swallow the whole tip: leave a shank long enough to rivet through.
nose_len  = max(2.0, min(nose_len, tip_len - rivet_dia - 4.0))
rivet_dia = max(1.5, min(rivet_dia, min(5.0, strap_w * 0.25)))
rivets    = max(1, min(rivets, 3))

# ── Derived geometry ─────────────────────────────────────────────────────────
chan_w = strap_w + 0.6                 # channel width: strap plus a slip allowance
chan_t = strap_t + 0.4                 # channel height: strap plus a slip allowance
body_w = chan_w + 2.0 * wall_t         # tip outside width
body_t = chan_t + 2.0 * wall_t         # tip outside thickness
shank_len = tip_len - nose_len         # the straight riveted portion
# The channel stops short of the nose so the strap end butts against solid material.
chan_depth = shank_len + min(nose_len * 0.35, 4.0)
corner_r = min(wall_t * 0.8, body_t * 0.25)


def _nose_plan(kind):
    """The tip outline in plan (XY): shank rectangle plus the chosen nose.

    X runs along the strap (0 at the open back face, +X toward the nose tip);
    Y runs across the strap width.
    """
    hw = body_w / 2.0
    if kind == "pointed":
        # English point: straight sides, then a V.
        return (
            cq.Workplane("XY")
            .moveTo(0, -hw)
            .lineTo(shank_len, -hw)
            .lineTo(tip_len, 0)
            .lineTo(shank_len, hw)
            .lineTo(0, hw)
            .close()
        )
    if kind == "square":
        # Square nose: a plain rectangle; its corners get rounded on the clean blank.
        return (
            cq.Workplane("XY")
            .moveTo(0, -hw)
            .lineTo(tip_len, -hw)
            .lineTo(tip_len, hw)
            .lineTo(0, hw)
            .close()
        )
    # rounded: straight sides then a semicircular nose of radius hw. Built with
    # threePointArc — a radiusArc across a full diameter is degenerate (in verification
    # it collapsed the outline to a sliver), while threePointArc is unambiguous.
    return (
        cq.Workplane("XY")
        .moveTo(0, -hw)
        .lineTo(tip_len - hw, -hw)
        .threePointArc((tip_len, 0), (tip_len - hw, hw))
        .lineTo(0, hw)
        .close()
    )


def _rivet_points():
    """Rivet-bore centres across the strap, on the shank, clear of the channel end."""
    x = max(rivet_dia * 0.8 + 1.0, shank_len * 0.5)
    x = min(x, shank_len - rivet_dia / 2.0 - 1.0) if shank_len > rivet_dia + 2.0 else x
    if rivets == 1:
        return [(x, 0.0)]
    span = min(chan_w - rivet_dia - 2.0, chan_w * 0.7)
    step = span / (rivets - 1)
    return [(x, -span / 2.0 + i * step) for i in range(rivets)]


def build_tip(kind):
    """Solid nose tip with the strap channel cut in from the back face."""
    # Body: extrude the plan outline through the tip thickness, sitting on Z=0.
    body = _nose_plan(kind).extrude(body_t)
    if kind == "square":
        try:
            body = body.edges("|Z").fillet(min(body_w * 0.18, body_t * 0.9))
        except Exception:
            pass
    # Soften the top and bottom long edges on the CLEAN BLANK, before any cut.
    try:
        body = body.edges("|X").fillet(corner_r)
    except Exception:
        pass

    # Strap channel: an open-ended slot cut in from the back face (X = 0). The cutter
    # overshoots past X = 0 so the slot genuinely opens — never a sealed internal void.
    channel = (
        cq.Workplane("XY")
        .box(chan_depth + 4.0, chan_w, chan_t)
        .translate(((chan_depth + 4.0) / 2.0 - 4.0, 0, body_t / 2.0))
    )
    body = body.cut(channel)

    # Rivet bores: one operation, cutter overshoots both faces.
    bores = (
        cq.Workplane("XY")
        .pushPoints(_rivet_points())
        .circle(rivet_dia / 2.0)
        .extrude(body_t + 4.0)
        .translate((0, 0, -2.0))
    )
    return body.cut(bores)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pointed":
    result = build_tip("pointed")
elif target_part == "square":
    result = build_tip("square")
else:
    result = build_tip("rounded")
