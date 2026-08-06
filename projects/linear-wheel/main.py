"""
Linear Bushing / V-Wheel — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An OpenBuilds-style V-wheel that rolls in a V-slot aluminium extrusion rail, or a
plain flat idler wheel. The V-wheel's running surface is a double-V (two 45°
flanks meeting at the mid-plane) that grips the rail's 45° slot edges; the wheel
usually presses onto a 625 bearing (16 mm OD).

V geometry:
  The rim runs from the full outer radius at each face down to a minimum radius
  at the centre. For a 90°-included V (two 45° flanks matching the V-slot rail),
  the radius drops by width/2 from face to centre, so R_min = R_out − width/2.
  Modelled as two coaxial cones (frustums) joined at the centre — an exact,
  watertight double-V.

Modes (dispatched via `target_part`):
  * "vwheel"      — double-V wheel bored for a bearing press-fit (`bearing_bore`).
  * "flat_wheel"  — a flat-rim idler wheel, bored for the same bearing.
  * "solid_wheel" — a double-V wheel with NO bearing; a plain printed axle hole.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `outer_dia`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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
wheel_type   = str(  PARAM(lambda: wheel_type, "vslot"))   # "vslot" | "flat"
outer_dia    = float(PARAM(lambda: outer_dia,   24.0))     # wheel outer diameter, mm
width         = float(PARAM(lambda: width,       10.9))    # wheel width (OpenBuilds ≈ 10.9)
v_angle       = float(PARAM(lambda: v_angle,     90.0))    # V included angle, deg
bearing_bore  = float(PARAM(lambda: bearing_bore, 16.0))   # bearing OD press-fit (625 = 16)
axle_bore     = float(PARAM(lambda: axle_bore,    5.0))    # plain axle hole (solid wheel)
counterbore   = bool( PARAM(lambda: counterbore, True))    # recess bearing shoulders each face
cb_depth      = float(PARAM(lambda: cb_depth,     0.0))    # extra recess depth (0 = through seat)

target_part = str(  PARAM(lambda: target_part, "vwheel"))  # vwheel|flat_wheel|solid_wheel


# ── Derived / clamped geometry ───────────────────────────────────────────────
outer_dia = max(8.0, outer_dia)
outer_r = outer_dia / 2.0
width = max(4.0, width)
v_angle = max(60.0, min(v_angle, 120.0))
CLR = 0.10

# Radius drop from face to centre for the chosen V angle: dr = (width/2)*tan(half).
half = math.radians(v_angle / 2.0)
dr = (width / 2.0) * math.tan(half)
# Keep a solid core: R_min must stay well above the bore.
bearing_bore = max(3.0, min(bearing_bore, outer_dia - 4.0))
seat_r = bearing_bore / 2.0
axle_bore = max(2.0, min(axle_bore, outer_dia - 4.0))
min_r_floor = max(seat_r + 1.5, axle_bore / 2.0 + 1.5)
r_min = max(min_r_floor, outer_r - dr)
# If the requested V would cut below the core, cap dr so R_min == floor.
dr = outer_r - r_min


# ── Body builders ─────────────────────────────────────────────────────────────
def vwheel_body():
    """Double-V running surface: two frustums joined at the mid-plane."""
    lo = cq.Solid.makeCone(
        outer_r, r_min, width / 2.0, pnt=cq.Vector(0, 0, 0), dir=cq.Vector(0, 0, 1)
    )
    hi = cq.Solid.makeCone(
        r_min, outer_r, width / 2.0,
        pnt=cq.Vector(0, 0, width / 2.0), dir=cq.Vector(0, 0, 1),
    )
    return cq.Workplane(obj=lo).union(cq.Workplane(obj=hi))


def flat_body():
    """A plain flat-rim idler wheel with a light edge chamfer for tracking."""
    body = cq.Workplane("XY").circle(outer_r).extrude(width)
    ch = min(1.2, width * 0.15, outer_r * 0.1)
    if ch >= 0.3:
        try:
            body = body.edges("|Z").chamfer(ch)
        except Exception:
            pass
    return body


def bearing_seat(body):
    """Press-fit bearing bore straight through, with optional shallow shoulder
    recesses on each face so the bearing sits flush."""
    seat = (
        cq.Workplane("XY")
        .circle(seat_r + CLR)
        .extrude(width + 1.0)
        .translate((0, 0, -0.5))
    )
    body = body.cut(seat)
    if counterbore:
        # A shallow shoulder recess each face so the bearing sits flush; use the
        # explicit cb_depth when given, else a sensible default.
        d = cb_depth if cb_depth > 0.05 else 1.0
        d = min(d, width / 2.0 - 0.5)
        rec_r = seat_r + 1.5
        top = (
            cq.Workplane("XY")
            .circle(rec_r)
            .extrude(-d)
            .translate((0, 0, width))
        )
        bot = cq.Workplane("XY").circle(rec_r).extrude(d)
        body = body.cut(top).cut(bot)
    return body


def axle_hole(body):
    """A plain printed axle hole for a bearingless solid wheel."""
    hole = (
        cq.Workplane("XY")
        .circle(axle_bore / 2.0 + CLR)
        .extrude(width + 1.0)
        .translate((0, 0, -0.5))
    )
    return body.cut(hole)


# ── Builders ─────────────────────────────────────────────────────────────────
def build_vwheel():
    return bearing_seat(vwheel_body())


def build_flat():
    return bearing_seat(flat_body())


def build_solid():
    body = vwheel_body() if wheel_type == "vslot" else flat_body()
    return axle_hole(body)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "flat_wheel":
    result = build_flat()
elif target_part == "solid_wheel":
    result = build_solid()
else:
    # vwheel mode still honours wheel_type == "flat" as a flat bearing wheel.
    result = build_flat() if wheel_type == "flat" else build_vwheel()
