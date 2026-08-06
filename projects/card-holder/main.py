"""
Card / Book Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Holders that present cards and pages hands-free for people with limited dexterity
or grip. A card rack stands a fanned hand of playing cards upright in an angled
groove so they can be seen and played one-handed; a book stand props a book or
tablet at a reading angle; a page holder pins a single card or page open on a
weighted base. Sized to the standard poker playing card (63 x 88 mm) and common
books/tablets.

  * "card_rack"   — a base with angled grooves that stand a fan of cards
                    (target_part == "card_rack").
  * "book_stand"  — an inclined easel with a front ledge that holds a book/tablet
                    open at an angle (target_part == "book_stand").
  * "page_holder" — a low weighted base with an upright slot that pins a single
                    card/page open (target_part == "page_holder").

Watertight strategy: each holder is one solid. Card/page grooves are slots cut
from the top face straight down (open to the top → vented, never trapped). The
book stand is a single extruded right-trapezoid easel with a ledge unioned on
(overlapping). No revolves of cut profiles; fillets applied to clean blanks
before feature cuts, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
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
target_part = str(PARAM(lambda: target_part, "card_rack"))
# card_rack | book_stand | page_holder

base_len = float(PARAM(lambda: base_len, 150.0))   # holder length (mm)
base_depth = float(PARAM(lambda: base_depth, 55.0))  # front-to-back depth (mm)
base_h = float(PARAM(lambda: base_h, 16.0))        # base block height (mm)
card_t = float(PARAM(lambda: card_t, 1.2))         # card/page thickness the groove holds
groove_gap = float(PARAM(lambda: groove_gap, 2.4))  # groove width (a few cards)
groove_ang = float(PARAM(lambda: groove_ang, 65.0))  # card lean-back angle (deg from horizontal)
n_grooves = int(PARAM(lambda: n_grooves, 3))       # number of card rows (card_rack)
lip_h = float(PARAM(lambda: lip_h, 12.0))          # front ledge height (book_stand)
stand_ang = float(PARAM(lambda: stand_ang, 60.0))  # easel back angle (book_stand)

# ── Clamps ───────────────────────────────────────────────────────────────────
base_len = max(60.0, min(base_len, 300.0))
base_depth = max(30.0, min(base_depth, 120.0))
base_h = max(8.0, min(base_h, 40.0))
card_t = max(0.4, min(card_t, 6.0))
groove_gap = max(1.5, min(groove_gap, 12.0))
groove_ang = max(45.0, min(groove_ang, 85.0))
n_grooves = max(1, min(n_grooves, 6))
lip_h = max(5.0, min(lip_h, 40.0))
stand_ang = max(35.0, min(stand_ang, 80.0))


# ── Part builders ────────────────────────────────────────────────────────────
def _rounded_base(length, depth, height, rad):
    """A rounded-edge base slab, filleted on a clean blank before any cut."""
    blk = cq.Workplane("XY").box(length, depth, height, centered=(True, True, False))
    try:
        blk = blk.edges("|Z").fillet(min(rad, depth / 2.0 - 1.5, length / 2.0 - 1.5))
    except Exception:
        pass
    return blk


def build_card_rack():
    """A base with `n_grooves` parallel angled slots. Each slot is cut from the
    top face straight down but with the cutter tilted, so a card sits leaning back
    at `groove_ang`. Cards fan along the slot length. Slots vent to the top."""
    body = _rounded_base(base_len, base_depth, base_h, 5.0)

    slot_len = base_len - 16.0
    # Spread grooves across the depth, all leaning the same way.
    if n_grooves == 1:
        offsets = [0.0]
    else:
        span = base_depth - 20.0
        step = span / (n_grooves - 1)
        offsets = [-span / 2.0 + i * step for i in range(n_grooves)]

    lean = math.tan(math.radians(90.0 - groove_ang))  # horizontal run per unit up
    for yo in offsets:
        # A thin box cutter, tilted about X so the slot leans back, bored from
        # above the top down through into the base. Extra height so it vents up.
        cutter = (
            cq.Workplane("XY")
            .transformed(
                offset=cq.Vector(0, yo, base_h),
                rotate=cq.Vector(math.degrees(math.atan(lean)), 0, 0),
            )
            .box(slot_len, groove_gap, base_h * 1.4, centered=(True, True, False))
        )
        # Push the cutter down so it cuts a groove of depth ~0.7*base_h.
        cutter = cutter.translate((0, 0, -base_h * 0.72))
        body = body.cut(cutter)
    return body


def build_book_stand():
    """An inclined easel: a right-trapezoid prism (thick at the back, tapering to
    a thin front) with a front ledge lip unioned on so a book/tablet leans on the
    slope and rests on the lip. One manifold; the ledge overlaps the base."""
    # Easel profile in YZ (extruded along X). Back is tall, front is a thin edge.
    back_h = base_depth * math.tan(math.radians(stand_ang))
    back_h = max(back_h, base_h + 10.0)
    front_y = -base_depth / 2.0
    back_y = base_depth / 2.0
    pts = [
        (front_y, 0.0),
        (back_y, 0.0),
        (back_y, base_h),
        (front_y, base_h + back_h),   # sloped reading face rises to the back
    ]
    easel = (
        cq.Workplane("YZ")
        .polyline(pts)
        .close()
        .extrude(base_len / 2.0, both=True)
    )
    try:
        easel = easel.edges("|X").fillet(2.0)
    except Exception:
        pass

    # Front ledge: a bar along the front bottom edge, overlapping into the easel.
    ledge = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, front_y + 4.0, 0))
        .box(base_len - 8.0, 10.0, base_h + lip_h, centered=(True, True, False))
    )
    try:
        ledge = ledge.edges("|Y").fillet(1.5)
    except Exception:
        pass
    body = easel.union(ledge)
    return body


def build_page_holder():
    """A low weighted base with a single upright slot that pins a card or page.
    The slot is cut from the top down (vented). Two short posts flank the slot
    (part of the same solid) to steady a taller page."""
    depth = min(base_depth, 45.0)
    body = _rounded_base(base_len * 0.6, depth, base_h, 4.0)

    # A short upright wall along the back where the slot lives, unioned on.
    wall_h = base_h + max(lip_h, 14.0)
    wall = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, depth / 2.0 - 6.0, 0))
        .box(base_len * 0.6 - 6.0, 8.0, wall_h, centered=(True, True, False))
    )
    try:
        wall = wall.edges("|Y").fillet(1.5)
    except Exception:
        pass
    body = body.union(wall)

    # Vertical slot down the wall (and a little into the base) that grips a page.
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, depth / 2.0 - 6.0, base_h * 0.4))
        .box(base_len * 0.6 - 20.0, groove_gap, wall_h, centered=(True, True, False))
    )
    body = body.cut(slot)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "book_stand":
    result = build_book_stand()
elif target_part == "page_holder":
    result = build_page_holder()
else:  # "card_rack"
    result = build_card_rack()
