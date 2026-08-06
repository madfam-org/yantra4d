"""
Cutlery Drawer Tray — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A drawer-filling cutlery tray sized by interior dimensions, with a configurable
compartment grid. Reuses the shared bin/tray body idiom (a solid outer block
hollowed to a five-wall shell, plus evenly spaced partition walls) that the
kitchen batch shares with cabinet-bin. Three forms:

  * "tray"       — straight compartments across the drawer (N columns × M rows).
  * "angled_tray"— the same tray with the dividers raked so knives / forks lie at
                   an ergonomic angle (a slanted set of column walls).
  * "expandable" — a single modular tray SEGMENT with interlocking side tabs so
                   several segments tile to fill any drawer width.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `wall`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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


# ── Parameters (interior-driven) ─────────────────────────────────────────────
inner_w    = float(PARAM(lambda: inner_w,   360.0))  # interior X width (mm)
inner_d    = float(PARAM(lambda: inner_d,   240.0))  # interior Y depth (mm)
inner_h    = float(PARAM(lambda: inner_h,    50.0))  # interior Z height (mm)
wall       = float(PARAM(lambda: wall,        2.0))  # wall / floor / divider thickness
corner_r   = float(PARAM(lambda: corner_r,    2.0))  # outer vertical corner radius
cols       = int(  PARAM(lambda: cols,          5))  # compartment columns (across width)
rows       = int(  PARAM(lambda: rows,          1))  # compartment rows (across depth)
rake_deg   = float(PARAM(lambda: rake_deg,   20.0))  # divider rake angle (angled_tray)
seg_w      = float(PARAM(lambda: seg_w,      80.0))  # segment width (expandable)

target_part = str(PARAM(lambda: target_part, "tray"))  # tray | angled_tray | expandable

# ── Derived envelope + clamps ────────────────────────────────────────────────
wall = max(1.2, min(wall, inner_w / 4.0, inner_d / 4.0))
if target_part == "expandable":
    inner_w = max(30.0, min(seg_w, 200.0))   # a single segment uses seg_w
outer_w = inner_w + 2.0 * wall
outer_d = inner_d + 2.0 * wall
outer_h = inner_h + wall
corner_r = max(0.0, min(corner_r, min(outer_w, outer_d) / 2.0 - 0.01))
cols = max(1, min(cols, 12))
rows = max(1, min(rows, 6))
rake_deg = max(0.0, min(rake_deg, 45.0))


# ── Reusable bin/tray body idiom ─────────────────────────────────────────────
def _box(w, d, h, x=0.0, y=0.0, z=0.0):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z))
        .box(w, d, h, centered=(True, True, False))
    )


def shell():
    """Solid outer block minus interior cavity = a five-wall shell open at top."""
    body = _box(outer_w, outer_d, outer_h)
    if corner_r > 0.05:
        body = body.edges("|Z").fillet(corner_r)
    cavity = _box(inner_w, inner_d, inner_h + 1.0, 0.0, 0.0, wall)
    inner_r = max(0.0, corner_r - wall)
    if inner_r > 0.05:
        cavity = cavity.edges("|Z").fillet(inner_r)
    return body.cut(cavity)


def straight_dividers(n_cols, n_rows):
    """Evenly spaced column (X) and row (Y) partition walls."""
    walls = []
    if n_cols > 1:
        step = inner_w / n_cols
        for i in range(1, n_cols):
            x = -inner_w / 2.0 + i * step
            walls.append(_box(wall, inner_d, inner_h, x, 0.0, wall))
    if n_rows > 1:
        step = inner_d / n_rows
        for j in range(1, n_rows):
            y = -inner_d / 2.0 + j * step
            walls.append(_box(inner_w, wall, inner_h, 0.0, y, wall))
    if not walls:
        return None
    grid = walls[0]
    for w in walls[1:]:
        grid = grid.union(w)
    return grid


def raked_dividers(n_cols, deg):
    """Column dividers raked about Z so compartments slant — cutlery lies angled.
    Each divider is a tall thin wall rotated by `deg`, then trimmed to the cavity
    by intersecting with the interior volume so nothing pokes past the walls."""
    if n_cols <= 1:
        return None
    interior = _box(inner_w, inner_d, inner_h, 0.0, 0.0, wall)
    step = inner_w / n_cols
    walls = []
    # Make each divider long enough to cross the cavity even when rotated.
    long_d = (inner_w + inner_d) * 1.2
    for i in range(1, n_cols):
        x = -inner_w / 2.0 + i * step
        w = _box(wall, long_d, inner_h, x, 0.0, wall).rotate((x, 0, 0), (x, 0, 1), deg)
        walls.append(w)
    grid = walls[0]
    for w in walls[1:]:
        grid = grid.union(w)
    try:
        grid = grid.intersect(interior)
    except Exception:
        return straight_dividers(n_cols, 1)  # fall back to straight if trim fails
    return grid


def side_tabs():
    """Interlocking tabs/slots on the segment's left/right walls so segments tile.
    Right wall gets a protruding tab; left wall gets a matching recess."""
    tab_h = min(inner_h, 12.0)
    tab_w = wall
    tab_len = min(inner_d * 0.4, 40.0)
    z0 = wall + (inner_h - tab_h) / 2.0
    # Protruding tab on +X face.
    tab = _box(tab_w * 1.6, tab_len, tab_h, outer_w / 2.0 + tab_w * 0.3, 0.0, z0)
    # Recess pocket on -X face (cut later).
    pocket = _box(tab_w * 1.8, tab_len + 0.6, tab_h + 0.6, -outer_w / 2.0 + tab_w * 0.3, 0.0, z0 - 0.3)
    return tab, pocket


# ── Part builders ────────────────────────────────────────────────────────────
def build_tray():
    body = shell()
    grid = straight_dividers(cols, rows)
    if grid is not None:
        body = body.union(grid)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_angled_tray():
    body = shell()
    grid = raked_dividers(cols, rake_deg)
    if grid is not None:
        body = body.union(grid)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_expandable():
    body = shell()
    # A couple of straight dividers inside the single segment.
    grid = straight_dividers(max(1, cols // 2 + 1), 1)
    if grid is not None:
        body = body.union(grid)
    tab, pocket = side_tabs()
    body = body.union(tab)
    body = body.cut(pocket)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "angled_tray":
    result = build_angled_tray()
elif target_part == "expandable":
    result = build_expandable()
else:
    result = build_tray()
