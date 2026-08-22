"""Headband Blank — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The rigid arc a milliner or a costume maker covers in fabric to make a padded headband: an
elliptical half-arc struck on real head geometry, with tapered ends that carry sew holes so
the fabric casing is stitched shut and anchored instead of glued.

Head anthropometry: an adult head is not a circle. Measured ear-to-ear (bitragion) it runs
about 140-150 mm and front-to-back rather more, so a headband that sits over the crown is
an ellipse, not a semicircle — a circular blank pinches at the temples and gaps at the
crown. `head_width` is the ear-to-ear span; the crown height follows it at the usual 0.9
proportion, and both are parameters of the arc the fabric casing must be cut to.

The ends taper in both the band width and the thickness. That taper is what lets a covered
headband disappear behind the ear rather than ending in a visible square stub, and the sew
holes at each tapered end are where the casing's stitching bites.

Modes (dispatched via `target_part`):
  * "blank" — one headband blank.
  * "pair"  — two blanks nested on the plate, the way a maker prints a spare.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `head_width`).
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
head_width = float(PARAM(lambda: head_width, 145.0))  # ear-to-ear span (mm)
band_w     = float(PARAM(lambda: band_w,      22.0))  # band width over the crown (mm)
band_t     = float(PARAM(lambda: band_t,       2.4))  # band thickness (mm)
taper_len  = float(PARAM(lambda: taper_len,   32.0))  # tapered run at each end (mm)
tip_w      = float(PARAM(lambda: tip_w,        9.0))  # band width at the tip (mm)
sew_holes  = int(  PARAM(lambda: sew_holes,      3))  # sew holes per tapered end
hole_dia   = float(PARAM(lambda: hole_dia,     2.0))  # sew hole diameter (mm)

target_part = str(PARAM(lambda: target_part, "blank"))  # blank|pair

# ── Safe clamps ──────────────────────────────────────────────────────────────
head_width = max(110.0, min(head_width, 180.0))
band_w     = max(10.0, min(band_w, 45.0))
band_t     = max(1.2, min(band_t, 5.0))
taper_len  = max(8.0, min(taper_len, head_width * 0.35))
tip_w      = max(4.0, min(tip_w, band_w - 1.5))
sew_holes  = max(0, min(sew_holes, 6))
hole_dia   = max(1.0, min(hole_dia, 3.5))

# ── Derived geometry ─────────────────────────────────────────────────────────
# Elliptical head arc: the semi-major axis is the ear-to-ear half span, the semi-minor is
# the crown rise. 0.9 is the usual head proportion for a band that sits behind the ears.
arc_a = head_width / 2.0                 # X semi-axis (ear to ear)
arc_b = arc_a * 0.9                      # Y semi-axis (crown rise)
# Sew holes need wall around them; clamp to the tip width.
hole_dia = min(hole_dia, max(1.0, tip_w - 2.4))
# Hole spacing runs back from the tip along the taper.
hole_pitch = taper_len / (sew_holes + 1.0) if sew_holes > 0 else taper_len


def _arc_body():
    """The elliptical half-arc band: outer ellipse minus inner ellipse, upper half only."""
    outer = cq.Workplane("XY").ellipse(arc_a, arc_b).extrude(band_w)
    # Inner cutter overshoots both Z faces so no coincident surfaces survive.
    inner = (
        cq.Workplane("XY")
        .ellipse(max(0.5, arc_a - band_t), max(0.5, arc_b - band_t))
        .extrude(band_w + 6.0)
        .translate((0, 0, -3.0))
    )
    ring = outer.cut(inner)
    # Keep only the upper half (Y >= 0) — a band over the crown, open at the ears.
    lower = (
        cq.Workplane("XY")
        .box(arc_a * 3.0, arc_b * 3.0, band_w + 8.0)
        .translate((0, -arc_b * 1.5, band_w / 2.0))
    )
    return ring.cut(lower)


def _taper_cutters():
    """Four wedge cutters that thin the band width toward each tip.

    One slab per (end, Z face). Each starts as a half-space lying just outside a Z face,
    then hinges down about the line where the taper begins, so the cut takes the band from
    `band_w` at the hinge to `tip_w` at the tip. The slabs are oversized in every direction
    so no cut leaves a coincident surface.
    """
    drop = (band_w - tip_w) / 2.0            # removed from each Z face at the tip
    if drop <= 0.02:
        return None
    angle = math.degrees(math.atan2(drop, taper_len))
    big = max(arc_a, arc_b) * 4.0
    cutters = None
    for sign in (-1.0, 1.0):
        for zside in (-1.0, 1.0):
            hinge_x = sign * (arc_a - taper_len)
            hinge_z = band_w / 2.0 + zside * band_w / 2.0
            slab = (
                cq.Workplane("XY")
                .box(big, big, big)
                .translate((0, 0, hinge_z + zside * big / 2.0))
            )
            # Hinge about the line (hinge_x, *, hinge_z) running along Y.
            slab = slab.translate((-hinge_x, 0, -hinge_z))
            slab = slab.rotate((0, 0, 0), (0, 1, 0), sign * zside * angle)
            slab = slab.translate((hinge_x, 0, hinge_z))
            cutters = slab if cutters is None else cutters.union(slab)
    return cutters


def _sew_hole_cutters():
    """Sew holes through the band thickness at each tapered end.

    Bored along the local radial direction (through the band wall) so the thread passes
    the way a casing is stitched, not along the arc.
    """
    if sew_holes <= 0:
        return None
    cutters = None
    for sign in (-1.0, 1.0):
        for i in range(1, sew_holes + 1):
            # Walk back from the tip along X; find the ellipse Y at that X.
            x = sign * (arc_a - i * hole_pitch)
            frac = min(1.0, abs(x) / arc_a)
            y = arc_b * math.sqrt(max(0.0, 1.0 - frac * frac))
            # Wall mid-radius point, pulled in half a thickness.
            nx, ny = x / (arc_a * arc_a), y / (arc_b * arc_b)
            nlen = math.hypot(nx, ny) or 1.0
            nx, ny = nx / nlen, ny / nlen
            cx = x - nx * band_t / 2.0
            cy = y - ny * band_t / 2.0
            ang = math.degrees(math.atan2(ny, nx))
            # Band width at that station, so the hole stays centred in the taper.
            back = max(0.0, taper_len - i * hole_pitch)
            local_w = tip_w + (band_w - tip_w) * (back / taper_len if taper_len else 1.0)
            bore = (
                cq.Workplane("YZ")
                .circle(hole_dia / 2.0)
                .extrude(band_t * 4.0)
                .translate((-band_t * 2.0, 0, 0))
            )
            bore = bore.rotate((0, 0, 0), (0, 0, 1), ang)
            bore = bore.translate((cx, cy, band_w / 2.0))
            cutters = bore if cutters is None else cutters.union(bore)
            # Only bore where the band is actually wide enough to hold the hole.
            if local_w < hole_dia + 2.0:
                break
    return cutters


def build_blank():
    """One headband blank: elliptical arc, tapered ends, sew holes bored through."""
    body = _arc_body()
    tap = _taper_cutters()
    if tap is not None:
        body = body.cut(tap)
    holes = _sew_hole_cutters()
    if holes is not None:
        body = body.cut(holes)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pair":
    one = build_blank()
    bb = one.val().BoundingBox()
    gap = max(6.0, bb.ylen * 0.15)
    asm = cq.Assembly()
    asm.add(one.translate((0, -(bb.ylen + gap) / 2.0, 0)),
            name="blank_a", color=cq.Color("#d0c4b4"))
    # The spare nests flipped, the way two arcs pack on a plate.
    asm.add(one.rotate((0, 0, 0), (0, 0, 1), 180).translate((0, (bb.ylen + gap) / 2.0, 0)),
            name="blank_b", color=cq.Color("#c0b4a4"))
    result = asm
else:
    result = build_blank()
