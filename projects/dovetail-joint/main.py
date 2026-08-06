"""
Dovetail / Slide Joint — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A male + female dovetail slide connection for joining modular parts. The male is
a trapezoidal rail (wider at its base than its mouth, so it cannot pull straight
out); the female is a matching socket cut into a block. They slide together along
the rail axis with a printable clearance.

Because the socket is cut with the SAME trapezoid the rail is grown from — only
inflated by the clearance on every flank — the two halves are guaranteed to mate.

Three parts (dispatched via `target_part`):
  * "male"   — the trapezoidal rail on a backing plate.
  * "female" — the socket block with the dovetail groove cut through (or stopped).
  * "pair"   — both, positioned side by side to show the fit.

Two joint types (`joint_type`):
  * "straight_slide" — an open-ended groove; the rail slides fully through.
  * "locking"        — a detent stop near the far end so the rail clicks in and
                       resists sliding back out.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `dt_width`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "pair"))  # male|female|pair
if target_part not in ("male", "female", "pair"):
    target_part = "pair"

joint_type = str(PARAM(lambda: joint_type, "straight_slide"))  # straight_slide|locking
if joint_type not in ("straight_slide", "locking"):
    joint_type = "straight_slide"

dt_width = float(PARAM(lambda: dt_width, 20.0))     # dovetail WIDTH at the base (widest)
dt_depth = float(PARAM(lambda: dt_depth, 8.0))      # dovetail depth (rail height / groove depth)
angle = float(PARAM(lambda: angle, 15.0))           # flank angle from vertical (deg)
length = float(PARAM(lambda: length, 40.0))         # slide length along the rail axis
clearance = float(PARAM(lambda: clearance, 0.2))    # printed fit gap per flank
plate_thick = float(PARAM(lambda: plate_thick, 4.0))  # backing plate under male / around female
block_extra = float(PARAM(lambda: block_extra, 8.0))  # female material beyond the socket walls

# Clamp to safe, watertight ranges.
dt_width = max(6.0, dt_width)
dt_depth = max(2.0, dt_depth)
angle = max(0.0, min(angle, 40.0))
length = max(8.0, length)
clearance = max(0.0, min(clearance, 1.0))
plate_thick = max(1.5, plate_thick)
block_extra = max(3.0, block_extra)

# Horizontal inset per side from the flank angle over the full depth.
_inset = dt_depth * math.tan(math.radians(angle))
# Keep the mouth from crossing over (self-intersecting) on steep/deep dovetails.
if 2.0 * _inset >= dt_width - 1.0:
    _inset = (dt_width - 1.0) / 2.0

# Convention (cross-section in X–Z, tail axis along Y):
#   The tail is WIDEST at its outer face (the flare) and NARROWER at its neck,
#   so once engaged it cannot be lifted straight out — only slid along Y.
#   `dt_width` is the widest (flare) width; the neck is inset by the flank angle.
neck_w = dt_width - 2.0 * _inset


# ── Dovetail cross-section profiles (in the X–Z plane) ───────────────────────
def male_profile():
    """MALE tail trapezoid on its plate: NECK (narrow) at z=0 sitting on the
    plate, FLARE (widest, = dt_width) at z=dt_depth. CCW closed polygon (x, z)."""
    flare = dt_width / 2.0
    neck = neck_w / 2.0
    return [
        (-neck, 0.0),
        (neck, 0.0),
        (flare, dt_depth),
        (-flare, dt_depth),
    ]


def female_profile():
    """FEMALE socket cavity trapezoid — the male inflated by `clearance` on every
    face so the tail slides in with a printable gap. Same NECK-down / FLARE-up
    orientation so the cavity captures the identically shaped male tail."""
    flare = dt_width / 2.0 + clearance
    neck = neck_w / 2.0 + clearance
    over = clearance                      # depth over-cut so the tail bottoms cleanly
    return [
        (-neck, -over),
        (neck, -over),
        (flare, dt_depth + over),
        (-flare, dt_depth + over),
    ]


# ── Builders ─────────────────────────────────────────────────────────────────
def male_rail():
    """The male dovetail rail on a backing plate. Rail axis runs along +Y; the
    trapezoid lives in X–Z and is extruded along Y for `length`."""
    prof = male_profile()
    # Backing plate under the rail (rail base sits on top of the plate).
    plate_w = dt_width + 2.0 * block_extra
    plate = (
        cq.Workplane("XY")
        .box(plate_w, length, plate_thick, centered=(True, True, False))
    )
    # Rail: extrude the trapezoid (X–Z) along +Y. Base at z=0 → lift to plate top,
    # overlapping slightly into the plate for a watertight union.
    rail = (
        cq.Workplane("XZ")
        .polyline(prof)
        .close()
        .extrude(length)
    )
    # extrude on XZ pushes to -Y; recentre along the plate length.
    rail = rail.translate((0, length / 2.0, plate_thick - min(0.6, plate_thick * 0.4)))

    if joint_type == "locking":
        # A small detent bump on the rail mouth near one end that clicks past the
        # socket's matching stop. Built as an overlapping cylinder (watertight).
        det_r = min(neck_w * 0.28, dt_depth * 0.35)
        if det_r > 0.6:
            bump = (
                cq.Workplane("XZ")
                .workplane(offset=-(length * 0.85))
                .center(0, dt_depth * 0.55 + plate_thick - min(0.6, plate_thick * 0.4))
                .circle(det_r)
                .extrude(min(2.0, neck_w * 0.5))
            )
            rail = rail.union(bump)

    return plate.union(rail)


def female_block():
    """The female socket: a block with the dovetail groove cut through it along
    +Y. For `locking`, a stop reduces the groove near the far end."""
    prof = female_profile()
    block_w = dt_width + 2.0 * block_extra
    block_h = dt_depth + plate_thick
    block = (
        cq.Workplane("XY")
        .box(block_w, length, block_h, centered=(True, True, False))
    )
    # Groove cutter: female trapezoid extruded the full length (+overshoot each
    # end so it opens on both faces). The base (widest) of the trapezoid must sit
    # at the block TOP and the narrow mouth point DOWN into the block, so the
    # dovetail is undercut and the male cannot lift straight out.
    #
    # Build the trapezoid so its widest edge is at the top: negate the profile's
    # z so base→z=0 becomes base→z=0 pointing the tail toward -z, then lift so the
    # base sits flush with the block top surface.
    top_prof = [(x, -z) for (x, z) in prof]     # tail now extends downward (-z)
    cutter = (
        cq.Workplane("XZ")
        .polyline(top_prof)
        .close()
        .extrude(length + 2.0)
    )
    # extrude on XZ goes to -Y; recentre the cutter on Y=0 and lift to block top.
    cutter = cutter.translate((0, (length + 2.0) / 2.0, block_h))
    block = block.cut(cutter)

    if joint_type == "locking":
        # A stop wall filling the groove near the far end so the rail bottoms and
        # its detent clicks in just before it.
        stop_len = max(2.0, length * 0.08)
        stop = (
            cq.Workplane("XY")
            .box(neck_w + 2.0 * clearance, stop_len, dt_depth + 1.0,
                 centered=(True, True, False))
            .translate((0, length / 2.0 - stop_len / 2.0, plate_thick - 0.5))
        )
        block = block.union(stop)

    return block


def build_pair():
    """Male and female side by side (spaced in X) to show the mate."""
    male = male_rail()
    female = female_block()
    gap = dt_width + 2.0 * block_extra + 10.0
    male = male.translate((-gap / 2.0, 0, 0))
    female = female.translate((gap / 2.0, 0, 0))
    return male.union(female)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "male":
    result = male_rail()
elif target_part == "female":
    result = female_block()
else:
    result = build_pair()
