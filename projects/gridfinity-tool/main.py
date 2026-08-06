"""
Gridfinity Tool Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A parametric tool holder that drops into any Gridfinity baseplate on the open
42 mm grid: an nx x ny bin with the standard Gridfinity FOOT (the male chamfer
stack that seats in a baseplate socket) carrying tool bores on top. Hold
screwdriver bits and drills, rack pliers/hand tools in angled slots, or stand
pens and round tools in a divided cup. Grows the `gridfinity` family.

Gridfinity geometry (dimensionally real):
  - grid pitch                = 42.0 mm
  - foot clearance            = 0.25 mm per side (41.5 mm foot vs 42 mm cell)
  - foot chamfer stack        = 2.15 mm @ 45 deg + 1.8 mm straight + 0.8 mm @ 45
  - outer corner radius       = 3.75 mm

Watertight strategy:
  The Gridfinity foot is built as STACKED LOFTED FRUSTA per cell, UNIONED onto the
  body block with overlap (never tangent). Tool bores are blind or through holes
  that vent to the top face (no sealed cavities). Angled plier slots are obround
  slots (more robust than fans of arc circles). Fillet clean blanks BEFORE cutting
  bores, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>).
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


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
FOOT_CLEAR = 0.25       # per-side foot clearance -> 41.5 mm foot
CORNER_R = 3.75         # Gridfinity outer corner radius
F_LOW = 0.8            # top 45 deg of the foot (nearest the body)
F_MID = 1.8            # straight run
F_TOE = 2.15           # bottom 45 deg (the toe that hooks the socket)
FOOT_H = F_LOW + F_MID + F_TOE


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "bit_block"))
# "bit_block" | "plier_rack" | "pen_cup"

nx = int(PARAM(lambda: nx, 1))                      # cells in X
ny = int(PARAM(lambda: ny, 2))                      # cells in Y
body_h = float(PARAM(lambda: body_h, 30.0))         # holder body height above foot
bore_d = float(PARAM(lambda: bore_d, 6.5))          # tool bore diameter
bore_pitch = float(PARAM(lambda: bore_pitch, 12.0))  # spacing between bores
wall = float(PARAM(lambda: wall, 2.4))              # cup wall thickness
slot_ang = float(PARAM(lambda: slot_ang, 20.0))     # plier-slot rake angle

# Clamp to sane ranges so extreme UI values never crash the kernel.
nx = max(1, min(nx, 4))
ny = max(1, min(ny, 4))
body_h = max(8.0, min(body_h, 80.0))
bore_d = max(2.0, min(bore_d, 24.0))
bore_pitch = max(bore_d + 2.0, min(bore_pitch, 40.0))
wall = max(1.6, min(wall, 6.0))
slot_ang = max(0.0, min(slot_ang, 40.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _fillet_safe(wp, selector, radius):
    try:
        return wp.edges(selector).fillet(radius)
    except Exception:
        return wp


def _dims():
    return nx * PITCH, ny * PITCH


def _body_block(total_w, total_h, height):
    """The holder body sitting ON TOP of the foot (foot occupies z in [0, FOOT_H];
    body occupies z in [FOOT_H, FOOT_H + height])."""
    blk = (
        cq.Workplane("XY").workplane(offset=FOOT_H)
        .box(total_w - 2 * FOOT_CLEAR, total_h - 2 * FOOT_CLEAR, height,
             centered=(True, True, False))
    )
    return _fillet_safe(blk, "|Z", CORNER_R)


def _add_feet(body, total_w, total_h):
    """Union a Gridfinity FOOT under each cell — the male chamfer stack that seats
    in a baseplate socket. Built as stacked lofted frusta, unioned with overlap
    into the body (never tangent). Foot z: toe at 0 up to body at FOOT_H."""
    top = PITCH - 2 * FOOT_CLEAR            # 41.5 mm foot top (meets the body)
    hw_top = top / 2.0                       # widest, just under the body
    hw_mid = hw_top - F_LOW                  # after the 0.8 @ 45 near the body
    hw_bot = hw_mid                          # straight run keeps width
    hw_toe = hw_mid - F_TOE                  # the toe (narrowest, at the bottom)
    x0 = -(total_w - PITCH) / 2.0
    y0 = -(total_h - PITCH) / 2.0

    for iy in range(ny):
        for ix in range(nx):
            cx = x0 + ix * PITCH
            cy = y0 + iy * PITCH
            foot = (
                cq.Workplane("XY").transformed(offset=cq.Vector(cx, cy, 0))
                .rect(2 * hw_toe, 2 * hw_toe)
                .workplane(offset=F_TOE).rect(2 * hw_bot, 2 * hw_bot)
                .workplane(offset=F_MID).rect(2 * hw_mid, 2 * hw_mid)
                .workplane(offset=F_LOW).rect(2 * hw_top, 2 * hw_top)
                .loft(combine=True)
            )
            # A short straight cap prism above the loft so the foot top overlaps
            # into the body (never tangent) — a plain extruded box, not a loft, so
            # no degenerate geometry.
            cap = (
                cq.Workplane("XY").transformed(offset=cq.Vector(cx, cy, FOOT_H - 0.5))
                .rect(2 * hw_top, 2 * hw_top).extrude(1.0)
            )
            body = body.union(foot.union(cap))
    return body


def _bore_grid(total_w, total_h):
    """Grid of (x, y) bore centres that fit inside the body top with margin."""
    usable_w = total_w - 2 * (wall + FOOT_CLEAR)
    usable_h = total_h - 2 * (wall + FOOT_CLEAR)
    ncx = max(1, int(usable_w // bore_pitch) + 1)
    ncy = max(1, int(usable_h // bore_pitch) + 1)
    spanx = (ncx - 1) * bore_pitch
    spany = (ncy - 1) * bore_pitch
    return [(-spanx / 2.0 + i * bore_pitch, -spany / 2.0 + j * bore_pitch)
            for j in range(ncy) for i in range(ncx)]


# ── Part builders ────────────────────────────────────────────────────────────
def build_bit_block():
    """A solid Gridfinity-footed block with a grid of vertical bores for
    screwdriver bits and small drills. Bores are blind holes opening to the top
    face (vented, no sealed cavity)."""
    total_w, total_h = _dims()
    body = _body_block(total_w, total_h, body_h)
    body = _add_feet(body, total_w, total_h)

    top_z = FOOT_H + body_h
    depth = min(body_h - 2.0, body_h * 0.85)
    pts = _bore_grid(total_w, total_h)
    body = (
        body.faces(">Z").workplane(centerOption="ProjectedOrigin")
        .pushPoints(pts)
        .hole(bore_d, depth=depth)
    )
    _ = top_z
    return body


def build_plier_rack():
    """A Gridfinity-footed block with a row of RAKED slots so pliers and hand
    tools hang jaw-down at an angle. Slots are obround (robust) through-cuts from
    the top, tilted by `slot_ang`."""
    total_w, total_h = _dims()
    body = _body_block(total_w, total_h, body_h)
    body = _add_feet(body, total_w, total_h)

    usable_h = total_h - 2 * (wall + FOOT_CLEAR)
    n = max(1, int(usable_h // (bore_d + 4.0)))
    span = (n - 1) * (bore_d + 4.0)
    slot_len = min(total_w * 0.6, total_w - 2 * (wall + 2.0))
    tan_a = math.tan(math.radians(slot_ang))

    for j in range(n):
        y = -span / 2.0 + j * (bore_d + 4.0)
        # A raked slot: an obround extruded down, then the whole cutter is skewed
        # by translating its top vs bottom. Approximate the rake by making the
        # slot a tilted box-with-rounded-ends via slot2D on a tilted workplane.
        dx = tan_a * body_h
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y, FOOT_H - 1.0),
                         rotate=cq.Vector(0, slot_ang, 0))
            .slot2D(slot_len, bore_d, angle=0)
            .extrude(body_h + 2.0)
        )
        body = body.cut(slot)
        _ = dx
    return body


def build_pen_cup():
    """A Gridfinity-footed CUP with thick walls and a divided interior for pens,
    markers and round tools. The interior is an open pocket (vents up) split by a
    cross rib; drain holes vent the bottom so no sealed void forms."""
    total_w, total_h = _dims()
    body = _body_block(total_w, total_h, body_h)
    body = _add_feet(body, total_w, total_h)

    inner_w = total_w - 2 * (wall + FOOT_CLEAR)
    inner_h = total_h - 2 * (wall + FOOT_CLEAR)
    floor = 3.0
    # Hollow the cup: open pocket from the top down to a floor above the foot.
    pocket = (
        cq.Workplane("XY").workplane(offset=FOOT_H + floor)
        .box(inner_w, inner_h, body_h, centered=(True, True, False))
    )
    body = body.cut(pocket)

    # A single cross divider rib across the short axis, welded to the walls.
    rib = (
        cq.Workplane("XY").workplane(offset=FOOT_H + floor - 0.01)
        .box(inner_w + 2 * wall, wall, body_h * 0.85, centered=(True, True, False))
    )
    body = body.union(rib)

    # Drain / vent holes through the floor (so the pocket is never a sealed void).
    # Placed OFF the central rib line (at +/- inner_h/4 in Y) so they never graze
    # the rib base — a grazing cut leaves a non-manifold sliver. Cut cleanly from
    # below the floor up into the open pocket.
    for sy in (-1, 1):
        vent = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, sy * inner_h * 0.25, FOOT_H - 1.0))
            .circle(3.0)
            .extrude(floor + 2.0)
        )
        body = body.cut(vent)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "plier_rack":
    result = build_plier_rack()
elif target_part == "pen_cup":
    result = build_pen_cup()
else:
    result = build_bit_block()
