"""
Drip-Irrigation Fitting — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Barbed fittings for drip-irrigation tubing: straight couplers, tees, elbows, and
end caps. The functional interface is a series of tapered barbs sized to the tubing
INNER diameter — they push into the tube and grip from inside so pressurized water
does not blow the joint apart. Sized for the two common drip tubes: 1/4" (~6 mm ID)
and 1/2" (~16 mm ID).

Design idiom (shared barb helper):
  `barb_spigot()` builds ONE barbed prong: a solid column of length `prong_len`
  with `barb_count` tapered ridges (each ridge flares to tube_id then steps back).
  A straight coupler puts two prongs back-to-back through a collar; a tee adds a
  third prong at 90°; an elbow bends the second prong; an end cap keeps one prong
  and closes the far end. Prongs overlap into a solid collar so booleans stay
  volumetric and the mesh is watertight. A through-channel is bored last (except the
  end cap, which is bored only through its single prong).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `tube_id`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(  PARAM(lambda: target_part, "straight"))  # straight | tee | elbow_cap
tube_id     = float(PARAM(lambda: tube_id,      6.0))         # tubing inner diameter (mm); 1/4"≈6, 1/2"≈16
fitting     = str(  PARAM(lambda: fitting,     "straight"))   # straight | tee | elbow | end_cap
barb_count  = int(  PARAM(lambda: barb_count,     3))         # ridges per prong
prong_len   = float(PARAM(lambda: prong_len,   14.0))         # insertion length per prong (mm)
wall        = float(PARAM(lambda: wall,         1.4))         # prong / collar wall thickness (mm)
grip        = float(PARAM(lambda: grip,         0.5))         # barb over-size beyond tube_id (mm, radial)

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
tube_id = max(3.0, min(tube_id, 24.0))
barb_count = max(1, min(barb_count, 6))
prong_len = max(6.0, min(prong_len, 40.0))
wall = max(0.8, min(wall, 3.0))
grip = max(0.1, min(grip, 1.5))

# Barb geometry: shaft slips inside the tube, ridges flare to tube_id + grip.
shaft_r = max(1.0, tube_id / 2.0 - 0.3)     # bare shaft radius (slides in)
ridge_r = tube_id / 2.0 + grip               # ridge crest (grips tube wall)
chan_r = max(0.8, shaft_r - wall)            # fluid channel radius
collar_r = ridge_r + wall + 0.8              # central collar outer radius


# ── Shared barb helper ────────────────────────────────────────────────────────
def barb_spigot(length, collar_bury):
    """One barbed prong along +Z, base at z=0, extending to +length. `collar_bury`
    adds solid length below z=0 so the prong roots inside the collar (volumetric
    union). Ridges are lofted cones: shaft_r → ridge_r → shaft_r, repeated."""
    ridge_h = max(2.5, length / (barb_count + 0.6))
    body = cq.Workplane("XY").circle(shaft_r).extrude(length + collar_bury).translate((0, 0, -collar_bury))
    z = length - ridge_h
    for _ in range(barb_count):
        if z < 0.2:
            z = 0.2
        ring = (
            cq.Workplane("XY")
            .circle(shaft_r)
            .workplane(offset=ridge_h * 0.7)
            .circle(ridge_r)
            .workplane(offset=ridge_h * 0.3)
            .circle(shaft_r)
            .loft(combine=True)
            .translate((0, 0, z))
        )
        body = body.union(ring)
        z -= ridge_h
    return body


def collar(height, z0):
    """Central collar cylinder spanning [z0, z0+height]."""
    return cq.Workplane("XY").circle(collar_r).extrude(height).translate((0, 0, z0))


# ── Part builders ─────────────────────────────────────────────────────────────
def build_straight():
    """Straight barbed coupler: two prongs pointing opposite ways from a short
    collar, one fluid channel through both."""
    ch = max(3.0, collar_r * 0.5)   # collar height
    # Top prong up from top of collar; bottom prong down from bottom of collar.
    top = barb_spigot(prong_len, collar_r).translate((0, 0, ch))
    bot = barb_spigot(prong_len, collar_r).rotate((0, 0, 0), (1, 0, 0), 180)
    mid = collar(ch, 0.0)
    body = mid.union(top).union(bot)
    # Channel through the whole length.
    total_lo = -prong_len - 1.0
    total_hi = ch + prong_len + 1.0
    chan = cq.Workplane("XY").circle(chan_r).extrude(total_hi - total_lo).translate((0, 0, total_lo))
    body = body.cut(chan)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_tee():
    """Tee: a straight run of two collinear prongs plus a side prong at 90°.
    Cross-shaped channel joins all three."""
    ch = max(4.0, collar_r * 0.7)
    mid_z = ch / 2.0
    top = barb_spigot(prong_len, collar_r).translate((0, 0, ch))
    bot = barb_spigot(prong_len, collar_r).rotate((0, 0, 0), (1, 0, 0), 180)
    side = (
        barb_spigot(prong_len, collar_r)
        .rotate((0, 0, 0), (0, 1, 0), 90.0)
        .translate((0, 0, mid_z))
    )
    body = collar(ch, 0.0).union(top).union(bot).union(side)

    # Vertical run channel.
    v_lo = -prong_len - 1.0
    v_hi = ch + prong_len + 1.0
    vchan = cq.Workplane("XY").circle(chan_r).extrude(v_hi - v_lo).translate((0, 0, v_lo))
    body = body.cut(vchan)
    # Side channel along +X into the run.
    reach = prong_len + collar_r + 2.0
    schan = (
        cq.Workplane("XY")
        .circle(chan_r)
        .extrude(reach)
        .translate((0, 0, -collar_r))
        .rotate((0, 0, 0), (0, 1, 0), 90.0)
        .translate((0, 0, mid_z))
    )
    body = body.cut(schan)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_elbow():
    """90° elbow: two prongs meeting at a corner hub. A sphere fuses the legs so the
    bend is one watertight solid; each channel is bored along its own leg axis."""
    leg1 = barb_spigot(prong_len, collar_r)                     # up +Z from origin
    leg2 = (
        barb_spigot(prong_len, collar_r)
        .rotate((0, 0, 0), (0, 1, 0), 90.0)                     # along +X
    )
    hub = cq.Workplane("XY").sphere(collar_r)
    body = hub.union(leg1).union(leg2)

    reach = prong_len + collar_r + 2.0
    c1 = cq.Workplane("XY").circle(chan_r).extrude(reach).translate((0, 0, -collar_r))
    c2 = (
        cq.Workplane("XY")
        .circle(chan_r)
        .extrude(reach)
        .translate((0, 0, -collar_r))
        .rotate((0, 0, 0), (0, 1, 0), 90.0)
    )
    body = body.cut(c1).cut(c2)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_end_cap():
    """End cap: one barbed prong plus a closed dome, sealing the end of a tube run."""
    ch = max(3.0, collar_r * 0.6)
    prong = barb_spigot(prong_len, collar_r).translate((0, 0, ch))
    # Closed base: collar with a solid floor (no through channel past the collar).
    base = collar(ch, 0.0)
    body = base.union(prong)
    # Channel only through the prong + into the collar, stopping at a floor.
    floor = max(1.6, wall + 0.6)
    chan = (
        cq.Workplane("XY")
        .circle(chan_r)
        .extrude(prong_len + ch)
        .translate((0, 0, floor))
    )
    body = body.cut(chan)
    # Round the closed bottom for comfort.
    try:
        body = body.edges("<Z").fillet(min(collar_r * 0.3, 1.5))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
# `fitting` is the user-facing selector; `target_part` is the mode/part id the
# platform renders. The "elbow_cap" part shows either an elbow or an end cap.
if target_part == "tee" or fitting == "tee":
    result = build_tee()
elif target_part == "elbow_cap":
    result = build_end_cap() if fitting == "end_cap" else build_elbow()
elif fitting == "elbow":
    result = build_elbow()
elif fitting == "end_cap":
    result = build_end_cap()
else:
    result = build_straight()
