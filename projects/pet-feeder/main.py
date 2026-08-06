"""
Slow-Feed Pet Bowl — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A food bowl whose floor carries a maze of concentric rings and radial spokes so
a fast-eating dog or cat has to work the kibble out of the channels, slowing
gulping and easing digestion. Also a raised bowl stand and a drop-in maze insert
that turns an existing plain bowl into a slow feeder.

  * "slow_bowl"   — a bowl with the maze ridges built integrally into the floor
                    (target_part == "slow_bowl").
  * "bowl_stand"  — a raised ring stand that holds a bowl at a comfortable height
                    (target_part == "bowl_stand").
  * "maze_insert" — just the maze puck, to drop into an existing bowl
                    (target_part == "maze_insert").

Watertight strategy: the bowl is a lofted frustum hollowed by a smaller frustum
(leaving a floor); maze ridges are solid rings and radial bars unioned onto the
floor with a small overlap so each boolean is volumetric. The stand is a ring
solid with a recess. Every result is one manifold solid.

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
target_part = str(PARAM(lambda: target_part, "slow_bowl"))  # slow_bowl | bowl_stand | maze_insert

bowl_dia   = float(PARAM(lambda: bowl_dia,  180.0))   # bowl top inner diameter (mm)
bowl_depth = float(PARAM(lambda: bowl_depth, 55.0))   # bowl inner depth (mm)
wall       = float(PARAM(lambda: wall,        4.0))   # bowl wall / floor thickness
maze_rings = int(  PARAM(lambda: maze_rings,    3))   # number of concentric maze rings
maze_spokes= int(  PARAM(lambda: maze_spokes,   6))   # radial spokes
ridge_h    = float(PARAM(lambda: ridge_h,    22.0))   # maze ridge height
ridge_t    = float(PARAM(lambda: ridge_t,     6.0))   # maze ridge thickness
stand_h    = float(PARAM(lambda: stand_h,    70.0))   # bowl-stand height

# ── Clamps ───────────────────────────────────────────────────────────────────
bowl_dia    = max(80.0, min(bowl_dia, 300.0))
bowl_depth  = max(25.0, min(bowl_depth, 120.0))
wall        = max(2.5,  min(wall, 8.0))
maze_rings  = max(1,    min(maze_rings, 6))
maze_spokes = max(0,    min(maze_spokes, 16))
ridge_h     = max(8.0,  min(ridge_h, min(bowl_depth - 4.0, 60.0)))
ridge_t     = max(3.0,  min(ridge_t, 14.0))
stand_h     = max(25.0, min(stand_h, 160.0))

TOP_R = bowl_dia / 2.0
BOT_R = TOP_R * 0.72          # bowls taper inward toward the base


# ── Helpers ──────────────────────────────────────────────────────────────────
def bowl_body():
    """Lofted frustum bowl with a hollow interior, closed floor."""
    top_out = TOP_R + wall
    bot_out = BOT_R + wall
    total_h = bowl_depth + wall
    outer = (
        cq.Workplane("XY")
        .circle(bot_out)
        .workplane(offset=total_h)
        .circle(top_out)
        .loft(combine=True)
    )
    inner = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall))
        .circle(BOT_R)
        .workplane(offset=bowl_depth + 1.0)
        .circle(TOP_R)
        .loft(combine=True)
    )
    return outer.cut(inner), total_h


def maze_ridges(floor_z, avail_r):
    """Concentric rings + radial spokes rising `ridge_h` from the floor. Returns
    one unioned solid; each ridge overlaps the floor by 1 mm for a clean weld."""
    solids = []
    base_z = floor_z - 1.0
    h = ridge_h + 1.0
    # Concentric rings.
    for i in range(1, maze_rings + 1):
        rr = avail_r * i / (maze_rings + 1)
        ring = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, base_z))
            .circle(rr + ridge_t / 2.0)
            .circle(max(0.4, rr - ridge_t / 2.0))
            .extrude(h)
        )
        solids.append(ring)
    # Central pillar so the middle isn't a wide-open pool.
    pillar = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_z))
        .circle(ridge_t * 0.9)
        .extrude(h)
    )
    solids.append(pillar)
    # Radial spokes.
    for k in range(maze_spokes):
        ang = math.radians(k * 360.0 / max(1, maze_spokes))
        bar = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, base_z))
            .transformed(rotate=cq.Vector(0, 0, math.degrees(ang)))
            .box(avail_r, ridge_t, h, centered=(False, True, False))
        )
        solids.append(bar)
    out = solids[0]
    for s in solids[1:]:
        out = out.union(s)
    return out


# ── Part builders ────────────────────────────────────────────────────────────
def build_slow_bowl():
    body, _th = bowl_body()
    ridges = maze_ridges(wall, TOP_R * 0.92)
    # Trim ridges to the interior so nothing pokes above the rim or through walls.
    keep = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall))
        .circle(TOP_R - 1.0)
        .extrude(ridge_h)
    )
    ridges = ridges.intersect(keep)
    body = body.union(ridges)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_maze_insert():
    """A standalone maze puck: a thin base disc with the same ridges, to drop
    into a plain bowl. Base diameter a touch under the bowl top so it sits low."""
    base_r = TOP_R - 2.0
    base = cq.Workplane("XY").circle(base_r).extrude(wall)
    ridges = maze_ridges(wall, base_r * 0.9)
    keep = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall))
        .circle(base_r - 0.5)
        .extrude(ridge_h)
    )
    ridges = ridges.intersect(keep)
    body = base.union(ridges)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_bowl_stand():
    """A raised ring that cradles the bowl base at a comfortable height. A tube
    with a top recess sized to the bowl's tapered base, and feet flares."""
    ring_or = TOP_R + wall + 6.0
    recess_r = BOT_R + wall + 1.0     # bowl base drops into this recess
    body = cq.Workplane("XY").circle(ring_or).extrude(stand_h)
    # Hollow the centre (material-saving) leaving a shelf the bowl rests on.
    shelf = 6.0
    inner = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(ring_or - wall * 2.0)
        .extrude(stand_h - shelf + 1.0)
    )
    body = body.cut(inner)
    # Top recess so the bowl base seats and can't slide.
    recess = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, stand_h - shelf))
        .circle(recess_r)
        .extrude(shelf + 1.0)
    )
    body = body.cut(recess)
    # Flare the base outward for stability (a short wider ring at the bottom).
    flare = (
        cq.Workplane("XY")
        .circle(ring_or + 8.0)
        .workplane(offset=8.0)
        .circle(ring_or)
        .loft(combine=True)
    )
    body = body.union(flare)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bowl_stand":
    result = build_bowl_stand()
elif target_part == "maze_insert":
    result = build_maze_insert()
else:  # "slow_bowl"
    result = build_slow_bowl()
