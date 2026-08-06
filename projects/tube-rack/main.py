"""
Test-Tube / Vial Rack — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An organizer block that holds round test tubes or vials in a cols x rows grid of
bores. Choose whether the bores are blind cradles (a partial well the tube rests
in) or through-holes (so tubes drain and dry). A small linear single-row rack is
available for benchtop use.

  * "rack"        — a block with a grid of blind tube cradles + rubber feet
                    (target_part == "rack").
  * "rack_drain"  — the same grid bored ALL THE WAY THROUGH so washed tubes drain
                    and air-dry (target_part == "rack_drain").
  * "single_row"  — a compact linear rack, one row of cradles (target_part ==
                    "single_row").

Watertight strategy: the body is a solid block; blind cradles are flat-bottom
recesses that always leave a floor beneath them, through-bores are full
manifold cuts, and a tiny drainage hole (optional) is a clean cylinder from the
cradle floor to the underside. Feet are unioned solid pads.

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
target_part = str(PARAM(lambda: target_part, "rack"))  # rack | rack_drain | single_row

tube_dia   = float(PARAM(lambda: tube_dia,   16.0))   # tube / vial body diameter (mm)
cols       = int(  PARAM(lambda: cols,           6))   # tubes across (X)
rows       = int(  PARAM(lambda: rows,           4))   # tubes deep (Y)
well_pitch = float(PARAM(lambda: well_pitch,  0.0))    # centre spacing; 0 = auto from dia
well_depth = float(PARAM(lambda: well_depth, 30.0))    # cradle depth (blind modes)
clearance  = float(PARAM(lambda: clearance,   0.8))    # radial slip gap
wall       = float(PARAM(lambda: wall,        3.0))    # material around/between bores
floor      = float(PARAM(lambda: floor,       3.0))    # solid base under blind cradles
feet       = bool( PARAM(lambda: feet,       True))    # add corner feet
drain      = bool( PARAM(lambda: drain,     False))    # tiny drain hole per blind cradle

# ── Clamps ───────────────────────────────────────────────────────────────────
tube_dia   = max(5.0,  min(tube_dia, 60.0))
cols       = max(1,    min(cols, 16))
rows       = max(1,    min(rows, 12))
well_depth = max(5.0,  min(well_depth, 120.0))
clearance  = max(0.0,  min(clearance, 3.0))
wall       = max(2.0,  min(wall, 12.0))
floor      = max(2.0,  min(floor, 12.0))

bore_dia = tube_dia + 2.0 * clearance          # actual bore diameter
# Auto pitch = bore + wall; a user pitch is honoured but never tighter than that.
pitch = well_pitch if well_pitch > 0.0 else (bore_dia + wall)
pitch = max(pitch, bore_dia + 1.2)             # keep at least a thin wall between
DRAIN_DIA = 3.0                                # drainage hole diameter


# ── Shared helpers (reused across tube-rack / petri-rack family) ──────────────
def block(w, d, h, z0=0.0):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .box(w, d, h, centered=(True, True, False))
    )


def grid_points(nx, ny, px, py):
    """Centres of an nx x ny grid centred on the origin."""
    pts = []
    x0 = -((nx - 1) * px) / 2.0
    y0 = -((ny - 1) * py) / 2.0
    for r in range(ny):
        for c in range(nx):
            pts.append((x0 + c * px, y0 + r * py))
    return pts


def bore_array(pts, dia, z0, depth):
    """A union of vertical cylinders (the cutter for a bore grid)."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .pushPoints(pts)
        .circle(dia / 2.0)
        .extrude(depth)
    )


def corner_feet(w, d, foot_h):
    """Four small cylindrical feet inset from the block corners."""
    fr = max(3.0, wall)
    ix = w / 2.0 - fr - 1.0
    iy = d / 2.0 - fr - 1.0
    if ix <= 0 or iy <= 0:
        return None
    pads = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -foot_h))
        .pushPoints([(-ix, -iy), (ix, -iy), (-ix, iy), (ix, iy)])
        .circle(fr)
        .extrude(foot_h)
    )
    return pads


def _rack(nx, ny, through):
    """Core builder. `through` => bores pass fully through (drain/dry)."""
    body_h = well_depth + floor
    body_w = nx * pitch + wall
    body_d = ny * pitch + wall
    body = block(body_w, body_d, body_h)

    pts = grid_points(nx, ny, pitch, pitch)
    if through:
        cutter = bore_array(pts, bore_dia, -1.0, body_h + 2.0)
        body = body.cut(cutter)
    else:
        # Blind cradles: recess from the top, leaving `floor` beneath.
        cutter = bore_array(pts, bore_dia, floor, well_depth + 1.0)
        body = body.cut(cutter)
        if drain:
            # A narrow drain from each cradle floor straight down through the base.
            dr = bore_array(pts, DRAIN_DIA, -1.0, floor + 2.0)
            body = body.cut(dr)

    if feet:
        pads = corner_feet(body_w, body_d, 3.0)
        if pads is not None:
            body = body.union(pads)

    # Soften the top outer rim; non-fatal if degenerate.
    try:
        body = body.edges(">Z").edges("|Z").fillet(min(1.2, wall * 0.3))
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "rack_drain":
    result = _rack(cols, rows, through=True)
elif target_part == "single_row":
    # A compact linear rack: force one row, blind cradles.
    result = _rack(cols, 1, through=False)
else:  # "rack"
    result = _rack(cols, rows, through=False)
