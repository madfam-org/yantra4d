"""
Ice / Chocolate / Casting Mold Tray — Yantra4D Hyperobject Cartridge
(CadQuery / B-Rep).

A tray of cavities you can pour into directly (ice, chocolate, wax, resin) or use
as a master to cast a flexible silicone mold. Pick a cavity shape (cube,
half-sphere, bar, or a rounded custom pocket) and a grid count. Three parts share
one CDG interface — the mold cavity array.

  * "cavity_tray" — a solid tray with a grid ARRAY of the chosen cavity.
  * "bar_mold"    — a row of long BAR cavities (chocolate bars / ice sticks).
  * "single_large"— ONE large cavity centred in a small tray.

Watertight strategy (mold trays are all pockets): every cavity is CUT from a
solid tray blank (hollow-by-cut). The half-sphere cavity is a hemisphere
*subtracted* from the top face — an OPEN bowl, NOT a sphere unioned onto a
surface, so there is no sphere-tangent kiss and no trapped void. Cavities always
open UP through the top face, and a solid `floor` is kept beneath them by
deriving the tray height from floor + depth. Edge fillets are applied to the
clean tray blank BEFORE the cavities are cut. No sphere-tangent unions anywhere.

FOOD-CONTACT NOTE: direct-pour food use touches the print. Geometry only —
food-safe filament/resin, sealing, and hygiene are the maker's responsibility
(silicone casting sidesteps direct print-to-food contact). See README.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; parameters injected as bare globals.
  - Access params via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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
cavity     = str(  PARAM(lambda: cavity,     "cube"))   # cube|sphere_half|bar|custom
cavity_sz  = float(PARAM(lambda: cavity_sz,   28.0))    # cavity nominal size (mm)
depth      = float(PARAM(lambda: depth,       22.0))    # cavity depth (mm)
cols       = int(  PARAM(lambda: cols,           3))    # cavities across X
rows       = int(  PARAM(lambda: rows,           2))    # cavities across Y
wall       = float(PARAM(lambda: wall,         4.0))    # tray wall between cavities (mm)
floor      = float(PARAM(lambda: floor,        3.0))    # solid floor under cavities (mm)
draft      = float(PARAM(lambda: draft,        1.5))    # release draft per side (mm, top wider)

target_part = str( PARAM(lambda: target_part, "cavity_tray"))  # cavity_tray|bar_mold|single_large

# ── Clamps ───────────────────────────────────────────────────────────────────
cavity_sz  = max(8.0,  min(cavity_sz, 80.0))
depth      = max(4.0,  min(depth, 60.0))
cols       = max(1,    min(cols, 8))
rows       = max(1,    min(rows, 8))
wall       = max(2.0,  min(wall, 12.0))
floor      = max(2.0,  min(floor, 10.0))
draft      = max(0.0,  min(draft, 4.0))


# ── Cavity cutters ───────────────────────────────────────────────────────────
# Every cutter is a SINGLE clean solid whose top overshoots the tray top face by
# 1mm, so the subtraction opens a clean mouth through the top. No lip-unions, no
# cutter fillets — those tessellate into cracks when subtracted.
def _bowl_cutter(mouth_r, dep, top_z):
    """A spherical-cap (bowl) cutter built as a LOFT of stacked circles from the
    mouth down to a tiny FLAT bottom.

    Why not just cut a sphere: a true sphere/revolved bowl has a pole singularity
    at its apex, and CadQuery's STL tessellator leaves a degenerate sliver there
    (1 boundary edge → the mesh reads as non-watertight even though the B-Rep is
    a valid euler=2 solid). Lofting circles down to a small flat bottom removes
    the pole, so the STL is genuinely watertight. The flat spot (~0.8 mm) is
    imperceptible on an ice / chocolate bowl."""
    dep = max(1.5, dep)
    R = (mouth_r * mouth_r + dep * dep) / (2.0 * dep)  # cap sphere radius
    cz = top_z - dep + R                                # cap centre (above top)
    bottom_r = 0.8
    over = 1.0
    steps = 14
    sections = []
    for i in range(steps + 1):
        z = top_z + over - (over + dep) * i / steps
        if z > top_z:
            r = mouth_r                                 # short cylindrical mouth
        else:
            dz = z - cz
            val = R * R - dz * dz
            r = math.sqrt(val) if val > 0 else 0.0
        if i == steps:
            r = bottom_r                                # flat bottom kills the pole
        sections.append(cq.Wire.makeCircle(max(r, 0.05), cq.Vector(0, 0, z), cq.Vector(0, 0, 1)))
    solid = cq.Solid.makeLoft(sections)
    return cq.Workplane("XY").add(solid)


def _cavity_cutter(kind, size, dep, top_z):
    """A single cavity cutter, mouth at `top_z`, extending DOWN by `dep`, centred
    on the origin in X/Y."""
    half = size / 2.0

    if kind == "sphere_half":
        return _bowl_cutter(half, min(dep, half * 1.6), top_z)

    if kind == "bar":
        lx, ly = size * 1.6, size * 0.6
        return _frustum_box(lx, ly, dep, top_z)

    if kind == "custom":
        # Round (cylindrical) pocket — distinct from the square cube pocket.
        return _frustum_round(size, dep, top_z)

    # default: cube (square pocket)
    return _frustum_box(size, size, dep, top_z)


def _frustum_box(lx, ly, dep, top_z):
    """A rectangular pocket cutter as ONE solid: a lofted frustum (base narrower
    than mouth by `draft`) whose top overshoots the tray top by 1mm. When draft
    is ~0 it is a plain box extended above the top."""
    bx = max(1.0, lx - 2.0 * draft)
    by = max(1.0, ly - 2.0 * draft)
    over = 1.0
    if draft > 0.05:
        # Loft from base rect (at top_z - dep) up to a slightly-enlarged mouth
        # rect placed `over` above the top face — a single closed solid.
        mx = lx + 2.0 * draft * (over / dep)
        my = ly + 2.0 * draft * (over / dep)
        return (
            cq.Workplane("XY")
            .rect(bx, by)
            .workplane(offset=dep + over)
            .rect(mx, my)
            .loft(combine=True)
            .translate((0, 0, top_z - dep))
        )
    return (
        cq.Workplane("XY")
        .box(lx, ly, dep + over, centered=(True, True, False))
        .translate((0, 0, top_z - dep))
    )


def _frustum_round(size, dep, top_z):
    """A round pocket cutter as ONE solid: a lofted circular frustum (base
    narrower than mouth by `draft`), top overshooting the tray top by 1mm."""
    r_mouth = size / 2.0
    r_base = max(1.0, r_mouth - draft)
    over = 1.0
    if draft > 0.05:
        r_top = r_mouth + draft * (over / dep)
        return (
            cq.Workplane("XY")
            .circle(r_base)
            .workplane(offset=dep + over)
            .circle(r_top)
            .loft(combine=True)
            .translate((0, 0, top_z - dep))
        )
    return (
        cq.Workplane("XY")
        .circle(r_mouth)
        .extrude(dep + over)
        .translate((0, 0, top_z - dep))
    )


def _cavity_footprint(kind, size):
    """Plan (X, Y) footprint of one cavity, for grid spacing."""
    if kind == "bar":
        return size * 1.6, size * 0.6
    return size, size


# ── Tray builder ─────────────────────────────────────────────────────────────
def _build_tray(kind, size, dep, nx, ny):
    fx, fy = _cavity_footprint(kind, size)
    cell_x = fx + wall
    cell_y = fy + wall
    tray_w = nx * cell_x + wall
    tray_d = ny * cell_y + wall
    tray_h = floor + dep

    body = cq.Workplane("XY").box(tray_w, tray_d, tray_h, centered=(True, True, False))
    # Fillet outer vertical edges on the CLEAN blank before cutting cavities.
    try:
        body = body.edges("|Z").fillet(min(wall, 4.0))
    except Exception:
        pass

    # Build one combined cutter (union of all cavities), then a single cut.
    top_z = tray_h
    x0 = -(nx - 1) * cell_x / 2.0
    y0 = -(ny - 1) * cell_y / 2.0
    cutter = None
    for i in range(nx):
        for j in range(ny):
            x = x0 + i * cell_x
            y = y0 + j * cell_y
            c = _cavity_cutter(kind, size, dep, top_z).translate((x, y, 0))
            cutter = c if cutter is None else cutter.union(c)
    if cutter is not None:
        body = body.cut(cutter)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_cavity_tray():
    return _build_tray(cavity, cavity_sz, depth, cols, rows)


def build_bar_mold():
    # A row of long bars regardless of the selected cavity shape.
    n = max(2, cols)
    return _build_tray("bar", cavity_sz, depth, 1, n)


def build_single_large():
    # One large cavity of the selected shape, ~1.8x the size, in a snug tray.
    big = min(80.0, cavity_sz * 1.8)
    big_depth = min(60.0, depth * 1.3)
    return _build_tray(cavity, big, big_depth, 1, 1)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bar_mold":
    result = build_bar_mold()
elif target_part == "single_large":
    result = build_single_large()
else:
    result = build_cavity_tray()
