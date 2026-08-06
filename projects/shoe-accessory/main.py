"""
Shoe Accessories — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Footwear add-ons sized to lace width and sole geometry. A spring lace lock (a
single-piece cord-lock for shoelaces with a printed compliant button), a heel
clip that grips the shoe's heel counter, and a boot shaper / tree that holds a
boot shaft upright. Every part is one watertight solid built by cutting channels
and reliefs from a solid body.

Modes (dispatched via `target_part`):
  * "lace_lock"   — a barrel cord-lock: two lace channels and a printed sprung
                    button that pinches both laces; press to slide, release to
                    lock. Single piece, print-in-place.
  * "heel_clip"   — a C-clip that hooks over the heel counter (a back-of-shoe
                    grip / no-show sock helper), sized by heel width.
  * "boot_shaper" — a boot tree: a vertical spine with a flared foot and a curved
                    top spreader that keeps a boot shaft from slouching.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `lace_w`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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
lace_w      = float(PARAM(lambda: lace_w,      6.0))    # flat lace width (mm)
lace_t      = float(PARAM(lambda: lace_t,      2.5))    # lace thickness (mm)
wall        = float(PARAM(lambda: wall,        2.4))    # wall / rib thickness (mm)
heel_w      = float(PARAM(lambda: heel_w,     62.0))    # heel counter width (mm)
heel_h      = float(PARAM(lambda: heel_h,     34.0))    # heel grip height (mm)
sole_t      = float(PARAM(lambda: sole_t,     16.0))    # heel/sole counter thickness gripped (mm)
shaft_h     = float(PARAM(lambda: shaft_h,   150.0))    # boot shaft height for the shaper (mm)
shaft_w     = float(PARAM(lambda: shaft_w,    90.0))    # boot shaft interior width (mm)

target_part = str(  PARAM(lambda: target_part, "lace_lock"))  # lace_lock|heel_clip|boot_shaper

# ── Safe clamps ──────────────────────────────────────────────────────────────
lace_w  = max(3.0, min(lace_w, 14.0))
lace_t  = max(1.0, min(lace_t, 4.0))
wall    = max(1.6, min(wall, 5.0))
heel_w  = max(30.0, min(heel_w, 120.0))
heel_h  = max(15.0, min(heel_h, 70.0))
sole_t  = max(6.0, min(sole_t, 40.0))
shaft_h = max(60.0, min(shaft_h, 300.0))
shaft_w = max(40.0, min(shaft_w, 160.0))
chan_w = lace_w + 0.8      # lace channel width (clearance)
chan_t = lace_t + 0.6      # lace channel thickness (clearance)


# ── Helpers ───────────────────────────────────────────────────────────────────
def lace_channel(length):
    """A rounded slot sized to a flat lace: width along Y, thickness along Z,
    through-length along X. Cut from a body to form a lace pass-through. Shared
    across the lace parts so every lace slot sizes identically."""
    r = min(chan_t / 2.0 - 0.01, 0.8)
    slot = cq.Workplane("XY").box(length, chan_w, chan_t, centered=(True, True, True))
    if r > 0.05:
        try:
            slot = slot.edges("|X").fillet(r)
        except Exception:
            pass
    return slot


def rounded_block(w, d, h, r):
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.05:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass
    return wp


# ── Part builders ─────────────────────────────────────────────────────────────
def build_lace_lock():
    """A single-piece spring lace lock. A barrel body with two lace channels
    through it (both laces run along Z) and a printed compliant button: a U-slot
    frees a cantilever pad whose inner face bulges toward the channels so at rest
    it pinches the laces; pressing the pad flexes the beam out to release. One
    continuous watertight solid — slots are cuts, the beam stays rooted."""
    r = (lace_w + 2.0 * wall)          # barrel radius scales with lace group
    r = max(r, chan_w + 2.0 * wall)
    h = lace_w * 1.4 + 8.0

    body = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, h / 2.0))
        .cylinder(h, r)
    )

    # Two lace channels straight through along Z, spaced along X.
    spacing = chan_w + wall
    for ox in (-spacing / 2.0, spacing / 2.0):
        chan = lace_channel(h + 2.0)
        # channel currently runs along X; rotate so it runs along Z.
        chan = chan.rotate((0, 0, 0), (0, 1, 0), 90)
        chan = chan.translate((ox, 0, h / 2.0))
        body = body.cut(chan)

    # Compliant button: two side slots (along Z) that free a +Y cantilever pad,
    # plus a back relief so it can flex outward.
    slot_w = max(wall * 0.9, 1.0)
    beam_reach = h * 0.7
    beam_half = spacing / 2.0 + chan_w / 2.0
    for sx in (-1.0, 1.0):
        side = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * (beam_half + slot_w / 2.0), r * 0.4, h / 2.0 + (h - beam_reach) / 2.0))
            .box(slot_w, r, beam_reach)
        )
        body = body.cut(side)
    relief = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, r * 0.5 + wall, h / 2.0 + (h - beam_reach) / 2.0 + beam_reach * 0.1))
        .box(2.0 * beam_half, wall, beam_reach * 0.8)
    )
    body = body.cut(relief)

    # Finger pad ridge on the button outer face.
    pad = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, r - 0.4, h * 0.72))
        .box(2.0 * beam_half, 1.2, h * 0.22)
    )
    body = body.union(pad)
    try:
        body = body.edges("|Z").fillet(min(0.8, wall * 0.35))
    except Exception:
        pass
    return body


def build_heel_clip():
    """A C-clip that hooks over a shoe's heel counter: a curved back spine with a
    top hook and a bottom hook that grip the counter top and sole edge. Extruded
    once across the heel width so it is inherently watertight, with a compliant
    spine that clamps."""
    # Side C profile (in XZ), extruded across Y = heel width.
    depth = sole_t + 2.0 * wall
    height = heel_h + 2.0 * wall
    spine = wall * 1.4
    hook = wall * 1.6

    # Outline of the C (open toward -X where the counter sits).
    pts = [
        (0.0, 0.0),
        (depth, 0.0),
        (depth, hook),
        (spine, hook),
        (spine, height - hook),
        (depth, height - hook),
        (depth, height),
        (0.0, height),
    ]
    profile = (
        cq.Workplane("XZ")
        .polyline(pts)
        .close()
        .extrude(heel_w)
        .translate((0, heel_w / 2.0, 0))
    )
    try:
        profile = profile.edges("|Y").fillet(min(spine * 0.4, 1.2))
    except Exception:
        pass

    # Grip ribs on the inner faces (top & bottom hooks) for the counter bite.
    for zc in (hook * 0.5, height - hook * 0.5):
        rib = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(spine + 0.6, zc, 0))
            .box(1.2, 1.2, heel_w * 0.9)
        )
        profile = profile.union(rib)
    return profile


def build_boot_shaper():
    """A boot tree / shaper: a vertical spine, a flared foot at the bottom, and a
    curved top spreader that pushes the boot shaft walls apart so the shaft stands
    upright. Assembled as a union of solid primitives — watertight throughout."""
    spine_t = max(wall * 2.5, 8.0)
    spine_d = max(wall * 2.0, 6.0)

    # Vertical spine.
    spine = (
        cq.Workplane("XY")
        .box(spine_t, spine_d, shaft_h, centered=(True, True, False))
    )
    try:
        spine = spine.edges("|Z").fillet(min(spine_d * 0.4, 2.0))
    except Exception:
        pass

    # Flared foot: a wide low base the boot sole rests on.
    foot_w = shaft_w * 0.55
    foot = rounded_block(foot_w, spine_d + 10.0, wall * 2.5, min(spine_d, 4.0))
    body = spine.union(foot)

    # Top spreader: a curved bar across X near the top that spreads the shaft.
    spread_w = shaft_w * 0.9
    spread_t = max(wall * 2.0, 6.0)
    spreader = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, shaft_h - spread_t))
        .box(spread_w, spine_d + 4.0, spread_t, centered=(True, True, False))
    )
    try:
        spreader = spreader.edges("|Y").fillet(min(spread_t * 0.4, 3.0))
    except Exception:
        pass
    body = body.union(spreader)

    # Two contoured end pads on the spreader tips that press the shaft leather.
    for sx in (-1.0, 1.0):
        pad = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * spread_w / 2.0, 0, shaft_h - spread_t / 2.0))
            .cylinder(spread_t, spine_d * 0.9)
        )
        body = body.union(pad)

    # A lightening window through the spine (saves plastic, stays watertight).
    win = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, shaft_h * 0.5))
        .box(spine_t * 0.5, spine_d + 2.0, shaft_h * 0.4, centered=(True, True, True))
    )
    body = body.cut(win)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "heel_clip":
    result = build_heel_clip()
elif target_part == "boot_shaper":
    result = build_boot_shaper()
else:
    result = build_lace_lock()
