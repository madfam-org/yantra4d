"""Hat Size Reducer — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The ribbed C-profile sizing strip a milliner or a hat wearer clips inside a hatband to take
a hat down a size or two. Commercial hat sizing is sold as foam or felt tape in one fixed
thickness; this is the same job done as a printed rib strip whose take-up is a parameter,
so a 59 cm hat becomes a 58 cm or a 57 cm hat without cutting or replacing the sweatband.

Hat sizing arithmetic: one US/UK hat size is 1/8 inch of head DIAMETER, roughly 1 cm of
circumference. `reduction_mm` is stated as circumference take-up — the strip adds
`reduction_mm / (2*pi)` of radial build-up inside the band, so 10 mm is about a full hat
size and 5 mm is a half size.

The strip is a shallow arc struck on the head radius (it follows the head curve so it lies
flush against the sweatband instead of chording across it) with a C cross-section: a back
web plus a lip top and bottom that hooks the sweatband's free edges. Friction fit, no glue,
removable. The inner face carries vertical ribs that bear on the head — ribs spread the
take-up and vent, which is why sizing tape is ribbed or foamed rather than solid.

Modes (dispatched via `target_part`):
  * "strip" — one sizing strip.
  * "pair"  — two strips laid out flat, the usual fitting (one over each temple).

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
strip_length = float(PARAM(lambda: strip_length, 90.0))   # arc length of the strip (mm)
strip_height = float(PARAM(lambda: strip_height, 12.0))   # strip height, band-wise (mm)
reduction_mm = float(PARAM(lambda: reduction_mm, 10.0))   # circumference take-up (mm)
band_t       = float(PARAM(lambda: band_t,        2.2))   # sweatband thickness gripped (mm)
rib_count    = int(  PARAM(lambda: rib_count,       7))   # vertical ribs on the inner face
rib_depth    = float(PARAM(lambda: rib_depth,     1.2))   # how far each rib stands proud (mm)
head_circ    = float(PARAM(lambda: head_circ,   580.0))   # head circumference the hat fits (mm)

target_part = str(PARAM(lambda: target_part, "strip"))  # strip|pair

# ── Safe clamps ──────────────────────────────────────────────────────────────
strip_length = max(40.0, min(strip_length, 200.0))
strip_height = max(8.0, min(strip_height, 30.0))
reduction_mm = max(3.0, min(reduction_mm, 25.0))
band_t       = max(1.0, min(band_t, 5.0))
rib_count    = max(0, min(rib_count, 20))
rib_depth    = max(0.4, min(rib_depth, 3.0))
head_circ    = max(480.0, min(head_circ, 680.0))

# ── Derived geometry ─────────────────────────────────────────────────────────
# The head is treated as a circle of this radius; the strip is an arc struck on it.
head_r = head_circ / (2.0 * math.pi)
# Circumference take-up converted to radial build-up of the web, plus a printable wall.
web_t = max(1.2, reduction_mm / (2.0 * math.pi) + 0.8)
# Grip lips: the C that hooks the top and bottom edges of the sweatband.
lip_t = max(1.0, min(band_t * 0.7, 2.0))          # lip build-up, radially outward
lip_h = max(1.2, min(strip_height * 0.16, 3.0))   # lip height, band-wise
# The strip may not wrap more than most of the way around the head.
arc_span = min(strip_length / head_r, math.pi * 1.3)   # radians subtended
# Rib field leaves the strip ends clear so the lips can be sprung on.
rib_margin = max(3.0, strip_length * 0.06)
rib_h = max(2.0, strip_height - 2.0 * lip_h - 0.4)


def _pt(r, a):
    """Polar to cartesian on XY."""
    return (r * math.cos(a), r * math.sin(a))


def _arc_band(r_in, r_out, span, height, z0):
    """An annular sector centred on +X: closed planar face on XY, extruded in Z.

    Two straight radial ends plus an inner and an outer three-point arc — a single
    closed wire, so the extrude yields exactly one solid with no pending geometry.
    """
    a0, a1, am = -span / 2.0, span / 2.0, 0.0
    band = (
        cq.Workplane("XY")
        .moveTo(*_pt(r_in, a0))
        .lineTo(*_pt(r_out, a0))
        .threePointArc(_pt(r_out, am), _pt(r_out, a1))
        .lineTo(*_pt(r_in, a1))
        .threePointArc(_pt(r_in, am), _pt(r_in, a0))
        .close()
        .extrude(height)
    )
    return band.translate((0, 0, z0))


def _web():
    """The back web: the radial build-up that actually reduces the hat size."""
    return _arc_band(head_r - web_t, head_r, arc_span, strip_height, 0.0)


def _lips():
    """Top and bottom grip lips standing outward, toward the sweatband.

    They hook the sweatband's free edges. Each overlaps the web by 0.6 mm radially so
    the union is volumetric rather than a face-to-face touch.
    """
    r_in = head_r - 0.6
    r_out = head_r + lip_t
    bottom = _arc_band(r_in, r_out, arc_span, lip_h, 0.0)
    top = _arc_band(r_in, r_out, arc_span, lip_h, strip_height - lip_h)
    return bottom.union(top)


def _ribs():
    """Vertical comfort ribs on the inner (head-side) face, overlapping the web."""
    if rib_count <= 0:
        return None
    r_out = head_r - web_t + 0.5           # bite back into the web for real overlap
    r_in = head_r - web_t - rib_depth
    usable = max(1.0, strip_length - 2.0 * rib_margin)
    # Rib width along the arc: never more than 60 % of the available pitch.
    rib_w = min(0.6 * usable / max(rib_count, 1), 3.5)
    rib_span = rib_w / head_r
    ribs = None
    for i in range(rib_count):
        frac = 0.5 if rib_count == 1 else i / (rib_count - 1.0)
        centre_a = (-usable / 2.0 + usable * frac) / head_r
        seg = _arc_band(r_in, r_out, rib_span, rib_h, lip_h + 0.2)
        seg = seg.rotate((0, 0, 0), (0, 0, 1), math.degrees(centre_a))
        ribs = seg if ribs is None else ribs.union(seg)
    return ribs


def build_strip():
    """One complete sizing strip: web + grip lips + inner ribs, a single solid."""
    body = _web().union(_lips())
    ribs = _ribs()
    if ribs is not None:
        body = body.union(ribs)
    # Recentre so the strip straddles the origin rather than sitting out at head radius.
    return body.translate((-head_r + web_t / 2.0, 0, 0))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pair":
    one = build_strip()
    span_y = one.val().BoundingBox().ylen
    gap = max(6.0, span_y * 0.12)
    asm = cq.Assembly()
    asm.add(one.translate((0, -(span_y + gap) / 2.0, 0)),
            name="strip_left", color=cq.Color("#c8b8a0"))
    asm.add(one.translate((0, (span_y + gap) / 2.0, 0)),
            name="strip_right", color=cq.Color("#c8b8a0"))
    result = asm
else:
    result = build_strip()
