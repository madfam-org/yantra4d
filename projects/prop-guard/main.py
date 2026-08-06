"""
Prop Guard — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An impact / finger guard for FPV & RC propellers. A ring (or ducted shroud) sized
to the propeller diameter, carried on arms that bolt to the standard square motor
mount pattern (9x9 M2, 16x16 or 19x19 M3). Protects fingers and props on
bump-ins; the ducted variant also boosts static thrust on small craft.

Reuses the shared `motor_bolt_points()` / `motor_screw_d()` helper — the same
motor bolt-pattern interface used across the drone Commons.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `prop_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use
    globals()/eval/getattr — they are not in the sandbox's allowed builtins.
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


# ── Shared motor bolt-pattern interface (reused across the drone Commons) ─────
MOTOR_PATTERNS = {"16x16": 16.0, "19x19": 19.0, "9x9": 9.0}


def motor_bolt_points(pattern):
    """Return the 4 (x,y) motor-screw centres for a square NxN mount pattern."""
    s = MOTOR_PATTERNS.get(pattern, 16.0)
    h = s / 2.0
    return [(h, h), (h, -h), (-h, h), (-h, -h)]


def motor_screw_d(pattern):
    """Screw clearance diameter: 9x9 boards use M2, 16/19 use M3."""
    return 2.4 if pattern == "9x9" else 3.4


# ── Parameters ───────────────────────────────────────────────────────────────
prop_dia      = float(PARAM(lambda: prop_dia,     127.0))  # propeller diameter (mm) e.g. 5in=127
motor_pattern = str(  PARAM(lambda: motor_pattern, "16x16"))
clearance     = float(PARAM(lambda: clearance,      6.0))  # radial gap prop tip -> ring inner wall
ring_wall     = float(PARAM(lambda: ring_wall,      3.0))  # ring wall thickness (radial)
ring_height   = float(PARAM(lambda: ring_height,   10.0))  # ring height (Z)
arm_count     = int(  PARAM(lambda: arm_count,        3))  # number of arms hub -> ring
arm_width     = float(PARAM(lambda: arm_width,      6.0))  # arm width
hub_bore      = float(PARAM(lambda: hub_bore,      10.0))  # central hub bore (motor shaft/bell)
duct_depth    = float(PARAM(lambda: duct_depth,    16.0))  # ducted shroud height (ducted mode)
duct_lip      = float(PARAM(lambda: duct_lip,       3.0))  # rounded intake lip radius (ducted mode)

target_part   = str(PARAM(lambda: target_part, "ring_guard"))
# "ring_guard" | "ducted_shroud" | "half_guard"


# ── Derived / clamped geometry ───────────────────────────────────────────────
ring_r_in = max(6.0, prop_dia / 2.0 + clearance)     # inner radius of the guard
ring_r_out = ring_r_in + max(1.0, ring_wall)         # outer radius
screw_r = max(0.8, motor_screw_d(motor_pattern) / 2.0)
hub_r = max(screw_r + 3.5, hub_bore / 2.0 + 3.0)     # hub outer radius (holds bolt pattern)
hub_bore_r = max(1.0, min(hub_bore / 2.0, hub_r - screw_r - 2.0))
arm_count = max(2, min(arm_count, 8))


def _ring(r_in, r_out, h):
    """A watertight annular ring: outer cylinder minus inner cylinder.
    Base at z=0, extends up +h."""
    outer = cq.Workplane("XY").circle(r_out).extrude(h)
    inner = cq.Workplane("XY").circle(r_in).extrude(h + 2.0).translate((0, 0, -1.0))
    return outer.cut(inner)


def _hub(h):
    """Central hub disc carrying the motor bolt pattern + central bore.
    Base at z=0, extends up +h."""
    disc = cq.Workplane("XY").circle(hub_r).extrude(h)
    disc = disc.faces(">Z").workplane().circle(hub_bore_r).cutThruAll()
    disc = (
        disc.faces(">Z").workplane()
        .pushPoints(motor_bolt_points(motor_pattern))
        .circle(screw_r).cutThruAll()
    )
    return disc


def _arms(r_inner_attach, h, span_deg=360.0, start_deg=0.0):
    """Radial arms from the hub out to the ring inner radius. Arms are thin boxes
    laid along each spoke direction. `span_deg`/`start_deg` allow a partial fan
    (used by half_guard). Base at z=0, height h."""
    arms = None
    length = ring_r_in - r_inner_attach + ring_wall + 2.0  # overlap into hub and ring
    n = arm_count
    if span_deg >= 359.0:
        angles = [start_deg + i * (360.0 / n) for i in range(n)]
    else:
        # spread n arms across the given span inclusive of both ends
        if n == 1:
            angles = [start_deg + span_deg / 2.0]
        else:
            angles = [start_deg + i * (span_deg / (n - 1)) for i in range(n)]
    mid_r = r_inner_attach + length / 2.0 - 1.0
    for a in angles:
        rad = math.radians(a)
        cx = mid_r * math.cos(rad)
        cy = mid_r * math.sin(rad)
        arm = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, h / 2.0), rotate=cq.Vector(0, 0, a))
            .box(length, arm_width, h, centered=(True, True, True))
        )
        arms = arm if arms is None else arms.union(arm)
    return arms


def build_ring_guard():
    """Full protective ring on arms bolted to the motor hub."""
    ring = _ring(ring_r_in, ring_r_out, ring_height)
    hub = _hub(ring_height)
    arms = _arms(hub_r - 1.0, min(ring_height, arm_width + 2.0))
    body = ring.union(hub).union(arms)
    return body


def build_ducted_shroud():
    """A taller ducted shroud: a deep ring with a rounded intake lip, on arms.
    The duct wall closely follows the prop tip for a thrust-boosting shroud."""
    h = max(ring_height, duct_depth)
    duct = _ring(ring_r_in, ring_r_out, h)
    hub = _hub(min(h, arm_width + 4.0))
    arms = _arms(hub_r - 1.0, min(h, arm_width + 2.0))
    body = duct.union(hub).union(arms)
    # Chamfered intake lip on the shroud's top rim, applied last and restricted to
    # the top-outer edges. A fillet on this thin annulus can self-intersect, and
    # chamfering before the arm union leaves a coincident face — so chamfer the
    # finished body and, if the selector/op fails, keep the watertight solid.
    lip = max(0.4, min(duct_lip, ring_wall - 0.4, h / 3.0))
    try:
        body = body.faces(">Z").edges(cq.selectors.RadiusNthSelector(-1)).chamfer(lip)
    except Exception:
        try:
            body = body.edges(">Z").chamfer(lip)
        except Exception:
            pass
    return body


def build_half_guard():
    """A 180-degree bumper: half a ring on a fan of arms — the common
    'front bumper' style that protects the leading edge and saves weight."""
    h = ring_height
    full = _ring(ring_r_in, ring_r_out, h)
    # Keep only the +Y half by cutting away the -Y half-space.
    cutter = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -ring_r_out, h / 2.0))
        .box(ring_r_out * 2.4, ring_r_out * 2.0, h + 2.0, centered=(True, True, True))
    )
    half = full.cut(cutter)
    hub = _hub(h)
    arms = _arms(hub_r - 1.0, min(h, arm_width + 2.0), span_deg=180.0, start_deg=0.0)
    body = half.union(hub).union(arms)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "ducted_shroud":
    result = build_ducted_shroud()
elif target_part == "half_guard":
    result = build_half_guard()
else:  # "ring_guard"
    result = build_ring_guard()
