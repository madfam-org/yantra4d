"""Matrix Frame — Neopixel / Addressable LED Matrix Frame (Yantra4D Hyperobject).

Frames, diffusers, and mounts for WS2812 / NeoPixel addressable LED matrices and
rings, built to the REAL grid pitch: WS2812B matrices are laid out on a ~10 mm
pixel pitch (an 8x8 panel is ~80 mm, a 16x16 is ~160 mm; each 5050 LED is
~5x5 mm). Three distinct grid modes:

  * bezel_frame   — a picture-frame bezel that surrounds the panel with a front
    lip (window) and a rear rebate the PCB drops into.
  * diffuser_grid — an egg-crate: a thin floor + a wall grid with one open cell
    per pixel, so each LED lights its own diffused square (no bleed).
  * panel_mount   — a rear mounting plate with corner screw bosses on the panel
    footprint + a cable slot.

Watertightness: the diffuser is one solid slab with a grid of THROUGH cells
(each opens front→back, no trapped void); the bezel window + rebate are boolean
cuts open to faces; bosses are solid, filleted before boring. The grid of cell
cutters is unioned into ONE cutter before a single subtraction (fast + robust).

Sandbox contract (cq_runner.py): `cq`+`math` pre-injected; params bare globals
via PARAM(lambda: name, default); final solid assigned to `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "bezel_frame"))
cols        = int(PARAM(lambda: cols,   8))       # matrix columns
rows        = int(PARAM(lambda: rows,   8))       # matrix rows
pitch       = float(PARAM(lambda: pitch, 10.0))   # pixel pitch (mm) — WS2812 ~10
wall        = float(PARAM(lambda: wall,   2.0))   # frame / grid wall thickness
depth       = float(PARAM(lambda: depth,  8.0))   # frame / grid depth (mm)
lip         = float(PARAM(lambda: lip,    2.5))   # front lip (bezel) / floor (grid)
screw_d     = float(PARAM(lambda: screw_d, 3.2))  # M3 mount screw clearance

cols  = max(1, min(cols, 16))
rows  = max(1, min(rows, 16))
pitch = max(5.0, min(pitch, 20.0))
wall  = max(1.2, min(wall, 5.0))
depth = max(4.0, min(depth, 20.0))
lip   = max(1.2, min(lip, 6.0))
screw_d = max(2.0, min(screw_d, 6.0))


def _fillet_safe(wp, selector, radius):
    try:
        return wp.edges(selector).fillet(radius)
    except Exception:
        return wp


def _panel_wh():
    """Active panel width/height from the pixel grid."""
    return cols * pitch, rows * pitch


def _cell_positions():
    """Centre (x, y) of every pixel cell, grid centered on origin."""
    pw, ph = _panel_wh()
    x0 = -(pw - pitch) / 2.0
    y0 = -(ph - pitch) / 2.0
    return [(x0 + c * pitch, y0 + r * pitch) for r in range(rows) for c in range(cols)]


# ── bezel_frame ──────────────────────────────────────────────────────────────
def build_bezel_frame():
    """A picture-frame bezel: outer block, a front window (opening) with a lip,
    and a rear rebate the PCB seats into."""
    pw, ph = _panel_wh()
    outer_w = pw + 2.0 * wall
    outer_h = ph + 2.0 * wall

    body = cq.Workplane("XY").box(outer_w, outer_h, depth, centered=(True, True, False))
    body = _fillet_safe(body, "|Z", min(wall * 1.5, outer_w / 8.0))

    # Front window: an opening slightly inset from the panel edges (the lip). Cut
    # from the front (top, +Z) down through the front lip only, leaving the rear
    # rebate walls. Opens to the top face → no trapped void.
    win_w = pw - 2.0 * lip
    win_h = ph - 2.0 * lip
    window = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, depth - lip))
        .box(win_w, win_h, lip + 2.0, centered=(True, True, False))
    )
    body = body.cut(window)

    # Rear rebate: a pocket the panel PCB drops into from the back (opens to the
    # bottom face, up to the front lip).
    rebate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .box(pw, ph, depth - lip + 1.0, centered=(True, True, False))
    )
    body = body.cut(rebate)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── diffuser_grid ────────────────────────────────────────────────────────────
def build_diffuser_grid():
    """An egg-crate diffuser: a thin floor + a wall grid with one open cell per
    pixel. Built as a solid slab with a single unioned cutter of all cells
    (through the wall region, above the floor)."""
    pw, ph = _panel_wh()
    outer_w = pw + 2.0 * wall
    outer_h = ph + 2.0 * wall

    slab = cq.Workplane("XY").box(outer_w, outer_h, depth, centered=(True, True, False))
    slab = _fillet_safe(slab, "|Z", min(wall, outer_w / 10.0))

    # Cell opening size: pixel pitch minus the wall between cells.
    cell = max(1.0, pitch - wall)
    # Build ONE cutter = union of all cell boxes, then subtract once (robust/fast).
    cutter = None
    for (cx, cy) in _cell_positions():
        c = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, lip))
            .box(cell, cell, depth, centered=(True, True, False))
        )
        cutter = c if cutter is None else cutter.union(c)
    if cutter is not None:
        slab = slab.cut(cutter)

    try:
        slab = slab.clean()
    except Exception:
        pass
    return slab


# ── panel_mount ──────────────────────────────────────────────────────────────
def build_panel_mount():
    """A rear mounting plate on the panel footprint with corner screw bosses and
    a cable slot."""
    pw, ph = _panel_wh()
    plate_w = pw + 2.0 * wall
    plate_h = ph + 2.0 * wall
    plate_th = max(2.0, lip)

    plate = cq.Workplane("XY").box(plate_w, plate_h, plate_th, centered=(True, True, False))
    plate = _fillet_safe(plate, "|Z", min(wall * 1.5, plate_w / 8.0))

    # Corner standoff bosses (solid), unioned with overlap into the plate.
    boss_r = max(screw_d, 3.0)
    bx = plate_w / 2.0 - boss_r - 0.5
    by = plate_h / 2.0 - boss_r - 0.5
    boss_h = depth
    bosses = None
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            b = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(sx * bx, sy * by, 0))
                .circle(boss_r).extrude(boss_h)
            )
            bosses = b if bosses is None else bosses.union(b)
    body = plate.union(bosses)

    # Bore each boss for a screw (blind from the top, into a solid base → but
    # open the base with a matching clearance so no void is trapped: drill fully
    # through the plate).
    holes = None
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            h = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(sx * bx, sy * by, -1.0))
                .circle(screw_d / 2.0).extrude(boss_h + 2.0)
            )
            holes = h if holes is None else holes.union(h)
    body = body.cut(holes)

    # Cable slot through the plate near the bottom edge.
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -plate_h / 2.0 + wall + 3.0, -1.0))
        .box(min(pw * 0.4, 24.0), 6.0, plate_th + 2.0, centered=(True, True, False))
    )
    body = body.cut(slot)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "diffuser_grid":
    result = build_diffuser_grid()
elif target_part == "panel_mount":
    result = build_panel_mount()
else:
    result = build_bezel_frame()
