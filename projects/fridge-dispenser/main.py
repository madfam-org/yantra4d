"""
Fridge Gravity Can Dispenser — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A gravity-fed dispenser for cans (or small bottles) in the fridge: you load cans on
the top, they roll down an inclined floor, and you take the front one from the
bottom opening while the next rolls into place. Sized to the can diameter (`can_dia`,
default 66 mm for a standard soda can). Three feeds:

  * "single_lane" — one lane, cans single file down a ramp with a front stop.
  * "double_lane" — two side-by-side lanes sharing a centre wall (double capacity).
  * "compact"     — a short single lane (fewer cans, small fridges / door shelves).

The functional interface is the CAN GRAVITY RAIL — a U-channel floor sloped by a
gentle incline, wide enough for `can_dia` plus clearance, with a front lip that
holds the lead can until taken. Body is a solid outer block with the sloped lane
volume cut out (watertight by construction), plus a front dispensing window.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `can_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
can_dia   = float(PARAM(lambda: can_dia,   66.0))   # can diameter (mm; 66 = soda can)
can_len   = float(PARAM(lambda: can_len,  123.0))   # can length along the lane (mm)
capacity  = int(  PARAM(lambda: capacity,     5))   # cans per lane (depth)
wall      = float(PARAM(lambda: wall,       2.4))   # wall / floor thickness (mm)
clearance = float(PARAM(lambda: clearance,  2.0))   # side clearance so cans roll (per side)
incline   = float(PARAM(lambda: incline,    6.0))   # ramp incline angle (deg)
feed      = str(  PARAM(lambda: feed, "single-lane"))  # single-lane|double-lane|stacked
front_lip = float(PARAM(lambda: front_lip, 12.0))   # front stop lip height (mm)

target_part = str(PARAM(lambda: target_part, "single_lane"))  # single_lane|double_lane|compact

# ── Clamps ───────────────────────────────────────────────────────────────────
can_dia = max(30.0, min(can_dia, 100.0))
can_len = max(50.0, min(can_len, 200.0))
capacity = max(2, min(capacity, 12))
wall = max(1.6, min(wall, 5.0))
clearance = max(0.5, min(clearance, 6.0))
incline = max(2.0, min(incline, 15.0))
front_lip = max(4.0, min(front_lip, can_dia * 0.6))
if target_part == "compact":
    capacity = min(capacity, 3)

# Lane geometry:
#   lane_w  = can_len + 2*clearance    (X — the can's length lies across the lane)
#   depth   = capacity * can_dia + wall (Y — cans queue front-to-back)
#   height  = can_dia + wall + ramp rise + a little headroom
lane_w = can_len + 2.0 * clearance
depth = capacity * (can_dia + 2.0) + wall
ramp_rise = depth * math.tan(math.radians(incline))
height = can_dia + wall + ramp_rise + 6.0

FRONT_Y = -depth / 2.0   # dispensing end
BACK_Y = depth / 2.0     # loading end


# ── Geometry helpers ─────────────────────────────────────────────────────────
def _box(w, d, h, x=0.0, y=0.0, z=0.0, cx=True, cy=True):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z))
        .box(w, d, h, centered=(cx, cy, False))
    )


def lane_cavity(width, x_center):
    """The sloped lane volume to cut from the body: a box tilted about X so the
    floor slopes down toward the front, plus generous top clearance. Cutting a
    solid tilted box guarantees watertight walls."""
    # Build an oversized box, tilt it, and position it so its floor sits at `wall`
    # at the FRONT and rises toward the BACK.
    inner = _box(width, depth + 4.0, can_dia + ramp_rise + 4.0, x_center, 0.0, 0.0)
    # Tilt about the X axis passing through the front-bottom edge so the floor rises
    # toward +Y. Rotating about X by +incline lifts +Y upward.
    inner = inner.rotate((x_center, FRONT_Y, wall), (x_center + 1.0, FRONT_Y, wall), incline)
    # Lift so the sloped floor clears the base wall at the front.
    inner = inner.translate((0, 0, wall))
    return inner


def dispense_window(width, x_center):
    """Open the FRONT face below the lip so the lead can is reachable, but keep a
    `front_lip` curb that stops the can rolling out."""
    win_h = can_dia + ramp_rise
    win = _box(width - 2.0 * 0.0, can_dia * 1.2, win_h, x_center, FRONT_Y - can_dia * 0.3, wall + front_lip)
    return win


def load_opening(width, x_center):
    """Open the TOP-BACK so cans drop in from above at the high end."""
    op = _box(width, can_dia * 1.4, height, x_center, BACK_Y - can_dia * 0.2, wall + front_lip)
    return op


def build_lane_unit(n_lanes):
    """A dispenser body with `n_lanes` gravity lanes cut side by side."""
    total_w = n_lanes * lane_w + (n_lanes + 1) * wall
    body = _box(total_w, depth, height, 0.0, 0.0, 0.0)

    # Lane centres across X.
    first_cx = -total_w / 2.0 + wall + lane_w / 2.0
    for i in range(n_lanes):
        cx = first_cx + i * (lane_w + wall)
        body = body.cut(lane_cavity(lane_w, cx))
        body = body.cut(dispense_window(lane_w, cx))
        body = body.cut(load_opening(lane_w, cx))

    # Ease the top loading edge for comfort (non-fatal).
    try:
        body = body.edges(">Z").edges("|X").chamfer(min(2.0, wall))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_single_lane():
    return build_lane_unit(1)


def build_double_lane():
    return build_lane_unit(2)


def build_compact():
    # Compact is a single short lane (capacity already clamped to <=3 above).
    return build_lane_unit(1)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "double_lane" or (target_part == "single_lane" and feed == "double-lane"):
    result = build_double_lane()
elif target_part == "compact":
    result = build_compact()
else:
    result = build_single_lane()
