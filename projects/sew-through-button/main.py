"""Sew-Through Button — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The flat 2- or 4-hole button that closes shirts, blouses, trousers and coats — the
rigid hard good the Fashion Cabinet `sew-through-button` notion places and bridges to
here for its geometry. FC owns the fashion semantics (ligne sizing, placket spacing,
buttonhole math); this cartridge owns the solid. Sized in ligne, the button trade's
unit: 1 L = 0.635 mm, so `diameter_mm = button_ligne * 0.635` — the same ligne that
lays out an FC placket makes the matching button here.

Modes (dispatched via `target_part`):
  * "button" — one button.
  * "card"   — a laid-out batch of `card_count` buttons on one print bed, the way
               buttons ship on a card.

Geometry: a disc cylinder; the concave face (the thread dish that keeps the stitch
below the button's top plane) is cut by a shallow OVERSIZED CONE descending from
above — never a sphere, which leaves a pole singularity. The rim gets a small
try/except fillet. Sew holes are one `pushPoints(...).circle(...).cutThruAll()` op:
2 holes on a line, or 4 on a square, at `hole_spacing`. Card mode translates copies
into a row/grid with a computed gap and unions them (<= 12 unions).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `button_ligne`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
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


# ── Parameters ───────────────────────────────────────────────────────────────
button_ligne = int(  PARAM(lambda: button_ligne, 24))    # button size in ligne (1 L = 0.635 mm)
thickness    = float(PARAM(lambda: thickness,    3.0))   # button body thickness (mm)
hole_count   = int(  PARAM(lambda: hole_count,   4))     # sew holes: 2 or 4
hole_dia     = float(PARAM(lambda: hole_dia,     1.5))   # sew hole diameter (mm)
hole_spacing = float(PARAM(lambda: hole_spacing, 4.0))   # centre-to-centre hole spacing (mm)
dish_depth   = float(PARAM(lambda: dish_depth,   0.8))   # concave thread dish depth (mm)
card_count   = int(  PARAM(lambda: card_count,   6))     # buttons laid out in card mode

target_part = str(PARAM(lambda: target_part, "button"))  # button|card

# ── Safe clamps ──────────────────────────────────────────────────────────────
button_ligne = max(12, min(button_ligne, 60))
thickness    = max(1.0, min(thickness, 6.0))
hole_count   = 2 if hole_count <= 3 else 4
hole_dia     = max(1.0, min(hole_dia, 3.0))
dish_depth   = max(0.0, min(dish_depth, 2.0))
card_count   = max(2, min(card_count, 12))

DIA = button_ligne * 0.635          # ligne → mm, the button trade's convention
R = DIA / 2.0

# Dish radius: the concave face, kept inside a solid rim wall.
rim_wall = max(0.8, R * 0.14)
dish_r = max(R * 0.35, R - rim_wall)

# The dish never eats more than ~45% of the body, so the thinnest section stays printable.
dish_depth = min(dish_depth, thickness * 0.45)

# Cross-parameter clamps: the hole pattern must stay WELL INSIDE the dish AND the holes
# must never touch one another. A hole centre sits `_reach * hole_spacing` from the
# button centre — hole_spacing/2 for a 2-hole line, hole_spacing/sqrt(2) for a 4-hole
# square. Solve size and spacing together so no parameter combination can degenerate.
_reach = 0.5 if hole_count == 2 else (1.0 / math.sqrt(2.0))
_edge_gap = 0.4          # solid material left between a hole and the dish wall
_web = 0.5               # minimum web of material between two adjacent holes

hole_spacing = max(2.0, min(hole_spacing, 12.0))

# 1. Shrink the holes if they cannot fit the pattern at this spacing on this button.
#    Bound A: pattern must sit inside the dish.  Bound B: holes must not merge.
_by_dish = 2.0 * (dish_r - _reach * hole_spacing - _edge_gap)
_by_web = hole_spacing - _web
hole_dia = min(hole_dia, _by_dish, _by_web)

# 2. If that drove the hole below a sewable size, pull the spacing in and retry.
if hole_dia < 0.8:
    hole_dia = 0.8
    _max_spacing = (dish_r - hole_dia / 2.0 - _edge_gap) / _reach
    hole_spacing = max(hole_dia + _web, min(hole_spacing, _max_spacing))
    hole_dia = min(hole_dia, hole_spacing - _web)

# 3. Final floor: a button this small gets one honest minimum hole.
hole_dia = max(0.6, hole_dia)
hole_spacing = max(hole_dia + _web, hole_spacing)


def _hole_points():
    """Hole centres: 2 on a line along X, or 4 on a square, at hole_spacing."""
    h = hole_spacing / 2.0
    if hole_count == 2:
        return [(-h, 0.0), (h, 0.0)]
    return [(-h, -h), (h, -h), (-h, h), (h, h)]


def build_button():
    """One sew-through button: a disc, a shallow concave dish cut from above by an
    oversized cone, a filleted rim, and 2 or 4 sew holes cut clean through."""
    body = cq.Workplane("XY").circle(R).extrude(thickness)

    # Concave face: an oversized cone descending to a point ABOVE the dish floor, so
    # only its shallow flank intersects the body — a dish, never a sphere.
    if dish_depth > 0.02:
        # A truncated cone (frustum) — flat small end, no apex singularity. The flank
        # slope is set so the cut reaches dish_depth at radius dish_r.
        slope = dish_depth / dish_r                  # rise per unit radius of the flank
        small_r = max(0.6, dish_r * 0.10)            # flat bottom, never an apex point
        base_z = thickness - dish_depth + small_r * slope   # flat floor of the dish
        top_r = dish_r * 1.8                         # oversized well past the dish edge
        cone_h = (top_r - small_r) * slope           # frustum height at that slope
        # Guarantee the frustum breaks the top face even for a very shallow dish.
        overshoot = max(0.0, (thickness + 1.0) - (base_z + cone_h))
        top_r += overshoot / slope
        cone_h += overshoot
        cone = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, base_z))
            .circle(small_r)
            .workplane(offset=cone_h)
            .circle(top_r)
            .loft(combine=True)
        )
        body = body.cut(cone)

    # Rim fillet on the outer top edge (small; skip silently if it cannot be applied).
    try:
        body = body.edges(">Z").fillet(min(rim_wall * 0.35, thickness * 0.2))
    except Exception:
        pass

    # Sew holes — ONE cut op through the whole body.
    body = (
        body.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints(_hole_points())
        .circle(hole_dia / 2.0)
        .cutThruAll()
    )
    return body


def build_card():
    """A batch of `card_count` buttons laid out in a row or grid, ready for one print."""
    one = build_button()
    gap = max(1.5, DIA * 0.18)
    pitch = DIA + gap
    cols = card_count if card_count <= 4 else int(math.ceil(math.sqrt(card_count)))
    cols = max(1, min(cols, 4))
    rows = int(math.ceil(card_count / float(cols)))

    x0 = -(cols - 1) * pitch / 2.0
    y0 = -(rows - 1) * pitch / 2.0
    placed = 0
    batch = None
    for r in range(rows):
        for c in range(cols):
            if placed >= card_count:
                break
            solid = one.translate((x0 + c * pitch, y0 + r * pitch, 0))
            batch = solid if batch is None else batch.union(solid)
            placed += 1
    return batch


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "card":
    result = build_card()
else:
    result = build_button()
