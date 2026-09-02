"""
Filament Spool Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The spool runs on a bearing, and the core is whatever the core is.

Every filament spool has a different core. 52, 54, 56 mm are the sizes most often
quoted, but they are quoted rather than specified: there is no issuing body for a
spool core, and the only honest way to build against one is to measure it. What
does have a numbered standard is the bearing: 608 is an ISO 15 deep-groove ball
bearing, 8 x 22 x 7 mm, the single most available bearing on earth and already
the shared interface of six commons cartridges — `idler-608`, `gt2-idler`,
`bearing-housing`, `linear-wheel`, `roller-bracket`, `timing-pulley`.

So this cartridge fixes what is fixed and parameterises what is not: the bearing
seat is a 608 seat, and everything about the spool is a slider you measure.

Modes are dispatched via `target_part`:
  * "core_insert"  — presses into the spool core and carries a 608 bearing, so
                     the spool turns on a bearing instead of on its own plastic.
  * "axle_stub"    — the 8 mm shaft the bearing rides, on a bolt-through flange.
  * "spool_roller" — a roller with a 608 at each end, for the other common
                     arrangement: a spool resting on two rollers.

Why a bearing at all: a spool dragging on a printed axle is the commonest cause
of under-extrusion that is not the extruder's fault. The drag is not constant —
it rises as the spool empties and the tension arm has less mass to fight — so it
shows up as a print that degrades toward the end and looks like a heat or
retraction problem.

Watertightness strategy:
  * The bearing seat lives ENTIRELY in the flange, whose thickness is derived
    from the bearing width plus a shoulder. Letting the seat run into the core
    barrel would put a Ø22 bore inside a Ø20 barrel at the small end of the core
    range — a bore wider than the body it sits in, which is a shell, not a part.
  * Every union straddles what it grows from; every bore opens on a face, so
    nothing is ever a sealed void.
  * The grip fingers are slots bounded inside the barrel's own length, so they
    can never reach the flange and sever the barrel from it.
  * The axle bore is derived from the bearing bore and is always smaller than
    the seat, so the seat's shoulder always survives.
  * No fillet on any edge a bore has touched.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── ISO 15 608 deep-groove ball bearing ──────────────────────────────────────
# 8 x 22 x 7 mm. Exposed as sliders rather than hard-coded, because the same
# geometry serves 623 / 624 / 625 / 688 and the seat is the interface, not the
# part number — but 608 is the default because it is what the commons' other six
# bearing cartridges are built around.
BEARING_608 = {"bore": 8.0, "od": 22.0, "width": 7.0}

OVERLAP = 0.8


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "core_insert"))

core_dia = float(PARAM(lambda: core_dia, 54.0))
core_depth = float(PARAM(lambda: core_depth, 16.0))
flange_dia = float(PARAM(lambda: flange_dia, 70.0))
bearing_od = float(PARAM(lambda: bearing_od, BEARING_608["od"]))
bearing_w = float(PARAM(lambda: bearing_w, BEARING_608["width"]))
bearing_bore = float(PARAM(lambda: bearing_bore, BEARING_608["bore"]))
wall = float(PARAM(lambda: wall, 2.4))
press_fit = float(PARAM(lambda: press_fit, 0.10))
clearance = float(PARAM(lambda: clearance, 0.30))
grip_fingers = float(PARAM(lambda: grip_fingers, 6.0))
roller_len = float(PARAM(lambda: roller_len, 60.0))
bolt_dia = float(PARAM(lambda: bolt_dia, 5.0))

core_dia = max(20.0, min(core_dia, 90.0))
core_depth = max(5.0, min(core_depth, 40.0))
flange_dia = max(24.0, min(flange_dia, 120.0))
bearing_od = max(12.0, min(bearing_od, 32.0))
bearing_w = max(3.0, min(bearing_w, 14.0))
bearing_bore = max(3.0, min(bearing_bore, bearing_od - 4.0))
wall = max(1.6, min(wall, 6.0))
press_fit = max(0.0, min(press_fit, 0.4))
clearance = max(0.1, min(clearance, 0.8))
grip_fingers = int(max(0, min(round(grip_fingers), 12)))
roller_len = max(20.0, min(roller_len, 140.0))
bolt_dia = max(2.5, min(bolt_dia, 8.0))


# ── Derived, clamped against FINAL values ────────────────────────────────────
# The seat is a press fit ON the bearing's outer race: the bore is the bearing OD
# LESS the interference, so the plastic grips it. `press_fit` of 0 is a slip fit.
SEAT_R = bearing_od / 2.0 - press_fit
AXLE_R = bearing_bore / 2.0 + 0.35            # clearance around the shaft

# The shoulder behind the seat must touch only the bearing's OUTER race, or it
# drags on the inner race and the bearing does nothing at all.
SHOULDER_R = max(AXLE_R + 0.6, SEAT_R - max(1.6, wall * 0.7))

# The flange carries the whole seat, so it is at least the bearing plus a
# shoulder thick, and at least the seat plus a wall wide.
FLANGE_T = max(2.4, bearing_w + max(1.2, wall * 0.6))
FLANGE_R = max(flange_dia / 2.0, SEAT_R + wall, core_dia / 2.0 + 2.0)

# The barrel that enters the spool core.
BARREL_R = max(AXLE_R + wall, core_dia / 2.0 - clearance)


# ── Helpers ──────────────────────────────────────────────────────────────────
def bore(r, z0, z1):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(r)
        .extrude(z1 - z0)
    )


def bearing_pocket(z_face, downward):
    """A 608 seat cut from a face: the outer-race bore to `bearing_w` deep.

    Cut as one cylinder; the shoulder behind it is whatever material the smaller
    axle bore leaves, which is why SHOULDER_R is derived and not drawn."""
    if downward:
        return bore(SEAT_R, z_face - bearing_w, z_face + 1.0)
    return bore(SEAT_R, z_face - 1.0, z_face + bearing_w)


def finger_slots(body, z0, length):
    """Axial relief slots so the barrel can compress into an undersized core.

    Bounded inside the barrel's own length: a slot that reaches the flange would
    sever the barrel from it, and the result would be N separate watertight
    fingers plus a disc — a failure `is_watertight` cannot see."""
    n = grip_fingers
    if n < 1 or length < 6.0:
        return body
    slot_w = max(0.8, min(1.6, BARREL_R * 0.12))
    z_lo = z0 + 2.0
    z_hi = z0 + length - 1.0
    if z_hi - z_lo < 3.0:
        return body
    for i in range(n):
        ang = 360.0 * i / n
        tool = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z_lo))
            .box(BARREL_R * 3.0, slot_w, z_hi - z_lo, centered=(True, True, False))
            .rotate((0, 0, 0), (0, 0, 1), ang)
        )
        try:
            body = body.cut(tool)
        except Exception:
            pass
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_core_insert():
    """Presses into the spool core and carries a 608 bearing.

    Built flange-first at z = 0..FLANGE_T, with the barrel growing upward INTO
    the core and straddling the flange it grows from."""
    body = cq.Workplane("XY").circle(FLANGE_R).extrude(FLANGE_T)

    barrel = bore(BARREL_R, FLANGE_T - OVERLAP, FLANGE_T + core_depth)
    body = body.union(barrel)

    # A lead-in taper at the barrel's far end so the insert starts into a core
    # that is not quite round. A loft, never a chamfer on a bored edge.
    lead = min(2.0, core_depth * 0.25)
    if lead >= 0.5:
        taper = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, FLANGE_T + core_depth - lead))
            .circle(BARREL_R)
            .workplane(offset=lead)
            .circle(max(AXLE_R + 0.8, BARREL_R - lead * 0.8))
            .loft(ruled=True)
        )
        try:
            body = body.cut(
                bore(BARREL_R + 2.0, FLANGE_T + core_depth - lead,
                     FLANGE_T + core_depth + 1.0).cut(taper)
            )
        except Exception:
            pass

    body = finger_slots(body, FLANGE_T, core_depth)

    # The 608 seat, cut into the flange's OUTER face only. It never enters the
    # barrel: at the small end of the core range a Ø22 seat inside a Ø20 barrel
    # would be a bore wider than the body it sits in.
    body = body.cut(bearing_pocket(0.0, downward=False))
    body = body.cut(bore(AXLE_R, -1.0, FLANGE_T + core_depth + 1.0))

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_axle_stub():
    """The shaft the bearing rides, on a bolt-through flange."""
    body = cq.Workplane("XY").circle(FLANGE_R).extrude(FLANGE_T)

    shaft_r = max(1.2, bearing_bore / 2.0 - press_fit)
    shaft_len = bearing_w * 2.0 + 3.0
    shaft = bore(shaft_r, FLANGE_T - OVERLAP, FLANGE_T + shaft_len)
    body = body.union(shaft)

    # A retaining shoulder at the shaft's root so the bearing cannot walk down
    # onto the flange face. Straddles the flange, never sits on it.
    sh_r = min(shaft_r + max(1.0, wall * 0.6), FLANGE_R - 1.0)
    if sh_r > shaft_r + 0.3:
        body = body.union(bore(sh_r, FLANGE_T - OVERLAP, FLANGE_T + 1.4))

    # Bolt pattern through the flange, on a PCD derived from the flange so the
    # holes always land in material.
    n = 4
    pcd = (FLANGE_R + max(sh_r, shaft_r) + 1.0)
    pcd = min(pcd, FLANGE_R - bolt_dia / 2.0 - 1.6)
    if pcd > bolt_dia:
        pts = [(pcd * math.cos(2.0 * math.pi * i / n),
                pcd * math.sin(2.0 * math.pi * i / n)) for i in range(n)]
        tool = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -1.0))
            .pushPoints(pts)
            .circle(bolt_dia / 2.0)
            .extrude(FLANGE_T + 2.0)
        )
        try:
            body = body.cut(tool)
        except Exception:
            pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_spool_roller():
    """A roller with a 608 at each end, for a spool resting on two rollers."""
    roller_r = max(SEAT_R + wall, FLANGE_R * 0.45)
    body = cq.Workplane("XY").circle(roller_r).extrude(roller_len)

    # End rims, so a spool cannot walk off the roller. Each straddles the barrel.
    rim_r = roller_r + max(2.0, wall)
    rim_t = max(2.0, wall)
    body = body.union(bore(rim_r, -OVERLAP, rim_t))
    body = body.union(bore(rim_r, roller_len - rim_t, roller_len + OVERLAP))

    # A 608 seat in each end, and one axle bore through everything.
    body = body.cut(bearing_pocket(0.0, downward=False))
    body = body.cut(bearing_pocket(roller_len, downward=True))
    body = body.cut(bore(AXLE_R, -rim_t - 1.0, roller_len + rim_t + 1.0))

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "core_insert": build_core_insert,
    "axle_stub": build_axle_stub,
    "spool_roller": build_spool_roller,
}

result = _dispatch.get(target_part, build_core_insert)()
