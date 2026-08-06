"""
Paint Rack — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A hobby paint rack with cradle holes sized to the chosen bottle: Citadel pots
(34 mm), Vallejo droppers (30 mm) or Army Painter droppers (29 mm). Flat, tiered
(stepped so back rows stay visible) and wall-mounted variants.

Three parts (dispatched via `target_part`):
  * "flat_rack"   — a slab with a grid of blind cradle recesses for bottles.
  * "tiered_rack" — a staircase of rows, each row raised behind the one in front so
                    every label is visible; each step holds a row of bottles.
  * "wall_rack"   — a vertical back plate with a single forward shelf of cradles for
                    wall mounting (screw holes in the back plate).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `bottle`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.

Watertight strategy: every rack is a solid block (or union of solid step blocks)
with BLIND cradle recesses cut from the top — never through the floor. The wall
plate's screw holes go fully through a wall face (a clean through-hole keeps the
solid manifold). No sphere-tangent unions; recesses stay open at the top only.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Bottle diameters (mm) — cradle hole is diameter + fit clearance. ─────────
_BOTTLES = {
    "citadel": 34.0,       # Citadel base pot
    "vallejo": 30.0,       # Vallejo dropper
    "army-painter": 29.0,  # Army Painter dropper
}


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "flat_rack"))   # flat_rack|tiered_rack|wall_rack
bottle      = str(PARAM(lambda: bottle,       "citadel"))    # citadel|vallejo|army-painter

cols        = int(  PARAM(lambda: cols,         5))   # bottles per row
rows        = int(  PARAM(lambda: rows,         3))   # number of rows
hole_clear  = float(PARAM(lambda: hole_clear, 1.5))   # per-side clearance around bottle (mm)
recess      = float(PARAM(lambda: recess,     8.0))   # cradle recess depth (mm)
gap         = float(PARAM(lambda: gap,        4.0))   # wall between holes (mm)
margin      = float(PARAM(lambda: margin,     6.0))   # rack border (mm)
base_th     = float(PARAM(lambda: base_th,    4.0))   # solid floor thickness under the recess (mm)

step_rise   = float(PARAM(lambda: step_rise, 16.0))   # tiered: height added per row back (mm)
step_run    = float(PARAM(lambda: step_run,  0.0))    # tiered: extra depth per row (0 = auto)

wall_h      = float(PARAM(lambda: wall_h,    60.0))   # wall_rack back-plate height (mm)
wall_th     = float(PARAM(lambda: wall_th,    5.0))   # wall_rack back-plate thickness (mm)
screw_d     = float(PARAM(lambda: screw_d,    4.5))   # wall_rack screw hole diameter (mm)

# ── Clamp to sane ranges so extreme UI values still build watertight. ────────
cols        = max(1, min(cols, 10))
rows        = max(1, min(rows, 8))
hole_clear  = max(0.4, min(hole_clear, 4.0))
recess      = max(3.0, min(recess, 30.0))
gap         = max(1.5, min(gap, 12.0))
margin      = max(3.0, min(margin, 20.0))
base_th     = max(2.0, min(base_th, 10.0))
step_rise   = max(6.0, min(step_rise, 40.0))
wall_h      = max(30.0, min(wall_h, 160.0))
wall_th     = max(3.0, min(wall_th, 10.0))
screw_d     = max(2.5, min(screw_d, 8.0))


def _hole_d():
    dia = _BOTTLES.get(bottle, 34.0)
    return dia + 2.0 * hole_clear


def _cradles(cx_list, cy, top_z, depth):
    """Union of blind cylindrical recesses at (x, cy) for each x, cut downward from
    top_z by `depth`. Returns the cutter body (or None)."""
    hd = _hole_d()
    cutters = None
    for x in cx_list:
        pk = (
            cq.Workplane("XY").workplane(offset=top_z - depth)
            .center(x, cy).circle(hd / 2.0).extrude(depth + 0.5)
        )
        cutters = pk if cutters is None else cutters.union(pk)
    return cutters


def _row_x(n):
    hd = _hole_d()
    pitch = hd + gap
    x0 = -((n - 1) * pitch) / 2.0
    return [x0 + i * pitch for i in range(n)]


def _cell_pitch():
    return _hole_d() + gap


# ── Flat rack ──────────────────────────────────────────────────────────────────
def build_flat_rack():
    pitch = _cell_pitch()
    plate_w = cols * pitch - gap + 2.0 * margin
    plate_d = rows * pitch - gap + 2.0 * margin
    plate_h = recess + base_th
    body = cq.Workplane("XY").box(plate_w, plate_d, plate_h, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(margin, 4.0))
    except Exception:
        pass

    xs = _row_x(cols)
    y0 = -((rows - 1) * pitch) / 2.0
    cutters = None
    for r in range(rows):
        cy = y0 + r * pitch
        c = _cradles(xs, cy, plate_h, recess)
        if c is not None:
            cutters = c if cutters is None else cutters.union(c)
    if cutters is not None:
        body = body.cut(cutters)
    return body


# ── Tiered rack (staircase) ────────────────────────────────────────────────────
def build_tiered_rack():
    """A real staircase: each row is its own tread block (depth `run`) at an
    increasing Y and height, standing on the shared z=0 floor. Adjacent treads butt
    front-to-back on a coincident vertical face, so the union is a single manifold.
    Each cradle cuts into its own EXPOSED tread top — the taller tread behind starts
    at a larger Y and never overhangs, so no recess becomes a sealed internal void."""
    pitch = _cell_pitch()
    run = step_run if step_run > 0.05 else pitch          # depth of each tread
    plate_w = cols * pitch - gap + 2.0 * margin
    xs = _row_x(cols)

    y_front = -(rows * run) / 2.0                          # front edge of the whole rack
    body = None
    step_tops = []
    for r in range(rows):
        step_h = base_th + recess + r * step_rise         # each row taller than the one ahead
        cy = y_front + r * run + run / 2.0
        # Overlap each tread 0.02 mm into the next so the union is watertight even if
        # the coincident face is numerically fussy (never enough to overhang a recess).
        depth = run + (0.0 if r == rows - 1 else 0.02)
        block = (
            cq.Workplane("XY")
            .center(0, cy + (0.0 if r == rows - 1 else 0.01))
            .box(plate_w, depth, step_h, centered=(True, True, False))
        )
        body = block if body is None else body.union(block)
        step_tops.append((cy, step_h))

    # Cut one row of cradles into each tread's own exposed top.
    cutters = None
    for cy, step_h in step_tops:
        c = _cradles(xs, cy, step_h, recess)
        if c is not None:
            cutters = c if cutters is None else cutters.union(c)
    if cutters is not None and body is not None:
        body = body.cut(cutters)
    return body


# ── Wall rack ───────────────────────────────────────────────────────────────────
def build_wall_rack():
    pitch = _cell_pitch()
    plate_w = cols * pitch - gap + 2.0 * margin
    hd = _hole_d()
    shelf_d = hd + 2.0 * margin
    shelf_h = recess + base_th

    # Back plate (vertical), standing on the shelf back edge.
    back = (
        cq.Workplane("XY")
        .center(0, -shelf_d / 2.0 + wall_th / 2.0)
        .box(plate_w, wall_th, wall_h, centered=(True, True, False))
    )
    # Forward shelf at the bottom.
    shelf = cq.Workplane("XY").box(plate_w, shelf_d, shelf_h, centered=(True, True, False))
    body = shelf.union(back)

    # Cradles in the shelf top (single forward row).
    xs = _row_x(cols)
    cutters = _cradles(xs, 0.0, shelf_h, recess)
    if cutters is not None:
        body = body.cut(cutters)

    # Two screw holes through the back plate near the top corners.
    sy = -shelf_d / 2.0 + wall_th / 2.0
    sz = wall_h - max(8.0, wall_h * 0.15)
    sx = plate_w / 2.0 - max(8.0, margin + screw_d)
    screws = None
    for xsig in (-1.0, 1.0):
        hole = (
            cq.Workplane("XZ")
            .workplane(offset=-sy - wall_th)          # in front of the back plate
            .center(xsig * sx, sz)
            .circle(screw_d / 2.0)
            .extrude(wall_th + 2.0)
        )
        screws = hole if screws is None else screws.union(hole)
    if screws is not None:
        body = body.cut(screws)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tiered_rack":
    result = build_tiered_rack()
elif target_part == "wall_rack":
    result = build_wall_rack()
else:
    result = build_flat_rack()
