"""
Assistive Grip / Utensil Aid — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A grip aid that slips over a utensil, pen, or tool handle to enlarge it for users
with limited hand dexterity. A tube with a through bore sized to the handle; the
outer surface is cylindrical, a mid-swell "bulb", or a rounded triangle for an
easier hold. An optional strap slot lets a hand-strap thread through.

  * "grip"        — a plain slip-on cylindrical grip (target_part == "grip").
  * "bulb_grip"   — fatter in the middle for a relaxed power grasp
                    (target_part == "bulb_grip").
  * "strap_grip"  — a grip with a transverse strap slot for a hand strap
                    (target_part == "strap_grip").

Watertight strategy: the outer body is a single revolved/extruded solid; the
handle bore is one clean through-cut down the axis, leaving a continuous tube
wall. The strap slot is a rectangular through-cut across the wall that does not
reach the bore. Every result is one manifold solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import math

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
target_part = str(PARAM(lambda: target_part, "grip"))  # grip | bulb_grip | strap_grip

handle_dia = float(PARAM(lambda: handle_dia, 8.0))     # utensil handle diameter it slips over
grip_dia   = float(PARAM(lambda: grip_dia,  32.0))     # enlarged outer grip diameter
length     = float(PARAM(lambda: length,   95.0))      # grip length (mm)
shape      = str(  PARAM(lambda: shape, "cylindrical"))  # cylindrical | bulb | triangular
clearance  = float(PARAM(lambda: clearance,  0.4))     # bore slip clearance (radial)
bulb_gain  = float(PARAM(lambda: bulb_gain,  1.35))    # mid-swell factor for bulb shape
strap      = bool( PARAM(lambda: strap,    False))     # add a strap slot

# ── Clamps ───────────────────────────────────────────────────────────────────
handle_dia = max(3.0,  min(handle_dia, 30.0))
grip_dia   = max(handle_dia + 6.0, min(grip_dia, 60.0))  # always thicker than handle
length     = max(30.0, min(length, 200.0))
clearance  = max(0.0,  min(clearance, 2.0))
bulb_gain  = max(1.05, min(bulb_gain, 1.8))

bore_dia = handle_dia + 2.0 * clearance
BORE_R = bore_dia / 2.0
GRIP_R = grip_dia / 2.0


# ── Outer-body builders (before the bore is cut) ──────────────────────────────
def outer_cylinder():
    return cq.Workplane("XY").circle(GRIP_R).extrude(length)


def outer_bulb():
    """A barrel that swells to bulb_gain * GRIP_R at mid-length and tapers back to
    GRIP_R at the ends. Built by lofting a stack of circular sections, which stays
    watertight (no on-axis revolve singularity)."""
    r_end = GRIP_R
    r_mid = GRIP_R * bulb_gain
    n = 9
    step = length / (n - 1)
    wp = cq.Workplane("XY")
    for i in range(n):
        t = i / (n - 1)                       # 0..1 along length
        # Sine bulge: r_end at ends, r_mid at centre.
        r = r_end + (r_mid - r_end) * math.sin(math.pi * t)
        wp = (wp.workplane(offset=step) if i > 0 else wp).circle(r)
    return wp.loft(combine=True)


def outer_triangle():
    """A Reuleaux-ish rounded triangle prism: three lobes on a circle, unioned
    with a central disc so it stays a single fat rounded-triangular column."""
    lobe_r = GRIP_R * 0.62
    orbit = GRIP_R - lobe_r
    body = cq.Workplane("XY").circle(GRIP_R * 0.72).extrude(length)
    for k in range(3):
        ang = math.radians(90.0 + k * 120.0)
        x = orbit * math.cos(ang)
        y = orbit * math.sin(ang)
        lobe = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, 0))
            .circle(lobe_r)
            .extrude(length)
        )
        body = body.union(lobe)
    return body


def build_grip(with_strap):
    if shape == "bulb":
        body = outer_bulb()
    elif shape == "triangular":
        body = outer_triangle()
    else:
        body = outer_cylinder()

    # One clean through bore down the axis (extend past both ends to stay clean).
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(BORE_R)
        .extrude(length + 2.0)
    )
    body = body.cut(bore)

    # Comfort chamfer at each end of the bore (non-fatal).
    for zsel in (">Z", "<Z"):
        try:
            body = body.faces(zsel).edges(cq.selectors.RadiusNthSelector(0)).chamfer(min(1.2, BORE_R * 0.4))
        except Exception:
            pass

    if with_strap:
        body = _cut_strap_slot(body)
    return body


def _cut_strap_slot(body):
    """A transverse rectangular through-slot near one end, cut across the wall
    perpendicular to the axis but clear of the bore so a strap can thread it."""
    slot_w = 20.0
    slot_h = 4.0
    z = length * 0.16
    # Cut fully through Y at a height above the bore top, so it never opens the bore.
    y_off = BORE_R + (GRIP_R - BORE_R) * 0.5
    slot = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, z, -y_off))
        .box(slot_w, slot_h, (GRIP_R - BORE_R) * 0.9, centered=(True, True, True))
    )
    # Two slots (both sides) so a strap passes through symmetrically.
    slot2 = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, z, y_off))
        .box(slot_w, slot_h, (GRIP_R - BORE_R) * 0.9, centered=(True, True, True))
    )
    try:
        body = body.cut(slot).cut(slot2)
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bulb_grip":
    shape = "bulb"
    result = build_grip(with_strap=False)
elif target_part == "strap_grip":
    result = build_grip(with_strap=True)
else:  # "grip"
    result = build_grip(with_strap=strap)
