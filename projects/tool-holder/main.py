"""
Tool Holder (CNC / lathe) — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A shop organizer that holds cutting tools by their shank. A block carries an
array of correctly-sized bores or pockets for the selected tool family, and can
be freestanding, wall-mounted, or dropped into a drawer as a low tray.

`tool_type` select:
  - "end_mill"     : vertical round bores for straight-shank end mills (Ø shank)
  - "er_collet"    : round bores at the ER collet outer diameter
  - "lathe_insert" : rectangular pockets for indexable inserts (tray)
  - "drill_index"  : a stepped row of graduated bores for a drill set

Three build targets are dispatched by `target_part`:
  - "block"         : a freestanding block with the tool array
  - "wall_rack"     : the block with a back plate + wall screw holes
  - "drawer_insert" : a low tray version for a drawer

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `shank_dia`).
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


# ER collet nominal outer diameters (series -> OD mm). ER20 seats an ~Ø20 collet.
ER_OD = {"ER11": 11.5, "ER16": 17.0, "ER20": 21.0, "ER25": 26.0, "ER32": 33.0}

# ── Parameters ───────────────────────────────────────────────────────────────
tool_type    = str(  PARAM(lambda: tool_type, "end_mill"))  # end_mill|er_collet|lathe_insert|drill_index
shank_dia    = float(PARAM(lambda: shank_dia,      6.0))   # straight shank diameter (end_mill)
er_series    = str(  PARAM(lambda: er_series,   "ER20"))   # ER collet series
slots        = int(  PARAM(lambda: slots,            8))   # number of tools per row
rows         = int(  PARAM(lambda: rows,             1))   # number of rows
pitch        = float(PARAM(lambda: pitch,         25.0))   # centre-to-centre spacing
bore_depth   = float(PARAM(lambda: bore_depth,    22.0))   # how deep each bore/pocket goes
block_h      = float(PARAM(lambda: block_h,       30.0))   # block height
margin       = float(PARAM(lambda: margin,        12.0))   # material around the array
drill_min    = float(PARAM(lambda: drill_min,      2.0))   # smallest drill (drill_index)
drill_step   = float(PARAM(lambda: drill_step,     1.0))   # drill size increment
insert_w     = float(PARAM(lambda: insert_w,      14.0))   # insert pocket size (lathe_insert)
wall_mount   = bool( PARAM(lambda: wall_mount,   False))   # add back plate + screw holes
screw_dia    = float(PARAM(lambda: screw_dia,      4.5))   # wall screw clearance dia

target_part  = str(  PARAM(lambda: target_part, "block"))

# ── Derived / clamped ────────────────────────────────────────────────────────
slots       = max(1, min(slots, 24))
rows        = max(1, min(rows, 8))
shank_dia   = max(1.0, min(shank_dia, 40.0))
pitch       = max(6.0, min(pitch, 80.0))
bore_depth  = max(4.0, min(bore_depth, 100.0))
block_h     = max(bore_depth + 4.0, min(block_h, 120.0))
margin      = max(4.0, min(margin, 40.0))
drill_step  = max(0.1, min(drill_step, 5.0))
insert_w    = max(4.0, min(insert_w, 40.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _hole_dia(i):
    """Diameter of the i-th tool opening, by tool family."""
    if tool_type == "er_collet":
        return ER_OD.get(er_series, 21.0)
    if tool_type == "drill_index":
        return max(0.6, drill_min + i * drill_step)
    # end_mill (and default)
    return shank_dia


def _footprint():
    """(width X, depth Y) of the block that holds the array."""
    max_open = max(_hole_dia(slots - 1), shank_dia, insert_w)
    w = (slots - 1) * pitch + max_open + 2.0 * margin
    d = (rows - 1) * pitch + max_open + 2.0 * margin
    return w, d


def _cell_centres():
    """(x, y) centres for every opening in the grid."""
    w, d = _footprint()
    span_x = (slots - 1) * pitch
    span_y = (rows - 1) * pitch
    pts = []
    for r in range(rows):
        py = -span_y / 2.0 + r * pitch
        for c in range(slots):
            px = -span_x / 2.0 + c * pitch
            pts.append((px, py, c))
    return pts


def _bore_cutter(z_top):
    """One fused cutter of all tool openings, cut downward from z_top by
    bore_depth. Openings are batched by diameter (a single pushPoints per
    distinct size) so even a 24×8 array stays fast — no per-hole unions."""
    z0 = z_top - bore_depth
    cells = _cell_centres()

    if tool_type == "lathe_insert":
        # All pockets share one square size — one batched extrude.
        pts = [(x, y) for (x, y, _c) in cells]
        return (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, z0))
            .pushPoints(pts)
            .rect(insert_w, insert_w)
            .extrude(bore_depth + 0.5)
        )

    # Round openings: group centres by diameter so each distinct size is a
    # single pushPoints extrude (uniform families collapse to one group).
    groups = {}
    for (x, y, c) in cells:
        d = round(_hole_dia(c), 4)
        groups.setdefault(d, []).append((x, y))

    body = None
    for d, pts in groups.items():
        cut = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, z0))
            .pushPoints(pts)
            .circle(d / 2.0)
            .extrude(bore_depth + 0.5)
        )
        body = cut if body is None else body.union(cut)
    return body


def _block_solid(h):
    w, d = _footprint()
    solid = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    r = min(3.0, margin / 2.0)
    if r > 0.2:
        try:
            solid = solid.edges("|Z").fillet(r)
        except Exception:
            pass
    return solid, w, d


# ── block ────────────────────────────────────────────────────────────────────
def build_block():
    solid, _, _ = _block_solid(block_h)
    solid = solid.cut(_bore_cutter(block_h))
    return solid


# ── wall_rack ────────────────────────────────────────────────────────────────
def build_wall_rack():
    """Block plus a vertical back plate with keyhole-free screw clearance holes."""
    h = block_h
    solid, w, d = _block_solid(h)
    solid = solid.cut(_bore_cutter(h))

    back_t = max(5.0, margin * 0.6)
    back_h = h + 25.0
    back = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, -d / 2.0 - back_t / 2.0, 0.0))
        .box(w, back_t, back_h, centered=(True, True, False))
    )
    solid = solid.union(back)

    # Two screw holes through the back plate (thickness along Y).
    hx = w / 2.0 - max(screw_dia, 8.0)
    hz = h + 14.0
    holes = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0.0, hz, d / 2.0 + back_t + 1.0))
        .pushPoints([(hx, 0.0), (-hx, 0.0)])
        .circle(screw_dia / 2.0)
        .extrude(back_t + 2.0)
    )
    solid = solid.cut(holes)
    return solid


# ── drawer_insert ────────────────────────────────────────────────────────────
def build_drawer_insert():
    """A low tray: a shallow block whose bores do not pass through, sized to lie
    flat in a drawer. Height is capped so tools sit proud for easy grabbing."""
    h = min(block_h, bore_depth + 6.0)
    solid, _, _ = _block_solid(h)
    solid = solid.cut(_bore_cutter(h))
    return solid


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "block":         build_block,
    "wall_rack":     build_wall_rack,
    "drawer_insert": build_drawer_insert,
}

result = _dispatch.get(target_part, build_block)()
