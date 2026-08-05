"""
Syringe / Dosing Aid — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Aids for measuring or limiting an oral / dosing-syringe dose, plus a small
graduated measuring cup. Sized to the syringe barrel (Luer-style) diameter.

  * "plunger_stop"   — a C-clip ring that snaps onto the plunger shaft and stops
                       the plunger at a set depth, capping the drawn volume
                       (target_part == "plunger_stop").
  * "syringe_holder" — a weighted stand that holds a syringe upright, barrel down,
                       between doses (target_part == "syringe_holder").
  * "med_cup"        — a small graduated measuring cup whose inner volume is solved
                       from cup_ml (target_part == "med_cup").

Watertight strategy: the plunger stop is a solid ring with a radial access slot
(a C is still one manifold solid) and a thumb tab; the holder is a solid puck
with a blind barrel socket (solid floor beneath); the cup is a solid revolve with
its bowl bored out, leaving a base and walls. Each result is one manifold solid.

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
target_part = str(PARAM(lambda: target_part, "plunger_stop"))
aid_type    = str(PARAM(lambda: aid_type, "plunger_stop"))  # plunger_stop|syringe_holder|med_cup

barrel_dia  = float(PARAM(lambda: barrel_dia, 20.0))   # syringe barrel outer diameter (mm)
shaft_dia   = float(PARAM(lambda: shaft_dia,  7.0))    # plunger shaft diameter (mm)
stop_depth  = float(PARAM(lambda: stop_depth, 15.0))   # plunger travel remaining when stop hits
cup_ml      = float(PARAM(lambda: cup_ml,     30.0))   # measuring-cup volume (mL)
wall        = float(PARAM(lambda: wall,        2.4))   # wall / ring thickness
clearance   = float(PARAM(lambda: clearance,   0.5))   # fit clearance

# ── Clamps ───────────────────────────────────────────────────────────────────
barrel_dia = max(6.0,  min(barrel_dia, 40.0))
shaft_dia  = max(3.0,  min(shaft_dia, 20.0))
stop_depth = max(3.0,  min(stop_depth, 80.0))
cup_ml     = max(2.0,  min(cup_ml, 120.0))
wall       = max(1.6,  min(wall, 6.0))
clearance  = max(0.1,  min(clearance, 1.5))


def block(w, d, h, z0=0.0):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .box(w, d, h, centered=(True, True, False))
    )


def build_plunger_stop():
    """A C-clip that grips the plunger shaft. Height = stop_depth so, clipped onto
    the shaft against the barrel top, it blocks the plunger from being drawn
    further than the intended volume."""
    bore_r = (shaft_dia + 2.0 * clearance) / 2.0
    ring_r = bore_r + wall
    height = stop_depth
    # Solid ring.
    ring = (
        cq.Workplane("XY")
        .circle(ring_r)
        .circle(bore_r)
        .extrude(height)
    )
    # Radial access slot so it snaps over the shaft: cut a wedge/gap on +X.
    slot_w = max(shaft_dia * 0.55, 2.0)
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(ring_r, 0, height / 2.0))
        .box(2.0 * wall + 2.0, slot_w, height + 2.0, centered=(True, True, True))
    )
    ring = ring.cut(slot)
    # A thumb tab opposite the slot to press it on.
    tab = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(-(ring_r + 5.0), 0, 0))
        .box(12.0, max(shaft_dia, 8.0), height, centered=(True, True, False))
    )
    # Fillet the tab-body junction lightly (non-fatal).
    body = ring.union(tab)
    try:
        body = body.edges(">Z").fillet(min(0.8, wall * 0.3))
    except Exception:
        pass
    return body


def build_syringe_holder():
    """A stable puck with a blind socket that cradles the barrel upright."""
    sock_r = (barrel_dia + 2.0 * clearance) / 2.0
    base_r = sock_r + wall + 8.0            # wide skirt for stability
    depth = min(stop_depth + 10.0, 45.0)    # socket depth
    floor = max(wall + 1.0, 3.0)
    total_h = depth + floor
    body = cq.Workplane("XY").circle(base_r).extrude(total_h)
    # Taper the outside a touch for a nicer stand (non-fatal).
    socket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor))
        .circle(sock_r)
        .extrude(depth + 1.0)
    )
    body = body.cut(socket)
    # Hollow the underside to save material, keeping a solid rim + floor.
    relief = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.001))
        .circle(base_r - wall - 2.0)
        .extrude(min(floor * 0.6, 2.0))
    )
    if (base_r - wall - 2.0) > (sock_r + 1.0):
        body = body.cut(relief)
    try:
        body = body.edges("|Z").fillet(min(3.0, wall))
    except Exception:
        pass
    return body


def build_med_cup():
    """A graduated measuring cup. Inner bowl volume solved from cup_ml assuming a
    cylinder with height ≈ 1.25 x inner radius; then add wall + base."""
    vol_mm3 = cup_ml * 1000.0
    # V = pi r^2 h, with h = k r  ->  r = (V / (pi k))^(1/3)
    k = 1.25
    r_in = (vol_mm3 / (math.pi * k)) ** (1.0 / 3.0)
    h_in = k * r_in
    base = max(wall + 0.5, 2.5)
    r_out = r_in + wall
    total_h = h_in + base
    body = cq.Workplane("XY").circle(r_out).extrude(total_h)
    bowl = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base))
        .circle(r_in)
        .extrude(h_in + 1.0)
    )
    body = body.cut(bowl)
    # Graduation rings: shallow external grooves at 1/4, 1/2, 3/4 fill.
    for frac in (0.25, 0.5, 0.75):
        z = base + h_in * frac
        groove = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z))
            .circle(r_out + 0.3)
            .circle(r_out - 0.6)
            .extrude(0.8)
        )
        try:
            body = body.cut(groove)
        except Exception:
            pass
    # A small pour lip / rim comfort fillet (non-fatal).
    try:
        body = body.edges(">Z").fillet(min(1.0, wall * 0.4))
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
# The platform injects target_part from the active mode's parts[]. When it is left
# at the default, fall back to the aid_type selector so the standalone/preview path
# still honours the user's chosen aid.
_part = target_part
if _part == "plunger_stop" and aid_type in ("syringe_holder", "med_cup"):
    _part = aid_type

if _part == "syringe_holder":
    result = build_syringe_holder()
elif _part == "med_cup":
    result = build_med_cup()
else:  # "plunger_stop"
    result = build_plunger_stop()
