"""
Cuvette / Vial Rack — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A benchtop rack that holds spectrophotometer cuvettes (the standard 10 mm square
footprint) and/or round sample vials in a cols x rows grid of pockets. Cuvette
pockets are square; vial pockets are round; a combo rack offers a block of each.

  * "rack"       — a grid of square 10 mm cuvette pockets (target_part == "rack").
  * "vial_rack"  — a grid of round vial pockets (target_part == "vial_rack").
  * "combo_rack" — cuvettes on one half, round vials on the other
                   (target_part == "combo_rack").

Watertight strategy: the body is one solid block; every pocket is a blind recess
that leaves a solid floor beneath, so the result is always a single manifold
solid. A finger cut-out on one side eases removal.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
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


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "rack"))  # rack | vial_rack | combo_rack

cuvette     = float(PARAM(lambda: cuvette,   10.0))   # cuvette square footprint (mm)
vial_dia    = float(PARAM(lambda: vial_dia,  12.0))   # round vial diameter (mm)
cols        = int(  PARAM(lambda: cols,          6))  # pockets across (X)
rows        = int(  PARAM(lambda: rows,          4))  # pockets deep (Y)
clearance   = float(PARAM(lambda: clearance,  0.4))   # slip gap per side
wall        = float(PARAM(lambda: wall,       3.0))   # material between/around pockets
depth       = float(PARAM(lambda: depth,     22.0))   # pocket depth
floor       = float(PARAM(lambda: floor,      3.0))   # solid base under pockets

# ── Clamps ───────────────────────────────────────────────────────────────────
cuvette     = max(6.0,  min(cuvette, 20.0))
vial_dia    = max(5.0,  min(vial_dia, 40.0))
cols        = max(1,    min(cols, 16))
rows        = max(1,    min(rows, 12))
clearance   = max(0.0,  min(clearance, 2.0))
wall        = max(2.0,  min(wall, 10.0))
depth       = max(6.0,  min(depth, 80.0))
floor       = max(2.0,  min(floor, 12.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def grid_points(nx, ny, px, py):
    """Centres of an nx x ny grid centred on the origin."""
    pts = []
    x0 = -((nx - 1) * px) / 2.0
    y0 = -((ny - 1) * py) / 2.0
    for r in range(ny):
        for c in range(nx):
            pts.append((x0 + c * px, y0 + r * py))
    return pts


def square_pockets(pts, side, z0):
    """Union of square blind pockets (the cutter)."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .pushPoints(pts)
        .rect(side, side)
        .extrude(depth + 1.0)
    )


def round_pockets(pts, dia, z0):
    """Union of round blind pockets (the cutter)."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .pushPoints(pts)
        .circle(dia / 2.0)
        .extrude(depth + 1.0)
    )


def base_block(w, d):
    body_h = depth + floor
    return cq.Workplane("XY").box(w, d, body_h, centered=(True, True, False)), body_h


def finger_cutout(body, w, d, body_h):
    """A shallow scoop on the front face so pockets are easy to grab."""
    try:
        scoop = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, -d / 2.0, body_h))
            .circle(w * 0.18)
            .extrude(-(depth * 0.6))
        )
        body = body.cut(scoop)
    except Exception:
        pass
    return body


def build_rack():
    """Square cuvette pockets."""
    pitch = cuvette + 2.0 * clearance + wall
    pw = cols * pitch + wall
    pd = rows * pitch + wall
    body, body_h = base_block(pw, pd)
    pts = grid_points(cols, rows, pitch, pitch)
    body = body.cut(square_pockets(pts, cuvette + 2.0 * clearance, floor))
    body = finger_cutout(body, pw, pd, body_h)
    return _soften(body)


def build_vial_rack():
    """Round vial pockets."""
    bore = vial_dia + 2.0 * clearance
    pitch = bore + wall
    pw = cols * pitch + wall
    pd = rows * pitch + wall
    body, body_h = base_block(pw, pd)
    pts = grid_points(cols, rows, pitch, pitch)
    body = body.cut(round_pockets(pts, bore, floor))
    body = finger_cutout(body, pw, pd, body_h)
    return _soften(body)


def build_combo_rack():
    """A block split in Y: the back rows are square cuvette pockets, the front
    rows are round vial pockets."""
    cuv_side = cuvette + 2.0 * clearance
    bore = vial_dia + 2.0 * clearance
    pitch = max(cuv_side, bore) + wall
    half = max(1, rows // 2)
    pw = cols * pitch + wall
    pd = rows * pitch + wall
    body, body_h = base_block(pw, pd)

    # Y centres for back (cuvette) rows and front (vial) rows.
    y0 = -((rows - 1) * pitch) / 2.0
    all_y = [y0 + r * pitch for r in range(rows)]
    x0 = -((cols - 1) * pitch) / 2.0
    xs = [x0 + c * pitch for c in range(cols)]

    cuv_pts = [(x, y) for y in all_y[half:] for x in xs]  # back half → cuvettes
    vial_pts = [(x, y) for y in all_y[:half] for x in xs]  # front half → vials

    if cuv_pts:
        body = body.cut(square_pockets(cuv_pts, cuv_side, floor))
    if vial_pts:
        body = body.cut(round_pockets(vial_pts, bore, floor))
    body = finger_cutout(body, pw, pd, body_h)
    return _soften(body)


def _soften(body):
    try:
        body = body.edges(">Z").edges("|Z").fillet(min(1.2, wall * 0.3))
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "vial_rack":
    result = build_vial_rack()
elif target_part == "combo_rack":
    result = build_combo_rack()
else:  # "rack"
    result = build_rack()
