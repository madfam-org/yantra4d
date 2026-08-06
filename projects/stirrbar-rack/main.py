import cadquery as cq
import math


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part = PARAM(lambda: target_part, "slot_rack")
bar_diameter = float(PARAM(lambda: bar_diameter, 8.0))
slot_count = int(PARAM(lambda: slot_count, 5))
max_bar_length = float(PARAM(lambda: max_bar_length, 40.0))
magnet_diameter = float(PARAM(lambda: magnet_diameter, 10.0))

# ─── Real-world reference dimensions (cited in manifest CDG standards) ─────────
# PTFE octagonal magnetic stir bars: standard lengths 12/20/25/38 mm (also 15/30/50);
# body diameter ~8 mm (3-10.5 mm across the range).
STD_BAR_LENGTHS = [12.0, 20.0, 25.0, 38.0, 50.0]   # mm, common PTFE stir-bar set
WALL = 3.0


def _fillet_safe(wp, edges_selector, radius):
    """Fillet the blank BEFORE cutting features; fall back gracefully."""
    try:
        return wp.edges(edges_selector).fillet(radius)
    except Exception:
        return wp


def _polar(radius, angle_deg):
    a = math.radians(angle_deg)
    return radius * math.cos(a), radius * math.sin(a)


def _graded_lengths(n, longest):
    """A rising set of slot lengths from the standard set, scaled to <= longest."""
    n = max(2, n)
    base = [x for x in STD_BAR_LENGTHS if x <= longest] or [longest]
    out = []
    for i in range(n):
        out.append(base[i % len(base)] if i < len(base) else min(longest, base[-1] * (1.0 + 0.15 * (i - len(base) + 1))))
    # Ensure strictly usable, capped at longest.
    return [min(longest, v) for v in out]


# ─── Mode 1: linear length-graded slot rack ───────────────────────────────────
def build_slot_rack():
    """A block of parallel open-top channels, each sized to a standard stir-bar
    length. Channels are troughs OPEN to the top face (no trapped void) with a
    finger scoop cut across the front so bars are easy to lift out."""
    n = max(2, slot_count)
    lengths = _graded_lengths(n, max_bar_length)
    chan_w = bar_diameter + 1.6
    chan_pitch = chan_w + WALL
    depth_max = max(lengths) + 2 * WALL
    width = n * chan_pitch + WALL
    block_h = bar_diameter + 6.0

    block = cq.Workplane("XY").box(width, depth_max, block_h, centered=(True, True, False))
    block = _fillet_safe(block, "|Z", 3.0)

    x0 = -(n - 1) * chan_pitch / 2.0
    chan_depth = block_h * 0.7
    for i in range(n):
        cx = x0 + i * chan_pitch
        L = lengths[i]
        # Trough: a rounded channel open to the top, length matched to the bar.
        trough = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, 0, block_h - chan_depth / 2.0))
            .box(chan_w, L + 1.5, chan_depth)
        )
        block = block.cut(trough)

    # Finger scoop across the front edge (open to the front + top faces).
    scoop = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(depth_max / 2.0, block_h, 0))
        .cylinder(width + 2.0, bar_diameter * 0.8)
    )
    block = block.cut(scoop)
    return block


# ─── Mode 2: radial carousel rack ─────────────────────────────────────────────
def build_carousel_rack():
    """A round rack with radial open-top slots of graded lengths around a solid
    hub; slots are troughs open to the top and outer rim (no trapped void)."""
    n = max(3, slot_count)
    lengths = _graded_lengths(n, max_bar_length)
    chan_w = bar_diameter + 1.6
    hub_r = chan_w + 6.0
    disc_r = hub_r + max(lengths) + WALL
    disc_h = bar_diameter + 6.0
    chan_depth = disc_h * 0.7

    disc = cq.Workplane("XY").circle(disc_r).extrude(disc_h)
    disc = _fillet_safe(disc, "|Z", 2.0)

    for i in range(n):
        ang = i * 360.0 / n
        L = lengths[i]
        # Slot spans from just outside the hub to the rim (open to rim + top).
        r_mid = hub_r + L / 2.0
        sx, sy = _polar(r_mid, ang)
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx, sy, disc_h - chan_depth / 2.0))
            .transformed(rotate=cq.Vector(0, 0, ang))
            .box(L + WALL * 2.0, chan_w, chan_depth)
        )
        disc = disc.cut(slot)

    # Central solid hub raised as a grip knob (kept solid → no cavity).
    knob = cq.Workplane("XY").circle(hub_r * 0.7).extrude(disc_h + 6.0)
    disc = disc.union(knob)
    return disc


# ─── Mode 3: magnetic retriever wand ──────────────────────────────────────────
def build_magnet_wand():
    """A hand wand that holds a cylindrical retrieval magnet at the tip to fish
    stir bars out of a flask. The magnet pocket is a blind bore open to the tip
    face (no sealed cavity); the handle is solid with shallow grip flutes."""
    mag_r = magnet_diameter / 2.0 + 0.3
    handle_r = magnet_diameter / 2.0 + 4.0
    handle_len = 90.0
    tip_len = magnet_diameter + 6.0

    handle = cq.Workplane("XY").circle(handle_r).extrude(handle_len)
    handle = _fillet_safe(handle, ">Z", 3.0)
    handle = _fillet_safe(handle, "<Z", 2.0)

    # Magnet pocket bored into the bottom tip (open to the -Z tip face only).
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, tip_len / 2.0))
        .cylinder(tip_len, mag_r)
    )
    wand = handle.cut(pocket)

    # Grip flutes: shallow cylinders cut along the handle for a sure grip.
    flutes = 8
    for i in range(flutes):
        ang = i * 360.0 / flutes
        fx, fy = _polar(handle_r, ang)
        flute = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(fx, fy, handle_len * 0.6))
            .cylinder(handle_len * 0.5, 1.4)
        )
        wand = wand.cut(flute)
    return wand


# ─── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "slot_rack":
    result = build_slot_rack()
elif target_part == "carousel_rack":
    result = build_carousel_rack()
elif target_part == "magnet_wand":
    result = build_magnet_wand()
else:
    result = build_slot_rack()
