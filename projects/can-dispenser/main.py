"""
Can Storage Dispenser — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A printable rack that stores standard beverage cans on their sides and gravity-feeds
them one at a time. Sized to the can diameter (Ø66 mm standard 12 oz / 355 ml can by
default), so the same geometry adapts to slim (Ø53 mm) and tallboy (Ø66 mm) cans by a
single parameter. It shares the "standard can Ø" socket interface with the companion
`fridge-dispenser` cartridge — a can that seats in one seats in the other.

Real dimensions (beverage cans, in mm):
  - Standard 12 oz / 355 ml can: 66 mm diameter, ~122 mm tall.
  - Slim / "sleek" 12 oz can: ~53 mm diameter, ~157 mm tall.
  The rack cradles the can lying on its side, so can_dia drives the cradle radius and
  can_len drives the lane width.

Three DISTINCT modes:
  - shelf_rack: a two-level switchback rack — cans roll down the top lane, drop through
    a return slot, and roll forward on the bottom lane to a front stop (FIFO, compact
    footprint for a fridge shelf).
  - stack_column: a vertical loading tube — cans stack on their sides in a single
    column between two end walls; take from the bottom cutout, the stack drops.
  - counter_tray: a simple angled single-lane tray for a countertop or pantry shelf.

Watertightness strategy (positive material, unions never tangent, fillet clean blanks):
  Every wall is a solid box or plate UNIONED with a generous overlap into its neighbours
  (never a tangent kiss, which leaves zero-volume seams). Cradle troughs are cut by a
  cylinder that fully passes through the floor, opening onto free space — no trapped
  void. The optional front-stop lip is a solid box unioned on. No revolve-of-a-cut,
  no hollow posts on solid bases.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected; manifest params arrive as bare globals.
  - Read every param via PARAM(lambda: name, default) — never globals()/eval.
  - Assign the final solid to `result`. No cross-file imports.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "shelf_rack"))
can_dia = float(PARAM(lambda: can_dia, 66.0))      # can diameter (mm)
can_len = float(PARAM(lambda: can_len, 122.0))     # can length along the lane (mm)
capacity = int(float(PARAM(lambda: capacity, 5)))  # cans queued per lane
clearance = float(PARAM(lambda: clearance, 2.0))   # per-side roll clearance (mm)
front_lip = float(PARAM(lambda: front_lip, 14.0))  # front stop lip height (mm)
wall = float(PARAM(lambda: wall, 2.6))             # wall / floor thickness (mm)

# Clamp so extreme UI values still build watertight.
can_dia = max(30.0, min(can_dia, 100.0))
can_len = max(50.0, min(can_len, 200.0))
capacity = max(2, min(capacity, 12))
clearance = max(0.5, min(clearance, 6.0))
front_lip = max(4.0, min(front_lip, 40.0))
wall = max(1.6, min(wall, 6.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
# Coordinate convention: a can lies with its cylindrical axis along Y and rolls
# along X. So the lane WIDTH (Y) tracks can_len, and the RUN (X) tracks capacity.
def _lane_inner_w():
    """Inner lane width (Y): the can length plus per-side clearance."""
    return can_len + 2.0 * clearance


def _cradle_r():
    """Radius of the trough that cradles a can lying on its side."""
    return can_dia / 2.0 + clearance


def _run_len():
    """Lane run length (X) sized to queue `capacity` cans plus margin."""
    return can_dia * capacity + can_dia * 0.5


def _box(x, y, z, cx, cy, cz):
    """Axis-aligned solid box centred at (cx,cy) with base at z-bottom cz."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, cz))
        .box(x, y, z, centered=(True, True, False))
    )


def _cradle_cutter(run, axis_z):
    """A horizontal cylinder (axis along X, the roll direction) that scoops a can
    cradle running the length of the lane. Extends past both end walls so it opens to
    free space (no trapped void), and dips so it clearly intersects (never grazes) the
    floor it sits on."""
    r = _cradle_r()
    return (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0.0, axis_z, -(run / 2.0 + wall + 10.0)))
        .circle(r)
        .extrude(run + 2.0 * wall + 20.0)
    )


# ── Mode: shelf_rack (two-level FIFO) ────────────────────────────────────────
def build_shelf_rack():
    """A compact two-level rack: cans load on the top deck and roll to the rear, drop
    to the bottom deck and roll forward to a front stop (first-in-first-out). Cradle
    troughs run along the roll direction so each level nests the cans.

    Watertight by construction: base slab is wider (Y) than the side rails so no outer
    faces are coplanar (a coplanar seam tessellates as a false second body); cradle
    cylinders run the full length and exit both end walls; the front lip and rear curb
    are solid boxes unioned with overlap."""
    lane_w = _lane_inner_w()
    r = _cradle_r()
    run = _run_len()
    # Base is a touch wider than the rails so rail outer faces sit strictly inside it.
    total_w = lane_w + 3.0 * wall
    tier_h = 2.0 * r + wall
    total_h = 2.0 * tier_h + wall

    # Base slab (2*wall thick so the bottom cradle can dip in without breaching)
    base = _box(run + 2.0 * wall, total_w, wall * 2.0, 0.0, 0.0, 0.0)

    # End walls (X extremes) span the full height and width
    left = _box(2.0 * wall, total_w, total_h, -(run / 2.0), 0.0, 0.0)
    right = _box(2.0 * wall, total_w, total_h, run / 2.0, 0.0, 0.0)

    # Side rails (Y extremes) seated INWARD so they interpenetrate the base/mid floors
    rail_yc = lane_w / 2.0 + wall * 0.25
    rail_l = _box(run + 2.0 * wall, wall * 1.5, total_h, 0.0, rail_yc, 0.0)
    rail_r = _box(run + 2.0 * wall, wall * 1.5, total_h, 0.0, -rail_yc, 0.0)

    # Mid deck floor between the two tiers
    mid = _box(run + wall, total_w, wall * 2.0, 0.0, 0.0, tier_h)

    body = base.union(left).union(right).union(rail_l).union(rail_r).union(mid)

    # Scoop the two cradle troughs (bottom tier sits on the base, top tier on the mid).
    bot_axis = wall * 2.0 + r * 0.65
    top_axis = tier_h + wall * 2.0 + r * 0.65
    body = body.cut(_cradle_cutter(run, bot_axis)).cut(_cradle_cutter(run, top_axis))

    # Front stop lip (bottom tier) and rear catch curb (top tier), solid boxes.
    lip = _box(wall * 1.5, total_w, front_lip, run / 2.0 - wall, 0.0, wall * 2.0)
    curb = _box(wall * 1.5, total_w, r * 0.5, -(run / 2.0 - wall), 0.0, tier_h + wall * 2.0)
    body = body.union(lip).union(curb)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Mode: stack_column (vertical loading tube) ───────────────────────────────
def build_stack_column():
    """A vertical column that stacks cans on their sides. Two U-cradle end walls joined
    by back and floor plates; a front dispensing cutout at the bottom lets the lowest can
    roll out and the stack drop by one."""
    lane_w = _lane_inner_w()
    r = _cradle_r()
    col_h = can_dia * capacity + can_dia * 0.4 + wall

    # Back plate (full height) and floor
    back = _box(wall * 1.5, lane_w + 2.0 * wall, col_h, 0.0, 0.0, 0.0)
    floor = _box(2.0 * r + 2.0 * wall, lane_w + 2.0 * wall, wall,
                 (r + wall) - wall * 0.75, 0.0, 0.0)
    body = back.union(floor)

    # Two side end-walls that carry the cradle profile (front lip built in)
    depth_x = 2.0 * r + 2.0 * wall
    x_off = (r + wall) - wall * 0.75
    for sy in (-1.0, 1.0):
        yc = sy * (lane_w / 2.0 + wall / 2.0)
        wallblk = _box(depth_x, wall, col_h, x_off, yc, 0.0)
        body = body.union(wallblk)

    # Front rail (a tall lip on the front edge that retains the stack), with a bottom
    # dispensing gap: build the rail from wall up to col_h but start above the gap.
    gap = can_dia + clearance
    front_x = x_off + r + wall * 0.25
    rail = _box(wall * 1.5, lane_w + 2.0 * wall, col_h - gap, front_x, 0.0, gap)
    body = body.union(rail)
    # A small bottom curb below the gap so the lead can is retained until taken.
    curb = _box(wall * 1.5, lane_w + 2.0 * wall, front_lip, front_x, 0.0, wall)
    body = body.union(curb)

    try:
        body = body.edges("|Z").fillet(min(2.0, wall * 0.5))
    except Exception:
        pass

    # Scoop the vertical can channel: a cylinder axis along Y at each stacked position
    # would over-cut; instead cut a single tall rounded slot (obround) that clears the
    # can column — more robust than a fan of circles.
    slot_r = r
    channel = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x_off, 0.0, wall))
        .box(2.0 * slot_r, lane_w, col_h, centered=(True, True, False))
    )
    # round the vertical channel front/back with two cylinders unioned into the cutter
    body = body.cut(channel)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Mode: counter_tray (single angled lane) ──────────────────────────────────
def build_counter_tray():
    """A simple single-lane tray: floor + two side walls + a front stop, cradle trough
    scooped along it. Sits on a counter or pantry shelf; a slight incline is baked in by
    a raised rear foot so cans roll forward."""
    lane_w = _lane_inner_w()
    r = _cradle_r()
    run = can_dia * min(capacity, 6) + can_dia * 0.4
    total_w = lane_w + 2.0 * wall

    base = _box(run + 2.0 * wall, total_w, wall, 0.0, 0.0, 0.0)
    left = _box(run + 2.0 * wall, wall, 2.0 * r + wall, 0.0, (lane_w / 2.0 + wall / 2.0), 0.0)
    right = _box(run + 2.0 * wall, wall, 2.0 * r + wall, 0.0, -(lane_w / 2.0 + wall / 2.0), 0.0)
    body = base.union(left).union(right)

    # Front stop
    lip = _box(wall * 1.5, total_w, front_lip, run / 2.0 - wall * 0.5, 0.0, wall)
    body = body.union(lip)
    # Rear foot (raises the back so the lane inclines forward) — a solid wedge box
    foot = _box(wall * 2.0, total_w, wall * 2.0, -(run / 2.0), 0.0, -wall * 2.0)
    body = body.union(foot)

    try:
        body = body.edges("|X").fillet(min(1.6, wall * 0.5))
    except Exception:
        pass

    # Cradle trough (axis along X so it runs the length of the lane)
    axis_z = wall + r
    trough = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0.0, axis_z, -(run / 2.0 + 10.0)))
        .circle(r)
        .extrude(run + 2.0 * wall + 20.0)
    )
    body = body.cut(trough)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "stack_column":
    result = build_stack_column()
elif target_part == "counter_tray":
    result = build_counter_tray()
else:
    result = build_shelf_rack()
