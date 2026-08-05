"""
Drawer Divider / Insert Grid — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An adjustable cell grid sized to a drawer. Three parts:
  - "tray"           : a solid-bottom divided tray (drop-in organiser with floor).
  - "dividers"       : a bottomless interlocking grid (slotted half-lap) that drops
                       into an existing drawer — no floor, just the walls + partitions.
  - "single_divider" : one slotted strip, to hand-assemble a custom grid.

Sized by the overall drawer envelope (width x depth x height); the user picks how
many columns and rows of cells. Cross partitions meet with a slotted half-lap so
the bottomless grid stays rigid without a floor.

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
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters (overall-envelope driven) ─────────────────────────────────────
overall_w = float(PARAM(lambda: overall_w, 200.0))   # drawer interior X (mm)
overall_d = float(PARAM(lambda: overall_d, 150.0))   # drawer interior Y (mm)
overall_h = float(PARAM(lambda: overall_h,  50.0))   # divider / tray height (mm)
cols      = int(  PARAM(lambda: cols,          3))   # cell columns (across width)
rows      = int(  PARAM(lambda: rows,          2))   # cell rows (across depth)
wall      = float(PARAM(lambda: wall,        1.6))   # wall / partition thickness
floor     = float(PARAM(lambda: floor,       1.6))   # floor thickness (tray only)
interlock = bool( PARAM(lambda: interlock,  True))   # slotted half-lap cross joints

target_part = str(PARAM(lambda: target_part, "tray"))  # tray | dividers | single_divider

# ── Clamp to sane ranges so geometry never degenerates ───────────────────────
cols = max(1, min(cols, 12))
rows = max(1, min(rows, 12))
wall = max(0.8, min(wall, overall_w / 4.0, overall_d / 4.0))
floor = max(0.8, min(floor, overall_h - 1.0))

# Number of interior partitions in each axis (fence posts between the cells).
n_x = cols - 1   # partitions running along Y, spaced across X
n_y = rows - 1   # partitions running along X, spaced across Y

# Interior span available to cells (inside the perimeter walls).
span_x = overall_w - 2.0 * wall
span_y = overall_d - 2.0 * wall


# ── Helpers ──────────────────────────────────────────────────────────────────
def _x_positions():
    """Center X of each partition that runs along Y (evenly spaced across width)."""
    step = overall_w / cols
    return [-overall_w / 2.0 + step * i for i in range(1, cols)]


def _y_positions():
    """Center Y of each partition that runs along X (evenly spaced across depth)."""
    step = overall_d / rows
    return [-overall_d / 2.0 + step * i for i in range(1, rows)]


def _perimeter_frame(height, base_z):
    """A hollow rectangular wall frame (no floor) of the given height."""
    outer = cq.Workplane("XY").box(overall_w, overall_d, height, centered=(True, True, False))
    inner = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .box(span_x, span_y, height + 2.0, centered=(True, True, False))
    )
    frame = outer.cut(inner)
    return frame.translate((0, 0, base_z))


def _slot(w, d, h, x, y, z):
    """A rectangular cutting tool centered at (x,y) with base at z."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z))
        .box(w, d, h, centered=(True, True, False))
    )


def _grid_walls(height, base_z):
    """Interior partition walls of the given height, standing on base_z.

    When `interlock` is on, partitions running along X are notched from the top
    and partitions running along Y are notched from the bottom, at every crossing,
    so the two sets mate as a half-lap and lock the grid together.
    """
    parts = []
    half = height / 2.0

    # Partitions spanning the full depth, positioned across the width (run along Y).
    for x in _x_positions():
        w = _perim_or_span_bar(axis="y", x=x, height=height, base_z=base_z)
        if interlock and n_y > 0:
            for y in _y_positions():
                # notch the lower half at each crossing
                w = w.cut(_slot(wall + 0.4, wall + 0.4, half + 0.2, x, y, base_z - 0.1))
        parts.append(w)

    # Partitions spanning the full width, positioned across the depth (run along X).
    for y in _y_positions():
        w = _perim_or_span_bar(axis="x", y=y, height=height, base_z=base_z)
        if interlock and n_x > 0:
            for x in _x_positions():
                # notch the upper half at each crossing
                w = w.cut(_slot(wall + 0.4, wall + 0.4, half + 0.2, x, y, base_z + half + 0.1))
        parts.append(w)

    if not parts:
        return None
    grid = parts[0]
    for p in parts[1:]:
        grid = grid.union(p)
    return grid


def _perim_or_span_bar(axis, height, base_z, x=0.0, y=0.0):
    """A single partition bar spanning the full interior in the given axis."""
    if axis == "y":  # runs along Y (full depth), thin in X
        return _slot(wall, span_y, height, x, 0.0, base_z)
    return _slot(span_x, wall, height, 0.0, y, base_z)  # runs along X (full width)


def build_dividers():
    """Bottomless interlocking grid: perimeter frame + notched interior partitions."""
    body = _perimeter_frame(overall_h, 0.0)
    grid = _grid_walls(overall_h, 0.0)
    if grid is not None:
        body = body.union(grid)
    return body


def build_tray():
    """Solid-bottom divided tray: floor slab + perimeter walls + partitions."""
    base = cq.Workplane("XY").box(overall_w, overall_d, floor, centered=(True, True, False))
    wall_h = overall_h - floor
    frame = _perimeter_frame(wall_h, floor)
    body = base.union(frame)
    # For a floored tray the partitions rest on the floor and need no interlock,
    # but we reuse the same notched grid so tray + dividers share the CDG.
    grid = _grid_walls(wall_h, floor)
    if grid is not None:
        body = body.union(grid)
    # Soften the top rim for comfort.
    try:
        body = body.edges(">Z").fillet(min(wall * 0.35, 0.6))
    except Exception:
        pass
    return body


def build_single_divider():
    """One partition strip spanning the width, slotted from the top at each column
    crossing so cross strips can half-lap into it. Laid flat-ready, standing upright."""
    strip = _slot(span_x, wall, overall_h, 0.0, 0.0, 0.0)
    if interlock:
        half = overall_h / 2.0
        for x in _x_positions():
            strip = strip.cut(_slot(wall + 0.4, wall + 0.6, half + 0.2, x, 0.0, half + 0.1))
    return strip


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "dividers":
    result = build_dividers()
elif target_part == "single_divider":
    result = build_single_divider()
else:
    result = build_tray()
