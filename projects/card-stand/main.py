"""
Business Card / Note Stand — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A desk stand that holds business cards or note cards upright at a viewing angle,
parametric on the card's width and thickness. The card sits in a slot cut into
a raked block. Three distinct forms dispatched by `target_part`:

  * "card_stand" — a wedge easel with a single card slot raked back so a stack of
                   cards leans at a comfortable reading angle. The slot is an
                   upward-open groove (cut into the top face of the wedge — never
                   a buried cavity).
  * "note_clip"  — a low, heavy base with a thin near-vertical slot that grips a
                   single note / memo / photo upright at a slight lean.
  * "multi_slot" — a terraced block with several parallel card slots so a set of
                   cards fans out for display (a stepped display rack).

Reference dimensions (why the defaults are what they are):
  - A standard business card is 3.5 x 2 in = 88.9 x 50.8 mm.
  - Printed card stock runs ~0.3-0.5 mm thick; a small STACK needs a wider slot,
    so `slot_w` defaults to 4 mm (a dozen-ish cards) with room to adjust.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `card_w`).
  - Read them via PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
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


# ── Parameters ───────────────────────────────────────────────────────────────
card_w     = float(PARAM(lambda: card_w,     88.9))   # card width along the slot (mm) — business card = 88.9
slot_w     = float(PARAM(lambda: slot_w,      4.0))   # slot width — holds a small stack of cards (mm)
lean_deg   = float(PARAM(lambda: lean_deg,   18.0))   # backward lean of the card from vertical (deg)
depth      = float(PARAM(lambda: depth,      45.0))   # base depth front-to-back (mm)
height     = float(PARAM(lambda: height,     40.0))   # stand height at the back (mm)
wall       = float(PARAM(lambda: wall,        4.0))   # min wall / floor thickness (mm)
slot_depth = float(PARAM(lambda: slot_depth, 18.0))   # how deep the card sits into the slot (mm)
slots      = int(  PARAM(lambda: slots,        3))    # slot count (multi_slot)
step       = float(PARAM(lambda: step,       14.0))   # terrace step spacing (multi_slot, mm)

target_part = str(PARAM(lambda: target_part, "card_stand"))  # card_stand | note_clip | multi_slot

# ── Clamps / derived values ──────────────────────────────────────────────────
card_w     = max(30.0, min(card_w, 210.0))
slot_w     = max(1.0, min(slot_w, 20.0))
lean_deg   = max(0.0, min(lean_deg, 45.0))
depth      = max(25.0, min(depth, 160.0))
height     = max(18.0, min(height, 120.0))
wall       = max(2.5, min(wall, 12.0))
slot_depth = max(6.0, min(slot_depth, height - wall))
slots      = max(1, min(slots, 8))
step       = max(8.0, min(step, 40.0))

body_w = card_w + 2.0 * wall          # full stand width (card + side walls)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _box(w, d, h, x=0.0, y=0.0, z=0.0):
    """Box centred in X/Y (Y = the card-width axis), base at z."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z))
        .box(w, d, h, centered=(True, True, False))
    )


def _slot_cutter(length, wid, deep, x, z, lean):
    """A rectangular slot cutter: a box of cross-section (wid x deep) running the
    full card width (`length` along Y), raked back by `lean` degrees about Y, its
    mouth reaching above the top face. Cut into a solid it leaves an upward-open
    groove with rounded-free straight walls (rect slot)."""
    over = deep + 12.0  # extend well above the surface so the mouth is fully open
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, 0.0, z))
        .transformed(rotate=cq.Vector(0, lean, 0))
        .box(wid, length + 0.02, over, centered=(True, True, False))
    )


def _fillet_vertical(body, r):
    try:
        return body.edges("|Z").fillet(r)
    except Exception:
        return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_card_stand():
    """A wedge easel: a solid block whose front is lower than the back, with a
    single raked slot cut into the top so a stack of cards leans back."""
    # Solid rounded base block (fillet BEFORE cutting the slot).
    block = _box(depth, body_w, height)
    block = _fillet_vertical(block, min(wall * 1.5, depth / 6.0, body_w / 6.0))
    # Chamfer the top front edge into a wedge so cards clear the front lip: cut a
    # long wedge off the front-top (a boolean cut, always watertight).
    wedge = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(depth / 2.0, 0.0, height))
        .transformed(rotate=cq.Vector(0, 35, 0))
        .box(depth * 1.4, body_w + 2.0, height * 1.4, centered=(True, True, False))
    )
    block = block.cut(wedge)
    # Card slot: raked back, positioned toward the back third, cut into the top.
    slot_x = depth * 0.12
    slot = _slot_cutter(body_w, slot_w, slot_depth, slot_x, height - slot_depth, lean_deg)
    body = block.cut(slot)
    return body


def build_note_clip():
    """A low, heavy base with a thin near-vertical slot gripping a single note."""
    base_h = max(wall * 3.0, height * 0.5)
    block = _box(depth * 0.8, body_w, base_h)
    block = _fillet_vertical(block, min(wall * 1.5, body_w / 6.0))
    # Round the top outer edges for a friendly look (before the slot cut).
    try:
        block = block.edges("|Y").fillet(min(wall, base_h * 0.4))
    except Exception:
        pass
    # A thin slot (card-thickness) with a gentle lean, cut into the top.
    slot = _slot_cutter(body_w, slot_w, base_h * 0.7, 0.0,
                        base_h - base_h * 0.7, max(6.0, lean_deg * 0.5))
    body = block.cut(slot)
    return body


def build_multi_slot():
    """A terraced block with several parallel raked slots so cards fan out. Each
    terrace is one step taller toward the back; every slot is an upward-open cut,
    so the whole thing stays a single watertight solid."""
    n = slots
    total_depth = max(depth, n * step + wall * 2.0)
    # Build a staircase of solid boxes (each overlaps the previous → one solid).
    body = None
    for i in range(n):
        seg_h = wall + (i + 1) * (step * 0.5)
        seg_d = total_depth - i * step
        x0 = -total_depth / 2.0 + seg_d / 2.0
        seg = _box(seg_d, body_w, seg_h, x=x0)
        body = seg if body is None else body.union(seg)
    body = _fillet_vertical(body, min(wall, body_w / 8.0))
    # One raked slot per terrace tread, cut into that tread's top.
    for i in range(n):
        seg_h = wall + (i + 1) * (step * 0.5)
        # slot sits just behind each step's front face
        x_front = -total_depth / 2.0 + i * step
        slot_x = x_front + step * 0.5
        s_depth = min(slot_depth, seg_h - wall)
        slot = _slot_cutter(body_w, slot_w, s_depth, slot_x, seg_h - s_depth, lean_deg)
        body = body.cut(slot)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "note_clip":
    result = build_note_clip()
elif target_part == "multi_slot":
    result = build_multi_slot()
else:
    result = build_card_stand()
