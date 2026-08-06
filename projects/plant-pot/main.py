"""
Drainage Plant Pot & Saucer — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A tapered plant pot with a real drainage array in the floor (the CDG "Pot
Drainage" surface), a matching drip saucer, and a hanging variant with three
integrated lugs for cord or wire. Sized by top rim diameter and height with an
adjustable wall taper so pots nest for storage and shipping.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `pot_dia`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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
target_part = str(PARAM(lambda: target_part, "pot"))   # pot | saucer | hanging_pot

pot_dia    = float(PARAM(lambda: pot_dia,   120.0))   # top (rim) inner diameter (mm)
pot_h      = float(PARAM(lambda: pot_h,     110.0))   # pot height (mm)
taper      = float(PARAM(lambda: taper,      12.0))   # inward taper of base vs rim, per side (mm)
wall       = float(PARAM(lambda: wall,        3.0))   # wall thickness (mm)
floor      = float(PARAM(lambda: floor,       4.0))   # floor thickness (mm)
drain_dia  = float(PARAM(lambda: drain_dia,  10.0))   # drainage hole diameter (mm)
drain_ring = int(  PARAM(lambda: drain_ring,     6))  # drain holes around the ring
rim_lip    = bool( PARAM(lambda: rim_lip,   True))    # rolled top rim for strength/grip
foot_ring  = bool( PARAM(lambda: foot_ring, True))    # raised foot ring to lift the pot
saucer_h   = float(PARAM(lambda: saucer_h,   22.0))   # saucer wall height (mm)
hang_lugs  = int(  PARAM(lambda: hang_lugs,      3))  # hanging lugs (hanging_pot)
lug_hole   = float(PARAM(lambda: lug_hole,    6.0))   # hanging cord hole diameter (mm)

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
pot_dia   = max(40.0, min(pot_dia, 400.0))
pot_h     = max(30.0, min(pot_h, 400.0))
taper     = max(0.0, min(taper, pot_dia / 2.0 - 8.0))
wall      = max(2.0, min(wall, 8.0))
floor     = max(2.5, min(floor, 12.0))
drain_dia = max(3.0, min(drain_dia, 24.0))
drain_ring = max(0, min(drain_ring, 12))
saucer_h  = max(8.0, min(saucer_h, 60.0))
hang_lugs = max(2, min(hang_lugs, 6))
lug_hole  = max(3.0, min(lug_hole, 14.0))

rim_r_in = pot_dia / 2.0
base_r_in = max(6.0, rim_r_in - taper)


def _frustum(r_bottom, r_top, h, z0=0.0):
    """A solid truncated cone (loft between two circles), base at z0."""
    return (
        cq.Workplane("XY")
        .circle(r_bottom)
        .workplane(offset=h)
        .circle(r_top)
        .loft(combine=True)
        .translate((0, 0, z0))
    )


def _pot_body():
    """Tapered pot: solid outer frustum hollowed by an inner frustum, with a floor
    left at the bottom. Returns (solid, rim_outer_r)."""
    base_r_out = base_r_in + wall
    rim_r_out = rim_r_in + wall

    outer = _frustum(base_r_out, rim_r_out, pot_h)
    # Inner cavity starts at the floor and opens slightly wider at the rim.
    inner = _frustum(base_r_in, rim_r_in, pot_h - floor + 1.0, z0=floor)
    body = outer.cut(inner)

    if foot_ring:
        # A short ring foot: a thin annulus dropped below the base so the pot sits
        # off a surface and water can escape the drain holes.
        foot_h = 4.0
        fr_out = base_r_out
        fr_in = max(3.0, base_r_out - max(4.0, wall * 1.5))
        ring = (
            cq.Workplane("XY").circle(fr_out).circle(fr_in)
            .extrude(foot_h).translate((0, 0, -foot_h))
        )
        body = body.union(ring)

    if rim_lip:
        # A small torus-like rolled rim: a ring bar around the top edge for grip.
        try:
            lip = (
                cq.Workplane("XZ")
                .center(rim_r_out, pot_h)
                .circle(min(wall * 0.9, 2.6))
                .revolve(360, (0, 0, 0), (0, 1, 0))
            )
            body = body.union(lip)
        except Exception:
            pass  # rim lip is comfort/strength — never fatal

    try:
        body = body.clean()
    except Exception:
        pass
    return body, rim_r_out


def _drain_holes(body):
    """Punch the drainage array through the floor: one central hole plus a ring.
    This IS the 'Pot Drainage' CDG surface."""
    dr = drain_dia / 2.0
    # Central hole.
    center = cq.Workplane("XY").circle(dr).extrude(floor + 4.0).translate((0, 0, -2.0))
    body = body.cut(center)
    # Ring of holes on a circle inside the base floor.
    if drain_ring > 0:
        ring_r = max(dr + 3.0, base_r_in * 0.55)
        try:
            holes = (
                cq.Workplane("XY")
                .polarArray(radius=ring_r, startAngle=0, angle=360, count=drain_ring)
                .circle(dr).extrude(floor + 4.0)
                .translate((0, 0, -2.0))
            )
            body = body.cut(holes)
        except Exception:
            pass  # if a hole would breach the wall, skip the ring
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Part builders ─────────────────────────────────────────────────────────────
def build_pot():
    body, _ = _pot_body()
    return _drain_holes(body)


def build_saucer():
    """A shallow drip tray sized to catch the pot's base footprint with room to
    spare. Slightly tapered so saucers nest; a raised inner ridge keeps the pot
    base up out of standing water."""
    base_r_out = base_r_in + wall
    tray_base = base_r_out + 6.0        # inner floor radius
    tray_rim = tray_base + saucer_h * 0.25  # gentle outward flare
    body = _frustum(tray_base + wall, tray_rim + wall, saucer_h)
    cavity = _frustum(tray_base, tray_rim, saucer_h, z0=floor)
    body = body.cut(cavity)

    # Inner support ridge: a low ring the pot foot rests on, keeping the drain
    # holes above any caught water.
    ridge_r = tray_base * 0.7
    ridge = (
        cq.Workplane("XY").circle(ridge_r + 2.0).circle(ridge_r - 2.0)
        .extrude(min(4.0, saucer_h * 0.3)).translate((0, 0, floor))
    )
    body = body.union(ridge)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_hanging_pot():
    """The pot with hanging lugs: solid tabs bonded to the outer rim, each pierced
    for cord or wire. Drain holes still present."""
    body, rim_r_out = _pot_body()
    body = _drain_holes(body)

    lug_w = max(10.0, lug_hole * 2.4)
    lug_t = max(4.0, wall * 1.4)
    lug_up = 6.0  # how far the lug rises above the rim
    for i in range(hang_lugs):
        ang = (360.0 / hang_lugs) * i
        a = math.radians(ang)
        cx, cy = math.cos(a), math.sin(a)
        # Tab centered on the rim, standing up and slightly outboard.
        tab = (
            cq.Workplane("XY")
            .box(lug_t, lug_w, lug_up + 12.0, centered=(True, True, False))
            .translate((0, 0, pot_h - 6.0))
            .rotate((0, 0, 0), (0, 0, 1), ang)
            .translate((cx * (rim_r_out - 0.5), cy * (rim_r_out - 0.5), 0))
        )
        # Cord hole through the tab (axis pointing radially outward → drill along
        # the tab's local X, i.e. rotate a Z-cylinder appropriately).
        hole = (
            cq.Workplane("XY")
            .circle(lug_hole / 2.0).extrude(lug_t + 6.0)
            .rotate((0, 0, 0), (1, 0, 0), 90)     # lay cylinder along Y
            .rotate((0, 0, 0), (0, 0, 1), ang)    # aim it radially
            .translate((cx * (rim_r_out - 0.5), cy * (rim_r_out - 0.5), pot_h + lug_up))
        )
        body = body.union(tab).cut(hole)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "saucer":
    result = build_saucer()
elif target_part == "hanging_pot":
    result = build_hanging_pot()
else:
    result = build_pot()
