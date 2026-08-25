"""
Business Card Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A desk card holder for standard business cards. Sits in the `card-format` family
next to card-holder and deck-box: all three share the ISO 7810 ID-1 / business-card
footprint groove, so a stack cut for one prints and displays in another.

Modes are dispatched via `target_part`:
  * "desk_tray"    — an angled display tray that fans a stack of cards forward.
  * "wall_holder"  — a flat-backed wall pocket with a front lip and cable/screw slots.
  * "stack_box"    — an upright divider box that holds a full brick of cards on edge.

Reference dimensions (mm):
  * Business card (ISO 7810 ID-1 / US): 88.9 × 50.8, ~0.35 mm per card.
  * A US 3.5×2 in card is 88.9 × 50.8; the EU 85×55 card fits the same groove width.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals.
  - Access them via PARAM(lambda: <name>, <default>). Never use globals()/eval.
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


# ── Parameters ───────────────────────────────────────────────────────────────
card_len = float(PARAM(lambda: card_len, 89.0))    # long edge of the card
card_wid = float(PARAM(lambda: card_wid, 51.0))    # short edge of the card
stack_mm = float(PARAM(lambda: stack_mm, 12.0))    # thickness of the card brick
wall = float(PARAM(lambda: wall, 3.0))             # wall / floor thickness
lean_ang = float(PARAM(lambda: lean_ang, 15.0))    # display lean angle (desk_tray)

target_part = str(PARAM(lambda: target_part, "desk_tray"))

# ── Clamp to printable ranges ────────────────────────────────────────────────
card_len = max(60.0, min(card_len, 120.0))
card_wid = max(40.0, min(card_wid, 70.0))
stack_mm = max(3.0, min(stack_mm, 40.0))
wall = max(1.6, min(wall, 6.0))
lean_ang = max(0.0, min(lean_ang, 30.0))

CLR = 0.6   # per-side slip clearance so the printed groove accepts a real stack


def _fillet_safe(wp, selector, radius):
    """Fillet the blank BEFORE cutting features; fall back if OCCT refuses."""
    try:
        return wp.edges(selector).fillet(radius)
    except Exception:
        return wp


# ── Mode 1: angled desk display tray ─────────────────────────────────────────
def build_desk_tray():
    """A shallow tray whose back wall leans back so cards fan forward for display.
    The card pocket is open to the top and front faces — no trapped void."""
    slot_w = stack_mm + 2 * CLR
    inner_l = card_len + 2 * CLR
    body_l = inner_l + 2 * wall
    body_w = slot_w + 2 * wall
    back_h = card_wid * 0.62 + wall           # supports lower half of the card
    front_h = wall + max(6.0, card_wid * 0.14)  # front retaining lip

    # Solid base block, rounded vertical corners on the blank first.
    base = (
        cq.Workplane("XY")
        .box(body_l, body_w, back_h, centered=(True, True, False))
    )
    base = _fillet_safe(base, "|Z", min(4.0, wall + 1.0))

    # Card pocket: open to the top, slot centred across width.
    base = (
        base.faces(">Z").workplane()
        .rect(inner_l, slot_w)
        .cutBlind(-(back_h - wall))
    )

    # Lean the whole block back about the front bottom edge for display.
    if lean_ang > 0.1:
        base = base.rotate((0, -body_w / 2.0, 0), (1, 0, 0), -lean_ang)
        # Re-level: drop the lowest point back onto Z=0 by trimming below the plane.
        bb = base.val().BoundingBox()
        if bb.zmin < 0:
            base = base.translate((0, 0, -bb.zmin))
        # Slice off any material that now dips under Z=0 to give a flat print base.
        cutter = cq.Workplane("XY").box(
            body_l * 4, body_w * 4, back_h * 4,
            centered=(True, True, False),
        ).translate((0, 0, -back_h * 4))
        base = base.cut(cutter)

    # Front retaining lip: a low bar across the front, open pocket kept clear.
    lip = (
        cq.Workplane("XY")
        .box(body_l, wall, front_h, centered=(True, False, False))
        .translate((0, -body_w / 2.0, 0))
    )
    return base.union(lip)


# ── Mode 2: flat-backed wall pocket ──────────────────────────────────────────
def build_wall_holder():
    """A wall-mount pocket: flat back plate with two keyhole screw slots, a card
    pocket open to the top, and a front window so a thumb can lift the stack."""
    slot_w = stack_mm + 2 * CLR
    inner_l = card_len + 2 * CLR
    body_l = inner_l + 2 * wall
    depth = slot_w + 2 * wall
    height = card_wid * 0.55 + wall

    body = (
        cq.Workplane("XY")
        .box(body_l, depth, height, centered=(True, True, False))
    )
    body = _fillet_safe(body, "|Z", min(3.0, wall))

    # Card pocket open to the top.
    body = (
        body.faces(">Z").workplane()
        .rect(inner_l, slot_w)
        .cutBlind(-(height - wall))
    )

    # Front thumb window: a rounded slot cut through the front wall only.
    win_w = inner_l * 0.5
    win_h = height * 0.5
    window = (
        cq.Workplane("XZ")
        .workplane(offset=-depth / 2.0 - 1.0)
        .center(0, wall + win_h / 2.0)
        .slot2D(win_w, win_h, 0)
        .extrude(-(wall + 2.0))
    )
    body = body.cut(window)

    # Two mounting screw holes through the back wall (open both faces of the wall).
    hole_dx = body_l * 0.30
    back = (
        cq.Workplane("XZ")
        .workplane(offset=depth / 2.0)
        .pushPoints([(hole_dx, height * 0.6), (-hole_dx, height * 0.6)])
        .circle(2.2)  # M4 clearance
        .extrude(-(wall + 2.0))
    )
    return body.cut(back)


# ── Mode 3: upright stack divider box ────────────────────────────────────────
def build_stack_box():
    """An upright box that holds a full brick of cards on their long edge, with a
    scalloped front so you can thumb cards out. Pocket open to the top face."""
    inner_w = stack_mm + 2 * CLR          # brick thickness across the box
    inner_l = card_wid + 2 * CLR          # card stands on its long edge
    body_l = inner_l + 2 * wall
    body_w = inner_w + 2 * wall
    height = card_len * 0.55 + wall

    box = (
        cq.Workplane("XY")
        .box(body_l, body_w, height, centered=(True, True, False))
    )
    box = _fillet_safe(box, "|Z", min(4.0, wall + 1.0))

    # Card pocket, open to the top.
    box = (
        box.faces(">Z").workplane()
        .rect(inner_l, inner_w)
        .cutBlind(-(height - wall))
    )

    # Front scallop: a cylinder cut through the front wall gives a finger notch.
    scallop_r = min(inner_l, height) * 0.42
    scallop = (
        cq.Workplane("XZ")
        .workplane(offset=-body_w / 2.0 - 1.0)
        .center(0, height)
        .circle(scallop_r)
        .extrude(-(wall + 2.0))
    )
    return box.cut(scallop)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "desk_tray":
    result = build_desk_tray()
elif target_part == "wall_holder":
    result = build_wall_holder()
elif target_part == "stack_box":
    result = build_stack_box()
else:
    result = build_desk_tray()
