import cadquery as cq
import math


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part = PARAM(lambda: target_part, "cup_holder")
tube_dia = float(PARAM(lambda: tube_dia, 25.0))
cup_dia = float(PARAM(lambda: cup_dia, 74.0))
clamp_wall = float(PARAM(lambda: clamp_wall, 4.0))
clearance = float(PARAM(lambda: clearance, 0.4))
cup_wall = float(PARAM(lambda: cup_wall, 3.0))
cup_h = float(PARAM(lambda: cup_h, 55.0))

# ─── Real-world reference dimensions (cited in manifest CDG standards) ─────────
# Wheelchair / walker / rollator frame tubing is commonly 3/4"–1" (19.05–25.4 mm)
#   round tube. A C-shaped snap clamp on that tube is the shared interface with the
#   mobility-accessory cartridge. Standard drink cups are ~74 mm across the base.
CLAMP_OPENING_FRAC = 0.62   # mouth width as a fraction of tube diameter (snap fit)


def _fillet_safe(wp, sel, r):
    try:
        return wp.edges(sel).fillet(r)
    except Exception:
        return wp


def _c_clamp(bore_d, wall, height):
    """A C-shaped snap clamp: a ring (bore_d + wall) with a mouth cut on the +X
    side so it clips onto a tube. Returns the clamp solid centred on the origin,
    its bore axis along Z. Mouth opens to a face → no trapped void."""
    r_in = bore_d / 2.0
    r_out = r_in + wall
    ring = (
        cq.Workplane("XY")
        .circle(r_out)
        .circle(r_in)
        .extrude(height)
    )
    # Mouth: a rectangular gap on +X so the ring can spring open over the tube.
    mouth = CLAMP_OPENING_FRAC * bore_d
    gap = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(r_out, 0, -1.0))
        .box(r_out * 2.0, mouth, height + 2.0, centered=(True, True, False))
    )
    ring = ring.cut(gap)
    return ring


def _cup_basket(inner_d, wall, height, floor_th):
    """An open-top cup basket: outer cylinder, bore open to the top, solid floor.
    Watertight (pocket opens to top only)."""
    outer_r = inner_d / 2.0 + wall
    basket = cq.Workplane("XY").circle(outer_r).extrude(height)
    basket = _fillet_safe(basket, "|Z", 2.0)
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor_th))
        .cylinder(height, inner_d / 2.0, centered=(True, True, False))
    )
    basket = basket.cut(bore)
    # Drainage / weight-saving windows in the wall (open through the wall → not a void).
    for i in range(3):
        a = math.radians(120.0 * i + 60.0)
        win = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(math.cos(a) * outer_r, math.sin(a) * outer_r,
                                          floor_th + height * 0.30))
            .box(wall * 4.0, inner_d * 0.34, height * 0.42, centered=(True, True, False))
            .rotate((math.cos(a) * outer_r, math.sin(a) * outer_r, 0), (0, 0, 1),
                    math.degrees(a))
        )
        basket = basket.cut(win)
    return basket


def _assemble(clamp_bore, clamp_h, basket_inner, basket_h, floor_th):
    """Join a C-clamp (on +X tube) to a cup basket (on -X) via a solid neck so the
    cup hangs beside the tube. Deep overlaps keep it one watertight body."""
    clamp = _c_clamp(clamp_bore, clamp_wall, clamp_h)
    clamp_r_out = clamp_bore / 2.0 + clamp_wall

    basket_r_out = basket_inner / 2.0 + cup_wall
    # Place basket to the -X side, clear of the clamp.
    gap_between = 6.0
    basket_x = -(clamp_r_out + gap_between + basket_r_out)
    basket = _cup_basket(basket_inner, cup_wall, basket_h, floor_th)
    basket = basket.translate((basket_x, 0, 0))

    # Solid connecting neck spanning clamp to basket, embedded into both.
    neck_len = abs(basket_x) + clamp_r_out + basket_r_out
    neck_h = min(clamp_h, basket_h * 0.5) + 4.0
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector((basket_x) / 2.0, 0, 0))
        .box(neck_len, clamp_bore * 0.75, neck_h, centered=(True, True, False))
    )
    body = clamp.union(neck).union(basket)
    # NOTE: no trailing fillet — filleting this feature-laden assembly (clamp mouth
    # + basket bore + wall windows + neck) produces degenerate faces (non-watertight).
    # The basket was already filleted where safe before its features were cut.
    return body


# ─── Mode 1: cup holder ───────────────────────────────────────────────────────
def build_cup_holder():
    """C-clamp on the mobility tube carrying an open cup basket sized to a standard
    drink cup (~74 mm)."""
    bore = tube_dia + 2.0 * clearance
    clamp_h = max(28.0, tube_dia + 6.0)
    basket_inner = cup_dia + 2.0 * clearance
    return _assemble(bore, clamp_h, basket_inner, cup_h, floor_th=cup_wall)


# ─── Mode 2: bottle clamp (deeper, narrower cradle) ───────────────────────────
def build_bottle_clamp():
    """C-clamp carrying a deeper, narrower basket for a water bottle."""
    bore = tube_dia + 2.0 * clearance
    clamp_h = max(28.0, tube_dia + 6.0)
    basket_inner = max(66.0, cup_dia - 6.0) + 2.0 * clearance
    return _assemble(bore, clamp_h, basket_inner, cup_h + 25.0, floor_th=cup_wall)


# ─── Mode 3: clamp only (universal bracket) ───────────────────────────────────
def build_clamp_only():
    """Just the C-clamp with a flat mounting pad (two bolt holes) so a user can
    bolt their own tray or accessory to the mobility tube. Bolt holes pass through
    the pad → no trapped void."""
    bore = tube_dia + 2.0 * clearance
    clamp_h = max(30.0, tube_dia + 8.0)
    clamp = _c_clamp(bore, clamp_wall, clamp_h)
    clamp_r_out = bore / 2.0 + clamp_wall

    pad_w = clamp_h
    pad_t = 5.0
    pad_x = -(clamp_r_out + pad_t / 2.0)
    pad = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(pad_x, 0, clamp_h / 2.0))
        .box(pad_t + 4.0, pad_w, clamp_h, centered=(True, True, True))
    )
    body = clamp.union(pad)

    # Two mounting bolt holes through the pad (along X).
    holes = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, clamp_h / 2.0, pad_x - pad_t))
        .pushPoints([(0, -clamp_h * 0.25), (0, clamp_h * 0.25)])
        .circle(2.2)
        .extrude(pad_t + 12.0)
    )
    body = body.cut(holes)
    # NOTE: no trailing fillet on the feature-laden clamp+pad body (see _assemble).
    return body


# ─── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "cup_holder":
    result = build_cup_holder()
elif target_part == "bottle_clamp":
    result = build_bottle_clamp()
elif target_part == "clamp_only":
    result = build_clamp_only()
else:
    result = build_cup_holder()
