"""
Pill Organizer — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A compartmentalized pill box. A tray carries a grid of open compartments laid out
by the chosen schedule (7-day, 7-day AM/PM = 14, or a custom cols x rows). A
sliding lid can cap the whole tray, or a single-compartment travel box can be
printed on its own.

  * "tray"         — the open compartment tray (target_part == "tray").
  * "tray_lidded"  — the tray plus a sliding lid that runs in side rails and seals
                     the compartments (target_part == "tray_lidded").
  * "single_day"   — one compartment as a small travel box with a friction lid
                     (target_part == "single_day").

Watertight strategy: the tray is a solid slab with rectangular pockets cut from
the top, always leaving a floor beneath each pocket and full walls between them.
The sliding lid and its rails are solid boxes cut with clearance grooves. The
single-day box is a hollowed cube with a press-fit cap; each piece exports as an
independent manifold solid.

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
target_part = str(PARAM(lambda: target_part, "tray"))  # tray | tray_lidded | single_day

days      = str(  PARAM(lambda: days,      "7day"))    # 7day | 7day_2x | custom
custom_cols = int(PARAM(lambda: custom_cols,   4))     # columns when days == custom
custom_rows = int(PARAM(lambda: custom_rows,   2))     # rows when days == custom
cell       = float(PARAM(lambda: cell,      26.0))     # compartment inner size (mm, square)
cell_depth = float(PARAM(lambda: cell_depth, 18.0))    # compartment inner depth (mm)
wall       = float(PARAM(lambda: wall,       2.0))     # wall between/around compartments
floor      = float(PARAM(lambda: floor,      2.0))     # tray floor thickness
lid        = str(  PARAM(lambda: lid,   "sliding"))    # sliding | individual | none
clearance  = float(PARAM(lambda: clearance,  0.4))     # fit clearance (lid / cap)

# ── Clamps ───────────────────────────────────────────────────────────────────
custom_cols = max(1, min(custom_cols, 10))
custom_rows = max(1, min(custom_rows, 6))
cell       = max(10.0, min(cell, 60.0))
cell_depth = max(6.0,  min(cell_depth, 60.0))
wall       = max(1.2,  min(wall, 6.0))
floor      = max(1.2,  min(floor, 6.0))
clearance  = max(0.1,  min(clearance, 1.0))


def layout():
    """Return (cols, rows) for the chosen schedule."""
    if days == "7day":
        return 7, 1
    if days == "7day_2x":
        return 7, 2
    return custom_cols, custom_rows


# ── Shared helpers ────────────────────────────────────────────────────────────
def block(w, d, h, z0=0.0):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .box(w, d, h, centered=(True, True, False))
    )


def grid_points(nx, ny, px, py):
    pts = []
    x0 = -((nx - 1) * px) / 2.0
    y0 = -((ny - 1) * py) / 2.0
    for r in range(ny):
        for c in range(nx):
            pts.append((x0 + c * px, y0 + r * py))
    return pts


def rect_pockets(pts, w, d, z0, depth):
    """A union of rectangular pockets (the cutter for a compartment grid)."""
    cutter = None
    for (x, y) in pts:
        p = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, z0))
            .box(w, d, depth, centered=(True, True, False))
        )
        cutter = p if cutter is None else cutter.union(p)
    return cutter


def build_tray(with_lid):
    nx, ny = layout()
    pitch = cell + wall
    inner_w = nx * pitch - wall          # span of cells + inter-walls
    inner_d = ny * pitch - wall
    body_h = cell_depth + floor

    # Extra shoulder around the pocket field for structure (and lid rails).
    rail_extra = (2.0 * (wall + clearance) + 3.0) if with_lid else wall
    body_w = inner_w + 2.0 * rail_extra
    body_d = inner_d + 2.0 * wall

    body = block(body_w, body_d, body_h)

    pts = grid_points(nx, ny, pitch, pitch)
    body = body.cut(rect_pockets(pts, cell, cell, floor, cell_depth + 1.0))

    if with_lid:
        body = body.union(_lid_rails(body_w, body_d, body_h))
        slider = _sliding_lid(body_w, body_d, body_h)
        # Park the lid alongside the tray so both print flat and are visible.
        slider = slider.translate((0, body_d / 2.0 + 8.0 + body_d / 2.0, 0))
        body = body.union(slider)

    try:
        body = body.edges(">Z").edges("|Z").fillet(min(1.0, wall * 0.4))
    except Exception:
        pass
    return body


def _lid_rails(body_w, body_d, body_h):
    """Two rails along the long (X) edges with an inward-facing groove the lid
    tongue slides into. Modelled as solid rails minus a groove channel."""
    rail_h = 4.0
    rail_t = wall + clearance + 1.5
    groove_h = 2.0 + clearance
    rails = None
    for sign in (-1.0, 1.0):
        y = sign * (body_d / 2.0 - rail_t / 2.0)
        solid = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y, body_h))
            .box(body_w, rail_t, rail_h, centered=(True, True, False))
        )
        # Groove opens toward the tray centre.
        gy = y - sign * (rail_t / 2.0 - (0.8 + clearance) / 2.0)
        groove = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, gy, body_h + rail_h - groove_h))
            .box(body_w + 2.0, 0.8 + clearance, groove_h + 0.5, centered=(True, True, False))
        )
        solid = solid.cut(groove)
        rails = solid if rails is None else rails.union(solid)
    return rails


def _sliding_lid(body_w, body_d, body_h):
    """A flat cover with side tongues that ride the rail grooves."""
    lid_t = 2.0
    cover = block(body_w - 2.0 * clearance, body_d - 2.0 * (wall + clearance), lid_t)
    # Tongues along both long edges.
    tongue = None
    for sign in (-1.0, 1.0):
        y = sign * ((body_d - 2.0 * (wall + clearance)) / 2.0 + 0.4)
        t = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y, 0))
            .box(body_w - 2.0 * clearance, 0.8, lid_t, centered=(True, True, False))
        )
        tongue = t if tongue is None else tongue.union(t)
    cover = cover.union(tongue)
    return cover


def build_single_day():
    """One compartment as a small travel box with a friction-fit cap."""
    outer = cell + 2.0 * wall
    box_h = cell_depth + floor
    body = block(outer, outer, box_h)
    body = body.cut(
        block(cell, cell, cell_depth + 1.0, z0=floor)
    )
    # A friction cap: a lid plate with a downward plug that nests in the cell.
    plug_w = cell - 2.0 * clearance
    plug_h = 5.0
    cap = block(outer, outer, floor)
    plug_outer = block(plug_w, plug_w, plug_h)
    plug_inner = block(plug_w - 2.0 * max(1.0, wall - 0.6),
                       plug_w - 2.0 * max(1.0, wall - 0.6),
                       plug_h + 1.0)
    plug = plug_outer.cut(plug_inner).translate((0, 0, -plug_h))
    cap = cap.union(plug)
    # Park the cap beside the box.
    cap = cap.translate((outer + 8.0, 0, 0))
    return body.union(cap)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tray_lidded":
    result = build_tray(with_lid=(lid != "none"))
elif target_part == "single_day":
    result = build_single_day()
else:  # "tray"
    result = build_tray(with_lid=False)
