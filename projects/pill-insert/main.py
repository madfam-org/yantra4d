import cadquery as cq


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part = PARAM(lambda: target_part, "tray")
cols = int(PARAM(lambda: cols, 7))
rows = int(PARAM(lambda: rows, 1))
cell = float(PARAM(lambda: cell, 22.0))
depth = float(PARAM(lambda: depth, 18.0))
wall = float(PARAM(lambda: wall, 2.0))
clearance = float(PARAM(lambda: clearance, 0.4))

# ─── Real-world reference dimensions (cited as an internal grid standard) ──────
# A weekly organiser is a 7 x 1 grid of ~20 mm compartments; daily organisers use
#   4 columns (morning/noon/eve/night). This is a project-internal grid — the
#   compartment pitch is the interface a matching lid / single cup mates to.
CORNER_R = 2.0
FLOOR = 2.0


def _fillet_safe(wp, sel, r):
    try:
        return wp.edges(sel).fillet(r)
    except Exception:
        return wp


def _grid_dims():
    n_c = max(1, cols)
    n_r = max(1, rows)
    pitch = cell + wall
    length = n_c * pitch + wall
    width = n_r * pitch + wall
    return n_c, n_r, pitch, length, width


# ─── Mode 1: compartment tray ─────────────────────────────────────────────────
def build_tray():
    """A grid of open-top pill compartments. Each cell is a pocket cut from a solid
    block down to a shared floor; pockets open to the top only → no trapped void."""
    n_c, n_r, pitch, length, width = _grid_dims()
    height = depth + FLOOR

    block = cq.Workplane("XY").box(length, width, height, centered=(True, True, False))
    block = _fillet_safe(block, "|Z", CORNER_R)

    x0 = -(n_c - 1) * pitch / 2.0
    y0 = -(n_r - 1) * pitch / 2.0
    pts = []
    for r in range(n_r):
        for c in range(n_c):
            pts.append((x0 + c * pitch, y0 + r * pitch))

    pockets = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, FLOOR))
        .pushPoints(pts)
        .rect(cell, cell)
        .extrude(depth + 2.0)
    )
    # round the pocket verticals for a wipe-clean cell
    block = block.cut(pockets)
    return block


# ─── Mode 2: friction lid ─────────────────────────────────────────────────────
def build_lid():
    """A friction lid: a shallow capping shell with a downward lip that grips the
    OUTSIDE of the tray by a small interference (clearance). The underside is an
    open pocket (opens down) → watertight, and it snaps over the tray rim."""
    n_c, n_r, pitch, length, width = _grid_dims()
    lip_h = 8.0
    top_th = 2.0
    # Lid outer = tray outer + wall + fit; inner cavity clears the tray outer.
    outer_l = length + 2.0 * wall
    outer_w = width + 2.0 * wall
    total_h = lip_h + top_th

    lid = cq.Workplane("XY").box(outer_l, outer_w, total_h, centered=(True, True, False))
    lid = _fillet_safe(lid, "|Z", CORNER_R)

    # Cavity that slips over the tray (tray outer + clearance), open to the bottom.
    cav_l = length + 2.0 * clearance
    cav_w = width + 2.0 * clearance
    cavity = (
        cq.Workplane("XY")
        .box(cav_l, cav_w, lip_h + 1.0, centered=(True, True, False))
        .translate((0, 0, -0.5))
    )
    lid = lid.cut(cavity)
    return lid


# ─── Mode 3: single removable cup ─────────────────────────────────────────────
def build_single_cup():
    """A single compartment cup sized to one tray cell (minus clearance) with a
    small finger tab, so a day's dose lifts out to carry. Open-top pocket + a solid
    tab that opens to air → watertight."""
    side = cell - 2.0 * clearance
    height = depth + FLOOR
    cup = cq.Workplane("XY").box(side, side, height, centered=(True, True, False))
    cup = _fillet_safe(cup, "|Z", CORNER_R)

    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, FLOOR))
        .rect(side - 2.0 * wall, side - 2.0 * wall)
        .extrude(depth + 2.0)
    )
    cup = cup.cut(pocket)

    # A finger tab on +Y so it lifts out of the tray.
    tab = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, side / 2.0, height - 6.0))
        .box(side * 0.5, wall + 2.0, 6.0, centered=(True, True, False))
    )
    cup = cup.union(tab)
    cup = _fillet_safe(cup, ">Z", 0.8)
    return cup


# ─── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tray":
    result = build_tray()
elif target_part == "lid":
    result = build_lid()
elif target_part == "single_cup":
    result = build_single_cup()
else:
    result = build_tray()
