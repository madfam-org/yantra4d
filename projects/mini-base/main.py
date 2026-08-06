"""
Miniature Base — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Wargame / RPG miniature bases in the standard tabletop footprints (25 / 32 / 40 /
50 / 60 mm round, 25 / 50 mm square). Each base has a beveled (chamfered) top
edge, an optional raised rim lip, an optional lightly-textured top, and an
optional 6x2 mm magnet pocket recessed into the underside so the mini snaps to a
steel movement tray or storage sheet.

Three parts (dispatched via `target_part`):
  * "round_base"    — a single round base at the chosen size.
  * "square_base"   — a single square base at the chosen size.
  * "movement_tray" — a rimmed tray with a grid of recessed base-shaped seats
                      that hold N minis together as a unit.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `base_size`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.

Watertight strategy: every base is a primitive disc/box; the top edge is
chamfered on a CLEAN blank BEFORE any pockets are cut; the magnet pocket is an
OPEN blind pocket (never pierces through); the movement-tray seats are open
recesses. No sphere-tangent unions.
"""

import math

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Standard footprints (mm). Round diameters + square edge lengths. ──────────
_ROUND = {"25mm": 25.0, "32mm": 32.0, "40mm": 40.0, "50mm": 50.0, "60mm": 60.0}
_SQUARE = {"25sq": 25.0, "50sq": 50.0}


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "round_base"))   # round_base|square_base|movement_tray
base_size   = str(PARAM(lambda: base_size,   "32mm"))         # footprint key (see _ROUND/_SQUARE)

thickness   = float(PARAM(lambda: thickness,   3.0))   # base plate thickness (mm)
bevel       = float(PARAM(lambda: bevel,       1.0))   # top-edge chamfer (mm)
lip         = bool( PARAM(lambda: lip,        False))  # raised rim lip on top
lip_h       = float(PARAM(lambda: lip_h,       1.0))   # lip height (mm)
textured    = bool( PARAM(lambda: textured,   False))  # light recessed texture on top
magnet      = bool( PARAM(lambda: magnet,     False))  # 6x2mm magnet pocket underneath
magnet_d    = float(PARAM(lambda: magnet_d,    6.0))   # magnet diameter (mm)
magnet_h    = float(PARAM(lambda: magnet_h,    2.0))   # magnet pocket depth (mm)

tray_cols   = int(  PARAM(lambda: tray_cols,     2))   # movement tray: seats across X
tray_rows   = int(  PARAM(lambda: tray_rows,     2))   # movement tray: seats across Y
tray_gap    = float(PARAM(lambda: tray_gap,    2.0))   # wall between seats (mm)
tray_wall   = float(PARAM(lambda: tray_wall,   2.0))   # outer rim wall thickness (mm)
tray_seat_h = float(PARAM(lambda: tray_seat_h, 2.0))   # depth minis sit into the tray (mm)

# ── Clamp to sane ranges so extreme UI values still build watertight. ────────
thickness   = max(1.5, min(thickness, 8.0))
bevel       = max(0.0, min(bevel, thickness * 0.6, 4.0))
lip_h       = max(0.4, min(lip_h, 4.0))
magnet_d    = max(2.0, min(magnet_d, 12.0))
magnet_h    = max(0.8, min(magnet_h, thickness - 0.8))
tray_cols   = max(1, min(tray_cols, 6))
tray_rows   = max(1, min(tray_rows, 6))
tray_gap    = max(0.6, min(tray_gap, 8.0))
tray_wall   = max(1.0, min(tray_wall, 6.0))
tray_seat_h = max(0.8, min(tray_seat_h, thickness - 0.6))


def _footprint():
    """Return (is_round, span) where span is the round diameter or square edge."""
    if base_size in _ROUND:
        return True, _ROUND[base_size]
    if base_size in _SQUARE:
        return False, _SQUARE[base_size]
    # Unknown key: treat a trailing 'sq' as square, else round-32 default.
    if base_size.endswith("sq"):
        return False, 32.0
    return True, 32.0


# ── Blank builders (clean solids, top edge chamfered BEFORE cutting) ─────────
def _round_blank(dia, h, chamfer):
    solid = cq.Workplane("XY").circle(dia / 2.0).extrude(h)
    if chamfer > 0.05:
        try:
            solid = solid.edges(">Z").chamfer(chamfer)
        except Exception:
            pass
    return solid


def _square_blank(edge, h, chamfer):
    solid = cq.Workplane("XY").box(edge, edge, h, centered=(True, True, False))
    if chamfer > 0.05:
        try:
            solid = solid.edges(">Z").chamfer(chamfer)
        except Exception:
            pass
    return solid


def _add_lip(solid, is_round, span, h):
    """Union a thin raised rim on top of the base (open ring)."""
    band = min(2.0, span * 0.12)
    if is_round:
        outer = cq.Workplane("XY").workplane(offset=h).circle(span / 2.0).extrude(lip_h)
        inner = (
            cq.Workplane("XY").workplane(offset=h)
            .circle(max(0.5, span / 2.0 - band)).extrude(lip_h + 0.2)
        )
    else:
        outer = (
            cq.Workplane("XY").workplane(offset=h)
            .box(span, span, lip_h, centered=(True, True, False))
        )
        inner = (
            cq.Workplane("XY").workplane(offset=h)
            .box(span - 2.0 * band, span - 2.0 * band, lip_h + 0.2, centered=(True, True, False))
        )
    ring = outer.cut(inner)
    return solid.union(ring)


def _add_texture(solid, is_round, span, h):
    """Cut a shallow ring of small dimples into the top for a rough tabletop look."""
    depth = 0.4
    dot_r = max(0.6, span * 0.03)
    ring_r = span * 0.30
    n = max(6, int(span / 6.0))
    cutters = None
    for i in range(n):
        a = 2.0 * math.pi * i / n
        x = ring_r * math.cos(a)
        y = ring_r * math.sin(a)
        dot = (
            cq.Workplane("XY").workplane(offset=h - depth)
            .center(x, y).circle(dot_r).extrude(depth + 0.2)
        )
        cutters = dot if cutters is None else cutters.union(dot)
    if cutters is not None:
        try:
            solid = solid.cut(cutters)
        except Exception:
            pass
    return solid


def _add_magnet(solid, h):
    """Cut a blind magnet pocket into the UNDERSIDE (does not pierce top)."""
    pocket = (
        cq.Workplane("XY")
        .circle(magnet_d / 2.0)
        .extrude(magnet_h)
    )
    return solid.cut(pocket)


def _finish_base(is_round, span):
    """Build one base: blank → chamfer → (lip) → (texture) → (magnet)."""
    h = thickness
    blank = _round_blank(span, h, bevel) if is_round else _square_blank(span, h, bevel)
    if lip:
        blank = _add_lip(blank, is_round, span, h)
    if textured:
        blank = _add_texture(blank, is_round, span, h)
    if magnet:
        blank = _add_magnet(blank, h)
    return blank


# ── Part builders ────────────────────────────────────────────────────────────
def build_round_base():
    _, span = _footprint()
    # If the chosen key is square, still honor "round" mode with the same span.
    return _finish_base(True, span)


def build_square_base():
    _, span = _footprint()
    return _finish_base(False, span)


def build_movement_tray():
    """A rimmed tray with a grid of recessed seats for the chosen base footprint.
    Base plate (solid) → cut open seat recesses → the outer rim remains raised."""
    is_round, span = _footprint()
    seat = span + 0.4                      # small clearance so minis drop in
    pitch = seat + tray_gap
    plate_w = tray_cols * seat + (tray_cols - 1) * tray_gap + 2.0 * tray_wall
    plate_d = tray_rows * seat + (tray_rows - 1) * tray_gap + 2.0 * tray_wall
    plate_h = thickness + tray_seat_h      # floor thickness + seat depth

    body = cq.Workplane("XY").box(plate_w, plate_d, plate_h, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(tray_wall, 3.0))
    except Exception:
        pass

    # Cut the seat recesses from the top, leaving a floor of `thickness`.
    x0 = -((tray_cols - 1) * pitch) / 2.0
    y0 = -((tray_rows - 1) * pitch) / 2.0
    cutters = None
    for r in range(tray_rows):
        for c in range(tray_cols):
            cx = x0 + c * pitch
            cy = y0 + r * pitch
            if is_round:
                seat_cut = (
                    cq.Workplane("XY").workplane(offset=thickness)
                    .center(cx, cy).circle(seat / 2.0).extrude(tray_seat_h + 1.0)
                )
            else:
                seat_cut = (
                    cq.Workplane("XY").workplane(offset=thickness)
                    .center(cx, cy).box(seat, seat, tray_seat_h + 1.0, centered=(True, True, False))
                )
            cutters = seat_cut if cutters is None else cutters.union(seat_cut)
    if cutters is not None:
        body = body.cut(cutters)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "square_base":
    result = build_square_base()
elif target_part == "movement_tray":
    result = build_movement_tray()
else:
    result = build_round_base()
