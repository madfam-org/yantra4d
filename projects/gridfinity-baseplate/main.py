"""
Gridfinity Baseplate (Screw-Down) — Yantra4D Hyperobject Cartridge (CadQuery).

A Gridfinity baseplate on the open 42 mm grid: an nx x ny field of cells, each
with the standard stacked-chamfer socket a Gridfinity bin foot drops into. Fix it
to a drawer or bench with screws, seat magnets under the cells, or add a weighted
perimeter skirt. Grows the `gridfinity` family.

Gridfinity geometry (dimensionally real):
  - grid pitch                = 42.0 mm
  - inter-cell clearance      = 0.5 mm  (41.5 mm top opening)
  - bin-foot chamfer stack    = 0.8 mm @ 45 deg + 1.8 mm straight + 2.15 mm @ 45
  - outer corner radius       = 3.75 mm

Watertight strategy:
  The socket chamfer stack is built as STACKED LOFTED FRUSTA (loft to a flat
  bottom, never a revolve of a cut profile — a revolve of a groove yields a
  multi-component non-watertight mesh). Screw counterbores and magnet pockets are
  through / blind bores that vent to a face. The skirt is a solid wall UNIONED
  with overlap onto the slab. Fillet the clean blank BEFORE the sockets are cut,
  wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>).
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


# ── Gridfinity constants (real spec) ─────────────────────────────────────────
PITCH = 42.0            # grid pitch (mm)
CLEAR = 0.5             # inter-cell clearance -> 41.5 mm top opening
CORNER_R = 3.75         # Gridfinity outer corner radius
C1 = 0.8               # top 45 deg lead-in
S2 = 1.8               # straight run
C3 = 2.15              # lower 45 deg
SOCKET_H = C1 + S2 + C3


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "screw_baseplate"))
# "screw_baseplate" | "magnet_baseplate" | "weighted_frame"

nx = int(PARAM(lambda: nx, 2))                      # cells in X
ny = int(PARAM(lambda: ny, 2))                      # cells in Y
floor_th = float(PARAM(lambda: floor_th, 4.0))      # baseplate floor thickness
screw_d = float(PARAM(lambda: screw_d, 4.4))        # screw clearance (M4 ~4.4)
screw_head_d = float(PARAM(lambda: screw_head_d, 8.5))  # screw head counterbore
magnet_d = float(PARAM(lambda: magnet_d, 6.2))      # magnet pocket dia (6 mm mag)
magnet_h = float(PARAM(lambda: magnet_h, 2.2))      # magnet pocket depth
skirt_h = float(PARAM(lambda: skirt_h, 8.0))        # weighted-frame skirt height

# Clamp to sane ranges so extreme UI values never crash the kernel.
# Cap the grid at 4 x 4 (matches the proven grid-hub limit): the lofted socket
# stack is expensive, and 16 cells render well under the time threshold whereas
# a 6 x 6 (36 cells) blows past it.
nx = max(1, min(nx, 4))
ny = max(1, min(ny, 4))
floor_th = max(2.5, min(floor_th, 12.0))
screw_d = max(2.5, min(screw_d, 7.0))
screw_head_d = max(screw_d + 1.5, min(screw_head_d, 14.0))
magnet_d = max(3.0, min(magnet_d, 10.0))
magnet_h = max(1.0, min(magnet_h, floor_th - 1.0))
skirt_h = max(4.0, min(skirt_h, 25.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _fillet_safe(wp, selector, radius):
    try:
        return wp.edges(selector).fillet(radius)
    except Exception:
        return wp


def _base_slab(total_w, total_h, slab_h):
    slab = cq.Workplane("XY").box(total_w, total_h, slab_h, centered=(True, True, False))
    return _fillet_safe(slab, "|Z", CORNER_R)


def _cut_sockets(body, total_w, total_h, slab_h):
    """Cut the chamfer-stack socket into every cell, built as stacked lofted
    frusta (loft to a flat bottom → watertight, never a revolve of a groove).
    Each socket is cut individually from the slab — sequential local cuts are far
    faster than accumulating one giant fused cutter then a single boolean."""
    top_out = PITCH - CLEAR                 # 41.5 mm opening at the very top
    hw_top = top_out / 2.0
    hw_mid = hw_top - C1
    hw_bot = hw_mid
    hw_floor = hw_mid - C3
    x0 = -(total_w - PITCH) / 2.0
    y0 = -(total_h - PITCH) / 2.0
    z_floor = slab_h - SOCKET_H

    for iy in range(ny):
        for ix in range(nx):
            cx = x0 + ix * PITCH
            cy = y0 + iy * PITCH
            prof = (
                cq.Workplane("XY").transformed(offset=cq.Vector(cx, cy, z_floor))
                .rect(2 * hw_floor, 2 * hw_floor)
                .workplane(offset=C3).rect(2 * hw_bot, 2 * hw_bot)
                .workplane(offset=S2).rect(2 * hw_mid, 2 * hw_mid)
                .workplane(offset=C1).rect(2 * hw_top, 2 * hw_top)
                .loft(combine=True)
            )
            cap = (
                cq.Workplane("XY").transformed(offset=cq.Vector(cx, cy, slab_h - 0.01))
                .rect(2 * hw_top, 2 * hw_top).extrude(0.5)
            )
            body = body.cut(prof.union(cap))
    return body


def _cell_centres(total_w, total_h):
    x0 = -(total_w - PITCH) / 2.0
    y0 = -(total_h - PITCH) / 2.0
    return [(x0 + ix * PITCH, y0 + iy * PITCH)
            for iy in range(ny) for ix in range(nx)]


def _dims():
    return nx * PITCH, ny * PITCH


# ── Part builders ────────────────────────────────────────────────────────────
def build_screw_baseplate():
    """The classic Gridfinity baseplate with a countersunk SCREW hole at each cell
    centre so it fixes down to a drawer or bench. Holes vent through both faces;
    counterbores are open pockets on the underside."""
    total_w, total_h = _dims()
    slab_h = SOCKET_H + floor_th
    body = _base_slab(total_w, total_h, slab_h)
    body = _cut_sockets(body, total_w, total_h, slab_h)

    # Screw counterbore + through-hole at each cell centre, drilled from BELOW so
    # the head sinks under the plate (vents to both faces).
    pts = _cell_centres(total_w, total_h)
    body = (
        body.faces("<Z").workplane(centerOption="ProjectedOrigin")
        .pushPoints(pts)
        .cboreHole(screw_d, screw_head_d, floor_th * 0.6)
    )
    return body


def build_magnet_baseplate():
    """A Gridfinity baseplate with MAGNET pockets at each cell's four corners so a
    printed bin with corner magnets snaps down. Pockets are blind bores opening to
    the underside (vented, no trapped void)."""
    total_w, total_h = _dims()
    slab_h = SOCKET_H + floor_th
    body = _base_slab(total_w, total_h, slab_h)
    body = _cut_sockets(body, total_w, total_h, slab_h)

    # Four magnet pockets per cell, inset from the corners (Gridfinity ~ 13 mm off
    # centre). Bored up from the underside.
    off = 13.0
    pockets = []
    for (cx, cy) in _cell_centres(total_w, total_h):
        for sx in (-1, 1):
            for sy in (-1, 1):
                pockets.append((cx + sx * off, cy + sy * off))
    body = (
        body.faces("<Z").workplane(centerOption="ProjectedOrigin")
        .pushPoints(pockets)
        .hole(magnet_d, depth=magnet_h)
    )
    return body


def build_weighted_frame():
    """A heavier baseplate with a solid perimeter SKIRT so it sits stable on a
    desk without screws (fill the skirt with shot/epoxy if desired). The skirt is
    a wall unioned with overlap around the slab; the cell sockets stay open."""
    total_w, total_h = _dims()
    slab_h = SOCKET_H + floor_th
    body = _base_slab(total_w, total_h, slab_h)
    body = _cut_sockets(body, total_w, total_h, slab_h)

    # Perimeter skirt: an outer ring wall hanging BELOW the slab (in -Z), built as
    # an outer block minus an inner block, unioned with overlap onto the slab.
    wall = 3.0
    outer = _base_slab(total_w, total_h, skirt_h)
    outer = outer.translate((0, 0, -skirt_h + 0.01))
    inner = (
        cq.Workplane("XY")
        .box(total_w - 2 * wall, total_h - 2 * wall, skirt_h + 1.0,
             centered=(True, True, False))
        .translate((0, 0, -skirt_h - 0.5))
    )
    ring = outer.cut(inner)
    body = body.union(ring)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "magnet_baseplate":
    result = build_magnet_baseplate()
elif target_part == "weighted_frame":
    result = build_weighted_frame()
else:
    result = build_screw_baseplate()
