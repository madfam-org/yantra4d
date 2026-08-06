"""
Dice Tower — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A dice tower with internal angled baffles that tumble the dice for a fair,
un-scoopable roll, plus a matching catch tray. Dice drop in the open top, ricochet
down an alternating stack of ramps, and roll out a front window into the tray.

Three parts (dispatched via `target_part`):
  * "tower"         — the full tower: a four-wall chimney (open top, closed floor),
                      a front exit window, and N alternating angled baffles.
  * "tray"          — a shallow rolling / catch tray with a raised rim.
  * "compact_tower" — a shorter, smaller-footprint tower for travel (fewer baffles).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `tower_h`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.

Watertight strategy: the tower is a closed-floor cup (an outer prism with a blind
interior cavity) — a single closed manifold. The dice exit is a rectangular window
cut fully through ONE wall face (never a rim notch), so no open edges are created.
Baffles are solid wedges unioned to the inner walls (their outer faces are buried in
the shell). The tray is a solid box with a blind recess. No sphere-tangent unions.
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
target_part = str(PARAM(lambda: target_part, "tower"))   # tower|tray|compact_tower

tower_h     = float(PARAM(lambda: tower_h,   150.0))  # tower height (mm)
bore        = float(PARAM(lambda: bore,       55.0))  # interior clear width/depth (mm)
wall        = float(PARAM(lambda: wall,        3.0))  # wall thickness (mm)
baffles     = int(  PARAM(lambda: baffles,       4))  # number of angled ramps
baffle_slope = float(PARAM(lambda: baffle_slope, 35.0))  # ramp angle from horizontal (deg)

tray_w      = float(PARAM(lambda: tray_w,    120.0))  # tray outer width (mm)
tray_d      = float(PARAM(lambda: tray_d,     90.0))  # tray outer depth (mm)
tray_wall   = float(PARAM(lambda: tray_wall,   3.0))  # tray wall thickness (mm)
tray_rim    = float(PARAM(lambda: tray_rim,   16.0))  # tray rim height (mm)
tray_floor  = float(PARAM(lambda: tray_floor,  2.5))  # tray floor thickness (mm)

# ── Clamp to sane ranges so extreme UI values still build watertight. ────────
tower_h      = max(70.0, min(tower_h, 260.0))
bore         = max(30.0, min(bore, 110.0))
wall         = max(2.0, min(wall, 6.0))
baffles      = max(2, min(baffles, 8))
baffle_slope = max(20.0, min(baffle_slope, 55.0))
tray_w       = max(60.0, min(tray_w, 220.0))
tray_d       = max(50.0, min(tray_d, 200.0))
tray_wall    = max(2.0, min(tray_wall, 6.0))
tray_rim     = max(6.0, min(tray_rim, 40.0))
tray_floor   = max(1.5, min(tray_floor, 6.0))


# ── Tower ─────────────────────────────────────────────────────────────────────
def _tower_shell(height, inner, w, floor_t):
    """Closed-floor cup: outer prism minus a blind interior cavity (single manifold)."""
    outer = inner + 2.0 * w
    body = cq.Workplane("XY").box(outer, outer, height, centered=(True, True, False))
    cavity = (
        cq.Workplane("XY").workplane(offset=floor_t)
        .box(inner, inner, height, centered=(True, True, False))  # opens at the top only
    )
    return body.cut(cavity), outer


def _exit_window(shell, outer, inner, w, height):
    """Cut a rectangular exit fully THROUGH the front (-Y) wall near the base.
    The cut is inset from the wall's side and top edges so no rim notch / open
    edge is produced — the shell stays watertight."""
    win_w = inner * 0.8
    win_h = min(inner * 0.7, height * 0.32)
    z0 = 2.0                       # small sill above the floor
    cutter = (
        cq.Workplane("XZ")         # plane facing -Y; box extrudes in +Y by default via .box
        .workplane(offset=-outer / 2.0 - 1.0)
        .center(0, z0 + win_h / 2.0)
        .box(win_w, win_h, w + 2.0, centered=(True, True, False))
    )
    return shell.cut(cutter)


def _baffle_stack(inner, w, height, floor_t, n, slope_deg):
    """A stack of solid angled ramps alternating side to side. Each ramp is a
    triangular prism (a wedge) spanning the full interior depth, its high edge
    against one wall and its low edge past the centre so dice always fall onto the
    next ramp. Ramps are unioned into the shell."""
    slope = math.radians(slope_deg)
    span = inner * 0.72                      # horizontal reach of each ramp
    rise = span * math.tan(slope)            # vertical rise across that reach
    thick = max(1.6, w * 0.9)                # ramp material thickness (along normal)
    depth = inner + 2.0 * w                  # bury ends inside the walls

    top_z = height * 0.82
    bot_z = floor_t + max(8.0, height * 0.10)
    if n > 1:
        dz = (top_z - bot_z) / (n - 1)
    else:
        dz = 0.0

    ramps = None
    for i in range(n):
        z = top_z - i * dz
        side = -1.0 if (i % 2 == 0) else 1.0   # alternate which wall the ramp starts at
        # Build a right-triangle profile in the XZ plane, then extrude along Y.
        x_high = side * (inner / 2.0 - 0.5)    # high corner at the wall
        x_low = -side * (inner * 0.20)         # low corner past centre
        pts = [
            (x_high, z),
            (x_low, z - rise),
            (x_low, z - rise - thick),
            (x_high, z - thick),
        ]
        ramp = (
            cq.Workplane("XZ")
            .polyline(pts).close()
            .extrude(depth)
            .translate((0, depth / 2.0, 0))    # centre the extrusion on Y=0
        )
        ramps = ramp if ramps is None else ramps.union(ramp)
    return ramps


def build_tower(height, inner, n):
    floor_t = max(2.5, wall)
    shell, outer = _tower_shell(height, inner, wall, floor_t)
    shell = _exit_window(shell, outer, inner, wall, height)
    stack = _baffle_stack(inner, wall, height, floor_t, n, baffle_slope)
    if stack is not None:
        # Intersect the ramps with the interior column so nothing pokes out, then union.
        column = (
            cq.Workplane("XY").workplane(offset=floor_t)
            .box(inner, inner, height, centered=(True, True, False))
        )
        try:
            stack = stack.intersect(column)
            shell = shell.union(stack)
        except Exception:
            pass
    return shell


# ── Tray ──────────────────────────────────────────────────────────────────────
def build_tray():
    """A shallow catch/rolling tray: solid slab with a blind rectangular recess and
    a filleted outer rim (a watertight cup)."""
    body = cq.Workplane("XY").box(tray_w, tray_d, tray_rim, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(tray_wall * 2.0, 8.0))
    except Exception:
        pass
    recess = (
        cq.Workplane("XY").workplane(offset=tray_floor)
        .box(tray_w - 2.0 * tray_wall, tray_d - 2.0 * tray_wall, tray_rim, centered=(True, True, False))
    )
    try:
        recess = recess.edges("|Z").fillet(min(tray_wall, 4.0))
    except Exception:
        pass
    return body.cut(recess)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tray":
    result = build_tray()
elif target_part == "compact_tower":
    result = build_tower(max(70.0, tower_h * 0.6), max(30.0, bore * 0.8), max(2, min(baffles, 3)))
else:
    result = build_tower(tower_h, bore, baffles)
