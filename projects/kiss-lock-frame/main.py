"""Kiss-Lock Frame — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The simplified printable purse frame: two mirror-image half-frames that meet at a
ball-clasp kiss and pivot on a pin-bore hinge at each end. Along the bottom of every
half-frame runs the sew channel — the open flange groove the purse fabric is folded
into and glued or whip-stitched through, exactly as a metal kiss-lock frame is set.
This is the rigid hard good the Fashion Cabinet `kiss-lock-frame` notion places and
bridges to here for its geometry; the FC side owns the gusset pattern and the finished
mouth width, this side owns the hardware.

Modes (dispatched via `target_part`):
  * "half_frame" — one half-frame (either half of the pair; they are mirror-identical).
  * "set"        — both half-frames, hinged ends together, as a two-body print plate.

Geometry: a half-frame is a rounded-corner U profile extruded as a rectangular rod
(a rounded slab minus an oversized rounded slab, then the top half cut away so only
the arch survives). The sew channel is a slot cut up into the underside of the arch
along its whole run. Each end carries a hinge knuckle — a cylinder with a pin bore
through it. The clasp is a ball nub on one half and a matching dished cup on the
other, both revolved profiles (never a cylinder+sphere-cap union).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `frame_w`).
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
frame_w   = float(PARAM(lambda: frame_w,   90.0))  # finished mouth width of the purse (mm)
arch_h    = float(PARAM(lambda: arch_h,    22.0))  # how far the arch rises above the hinge (mm)
rod_t     = float(PARAM(lambda: rod_t,      5.0))  # frame rod thickness, front to back (mm)
rod_h     = float(PARAM(lambda: rod_h,      7.0))  # frame rod height, top to channel lip (mm)
channel_w = float(PARAM(lambda: channel_w,  2.4))  # sew channel width — fabric folds in (mm)
pin_dia   = float(PARAM(lambda: pin_dia,    2.0))  # hinge pin bore diameter (mm)
ball_dia  = float(PARAM(lambda: ball_dia,   4.0))  # kiss-clasp ball nub diameter (mm)

target_part = str(PARAM(lambda: target_part, "half_frame"))  # half_frame|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
# Real kiss-lock frames run 60-200 mm across the mouth; coin purses at the low end,
# doctor-bag frames at the high end.
frame_w   = max(50.0, min(frame_w, 220.0))
arch_h    = max(8.0, min(arch_h, frame_w * 0.45))
rod_t     = max(3.0, min(rod_t, 12.0))
rod_h     = max(4.0, min(rod_h, 16.0))
# The channel must leave real wall on both sides of the rod, and be wide enough that a
# folded fabric edge (two plies plus glue) actually seats.
channel_w = max(1.2, min(channel_w, rod_t - 1.6))
pin_dia   = max(1.2, min(pin_dia, rod_t - 1.2))
ball_dia  = max(2.5, min(ball_dia, min(rod_t * 1.4, rod_h * 0.9)))

# ── Derived geometry ─────────────────────────────────────────────────────────
# Hinge-pin centres sit at ±half_w, so frame_w IS the finished mouth width
# (hinge centre to hinge centre) — the number a purse pattern is drafted from.
half_w = frame_w / 2.0
knuckle_d = rod_h + 1.6                # hinge knuckle outside diameter
channel_d = rod_h * 0.62               # how deep the sew channel bites up into the rod
clasp_clear = 0.25                     # ball-to-cup diametral clearance (mm)
corner_r = min(arch_h * 0.8, half_w * 0.6)  # arch corner radius


def _rounded_slab(length, depth, height, rad):
    """A rounded-rectangle slab centred on X/Y, sitting on Z=0, rounded on |Z edges."""
    r = max(0.3, min(rad, min(length, depth) / 2.0 - 0.2))
    wp = cq.Workplane("XY").rect(length, depth).extrude(height)
    try:
        wp = wp.edges("|Z").fillet(r)
    except Exception:
        pass
    return wp


def _arch_blank():
    """The bare arch rod: a rounded-corner half-ring standing in the XZ plane.

    Built in plan (XY) as an outer rounded slab minus an oversized inner rounded slab,
    extruded through rod_t, then rotated upright and its lower half trimmed off so only
    the arch survives.
    """
    outer_l = half_w + rod_h / 2.0
    outer_d = arch_h + rod_h
    outer = _rounded_slab(outer_l * 2.0, outer_d * 2.0, rod_t, corner_r + rod_h)
    inner = (
        _rounded_slab(outer_l * 2.0 - 2.0 * rod_h, outer_d * 2.0 - 2.0 * rod_h,
                      rod_t + 6.0, corner_r)
        .translate((0, 0, -3.0))
    )
    ring = outer.cut(inner)
    # Trim to a half-ring: keep +Y only, cutter overshoots every face.
    big = max(outer_l, outer_d) * 3.0 + 10.0
    trim = (
        cq.Workplane("XY")
        .box(big, big, big)
        .translate((0, -big / 2.0, 0))
    )
    ring = ring.cut(trim)
    # Stand it up: XY plan becomes the XZ elevation.
    ring = ring.rotate((0, 0, 0), (1, 0, 0), 90)
    # Now the arch spans X in [-outer_l, outer_l], rises in +Z, is rod_t deep in Y.
    return ring.translate((0, rod_t / 2.0, 0))


def _cut_sew_channel(body):
    """Cut the fabric channel up into the underside of the arch, along its whole run.

    The channel is a slot swept as a thin rounded slab following the same plan outline
    as the arch, offset inward — i.e. the arch minus a shell of channel_w — so it hugs
    the rod centreline everywhere including around the corners.
    """
    outer_l = half_w + rod_h / 2.0
    outer_d = arch_h + rod_h
    mid = rod_h / 2.0  # channel is centred in the rod's radial thickness
    slab_o = _rounded_slab(
        (outer_l - mid + channel_w / 2.0) * 2.0,
        (outer_d - mid + channel_w / 2.0) * 2.0,
        channel_d + 4.0,
        corner_r + mid,
    ).translate((0, 0, -2.0))
    slab_i = _rounded_slab(
        (outer_l - mid - channel_w / 2.0) * 2.0,
        (outer_d - mid - channel_w / 2.0) * 2.0,
        channel_d + 8.0,
        corner_r,
    ).translate((0, 0, -4.0))
    shell = slab_o.cut(slab_i)
    shell = shell.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, rod_t / 2.0, 0))
    # Keep only the part of the shell below the channel roof, so the slot opens
    # downward/outward and never becomes a sealed internal void. Cutter overshoots.
    big = max(outer_l, outer_d) * 3.0 + 10.0
    roof = channel_d
    keep_cut = (
        cq.Workplane("XY")
        .box(big, big, big)
        .translate((0, 0, roof + big / 2.0))
    )
    shell = shell.cut(keep_cut)
    return body.cut(shell)


def _hinge_knuckle(x_sign):
    """A cylindrical hinge knuckle at one end of the arch, bored for the pin."""
    x = x_sign * half_w
    # The knuckle axis runs along Y (front-to-back), so the two half-frames pivot in
    # the plane of the mouth. It is one rod_t-deep boss flush with the arch's own
    # depth — the knuckle is the thickened arch end, not a protruding barrel.
    length = rod_t
    # An XZ workplane extrudes toward -Y, so shift by +rod_t/2 to land the knuckle on
    # the arch's own Y midplane — without this the knuckle sits half a rod off-face.
    body = (
        cq.Workplane("XZ")
        .circle(knuckle_d / 2.0)
        .extrude(length)
        .translate((x, rod_t / 2.0, rod_h / 2.0))
    )
    bore = (
        cq.Workplane("XZ")
        .circle(pin_dia / 2.0)
        .extrude(length + 6.0)
        .translate((x, rod_t / 2.0 + 3.0, rod_h / 2.0))
    )
    return body.cut(bore)


def _clasp_ball():
    """The kiss-clasp ball nub: a revolved dome profile on a short neck.

    Revolved from a 2D profile so there is no cylinder+sphere-cap union and no pole
    singularity — the crown is a flat land, not a point.
    """
    r = ball_dia / 2.0
    neck = max(0.8, r * 0.5)
    crown = max(0.4, r * 0.28)  # flat top land radius
    prof = (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(r * 0.62, 0)
        .lineTo(r, neck)
        .lineTo(r, neck + r * 0.55)
        .lineTo(crown, neck + r * 1.15)
        .lineTo(0, neck + r * 1.15)
        .close()
        .revolve(360, (0, 0, 0), (0, 1, 0))
    )
    return prof


def _clasp_cup():
    """The matching dished cup: same profile grown by the clearance, used as a cutter."""
    r = ball_dia / 2.0 + clasp_clear / 2.0
    neck = max(0.8, ball_dia / 2.0 * 0.5)
    crown = max(0.4, r * 0.28)
    return (
        cq.Workplane("XZ")
        .moveTo(0, -1.0)
        .lineTo(r * 0.62, -1.0)
        .lineTo(r * 0.62, 0)
        .lineTo(r, neck)
        .lineTo(r, neck + r * 0.55)
        .lineTo(crown, neck + r * 1.15)
        .lineTo(0, neck + r * 1.15)
        .close()
        .revolve(360, (0, 0, 0), (0, 1, 0))
    )


def build_half_frame(with_ball=True):
    """One half-frame: arch + sew channel + two hinge knuckles + clasp feature."""
    body = _arch_blank()
    body = _cut_sew_channel(body)
    body = body.union(_hinge_knuckle(1)).union(_hinge_knuckle(-1))

    # Clasp sits at the crown of the arch (X = 0, top of the rod).
    crown_z = arch_h + rod_h
    if with_ball:
        ball = _clasp_ball().rotate((0, 0, 0), (1, 0, 0), -90)
        # Sink it 0.6 mm into the crown so the union overlaps rather than touches.
        body = body.union(ball.translate((0, rod_t / 2.0, crown_z - 0.6)))
    else:
        cup = _clasp_cup().rotate((0, 0, 0), (1, 0, 0), -90)
        body = body.cut(cup.translate((0, rod_t / 2.0, crown_z - 0.6)))
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "set":
    # Two genuinely separate solids: the ball half and the cup half, laid out on one
    # plate with a real gap. Assembly (never .union() of non-touching bodies).
    gap = max(rod_h * 2.0, 6.0)
    asm = cq.Assembly()
    asm.add(build_half_frame(with_ball=True).translate((0, -(arch_h + rod_h + gap) / 1.0, 0)),
            name="half_frame_ball", color=cq.Color("#c9b48a"))
    asm.add(build_half_frame(with_ball=False),
            name="half_frame_cup", color=cq.Color("#b8a377"))
    result = asm
else:
    result = build_half_frame(with_ball=True)
