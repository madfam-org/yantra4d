"""Magnetic Pin Dish — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The magnetic pin dish of the cutting table: a shallow bowl with a disc magnet under the
floor, so dressmaker pins and machine needles jump to it instead of ending up in the carpet
— and so a spilled tin can be swept up by waving the dish over the floor. Retail versions
bond the magnet in permanently; here the magnet drops into a pocket underneath, sized by
the two parameters that actually matter (`magnet_dia`, `magnet_t`), so any tin of N35 discs
from the hardware bin fits.

Modes (dispatched via `target_part`):
  * "dish"  — one dish.
  * "twin"  — two dishes on one plate (pins in one, discarded needles in the other).
  * "sharps" — a deeper, narrower version for used needles and blades.

Geometry: a revolved dish profile (never a cylinder unioned with a dome — that seam cracks)
with a magnet pocket bored UP into the underside. The pocket opens downward, so it drains
and is not a sealed void; retention is three small compliant nibs, not a lid. A ring foot
keeps the magnet clear of the table so the dish does not drag on steel.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `magnet_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import math

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
dish_dia   = float(PARAM(lambda: dish_dia,   84.0))  # outside diameter at the rim (mm)
dish_h     = float(PARAM(lambda: dish_h,     18.0))  # overall height (mm)
bowl_d     = float(PARAM(lambda: bowl_d,     10.0))  # bowl depth below the rim (mm)
magnet_dia = float(PARAM(lambda: magnet_dia, 20.0))  # disc magnet diameter (mm)
magnet_t   = float(PARAM(lambda: magnet_t,   3.0))   # disc magnet thickness (mm)
floor_t    = float(PARAM(lambda: floor_t,    1.6))   # floor left over the magnet (mm)
magnet_clr = float(PARAM(lambda: magnet_clr, 0.25))  # pocket clearance on the magnet (mm)

target_part = str(PARAM(lambda: target_part, "dish"))  # dish|twin|sharps

# ── Safe clamps ──────────────────────────────────────────────────────────────
dish_dia   = max(40.0, min(dish_dia, 160.0))
dish_h     = max(8.0, min(dish_h, 50.0))
bowl_d     = max(4.0, min(bowl_d, dish_h - 3.0))
magnet_dia = max(6.0, min(magnet_dia, dish_dia - 20.0))
magnet_t   = max(1.0, min(magnet_t, 12.0))
floor_t    = max(0.8, min(floor_t, 4.0))
magnet_clr = max(0.05, min(magnet_clr, 0.8))


def build_dish(outer_dia, height, depth):
    """Revolve the dish wall, then bore the magnet pocket up into the underside."""
    outer_dia = max(40.0, min(outer_dia, 160.0))
    height = max(8.0, min(height, 50.0))
    depth = max(4.0, min(depth, height - 3.0))

    r_out = outer_dia / 2.0
    wall = max(min(outer_dia * 0.035, 3.5), 2.0)
    foot_h = max(min(height * 0.10, 3.0), 1.5)      # ring foot lifts the magnet off steel
    foot_in = r_out - wall - max(outer_dia * 0.10, 6.0)
    floor_top = height - depth                       # z of the bowl floor
    boss_z = max(floor_top - (magnet_t + magnet_clr) - floor_t, foot_h * 0.5)

    # Half-profile revolved about Z. Outside: foot → flared wall → rim. Inside: rim →
    # bowl wall → dished floor → back down the underside, leaving the ring-foot recess.
    prof = [
        (r_out - wall * 0.35, 0.0),                  # outer foot, sits on the table
        (r_out, height * 0.42),                      # wall flares out to the rim
        (r_out, height),                             # rim top, outside
        (r_out - wall, height),                      # rim top, inside
        (r_out - wall * 1.25, floor_top + depth * 0.25),
        (r_out - wall - max(outer_dia * 0.06, 4.0), floor_top),   # bowl floor edge
        (0.0, floor_top),                            # bowl floor, flat across the axis
        (0.0, boss_z),                               # underside of the magnet boss
        (max(magnet_dia / 2.0 + 3.0, 8.0), boss_z),  # boss shoulder
        (foot_in, foot_h),                           # up into the ring-foot recess
        (r_out - wall * 1.1, foot_h),
        (r_out - wall * 0.9, 0.0),                   # back to the foot
    ]
    body = cq.Workplane("XZ").polyline(prof).close().revolve(
        360.0, (0, 0, 0), (0, 1, 0))

    # Magnet pocket: bored UP from the underside of the boss. It overshoots downward, so
    # the pocket is unambiguously open at the bottom — it drains, and it is never a sealed
    # void. `floor_t` of solid stays between the magnet and the bowl floor.
    pocket_d = magnet_t + magnet_clr
    pocket = (
        cq.Workplane("XY")
        .circle(magnet_dia / 2.0 + magnet_clr)
        .extrude(pocket_d + 1.0)
        .translate((0, 0, boss_z - 1.0))
    )
    body = body.cut(pocket)

    # Retention nibs: three small posts in the pocket mouth that the magnet snaps past.
    # Generous section (1.1 mm radius) — a knife-edge lip would just shear off. They are
    # seated so each one OVERLAPS the pocket wall and reaches up into the solid boss: a
    # nib that merely kissed the wall tangentially would weld into a crack.
    nib_r = 1.1
    nibs = []
    seat = magnet_dia / 2.0 + magnet_clr - nib_r * 0.45   # bite into the pocket wall
    for i in range(3):
        a = 2.0 * math.pi * i / 3.0
        nibs.append(cq.Solid.makeCylinder(
            nib_r, pocket_d * 0.55 + 0.6,
            cq.Vector(seat * math.cos(a), seat * math.sin(a), boss_z),
            cq.Vector(0, 0, 1)))
    body = body.union(cq.Workplane(obj=cq.Compound.makeCompound(nibs)))

    # Pin ramp: a shallow scallop in the rim so a pin can be slid up and off one-handed.
    ramp = cq.Solid.makeCylinder(
        max(outer_dia * 0.09, 5.0), wall * 4.0,
        cq.Vector(0, r_out + wall, height - max(height * 0.10, 1.6)),
        cq.Vector(0, -1, 0))
    body = body.cut(cq.Workplane(obj=ramp))
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "twin":
    # Two separate dishes — a COMPOUND, never .union() of non-touching solids.
    a = build_dish(dish_dia, dish_h, bowl_d).translate((-(dish_dia / 2.0 + 5.0), 0, 0))
    b = build_dish(dish_dia, dish_h, bowl_d).translate(((dish_dia / 2.0 + 5.0), 0, 0))
    result = cq.Workplane(obj=cq.Compound.makeCompound(
        a.solids().vals() + b.solids().vals()))
elif target_part == "sharps":
    # Deeper and narrower: a sharps cup for used machine needles and blade snap-offs.
    result = build_dish(dish_dia * 0.62, dish_h * 1.7, bowl_d * 2.1)
else:
    result = build_dish(dish_dia, dish_h, bowl_d)
