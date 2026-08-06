"""
Sprue Tray — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A model-kit parts tray: a compartment grid to sort sprue-cut pieces during a build,
with a magnetized variant that clings to a steel bench, and a sorting lid whose
underside carries a fine grid of small-parts pockets for screws / photo-etch / tiny
bits.

Three parts (dispatched via `target_part`):
  * "parts_tray"    — an open tray with a `cols` x `rows` compartment grid.
  * "magnetic_tray" — the same tray with 6x2 mm magnet pockets in the underside.
  * "sorting_lid"   — a friction lid with its OWN finer grid of small-parts pockets.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cols`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.

Watertight strategy: the tray is a solid outer block with a BLIND interior cavity
cut from the top (a cup); dividers are solid walls unioned onto the floor. Magnet
pockets are blind recesses in the underside (never through the floor). The sorting
lid is a plate + a hollow skirt (a closed shell); its small-parts pockets are blind
recesses in the top plate. No sphere-tangent unions; hollows stay open at the top.
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
target_part = str(PARAM(lambda: target_part, "parts_tray"))   # parts_tray|magnetic_tray|sorting_lid

tray_w      = float(PARAM(lambda: tray_w,   120.0))  # tray outer width (mm)
tray_d      = float(PARAM(lambda: tray_d,    80.0))  # tray outer depth (mm)
tray_h      = float(PARAM(lambda: tray_h,    22.0))  # tray interior depth (mm)
wall        = float(PARAM(lambda: wall,       2.0))  # outer wall thickness (mm)
floor       = float(PARAM(lambda: floor,      2.0))  # floor thickness (mm)
cols        = int(  PARAM(lambda: cols,         3))  # compartments across X
rows        = int(  PARAM(lambda: rows,         2))  # compartments across Y
div_th      = float(PARAM(lambda: div_th,     1.6))  # divider thickness (mm)
corner_r    = float(PARAM(lambda: corner_r,   3.0))  # outer corner radius (mm)

magnet_d    = float(PARAM(lambda: magnet_d,   6.0))  # magnet diameter (mm)
magnet_h    = float(PARAM(lambda: magnet_h,   2.0))  # magnet pocket depth (mm)
mag_n       = int(  PARAM(lambda: mag_n,        4))  # magnets (corners) 2 or 4

fine_cols   = int(  PARAM(lambda: fine_cols,    4))  # sorting-lid small-parts grid X
fine_rows   = int(  PARAM(lambda: fine_rows,    3))  # sorting-lid small-parts grid Y
fine_depth  = float(PARAM(lambda: fine_depth, 8.0))  # small-parts pocket depth (mm)
lid_skirt   = float(PARAM(lambda: lid_skirt, 10.0))  # sorting-lid friction skirt (mm)
lid_clear   = float(PARAM(lambda: lid_clear, 0.35))  # lid-to-wall clearance (mm)

# ── Clamp to sane ranges so extreme UI values still build watertight. ────────
tray_w     = max(40.0, min(tray_w, 260.0))
tray_d     = max(40.0, min(tray_d, 200.0))
tray_h     = max(6.0, min(tray_h, 60.0))
wall       = max(1.2, min(wall, 5.0))
floor      = max(1.2, min(floor, 6.0))
cols       = max(1, min(cols, 8))
rows       = max(1, min(rows, 8))
div_th     = max(0.8, min(div_th, 4.0))
corner_r   = max(0.0, min(corner_r, 15.0))
magnet_d   = max(2.0, min(magnet_d, 12.0))
magnet_h   = max(0.8, min(magnet_h, floor - 0.4 if floor > 1.2 else 0.8))
mag_n      = 4 if mag_n >= 4 else 2
fine_cols  = max(1, min(fine_cols, 8))
fine_rows  = max(1, min(fine_rows, 8))
fine_depth = max(2.0, min(fine_depth, 20.0))
lid_skirt  = max(4.0, min(lid_skirt, 30.0))
lid_clear  = max(0.15, min(lid_clear, 0.8))


# ── Shared helpers ────────────────────────────────────────────────────────────
def _cup(ow, od, ih, w, floor_t, rad):
    """Watertight cup: outer rounded block minus a blind interior cavity."""
    outer_h = ih + floor_t
    rad = max(0.0, min(rad, min(ow, od) / 2.0 - 0.01))
    body = cq.Workplane("XY").box(ow, od, outer_h, centered=(True, True, False))
    if rad > 0.05:
        try:
            body = body.edges("|Z").fillet(rad)
        except Exception:
            pass
    cavity = (
        cq.Workplane("XY").workplane(offset=floor_t)
        .box(ow - 2.0 * w, od - 2.0 * w, ih + 1.0, centered=(True, True, False))
    )
    inner_r = max(0.0, rad - w)
    if inner_r > 0.05:
        try:
            cavity = cavity.edges("|Z").fillet(inner_r)
        except Exception:
            pass
    return body.cut(cavity), outer_h


def _grid_dividers(inner_w, inner_d, height, floor_t, ncols, nrows, thick):
    """Union of interior divider walls forming an ncols x nrows compartment grid."""
    walls = None
    if ncols > 1:
        step = inner_w / ncols
        for i in range(1, ncols):
            x = -inner_w / 2.0 + i * step
            dv = (
                cq.Workplane("XY").workplane(offset=floor_t)
                .center(x, 0).box(thick, inner_d, height, centered=(True, True, False))
            )
            walls = dv if walls is None else walls.union(dv)
    if nrows > 1:
        step = inner_d / nrows
        for j in range(1, nrows):
            y = -inner_d / 2.0 + j * step
            dv = (
                cq.Workplane("XY").workplane(offset=floor_t)
                .center(0, y).box(inner_w, thick, height, centered=(True, True, False))
            )
            walls = dv if walls is None else walls.union(dv)
    return walls


def _corner_magnets(ow, od):
    """Blind magnet pockets in the underside, at the corners (mag_n = 2 or 4)."""
    inset = magnet_d / 2.0 + max(wall, 3.0)
    xs = [ow / 2.0 - inset, -(ow / 2.0 - inset)]
    if mag_n == 4:
        pts = [(x, y) for x in xs for y in (od / 2.0 - inset, -(od / 2.0 - inset))]
    else:
        pts = [(x, 0.0) for x in xs]
    cutters = None
    for x, y in pts:
        pk = cq.Workplane("XY").center(x, y).circle(magnet_d / 2.0).extrude(magnet_h)
        cutters = pk if cutters is None else cutters.union(pk)
    return cutters


# ── Part builders ────────────────────────────────────────────────────────────
def build_parts_tray(with_magnets=False):
    body, _oh = _cup(tray_w, tray_d, tray_h, wall, floor, corner_r)
    inner_w = tray_w - 2.0 * wall
    inner_d = tray_d - 2.0 * wall
    grid = _grid_dividers(inner_w, inner_d, tray_h, floor, cols, rows, div_th)
    if grid is not None:
        body = body.union(grid)
    if with_magnets:
        mags = _corner_magnets(tray_w, tray_d)
        if mags is not None:
            body = body.cut(mags)
    return body


def build_sorting_lid():
    """A friction lid: outer plate (matching the tray footprint) + a hollow downward
    skirt that nests inside the tray, with a fine grid of blind small-parts pockets
    cut into the TOP of the plate."""
    plate_h = max(floor + fine_depth, floor + 3.0)   # thick enough to hold the pockets
    rad = max(0.0, min(corner_r, min(tray_w, tray_d) / 2.0 - 0.01))
    plate = cq.Workplane("XY").box(tray_w, tray_d, plate_h, centered=(True, True, False))
    if rad > 0.05:
        try:
            plate = plate.edges("|Z").fillet(rad)
        except Exception:
            pass

    # Downward friction skirt nesting into the tray interior.
    skirt_w = tray_w - 2.0 * wall - 2.0 * lid_clear
    skirt_d = tray_d - 2.0 * wall - 2.0 * lid_clear
    skirt_wall = max(1.2, wall - 0.4)
    skirt_outer = cq.Workplane("XY").box(skirt_w, skirt_d, lid_skirt, centered=(True, True, False))
    skirt_inner = cq.Workplane("XY").box(
        skirt_w - 2.0 * skirt_wall, skirt_d - 2.0 * skirt_wall, lid_skirt + 1.0,
        centered=(True, True, False),
    )
    skirt = skirt_outer.cut(skirt_inner).translate((0, 0, -lid_skirt))
    lid = plate.union(skirt)

    # Fine small-parts pockets: blind recesses into the plate top.
    pocket_span_w = tray_w - 2.0 * (wall + 3.0)
    pocket_span_d = tray_d - 2.0 * (wall + 3.0)
    pw = pocket_span_w / fine_cols
    pd = pocket_span_d / fine_rows
    cell_w = max(3.0, pw - div_th)
    cell_d = max(3.0, pd - div_th)
    x0 = -pocket_span_w / 2.0 + pw / 2.0
    y0 = -pocket_span_d / 2.0 + pd / 2.0
    depth = min(fine_depth, plate_h - 1.2)
    cutters = None
    for r in range(fine_rows):
        for c in range(fine_cols):
            cx = x0 + c * pw
            cy = y0 + r * pd
            pk = (
                cq.Workplane("XY").workplane(offset=plate_h - depth)
                .center(cx, cy).box(cell_w, cell_d, depth + 0.5, centered=(True, True, False))
            )
            cutters = pk if cutters is None else cutters.union(pk)
    if cutters is not None:
        lid = lid.cut(cutters)
    return lid.translate((0, 0, lid_skirt))   # lift so the skirt tip rests at z=0


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "magnetic_tray":
    result = build_parts_tray(with_magnets=True)
elif target_part == "sorting_lid":
    result = build_sorting_lid()
else:
    result = build_parts_tray(with_magnets=False)
