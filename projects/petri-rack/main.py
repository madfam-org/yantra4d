"""
Petri / Sample Storage Rack — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Racks that store or stack petri dishes (or round sample containers). Set the dish
diameter and how many slots, and choose how the dishes are held.

  * "edge_rack"    — a base with parallel vertical slots; dishes stand on edge in
                     the slots like records (target_part == "edge_rack").
  * "stack_holder" — an open ring frame that holds one vertical stack of dishes,
                     with cutaway windows to see and grab them
                     (target_part == "stack_holder").
  * "drying_rack"  — a base carrying a row of low ring pedestals; an inverted dish
                     sits on each to air-dry (target_part == "drying_rack").

Watertight strategy: bases are solid slabs; edge slots are through-channels cut in
raised comb walls; the stack ring is a solid tube with window cut-outs that never
disconnect it; drying pedestals are solid rings unioned to the base. Each result
is one manifold solid.

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
target_part = str(PARAM(lambda: target_part, "edge_rack"))  # edge_rack|stack_holder|drying_rack
orientation = str(PARAM(lambda: orientation, "vertical"))   # vertical | stacked (mirror)

dish_dia   = float(PARAM(lambda: dish_dia,  90.0))    # petri dish diameter (mm)
dish_h     = float(PARAM(lambda: dish_h,    15.0))    # dish height (used for slot depth / stack)
stacks     = int(  PARAM(lambda: stacks,       6))    # number of slots / stack capacity
clearance  = float(PARAM(lambda: clearance,  1.5))    # slot / ring clearance
wall       = float(PARAM(lambda: wall,       3.0))    # comb / ring wall thickness
slot_gap   = float(PARAM(lambda: slot_gap,   4.0))    # slot channel width (dish + lid stack)

# ── Clamps ───────────────────────────────────────────────────────────────────
dish_dia   = max(30.0, min(dish_dia, 150.0))
dish_h     = max(6.0,  min(dish_h, 40.0))
stacks     = max(1,    min(stacks, 20))
clearance  = max(0.5,  min(clearance, 4.0))
wall       = max(2.0,  min(wall, 8.0))
slot_gap   = max(2.5,  min(slot_gap, 20.0))

DISH_R = dish_dia / 2.0


# ── Shared helpers ────────────────────────────────────────────────────────────
def slab(w, d, h, z0=0.0):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .box(w, d, h, centered=(True, True, False))
    )


def build_edge_rack():
    """Dishes stand on edge in parallel slots. A solid base carries two comb walls
    (front and back) whose aligned notches form the slots; the dish rim drops into
    a notch and is held upright."""
    pitch = slot_gap + wall
    base_l = stacks * pitch + wall
    hold_h = min(dish_dia * 0.45, 55.0)     # how far up the dish is cradled
    base_d = dish_dia * 0.7                  # footprint depth
    base_t = 4.0

    # Solid base.
    body = slab(base_l, base_d, base_t)

    # Two comb walls near the front and back edges. Each is a tall slab with
    # rectangular notches cut down from the top to form the dish slots. A
    # semicircular cradle at the notch bottom matches the dish rim.
    for sign in (-1.0, 1.0):
        y = sign * (base_d / 2.0 - wall / 2.0)
        comb = slab(base_l, wall, hold_h, z0=base_t).translate((0, y, 0))
        # Cut a slot per dish.
        x0 = -((stacks - 1) * pitch) / 2.0
        notches = None
        for i in range(stacks):
            x = x0 + i * pitch
            notch = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x, y, base_t + hold_h * 0.35))
                .box(slot_gap + clearance, wall + 2.0, hold_h, centered=(True, True, False))
            )
            notches = notch if notches is None else notches.union(notch)
        if notches is not None:
            comb = comb.cut(notches)
        body = body.union(comb)
    return body


def build_stack_holder():
    """An open ring tube that holds a vertical stack of dishes, with tall windows
    cut in the wall to see and pull dishes out."""
    inner_r = DISH_R + clearance
    outer_r = inner_r + wall
    height = min(stacks * dish_h + wall, 300.0)
    floor = 3.0

    # Solid tube with a base floor.
    body = cq.Workplane("XY").circle(outer_r).extrude(height)
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor))
        .circle(inner_r)
        .extrude(height)
    )
    body = body.cut(bore)

    # Three vertical windows (leave 3 solid posts so the ring stays connected).
    win_h = height - 2.0 * wall
    for k in range(3):
        ang = math.radians(60.0 + k * 120.0)
        # A radial box wider than the wall, centred on the ring wall.
        cx = (inner_r + wall) * math.cos(ang)
        cy = (inner_r + wall) * math.sin(ang)
        window = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, wall + win_h / 2.0), rotate=cq.Vector(0, 0, math.degrees(ang)))
            .box(2.0 * wall + 4.0, outer_r * 0.9, win_h, centered=(True, True, True))
        )
        body = body.cut(window)
    return body


def build_drying_rack():
    """A base with a row of low ring pedestals; an inverted dish rests on each ring
    so condensation drains and it air-dries."""
    pitch = dish_dia + wall + 2.0
    base_l = stacks * pitch + wall
    base_d = dish_dia + 2.0 * wall
    base_t = 4.0
    body = slab(base_l, base_d, base_t)

    ring_h = 8.0
    ring_outer = DISH_R + clearance + wall
    ring_inner = DISH_R + clearance
    x0 = -((stacks - 1) * pitch) / 2.0
    for i in range(stacks):
        x = x0 + i * pitch
        ring = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, 0, base_t))
            .circle(ring_outer)
            .circle(ring_inner)
            .extrude(ring_h)
        )
        body = body.union(ring)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_part = target_part
# Mirror the orientation selector: "stacked" implies the stack holder.
if _part == "edge_rack" and orientation == "stacked":
    _part = "stack_holder"

if _part == "stack_holder":
    result = build_stack_holder()
elif _part == "drying_rack":
    result = build_drying_rack()
else:  # "edge_rack"
    result = build_edge_rack()
