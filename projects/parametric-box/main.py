"""
Parametric Storage Box — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A fits-anything box with independent wall/floor control, a rounded profile, an
optional press-fit lid, and an optional interior divider grid. Sized by interior
dimensions so the printed cavity is exactly what the user asked for.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `inner_w`).
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


# ── Parameters (interior-driven) ─────────────────────────────────────────────
inner_w      = float(PARAM(lambda: inner_w,      80.0))   # interior X (mm)
inner_d      = float(PARAM(lambda: inner_d,      60.0))   # interior Y (mm)
inner_h      = float(PARAM(lambda: inner_h,      40.0))   # interior Z (mm)
wall         = float(PARAM(lambda: wall,          2.0))   # side wall thickness
floor        = float(PARAM(lambda: floor,         2.0))   # floor thickness
corner_r     = float(PARAM(lambda: corner_r,      4.0))   # outer corner radius
fillet_top   = bool( PARAM(lambda: fillet_top,   True))   # soften top rim
lid_enabled  = bool( PARAM(lambda: lid_enabled,  True))   # generate a press-fit lid
lid_height   = float(PARAM(lambda: lid_height,    8.0))   # lid skirt height
lid_clear    = float(PARAM(lambda: lid_clear,     0.3))   # lid-to-wall clearance (print fit)
div_x        = int(  PARAM(lambda: div_x,           0))   # interior dividers along X
div_y        = int(  PARAM(lambda: div_y,           0))   # interior dividers along Y
div_thick    = float(PARAM(lambda: div_thick,     1.6))   # divider thickness

target_part  = str(  PARAM(lambda: target_part, "box"))   # "box" | "lid"

# Derived outer envelope
outer_w = inner_w + 2.0 * wall
outer_d = inner_d + 2.0 * wall
outer_h = inner_h + floor
# corner radius can't exceed half the shortest outer side
corner_r = max(0.0, min(corner_r, min(outer_w, outer_d) / 2.0 - 0.01))


# ── Helpers ──────────────────────────────────────────────────────────────────
def rounded_block(w, d, h, r):
    """Axis-aligned block on XY (origin centered in X/Y, base at z=0), optionally
    with rounded vertical edges."""
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.05:
        wp = wp.edges("|Z").fillet(r)
    return wp


def build_box():
    # Solid outer, then hollow the cavity from the top.
    body = rounded_block(outer_w, outer_d, outer_h, corner_r)

    inner_r = max(0.0, corner_r - wall)
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor))
        .box(inner_w, inner_d, inner_h + 1.0, centered=(True, True, False))
    )
    if inner_r > 0.05:
        cavity = cavity.edges("|Z").fillet(inner_r)
    body = body.cut(cavity)

    # Interior dividers (thin walls rising from the floor).
    if div_x > 0 or div_y > 0:
        body = body.union(_dividers())

    # Soften the top rim for comfort / printability.
    if fillet_top:
        rim = min(wall * 0.4, 0.8)
        try:
            body = body.edges(">Z").fillet(rim)
        except Exception:
            pass  # fillet can fail on some divider intersections — non-fatal
    return body


def _dividers():
    walls = []
    # Evenly spaced partitions across the interior span.
    if div_x > 0:
        step = inner_w / (div_x + 1)
        for i in range(1, div_x + 1):
            x = -inner_w / 2.0 + i * step
            walls.append(
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x, 0, floor))
                .box(div_thick, inner_d, inner_h, centered=(True, True, False))
            )
    if div_y > 0:
        step = inner_d / (div_y + 1)
        for i in range(1, div_y + 1):
            y = -inner_d / 2.0 + i * step
            walls.append(
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, y, floor))
                .box(inner_w, div_thick, inner_h, centered=(True, True, False))
            )
    result = walls[0]
    for w in walls[1:]:
        result = result.union(w)
    return result


def build_lid():
    """Press-fit lid: a top plate plus a downward skirt that nests inside the box
    walls with `lid_clear` clearance on each side."""
    # Top plate matches the outer footprint.
    plate = rounded_block(outer_w, outer_d, floor, corner_r)

    # Skirt: outer size = interior minus clearance, hollowed to a thin wall.
    skirt_w = inner_w - 2.0 * lid_clear
    skirt_d = inner_d - 2.0 * lid_clear
    skirt_wall = max(1.2, wall - 0.4)
    skirt_r = max(0.0, corner_r - wall - lid_clear)

    skirt_outer = cq.Workplane("XY").box(skirt_w, skirt_d, lid_height, centered=(True, True, False))
    if skirt_r > 0.05:
        skirt_outer = skirt_outer.edges("|Z").fillet(skirt_r)
    skirt_inner = cq.Workplane("XY").box(
        skirt_w - 2.0 * skirt_wall, skirt_d - 2.0 * skirt_wall, lid_height + 1.0,
        centered=(True, True, False),
    )
    skirt = skirt_outer.cut(skirt_inner)

    # Place the skirt hanging below the plate (plate occupies z:[0,floor]).
    skirt = skirt.translate((0, 0, -lid_height))
    lid = plate.union(skirt)
    return lid


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "lid" and lid_enabled:
    result = build_lid()
else:
    result = build_box()
