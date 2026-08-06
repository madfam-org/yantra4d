"""
Spice / Jar Rack — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Holds round jars in a row of circular cradles. Set the jar diameter and count,
arrange them across one or more tiers, and optionally add a magnet-pocket back
so metal-lidded jars stick under a shelf.

  * "rack"                 — a shelf / strip with N circular cradles sized to the
                             jar body (target_part == "rack").
  * "magnetic_lid_holder"  — a flat plate carrying a grid of 6 x 2 mm magnet
                             pockets; screwed under a shelf it grabs the steel
                             lids of hanging jars.

Watertight strategy: cradles are bored COMPLETELY through the shelf (full
through-cuts stay manifold); magnet pockets are blind recesses in a plate that is
always thicker than the pocket is deep, so a solid floor remains under each.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `jar_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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
target_part = str(PARAM(lambda: target_part, "rack"))  # "rack" | "magnetic_lid_holder"

jar_dia   = float(PARAM(lambda: jar_dia,   45.0))   # jar body diameter (mm)
cols      = int(  PARAM(lambda: cols,          5))   # jars per row
rows      = int(  PARAM(lambda: rows,          1))   # number of tiers / rows
clearance = float(PARAM(lambda: clearance,  1.0))   # radial gap so the jar drops in
wall      = float(PARAM(lambda: wall,        3.0))   # material between/around cradles
shelf_thick = float(PARAM(lambda: shelf_thick, 6.0))  # shelf plate thickness
magnet    = bool( PARAM(lambda: magnet,    False))   # add magnet pockets (rack back)

# ── Clamps ───────────────────────────────────────────────────────────────────
jar_dia   = max(15.0, min(jar_dia, 120.0))
cols      = max(1, min(cols, 12))
rows      = max(1, min(rows, 6))
clearance = max(0.0, min(clearance, 4.0))
wall      = max(2.0, min(wall, 12.0))
shelf_thick = max(4.0, min(shelf_thick, 20.0))

# Magnet standard: common 6 mm dia x 2 mm neodymium disc.
MAGNET_DIA = 6.0
MAGNET_DEPTH = 2.0

hole_dia = jar_dia + 2.0 * clearance       # cradle bore diameter
pitch = hole_dia + wall                     # centre-to-centre spacing
rack_w = cols * pitch + wall
rack_d = rows * pitch + wall


# ── Helpers ──────────────────────────────────────────────────────────────────
def block(w, d, h, z0=0.0):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .box(w, d, h, centered=(True, True, False))
    )


def cradle_points():
    """Centres of the jar cradles in a cols x rows grid."""
    pts = []
    x0 = -((cols - 1) * pitch) / 2.0
    y0 = -((rows - 1) * pitch) / 2.0
    for r in range(rows):
        for c in range(cols):
            pts.append((x0 + c * pitch, y0 + r * pitch))
    return pts


def build_rack():
    """A shelf with a through-bored circular cradle per jar."""
    body = block(rack_w, rack_d, shelf_thick)
    pts = cradle_points()
    cutter = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .pushPoints(pts)
        .circle(hole_dia / 2.0)
        .extrude(shelf_thick + 2.0)
    )
    body = body.cut(cutter)

    # Optional magnet-pocket back wall: a low rail along the rear edge whose
    # inner face carries blind magnet pockets (one per column).
    if magnet:
        body = body.union(_magnet_back())

    # Soften the top outer edge; non-fatal if degenerate.
    try:
        body = body.edges(">Z").edges("|Z").fillet(min(1.0, wall * 0.3))
    except Exception:
        pass
    return body


def _magnet_back():
    """A rear wall standing on the shelf, with a magnet pocket per column on its
    front face, so the rack itself can clamp to a steel surface."""
    back_h = 20.0
    back_t = max(wall + MAGNET_DEPTH + 2.0, 8.0)
    rear_y = rack_d / 2.0
    wall_solid = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, rear_y - back_t / 2.0, 0))
        .box(rack_w, back_t, back_h, centered=(True, True, False))
    )
    # Pockets open on the front face of the back wall (facing −Y).
    x0 = -((cols - 1) * pitch) / 2.0
    pocket_y = rear_y - back_t  # front face plane of the wall
    pockets = []
    for c in range(cols):
        x = x0 + c * pitch
        pockets.append(
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(x, back_h / 2.0, -pocket_y))
            .circle(MAGNET_DIA / 2.0)
            .extrude(-MAGNET_DEPTH)
        )
    if pockets:
        cut = pockets[0]
        for p in pockets[1:]:
            cut = cut.union(p)
        wall_solid = wall_solid.cut(cut)
    return wall_solid


def build_magnetic_lid_holder():
    """A flat plate with a grid of 6 x 2 mm magnet pockets on its underside,
    plus two mounting screw holes so it fastens under a shelf. The steel jar
    lids are held by the magnets."""
    plate_pitch = max(jar_dia + wall, 30.0)
    plate_w = cols * plate_pitch + wall
    plate_d = max(rows, 1) * plate_pitch + wall
    plate_t = MAGNET_DEPTH + 3.0        # keeps ≥3 mm solid above each pocket

    body = block(plate_w, plate_d, plate_t)

    # One magnet pocket at each cradle location, opening DOWN from the base (z=0)
    # up into the plate — a blind recess with solid material above it.
    pts = []
    x0 = -((cols - 1) * plate_pitch) / 2.0
    y0 = -((rows - 1) * plate_pitch) / 2.0
    for r in range(rows):
        for c in range(cols):
            pts.append((x0 + c * plate_pitch, y0 + r * plate_pitch))
    pockets = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, 0))
        .pushPoints(pts)
        .circle(MAGNET_DIA / 2.0)
        .extrude(MAGNET_DEPTH)
    )
    body = body.cut(pockets)

    # Two countersunk-free through screw holes near the short ends for mounting.
    sx = plate_w / 2.0 - wall - 3.0
    if sx > 0:
        screws = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -1.0))
            .pushPoints([(-sx, 0.0), (sx, 0.0)])
            .circle(2.0)
            .extrude(plate_t + 2.0)
        )
        body = body.cut(screws)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "magnetic_lid_holder":
    result = build_magnetic_lid_holder()
else:
    result = build_rack()
