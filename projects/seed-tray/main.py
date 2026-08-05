"""
Seed Tray / Cell Insert — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A seed-starting tray: an array of tapered cells (wide at the top, narrower at the
bottom so the plug pops out) each with a drainage hole. Sized to drop into a
standard 1020 propagation tray, or free-standing. A single-row cell strip and a
clear-ish humidity dome complete the set for germination.

Design idiom (solid block minus cell cavities):
  The tray is a solid slab; each cell is a tapered cavity (a lofted square, big at
  top → small at bottom) cut from the slab on a grid, then a drainage hole is drilled
  at each cell bottom. Cutting cavities from a solid keeps the mesh watertight. The
  dome is a thin-wall box shell (walls + roof, open bottom) sized to sit over the tray
  — an intentionally OPEN part (a cover), noted below.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cols`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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
target_part = str(  PARAM(lambda: target_part, "tray"))   # tray | cell_strip | humidity_dome
cols        = int(  PARAM(lambda: cols,           6))       # cells across (X)
rows        = int(  PARAM(lambda: rows,           4))       # cells down (Y)
cell_top    = float(PARAM(lambda: cell_top,     30.0))     # cell opening width at top (mm)
cell_taper  = float(PARAM(lambda: cell_taper,    6.0))     # how much narrower at the bottom (mm)
depth       = float(PARAM(lambda: depth,        45.0))     # cell depth (mm)
wall        = float(PARAM(lambda: wall,          2.0))     # wall between cells / outer wall (mm)
drainage    = bool( PARAM(lambda: drainage,     True))     # drainage hole per cell
fit_1020    = bool( PARAM(lambda: fit_1020,     False))    # add a rim lip to seat in a 1020 tray

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
cols = max(1, min(cols, 12))
rows = max(1, min(rows, 12))
cell_top = max(12.0, min(cell_top, 80.0))
cell_taper = max(0.0, min(cell_taper, cell_top * 0.5))
depth = max(15.0, min(depth, 120.0))
wall = max(1.2, min(wall, 6.0))

pitch = cell_top + wall                      # center-to-center cell spacing
floor_th = max(2.0, wall)
tray_w = cols * pitch + wall                 # overall tray footprint X
tray_d = rows * pitch + wall                 # overall tray footprint Y
tray_h = depth + floor_th
cell_bot = max(6.0, cell_top - cell_taper)   # cell width at the bottom


# ── Helpers ────────────────────────────────────────────────────────────────────
def _cell_centers(nx, ny):
    """Grid of cell-center (x, y) positions, centered on the origin."""
    pts = []
    for ix in range(nx):
        for iy in range(ny):
            x = -(nx - 1) * pitch / 2.0 + ix * pitch
            y = -(ny - 1) * pitch / 2.0 + iy * pitch
            pts.append((x, y))
    return pts


def _tapered_cavity(x, y):
    """One tapered cell cavity centered at (x, y): a lofted square, wide at the top
    (z=tray_h), narrow at the bottom (z=floor_th). Extends slightly above the rim so
    the opening is clean."""
    top_w = cell_top
    bot_w = cell_bot
    cav = (
        cq.Workplane("XY")
        .workplane(offset=floor_th)
        .rect(bot_w, bot_w)
        .workplane(offset=depth)
        .rect(top_w, top_w)
        .loft(combine=True)
        .translate((x, y, 0))
    )
    # a small top overshoot to guarantee an open mouth
    lip = (
        cq.Workplane("XY").workplane(offset=tray_h - 0.5).rect(top_w, top_w).extrude(1.0).translate((x, y, 0))
    )
    return cav.union(lip)


def _all_cutters(centers):
    """Build ONE Compound of every cell cavity (+ drainage hole) so the slab is
    hollowed with a single boolean cut. A Compound is a free grouping (no pairwise
    boolean union), so even a 12×12 array cuts in a few seconds — an O(n) union of
    144 lofts would instead take minutes. Cutting the compound once keeps the mesh
    watertight."""
    shapes = []
    for (x, y) in centers:
        shapes.append(_tapered_cavity(x, y).val())
        if drainage:
            hole = (
                cq.Workplane("XY").center(x, y).circle(max(1.5, cell_bot * 0.12)).extrude(floor_th + 2.0).translate((0, 0, -1.0))
            )
            shapes.append(hole.val())
    if not shapes:
        return None
    return cq.Workplane("XY").add(cq.Compound.makeCompound(shapes))


def build_tray():
    """Solid slab with a grid of tapered cell cavities and per-cell drainage holes."""
    body = cq.Workplane("XY").box(tray_w, tray_d, tray_h, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(wall * 1.5, 3.0))
    except Exception:
        pass

    cutter = _all_cutters(_cell_centers(cols, rows))
    if cutter is not None:
        try:
            body = body.cut(cutter)
        except Exception:
            pass

    if fit_1020:
        # A thin outward lip near the top so the tray hangs in a 1020 flat.
        lip = (
            cq.Workplane("XY")
            .box(tray_w + 2.0 * wall + 4.0, tray_d + 2.0 * wall + 4.0, max(2.0, wall), centered=(True, True, False))
            .translate((0, 0, tray_h - max(2.0, wall)))
        )
        void = cq.Workplane("XY").box(tray_w, tray_d, max(2.0, wall) + 2.0, centered=(True, True, False)).translate(
            (0, 0, tray_h - max(2.0, wall) - 1.0)
        )
        lip = lip.cut(void)
        body = body.union(lip)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_cell_strip():
    """A single row of cells (cols × 1) — a small propagation strip. Same tapered
    cavities and drainage, one row deep."""
    strip_d = pitch + wall
    body = cq.Workplane("XY").box(tray_w, strip_d, tray_h, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(wall * 1.5, 3.0))
    except Exception:
        pass
    centers = [(-(cols - 1) * pitch / 2.0 + ix * pitch, 0.0) for ix in range(cols)]
    cutter = _all_cutters(centers)
    if cutter is not None:
        try:
            body = body.cut(cutter)
        except Exception:
            pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_humidity_dome():
    """A vented humidity dome: a thin-wall box shell (walls + roof, open bottom) that
    sits over the tray to hold moisture during germination, with vent slots. This is
    an intentionally OPEN cover (its bottom face is open by design), so it is NOT a
    closed watertight solid — a cover has no floor."""
    d_wall = max(1.2, wall * 0.8)
    roof_t = max(1.2, wall * 0.8)
    dome_w = tray_w + 2.0 * d_wall + 3.0
    dome_d = tray_d + 2.0 * d_wall + 3.0
    dome_h = max(40.0, depth * 0.7)

    outer = cq.Workplane("XY").box(dome_w, dome_d, dome_h, centered=(True, True, False))
    try:
        outer = outer.edges("|Z").fillet(min(d_wall * 2.0, 4.0))
    except Exception:
        pass
    # Hollow from below, leaving a CLOSED roof of thickness roof_t at the top and an
    # OPEN bottom (a cover slips over the tray). The inner void starts at z=0 and
    # stops roof_t below the top, so the roof stays solid.
    inner = (
        cq.Workplane("XY")
        .box(dome_w - 2.0 * d_wall, dome_d - 2.0 * d_wall, dome_h - roof_t, centered=(True, True, False))
        .translate((0, 0, -0.5))
    )
    body = outer.cut(inner)   # walls + roof, open bottom (a cover)

    # Vent slots near the top on two sides.
    for sx in (-1.0, 1.0):
        vent = (
            cq.Workplane("YZ")
            .workplane(offset=sx * (dome_w / 2.0))
            .center(0.0, dome_h * 0.75)
            .rect(dome_d * 0.4, dome_h * 0.12)
            .extrude(-sx * (d_wall + 2.0))
        )
        try:
            body = body.cut(vent)
        except Exception:
            pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "cell_strip":
    result = build_cell_strip()
elif target_part == "humidity_dome":
    result = build_humidity_dome()
else:
    result = build_tray()
