"""
Stackable Tray / Sorting Bin — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An open-front stacking bin (the classic parts / hardware bin). Sized by interior
dimensions. The front wall is cut down at an angle so contents are visible and
easy to scoop; a stacking lip on the top rim nests the bin below's rim so bins
stack squarely; an optional recessed label slot sits on the front face.

Parts (via target_part):
  - "bin"              : the plain open-front stacking bin.
  - "bin_with_divider" : the same bin with 1-2 internal dividers.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `wall`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters (interior-driven) ─────────────────────────────────────────────
inner_w    = float(PARAM(lambda: inner_w,    90.0))   # interior X (mm)
inner_d    = float(PARAM(lambda: inner_d,   120.0))   # interior Y (mm) front-to-back
inner_h    = float(PARAM(lambda: inner_h,    70.0))   # interior Z (mm)
wall       = float(PARAM(lambda: wall,        2.0))   # wall / floor thickness
front_cut  = float(PARAM(lambda: front_cut,  35.0))   # height of the open front (mm)
lip        = float(PARAM(lambda: lip,         4.0))   # stacking-lip height (mm)
lip_clear  = float(PARAM(lambda: lip_clear,   0.4))   # lip-to-rim clearance (print fit)
label      = bool( PARAM(lambda: label,      True))   # recessed label slot on front
dividers   = int(  PARAM(lambda: dividers,      1))   # internal dividers (0..2)

target_part = str(PARAM(lambda: target_part, "bin"))  # bin | bin_with_divider

# ── Derived envelope + clamps ────────────────────────────────────────────────
outer_w = inner_w + 2.0 * wall
outer_d = inner_d + 2.0 * wall
outer_h = inner_h + wall               # floor thickness = wall
wall = max(1.0, min(wall, inner_w / 3.0, inner_d / 3.0))
front_cut = max(0.0, min(front_cut, inner_h - 2.0))   # keep some back-front wall
lip = max(0.0, min(lip, wall * 3.0))
dividers = max(0, min(dividers, 2))

# The front face is at -Y. The open front removes the front wall down to a sill of
# height `wall` (floor) + a short front curb; the top of the opening is front_cut.
FRONT_Y = -outer_d / 2.0


# ── Helpers ──────────────────────────────────────────────────────────────────
def _box(w, d, h, x=0.0, y=0.0, z=0.0):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z))
        .box(w, d, h, centered=(True, True, False))
    )


def _shell():
    """Solid outer minus interior cavity = a five-wall shell open at the top."""
    body = _box(outer_w, outer_d, outer_h)
    cavity = _box(inner_w, inner_d, inner_h + 1.0, 0.0, 0.0, wall)
    return body.cut(cavity)


def _open_front(body):
    """Cut the front wall down to an angled opening.

    The opening starts at the top of the front wall and slopes down toward the
    front, leaving the front wall standing only up to `front_cut` at the back edge
    of the wall and lower at the very front — the classic scoop opening.
    """
    # A wedge that removes the upper-front portion of the front wall.
    # Build a triangular prism spanning the bin width, cutting the front wall.
    top_z = outer_h
    # Rectangular removal of the front wall above the sill height `front_cut`.
    rect = _box(inner_w, wall * 2.0, (top_z - front_cut) + 1.0,
                0.0, FRONT_Y + wall, front_cut)
    body = body.cut(rect)

    # Angled scoop: slope the opening from front_cut (at back of front wall)
    # down to the sill near the top of the floor at the very front lip.
    pts = [
        (FRONT_Y - 1.0, wall),                 # outside-front, at floor top
        (FRONT_Y + wall + 0.01, front_cut),    # inside-front wall, at cut height
        (FRONT_Y - 1.0, front_cut + 1.0),      # outside-front, above cut
    ]
    wedge = (
        cq.Workplane("YZ")
        .polyline(pts).close()
        .extrude(inner_w / 2.0, both=True)
    )
    return body.cut(wedge)


def _stacking_lip(body):
    """Add a raised lip on the top rim and a matching recess in the underside so a
    bin sits down into the bin below. Lip outer = interior minus clearance."""
    if lip <= 0.05:
        return body
    lip_w = inner_w - 2.0 * lip_clear
    lip_d = inner_d - 2.0 * lip_clear
    lip_wall = max(1.2, wall - 0.4)
    # Raised ring on the rim (only around back/left/right — leave the open front).
    ring_outer = _box(lip_w, lip_d, lip, 0.0, 0.0, outer_h)
    ring_inner = _box(lip_w - 2.0 * lip_wall, lip_d - 2.0 * lip_wall, lip + 1.0,
                      0.0, 0.0, outer_h - 0.5)
    ring = ring_outer.cut(ring_inner)
    # Trim the ring's front so it doesn't block the open front.
    ring = ring.cut(_box(lip_w + 2.0, wall * 2.5, lip + 2.0, 0.0, FRONT_Y + wall, outer_h - 0.5))
    body = body.union(ring)

    # Underside recess so the lip of the bin below can enter.
    recess = _box(lip_w + 2.0 * lip_clear, lip_d + 2.0 * lip_clear, lip + lip_clear,
                  0.0, 0.0, -0.01)
    recess_keep = _box(lip_w + 2.0 * lip_clear - 2.0 * (lip_wall + lip_clear),
                       lip_d + 2.0 * lip_clear - 2.0 * (lip_wall + lip_clear),
                       lip + lip_clear + 1.0, 0.0, 0.0, -0.01)
    body = body.cut(recess.cut(recess_keep))
    return body


def _label_slot(body):
    """Recess a shallow label pocket into the standing part of the front wall."""
    if not label or front_cut < 8.0:
        return body
    slot_h = min(front_cut - 3.0, 14.0)
    slot_w = min(inner_w - 6.0, inner_w * 0.8)
    depth = min(wall - 0.8, 1.0)
    if depth <= 0.2 or slot_h <= 2.0:
        return body
    z0 = 2.0
    pocket = _box(slot_w, depth + 0.5, slot_h, 0.0, FRONT_Y - depth / 2.0 + 0.25, z0)
    return body.cut(pocket)


def _add_dividers(body):
    if dividers <= 0:
        return body
    step = inner_w / (dividers + 1)
    for i in range(1, dividers + 1):
        x = -inner_w / 2.0 + step * i
        body = body.union(_box(wall, inner_d, inner_h - front_cut * 0.0, x, 0.0, wall))
    return body


def build_bin(with_dividers):
    body = _shell()
    body = _open_front(body)
    body = _stacking_lip(body)
    body = _label_slot(body)
    if with_dividers:
        body = _add_dividers(body)
    # Soften the two top-back corners for comfort; non-fatal if it fails.
    try:
        body = body.edges("|Z").edges(">Y").fillet(min(wall * 0.4, 1.0))
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bin_with_divider":
    result = build_bin(with_dividers=True)
else:
    result = build_bin(with_dividers=False)
