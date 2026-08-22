"""Hook-and-Loop Tape — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The printable analogue of hook-and-loop tape: two mating strips that peel apart and
re-close. The hook strip carries a field of mushroom-headed pins; the loop strip carries
a waffle grid of thin walls whose square cells those mushroom heads snag on. Together they
stand in for the sewn-on woven tape at a vest front, a cuff tab, a flap or a pocket.

This is the rigid hard good the Fashion Cabinet `hook-loop-tape` hardware reference bridges
to — the garment owns the closure placement and overlap math, this owns the hardware solid.

Modes (dispatched via `target_part`):
  * "set"        — hook strip and loop strip side by side.
  * "hook_strip" — base plate + mushroom-pin field.
  * "loop_strip" — base plate + waffle wall grid.

Geometry approach: both strips are a flat base plate with a plain sew margin around the
engaging field. The pin field is built as exactly TWO array operations — one pushPoints
circle extrude for all the stems, one pushPoints circle extrude for all the cap discs —
never a per-pin union. The waffle is likewise two pushPoints rect extrudes (one per
direction). Small boolean count, no spheres, no swept arcs → fast and watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `strip_length`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import math

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
strip_length = float(PARAM(lambda: strip_length, 50.0))  # strip length along X (mm)
strip_width  = float(PARAM(lambda: strip_width,  20.0))  # strip width across Y (mm)
base_t       = float(PARAM(lambda: base_t,       1.2))   # base plate thickness (mm)
pin_pitch    = float(PARAM(lambda: pin_pitch,    3.5))   # pin / waffle cell pitch (mm)
pin_dia      = float(PARAM(lambda: pin_dia,      1.2))   # mushroom stem diameter (mm)
head_dia     = float(PARAM(lambda: head_dia,     2.0))   # mushroom head diameter (mm)
pin_h        = float(PARAM(lambda: pin_h,        2.0))   # pin / waffle wall height (mm)
sew_margin   = float(PARAM(lambda: sew_margin,   3.0))   # plain sewing margin (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|hook_strip|loop_strip

# ── Safe clamps ──────────────────────────────────────────────────────────────
strip_length = max(20.0, min(strip_length, 120.0))
strip_width  = max(10.0, min(strip_width, 50.0))
base_t       = max(0.8, min(base_t, 2.0))
pin_pitch    = max(2.5, min(pin_pitch, 6.0))
pin_dia      = max(0.8, min(pin_dia, 2.0))
pin_h        = max(1.0, min(pin_h, 4.0))
# Sew margin must leave a usable engaging field on the narrow axis.
sew_margin   = max(2.0, min(sew_margin, 6.0))
sew_margin   = min(sew_margin, (strip_width - pin_pitch * 2.0) / 2.0)
sew_margin   = max(1.0, sew_margin)
# Head must overhang the stem (that overhang IS the hook) but stay clear of the
# neighbouring pin so heads never merge into a solid slab.
head_dia     = max(pin_dia + 0.4, min(head_dia, 3.0))
head_dia     = min(head_dia, pin_pitch - 0.6)
head_dia     = max(head_dia, pin_dia + 0.4)
# If the pitch is too tight for that rule, open the pitch instead of merging heads.
pin_pitch    = max(pin_pitch, head_dia + 0.6)

WALL_T = 0.8   # waffle wall thickness (mm)
HEAD_T = 0.5   # mushroom cap disc thickness (mm)
MAX_PINS = 400  # hard cap on array features (sandbox / meshing budget)


def field_extent():
    """Usable engaging field (length, width) inside the sewing margin."""
    fl = max(pin_pitch, strip_length - 2.0 * sew_margin)
    fw = max(pin_pitch, strip_width - 2.0 * sew_margin)
    return fl, fw


def grid_points():
    """Centred grid of pin centres inside the sew margin.

    The nominal pitch is `pin_pitch`. If that pitch would place more than MAX_PINS
    features (a big strip at a fine pitch — e.g. 120x50 at 2.5 mm is ~900 pins), the
    EFFECTIVE pitch is grown by sqrt(n_nominal / MAX_PINS) and the counts recomputed,
    so the field stays visually identical but the feature budget is respected. This
    keeps the two array booleans cheap and the mesh watertight.
    """
    fl, fw = field_extent()
    pitch = pin_pitch
    nx = max(1, int(fl // pitch) + 1)
    ny = max(1, int(fw // pitch) + 1)
    if nx * ny > MAX_PINS:
        pitch = pitch * math.sqrt(float(nx * ny) / float(MAX_PINS))
        nx = max(1, int(fl // pitch) + 1)
        ny = max(1, int(fw // pitch) + 1)
        # Rounding can still nudge one over the cap; shrink counts, never the cap.
        while nx * ny > MAX_PINS and nx > 1:
            nx -= 1
        while nx * ny > MAX_PINS and ny > 1:
            ny -= 1
    span_x = (nx - 1) * pitch
    span_y = (ny - 1) * pitch
    pts = []
    for i in range(nx):
        for j in range(ny):
            pts.append((-span_x / 2.0 + i * pitch, -span_y / 2.0 + j * pitch))
    return pts, pitch


def build_base():
    """The flat sewable base plate shared by both strips."""
    plate = (
        cq.Workplane("XY")
        .box(strip_length, strip_width, base_t, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|Z").fillet(min(2.0, strip_width * 0.15))
    except Exception:
        pass
    return plate


def build_hook_strip():
    """Base plate + mushroom-pin field (two array extrudes, no per-pin union)."""
    plate = build_base()
    pts, _pitch = grid_points()

    stem_h = max(0.4, pin_h - HEAD_T)
    # One pushPoints op for EVERY stem.
    stems = (
        cq.Workplane("XY")
        .workplane(offset=base_t)
        .pushPoints(pts)
        .circle(pin_dia / 2.0)
        .extrude(stem_h)
    )
    # One pushPoints op for EVERY cap disc, sitting on top of the stems.
    caps = (
        cq.Workplane("XY")
        .workplane(offset=base_t + stem_h)
        .pushPoints(pts)
        .circle(head_dia / 2.0)
        .extrude(HEAD_T)
    )
    solid = plate.union(stems).union(caps)
    try:
        solid = solid.edges(">Z").fillet(HEAD_T * 0.35)
    except Exception:
        pass
    return solid


def build_loop_strip():
    """Base plate + waffle grid of thin walls the mushroom heads grab."""
    plate = build_base()
    pts, pitch = grid_points()

    xs = sorted({round(p[0], 4) for p in pts})
    ys = sorted({round(p[1], 4) for p in pts})
    fl, fw = field_extent()
    # Walls run the full field span, offset half a pitch so the cell centres land
    # where the mating strip's pins land.
    rib_len_x = min(strip_length - 2.0 * sew_margin, fl + pitch)
    rib_len_y = min(strip_width - 2.0 * sew_margin, fw + pitch)
    rib_len_x = max(rib_len_x, pitch)
    rib_len_y = max(rib_len_y, pitch)

    wall_t = min(WALL_T, max(0.4, pitch * 0.3))
    half = pitch / 2.0

    # Wall lines sit between pin columns/rows → the pins drop into cell centres.
    xline = [(x + half, 0.0) for x in xs]
    xline.append((xs[0] - half, 0.0))
    yline = [(0.0, y + half) for y in ys]
    yline.append((0.0, ys[0] - half))
    # Trim any line that would fall outside the sew margin.
    lim_x = (strip_length - 2.0 * sew_margin) / 2.0
    lim_y = (strip_width - 2.0 * sew_margin) / 2.0
    xline = [p for p in xline if abs(p[0]) <= lim_x - wall_t / 2.0] or [(0.0, 0.0)]
    yline = [p for p in yline if abs(p[1]) <= lim_y - wall_t / 2.0] or [(0.0, 0.0)]

    # ONE pushPoints rect extrude per direction.
    ribs_y = (
        cq.Workplane("XY")
        .workplane(offset=base_t)
        .pushPoints(xline)
        .rect(wall_t, rib_len_y)
        .extrude(pin_h)
    )
    ribs_x = (
        cq.Workplane("XY")
        .workplane(offset=base_t)
        .pushPoints(yline)
        .rect(rib_len_x, wall_t)
        .extrude(pin_h)
    )
    return plate.union(ribs_y).union(ribs_x)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "hook_strip":
    result = build_hook_strip()
elif target_part == "loop_strip":
    result = build_loop_strip()
else:
    gap = max(4.0, strip_width * 0.25)
    offset = (strip_width + gap) / 2.0
    result = build_hook_strip().translate((0, -offset, 0)).union(
        build_loop_strip().translate((0, offset, 0)))
