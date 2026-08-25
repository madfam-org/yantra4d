"""
18650 Battery Caddy — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A Li-ion cell caddy that keeps a set of 18650 or 21700 cells captive in a printed
carrier, with open contact windows at the ends so bus strips or spring contacts
reach the terminals. Sits in the battery-cell family next to battery-holder and
media-caddy: the cell-bore cradle array shares their cell-form-factor convention.

Modes are dispatched via `target_part`:
  * "caddy"    — a single row of cell cradles with end contact windows.
  * "dual_row" — two rows sharing a central spine (a fuller pack carrier).
  * "sleeve"   — a single-cell protective sleeve tube (open both ends).

Reference dimensions (mm, nominal outer):
  * 18650 cell: Ø18.4 × 65.0
  * 21700 cell: Ø21.2 × 70.0
Cradles carry per-side clearance so a real cell drops in and lifts out.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals.
  - Access them via PARAM(lambda: <name>, <default>). Never use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Cell table (outer diameter × length, mm) ─────────────────────────────────
_CELLS = {
    "18650": {"dia": 18.4, "len": 65.0},
    "21700": {"dia": 21.2, "len": 70.0},
}


def cell_spec(key):
    k = str(key).strip().upper().replace(" ", "")
    if k in ("21700",):
        return _CELLS["21700"]
    return _CELLS["18650"]


# ── Parameters ───────────────────────────────────────────────────────────────
cell = str(PARAM(lambda: cell, "18650"))           # 18650 | 21700
count = int(PARAM(lambda: count, 4))               # cells per row
wall = float(PARAM(lambda: wall, 2.2))             # wall around/between cells
cradle_frac = float(PARAM(lambda: cradle_frac, 0.62))  # cradle wrap fraction
clearance = float(PARAM(lambda: clearance, 0.5))   # per-side bore clearance
contact_w = float(PARAM(lambda: contact_w, 9.0))   # end contact-window width

target_part = str(PARAM(lambda: target_part, "caddy"))

# ── Clamp to printable ranges ────────────────────────────────────────────────
count = max(1, min(count, 8))
wall = max(1.2, min(wall, 5.0))
cradle_frac = max(0.4, min(cradle_frac, 0.85))
clearance = max(0.2, min(clearance, 1.2))
contact_w = max(4.0, min(contact_w, 14.0))

spec = cell_spec(cell)
CELL_D = spec["dia"]
CELL_L = spec["len"]
BORE_R = CELL_D / 2.0 + clearance


def _fillet_safe(wp, selector, radius):
    """Fillet the blank BEFORE cutting features; fall back if OCCT refuses."""
    try:
        return wp.edges(selector).fillet(radius)
    except Exception:
        return wp


def _row_geom(n):
    """Geometry of an n-cell row: cells lie along X, laid out across Y lanes.
    Bores are cradle troughs whose axis sits high enough that a cell drops in
    from the top without a full-height slot that would sever the block."""
    pitch_y = CELL_D + 2 * clearance + wall
    body_l = CELL_L + 2 * wall
    body_w = n * (CELL_D + 2 * clearance) + (n + 1) * wall
    # Axis height sets how much of the cell is wrapped: cradle_frac of the radius
    # below the axis remains as cradle floor; above the axis is open to the top.
    axis_z = wall + BORE_R * cradle_frac
    body_h = axis_z + BORE_R              # open trough: top face near cell top
    y0 = -(n - 1) * pitch_y / 2.0
    ys = [y0 + i * pitch_y for i in range(n)]
    return body_l, body_w, body_h, axis_z, ys


def _row_block(n):
    body_l, body_w, body_h, axis_z, ys = _row_geom(n)
    block = (
        cq.Workplane("XY")
        .box(body_l, body_w, body_h + BORE_R, centered=(True, True, False))
    )
    block = _fillet_safe(block, "|Z", min(3.0, wall))

    # Cradle troughs: one horizontal cylinder per lane along X, cut in a single
    # grouped boolean (fast + watertight). Axis at (any x, yc, axis_z).
    troughs = (
        cq.Workplane("XZ")
        .workplane(offset=-(body_l / 2.0 + 1.0))
        .pushPoints([(yc, axis_z) for yc in ys])
        .circle(BORE_R)
        .extrude(body_l + 2.0)
    )
    block = block.cut(troughs)

    # Trim the block top flat at the cradle rim so cells are open to the top.
    top_z = axis_z + BORE_R * 0.15
    cap = (
        cq.Workplane("XY")
        .box(body_l + 4.0, body_w + 4.0, BORE_R * 4.0, centered=(True, True, False))
        .translate((0, 0, top_z))
    )
    block = block.cut(cap)
    return block, body_l, body_w, axis_z, ys


def _end_windows(block, body_l, ys, axis_z):
    """End contact windows: a small square window at each cell end so a bus strip
    reaches the terminal. Modeled as boxes straddling each end wall (open the
    outer face + the bore), cut in one grouped boolean per end."""
    win = min(contact_w, CELL_D * 0.75)
    for sy in (-1.0, 1.0):
        # One window box per lane at this end, cut in a single grouped boolean.
        cutters = (
            cq.Workplane("YZ")
            .workplane(offset=sy * (body_l / 2.0))
            .pushPoints([(yc, axis_z) for yc in ys])
            .rect(win, win)
            .extrude(-sy * (wall + 2.0))
        )
        block = block.cut(cutters)
    return block


# ── Mode 1: single-row caddy ─────────────────────────────────────────────────
def build_caddy():
    block, body_l, body_w, axis_z, ys = _row_block(count)
    return _end_windows(block, body_l, ys, axis_z)


# ── Mode 2: dual-row caddy ───────────────────────────────────────────────────
def build_dual_row():
    """Two rows abutted along X, overlapping by one wall so the union is a single
    solid (overlapping, not tangent → no zero-volume seam)."""
    block, body_l, body_w, axis_z, ys = _row_block(count)
    row = _end_windows(block, body_l, ys, axis_z)
    row2 = row.translate((body_l - wall, 0, 0))
    dual = row.union(row2)
    cb = dual.val().BoundingBox()
    return dual.translate((-(cb.xmin + cb.xmax) / 2.0, 0, 0))


# ── Mode 3: single-cell sleeve ───────────────────────────────────────────────
def build_sleeve():
    """A protective tube for one cell, open at both ends (a clean through-bore
    annulus — no trapped void). Two grip flats keep it from rolling."""
    outer_r = BORE_R + wall
    length = CELL_L + 2 * wall
    tube = (
        cq.Workplane("XY")
        .circle(outer_r)
        .circle(BORE_R)
        .extrude(length)
    )
    # Grip flat depth must stay shallower than the wall so it never breaks into
    # the bore (which would split the annulus into two arcs → body_count>1).
    flat_depth = min(outer_r * 0.15, wall * 0.5)
    for sign in (1.0, -1.0):
        flat = (
            cq.Workplane("XY")
            .box(outer_r * 2, flat_depth, length, centered=(True, False, False))
            .translate((0, sign * (outer_r - flat_depth / 2.0), 0))
        )
        tube = tube.cut(flat)
    return tube


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "caddy":
    result = build_caddy()
elif target_part == "dual_row":
    result = build_dual_row()
elif target_part == "sleeve":
    result = build_sleeve()
else:
    result = build_caddy()
