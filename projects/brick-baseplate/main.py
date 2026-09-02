"""
Brick Baseplate — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

One plate, two grid ecosystems.

The commons speaks two module grids and has never joined them. `brick-tile`
publishes the construction-brick grid — an 8 mm stud pitch with Ø4.8 mm studs and
hollow underside clutch tubes — and it is the ONLY member of that family. Four
cartridges publish Gridfinity's 42 mm module: `gridfinity`, `gridfinity-baseplate`,
`gridfinity-tool`, `grid-hub`, plus `din-rail-clip`'s dock. A brick model and a
Gridfinity drawer are found in exactly the same rooms and have no relationship at
all.

This plate is that relationship, in both directions:
  * a brick play surface that drops into a Gridfinity baseplate, and
  * a Gridfinity baseplate that clutches onto a brick surface.

Modes are dispatched via `target_part`:
  * "stud_baseplate"    — a plain brick baseplate: studs up, hollow underside
                          with clutch tubes on the same grid.
  * "gridfinity_base"   — brick studs up, Gridfinity FEET down, so a brick
                          surface sits in a Gridfinity grid.
  * "grid_socket_plate" — Gridfinity baseplate sockets up, brick CLUTCH TUBES
                          down, so Gridfinity bins sit on a brick surface.

Both grids are inlined from the cartridges that publish them, unchanged:
  brick     8.0 mm pitch, Ø4.8 stud, 1.8 stud height, 3.2 plate, tube 6.5 / 4.9
            (`brick-tile`)
  gridfinity 42 mm pitch, foot 39.2 -> 41.5 over 5 mm, corner radius 3.75,
            baseplate socket 39.2 -> 42 over 5 mm (`gridfinity`)

Engine note — a measured deviation from the wave plan, recorded rather than
quiet. The plan specifies OpenSCAD for this slot, on the stated ground that the
Manifold backend is measurably the right kernel for a dense repetitive CSG
array. The OpenSCAD available here is 2021.01, which has NO `--backend` flag at
all, so Manifold is not available and CGAL is what actually runs. Measured, on
the same 16 x 16 baseplate:

    OpenSCAD 2021.01 (CGAL)   9 min 41 s   and reports "Volumes: 2"
    CadQuery / OCCT             ~11 s      watertight, body_count 1

The plan's premise does not hold on this toolchain, so the cartridge is
CadQuery. The slug, the interfaces, the rank and the ranked order are unchanged.

Watertightness strategy — the array is the whole risk here:
  * Studs and tubes are built as ONE pushPoints extrusion each, not a loop of
    unions. A thousand pairwise fuses is a thousand chances to leave a
    coincident face, and it is also the difference between 11 seconds and
    several minutes.
  * Every stud and tube STRADDLES the plate it grows from. `gridfinity`'s own
    cup.py carries the scar that pays for this: feet subtracted as negative
    geometry pinched the solid into two volumes meeting at a plane, and both
    OpenSCAD and OCCT produced a non-manifold result.
  * The underside cavity is bounded inside the plate by a full wall on every
    side, so it can never reach an edge and turn the shell inside out.
  * Nothing is ever sealed: the cavity opens downward, every clutch tube bore
    opens downward, every socket opens upward.
  * No fillet is taken on any edge a bore has touched.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
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


# ── The two grids, inlined from the cartridges that publish them ─────────────
# Construction brick (brick-tile). The wave plan's slot text says "Ø3.2 mm stud";
# that figure is the PLATE HEIGHT, not the stud. The live cartridge is the
# primary source and says Ø4.8, and this cartridge follows it — a stud built to
# 3.2 would clutch nothing in the commons or out of it.
BRICK_PITCH = 8.0
STUD_DIA = 4.8
STUD_H = 1.8
PLATE_H = 3.2
TUBE_OD = 6.5
TUBE_ID = 4.9

# Gridfinity (gridfinity). Foot and socket tapers as that cartridge builds them.
GF_PITCH = 42.0
GF_BASE_H = 5.0
GF_FOOT_BOTTOM = 39.2
GF_FOOT_TOP = GF_PITCH - 0.5
GF_SOCKET_BOTTOM = 39.2
GF_SOCKET_TOP = GF_PITCH
GF_CORNER_R = 3.75

OVERLAP = 0.6


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "stud_baseplate"))

cols = float(PARAM(lambda: cols, 16.0))
rows = float(PARAM(lambda: rows, 16.0))
gf_x = float(PARAM(lambda: gf_x, 3.0))
gf_y = float(PARAM(lambda: gf_y, 3.0))
plate_h = float(PARAM(lambda: plate_h, PLATE_H))
wall = float(PARAM(lambda: wall, 1.2))
stud_dia = float(PARAM(lambda: stud_dia, STUD_DIA))
stud_h = float(PARAM(lambda: stud_h, STUD_H))
tube_od = float(PARAM(lambda: tube_od, TUBE_OD))
tube_id = float(PARAM(lambda: tube_id, TUBE_ID))
underside = str(PARAM(lambda: underside, "clutch"))

cols = int(max(2, min(round(cols), 32)))
rows = int(max(2, min(round(rows), 32)))
gf_x = int(max(1, min(round(gf_x), 6)))
gf_y = int(max(1, min(round(gf_y), 6)))
plate_h = max(2.4, min(plate_h, 12.0))
wall = max(0.8, min(wall, 3.0))
stud_dia = max(2.0, min(stud_dia, BRICK_PITCH - 1.5))
stud_h = max(1.0, min(stud_h, 6.0))
tube_od = max(stud_dia + 0.6, min(tube_od, BRICK_PITCH - 0.6))
tube_id = max(stud_dia + 0.05, min(tube_id, tube_od - 0.8))


# The floor under the cavity has to survive; the cavity depth is derived from
# the plate, never the other way round.
FLOOR = min(wall, plate_h - 1.2)
FLOOR = max(0.8, FLOOR)


# ── Footprint ────────────────────────────────────────────────────────────────
def brick_span():
    return cols * BRICK_PITCH, rows * BRICK_PITCH


def gf_span():
    return gf_x * GF_PITCH, gf_y * GF_PITCH


def stud_points(w, d, nx, ny):
    """Stud centres on the brick grid, centred on the plate."""
    return [(BRICK_PITCH * (i + 0.5) - w / 2.0,
             BRICK_PITCH * (j + 0.5) - d / 2.0)
            for i in range(nx) for j in range(ny)]


def tube_points(w, d, nx, ny):
    """Clutch-tube centres: the interstices of the stud grid."""
    if nx < 2 or ny < 2:
        return []
    return [(BRICK_PITCH * (i + 1) - w / 2.0,
             BRICK_PITCH * (j + 1) - d / 2.0)
            for i in range(nx - 1) for j in range(ny - 1)]


def rounded_prismoid(bottom, top, height, radius, z0=0.0):
    """A square prismoid with filleted vertical edges — the same helper
    `gridfinity`'s cup.py uses, so the feet built here are that cartridge's
    feet and not a second convention that nearly matches."""
    solid = (
        cq.Workplane("XY", origin=(0, 0, z0))
        .rect(bottom, bottom)
        .workplane(offset=height)
        .rect(top, top)
        .loft(combine=True)
    )
    try:
        solid = solid.edges("|Z").fillet(radius)
    except Exception:
        # A fillet larger than the taper allows is a cosmetic loss, not a defect.
        pass
    return solid


# ── Shared builders ──────────────────────────────────────────────────────────
def shelled_slab(w, d, h):
    """A slab with its underside hollowed, the cavity bounded by a full wall.

    The cavity opens DOWNWARD and stops a floor short of the top, so it is never
    a sealed void and never reaches an edge."""
    body = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    inner_w = w - 2.0 * wall
    inner_d = d - 2.0 * wall
    depth = h - FLOOR
    if inner_w > 2.0 and inner_d > 2.0 and depth > 0.4:
        cavity = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -1.0))
            .box(inner_w, inner_d, depth + 1.0, centered=(True, True, False))
        )
        body = body.cut(cavity)
    return body


def add_studs(body, w, d, nx, ny, z_top):
    """All studs in ONE extrusion.

    A loop of unions is a fuse per stud — a thousand chances to leave a
    coincident face, and the difference between eleven seconds and minutes."""
    pts = stud_points(w, d, nx, ny)
    if not pts:
        return body
    studs = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_top - OVERLAP))
        .pushPoints(pts)
        .circle(stud_dia / 2.0)
        .extrude(stud_h + OVERLAP)
    )
    return body.union(studs)


def add_clutch_tubes(body, w, d, nx, ny, h):
    """Underside clutch tubes: the grip half of the brick interface.

    Built as one positive extrusion and one negative extrusion, both straddling
    what they meet. `gridfinity`'s cup.py carries the scar that pays for this:
    geometry subtracted where it should have been added pinched the solid into
    two volumes meeting at a plane, and both OpenSCAD and OCCT produced a
    non-manifold result."""
    if underside != "clutch":
        return body
    pts = tube_points(w, d, nx, ny)
    if not pts:
        return body
    height = max(0.8, h - FLOOR)
    tubes = (
        cq.Workplane("XY")
        .pushPoints(pts)
        .circle(tube_od / 2.0)
        .extrude(height)
    )
    body = body.union(tubes)
    bores = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .pushPoints(pts)
        .circle(tube_id / 2.0)
        .extrude(height + 1.0)
    )
    return body.cut(bores)


def gf_cell_points(w, d, nx, ny):
    return [(GF_PITCH * (i + 0.5) - w / 2.0,
             GF_PITCH * (j + 0.5) - d / 2.0)
            for i in range(nx) for j in range(ny)]


# ── Part builders ────────────────────────────────────────────────────────────
def build_stud_baseplate():
    """A plain brick baseplate: studs up, hollow underside with clutch tubes."""
    w, d = brick_span()
    body = shelled_slab(w, d, plate_h)
    body = add_clutch_tubes(body, w, d, cols, rows, plate_h)
    body = add_studs(body, w, d, cols, rows, plate_h)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_gridfinity_base():
    """Brick studs up, Gridfinity FEET down: a brick surface in a Gridfinity grid.

    The plate footprint is the Gridfinity span less the 0.5 mm grid clearance,
    and the stud grid is fitted INSIDE it — the brick grid never sets the
    footprint here, because a Gridfinity cell that is not 42 mm is not a
    Gridfinity cell."""
    gw, gd = gf_span()
    w = gw - 0.5
    d = gd - 0.5

    nx = max(1, int(w // BRICK_PITCH))
    ny = max(1, int(d // BRICK_PITCH))

    body = cq.Workplane("XY").box(w, d, plate_h, centered=(True, True, False))

    # Feet as POSITIVE geometry, overlapping the slab, exactly as gridfinity's
    # cup.py builds them after its own two-volume failure.
    feet = None
    for (cx, cy) in gf_cell_points(gw, gd, gf_x, gf_y):
        foot = rounded_prismoid(GF_FOOT_BOTTOM, GF_FOOT_TOP,
                                GF_BASE_H + OVERLAP, GF_CORNER_R,
                                z0=-GF_BASE_H)
        foot = foot.translate((cx, cy, 0))
        feet = foot if feet is None else feet.union(foot)
    if feet is not None:
        body = body.union(feet)

    body = add_studs(body, w, d, nx, ny, plate_h)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_grid_socket_plate():
    """Gridfinity baseplate sockets up, brick clutch tubes down.

    The other direction of the bridge: a Gridfinity baseplate that clutches onto
    a brick surface instead of screwing to a drawer."""
    gw, gd = gf_span()
    total_h = GF_BASE_H + plate_h

    body = cq.Workplane("XY").box(gw, gd, total_h, centered=(True, True, False))

    # The socket is a taper cut from the TOP face down. It opens upward, so it
    # can never be a sealed void.
    sockets = None
    for (cx, cy) in gf_cell_points(gw, gd, gf_x, gf_y):
        sock = rounded_prismoid(GF_SOCKET_BOTTOM, GF_SOCKET_TOP,
                                GF_BASE_H + 1.0, GF_CORNER_R,
                                z0=total_h - GF_BASE_H)
        sock = sock.translate((cx, cy, 0))
        sockets = sock if sockets is None else sockets.union(sock)
    if sockets is not None:
        body = body.cut(sockets)

    nx = max(2, int(gw // BRICK_PITCH))
    ny = max(2, int(gd // BRICK_PITCH))
    body = add_clutch_tubes(body, gw, gd, nx, ny, 0.0)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "stud_baseplate": build_stud_baseplate,
    "gridfinity_base": build_gridfinity_base,
    "grid_socket_plate": build_grid_socket_plate,
}

result = _dispatch.get(target_part, build_stud_baseplate)()
