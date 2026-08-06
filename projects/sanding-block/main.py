"""
Sanding Block — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A hand sanding block sized to a sheet of abrasive, with paper-clamp slots at each
end that pinch a torn quarter/half sheet so it can't slip. The sanding face is
flat, convex (for hollows) or a soft contour (for mouldings).

Three modes, dispatched by `target_part`:
  - flat_block    : a flat-faced block for flat surfaces, with an ergonomic top
                    and end clamp slots.
  - round_block   : a convex (cylindrical) face for sanding inside curves / coves.
  - contour_block : a gentle cove-and-bead contour face for shaped mouldings.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `block_l`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/
    getattr — they are not in the sandbox's allowed builtins.
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
block_l     = float(PARAM(lambda: block_l,   120.0))  # block length (paper wrap direction)
block_w     = float(PARAM(lambda: block_w,    65.0))   # block width (grip width)
block_h     = float(PARAM(lambda: block_h,    35.0))   # block height
face_r      = float(PARAM(lambda: face_r,     60.0))   # convex face radius (round mode)
contour_d   = float(PARAM(lambda: contour_d,   6.0))   # contour depth (contour mode)
clamp_slot  = float(PARAM(lambda: clamp_slot,  2.5))   # paper-clamp slot width
grip_scoop  = bool( PARAM(lambda: grip_scoop, True))   # scoop the top for grip

target_part = str(PARAM(lambda: target_part, "flat_block"))


# ── Helpers ──────────────────────────────────────────────────────────────────
def base_block(h):
    """Block centred in X/Y, base at z=0, sides softened for the hand."""
    b = cq.Workplane("XY").box(block_l, block_w, h, centered=(True, True, False))
    try:
        b = b.edges("|X").fillet(min(block_w * 0.12, 6.0))
    except Exception:
        pass
    return b


def add_grip(b, h):
    """Scoop the top face into a shallow cylindrical hand hollow."""
    if not grip_scoop:
        return b
    r = block_w * 0.9
    scoop = (
        cq.Workplane("XZ")
        .circle(r)
        .extrude(block_l * 1.2)
        .translate((0, block_l * 0.6, h + r * 0.72))
    )
    return b.cut(scoop)


def add_clamp_slots(b, h):
    """Two vertical slots near each end that a torn sheet's ends tuck into,
    pinched by a wedge or the paper's own spring."""
    inset = block_l * 0.5 - 6.0
    for sx in (-1, 1):
        slot = cq.Workplane("XY").box(
            clamp_slot, block_w * 0.85, h * 0.7, centered=(True, True, False)
        ).translate((sx * inset, 0, h - h * 0.7))
        # Angle the slot slightly outward so paper self-locks.
        slot = slot.rotate((sx * inset, 0, 0), (0, 1, 0), sx * -8.0)
        b = b.cut(slot)
    return b


# ── Flat block ───────────────────────────────────────────────────────────────
def build_flat_block():
    b = base_block(block_h)
    b = add_grip(b, block_h)
    b = add_clamp_slots(b, block_h)
    return b


# ── Round (convex) block ─────────────────────────────────────────────────────
def build_round_block():
    """Convex cylindrical sanding face on the bottom for sanding hollows/coves."""
    h = block_h
    b = base_block(h)
    # Cut a cylindrical relief from the underside so the face bulges convex: we
    # instead ADD a cylindrical face — build the block then intersect its lower
    # portion with a big cylinder to round the bottom.
    r = max(face_r, block_w * 0.6)
    cyl = (
        cq.Workplane("XZ")
        .circle(r)
        .extrude(block_l + 4.0)
        .translate((0, block_l / 2.0 + 2.0, r - min(r * 0.25, h * 0.6)))
    )
    # Keep only material inside the cylinder for the lower band, union with the
    # upper block so the top stays flat/gripable.
    lower = b.intersect(cyl)
    upper = cq.Workplane("XY").box(
        block_l, block_w, h, centered=(True, True, False)
    ).translate((0, 0, min(r * 0.25, h * 0.6)))
    try:
        upper = upper.edges("|X").fillet(min(block_w * 0.12, 6.0))
    except Exception:
        pass
    b = lower.union(upper)
    b = add_grip(b, h + min(r * 0.25, h * 0.6))
    b = add_clamp_slots(b, h)
    return b


# ── Contour block ────────────────────────────────────────────────────────────
def build_contour_block():
    """A gentle cove (concave) running the length of the face for sanding a
    bead/moulding. The cove is a shallow cylindrical channel down the middle."""
    h = block_h
    b = base_block(h)
    r = block_w * 0.5 + (block_w * block_w) / (8.0 * max(1.0, contour_d))  # chord->radius
    cove = (
        cq.Workplane("XZ")
        .circle(r)
        .extrude(block_l + 4.0)
        .translate((0, block_l / 2.0 + 2.0, -r + contour_d))
    )
    b = b.cut(cove)
    b = add_grip(b, h)
    b = add_clamp_slots(b, h)
    return b


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "round_block":
    result = build_round_block()
elif target_part == "contour_block":
    result = build_contour_block()
else:
    result = build_flat_block()
