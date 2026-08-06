"""
Jewelry Blanks — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Parametric ring and bracelet blanks sized by standard ring size. A plain ring
band, a signet blank with a flat top face for engraving / setting, and an
open bangle bracelet. Ring inner diameter is derived from US ring size via the
standard sizing conversion so the blank fits a real finger.

US ring size → inner diameter (mm):
    inner_dia = 11.63 + 0.8128 * size
This is the conventional US/Canada conversion (US size N ⇒ inner circumference
36.537 + 2.5535*N mm; diameter = circumference / pi). E.g. US 7 ⇒ 17.32 mm,
US 10 ⇒ 19.76 mm — matching published ring-size charts.

Modes (dispatched via `target_part`):
  * "ring_band"    — a plain band with a chosen cross-section profile.
  * "signet_blank" — a band carrying a raised flat plateau (the signet face) for
                     engraving or as a setting bezel blank.
  * "bracelet"     — an open bangle: a large ring with a gap, sized by wrist.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `ring_size`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
ring_size   = float(PARAM(lambda: ring_size,   7.0))    # US ring size (3-14)
band_w      = float(PARAM(lambda: band_w,       6.0))    # band width (mm, along axis)
band_t      = float(PARAM(lambda: band_t,       2.0))    # band radial thickness (mm)
profile     = str(  PARAM(lambda: profile, "domed"))    # flat|domed|comfort
signet_w    = float(PARAM(lambda: signet_w,    12.0))   # signet face width (mm)
signet_l    = float(PARAM(lambda: signet_l,    14.0))   # signet face length (mm)
signet_h    = float(PARAM(lambda: signet_h,     2.5))   # signet plateau height (mm)
wrist_dia   = float(PARAM(lambda: wrist_dia,   60.0))   # bracelet interior diameter (mm)
gap_deg     = float(PARAM(lambda: gap_deg,     70.0))   # bangle opening (degrees)

target_part = str(  PARAM(lambda: target_part, "ring_band"))  # ring_band|signet_blank|bracelet

# ── Ring sizing ───────────────────────────────────────────────────────────────
def us_ring_inner_dia(size):
    """US ring size -> inner diameter (mm). Standard conversion."""
    return 11.63 + 0.8128 * size


# ── Safe clamps ──────────────────────────────────────────────────────────────
ring_size = max(3.0, min(ring_size, 14.0))
band_w    = max(2.0, min(band_w, 16.0))
band_t    = max(1.2, min(band_t, 5.0))
signet_w  = max(6.0, min(signet_w, 24.0))
signet_l  = max(6.0, min(signet_l, 26.0))
signet_h  = max(1.0, min(signet_h, 6.0))
wrist_dia = max(45.0, min(wrist_dia, 75.0))
gap_deg   = max(20.0, min(gap_deg, 140.0))

inner_d = us_ring_inner_dia(ring_size)
inner_r = inner_d / 2.0
outer_r = inner_r + band_t


# ── Helpers ───────────────────────────────────────────────────────────────────
def band_solid(in_r, out_r, width, prof):
    """A ring band: a tube (outer minus inner cylinder) of the given profile,
    axis along Z, centred at origin, spanning z:[-width/2, width/2].
      * flat    — square outer wall.
      * domed   — outer edges rounded (a rounded outer rim).
      * comfort — inner edges eased (comfort-fit interior)."""
    tube = (
        cq.Workplane("XY")
        .circle(out_r)
        .circle(in_r)
        .extrude(width)
        .translate((0, 0, -width / 2.0))
    )
    if prof == "domed":
        r = min(band_t * 0.9, width * 0.45)
        try:
            tube = tube.edges("|Z").fillet(0.0001)  # no-op guard for selector
        except Exception:
            pass
        try:
            tube = tube.faces(">Z or <Z").edges(cq.selectors.RadiusNthSelector(0)).fillet(r)
        except Exception:
            # Fallback: round the outer top/bottom circular edges.
            try:
                tube = tube.edges(">Z").fillet(r).edges("<Z").fillet(r)
            except Exception:
                pass
    elif prof == "comfort":
        r = min(band_t * 0.5, width * 0.3)
        try:
            tube = tube.faces(">Z").edges().fillet(r)
        except Exception:
            pass
    return tube


def simple_band(in_r, out_r, width):
    """A plain square-section tube (used where a robust base is needed)."""
    return (
        cq.Workplane("XY")
        .circle(out_r)
        .circle(in_r)
        .extrude(width)
        .translate((0, 0, -width / 2.0))
    )


# ── Part builders ─────────────────────────────────────────────────────────────
def build_ring_band():
    """A plain ring band sized to the finger, with the chosen cross-section."""
    band = band_solid(inner_r, outer_r, band_w, profile)
    # Ease the outer top/bottom rims a touch for comfort (non-fatal).
    if profile == "flat":
        try:
            band = band.edges(">Z").chamfer(min(0.4, band_t * 0.2))
            band = band.edges("<Z").chamfer(min(0.4, band_t * 0.2))
        except Exception:
            pass
    return band


def build_signet_blank():
    """A ring band with a raised flat plateau on the outside (the signet face).
    The plateau is a rounded slab whose base curves down into the band (its lower
    portion overlaps the band OD so the fuse is solid), giving a flat top face for
    engraving or as a bezel-setting blank."""
    band = simple_band(inner_r, outer_r, band_w)

    # Signet plateau: a rounded box sitting on top (+Y here is the outside; we put
    # the face on +Y so the ring lies flat on a print bed with the band as a ring).
    # Place the plateau outward along +Y at the top of the ring.
    plate_th = signet_h + band_t          # extends from inside the band outward
    plate = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, outer_r + signet_h - plate_th / 2.0, 0))
        .box(signet_w, signet_l, plate_th)
    )
    try:
        plate = plate.edges("|Y").fillet(min(signet_w, signet_l) * 0.18)
    except Exception:
        pass

    # Trim the plateau's inner side to the band OD so it fuses volumetrically and
    # nothing floats inside the finger hole: cut away anything inside outer_r.
    core = cq.Workplane("XY").circle(outer_r).extrude(band_w + 8.0).translate((0, 0, -(band_w + 8.0) / 2.0))
    plate = plate.cut(core)

    body = band.union(plate)
    return body


def build_bracelet():
    """An open bangle: a large ring sized to the wrist with an angular gap so it
    slips on. Square-ish cross-section, rounded gap ends."""
    br_in_r = wrist_dia / 2.0
    br_out_r = br_in_r + max(band_t * 1.5, 3.0)
    width = max(band_w * 1.5, 6.0)

    ring = simple_band(br_in_r, br_out_r, width)

    # Cut an angular wedge to open the bangle. Build a pie wedge and subtract.
    half = math.radians(gap_deg) / 2.0
    big = br_out_r + 5.0
    # Wedge polygon centred on +X opening.
    pts = [(0, 0)]
    steps = 12
    for i in range(steps + 1):
        a = -half + (2.0 * half) * i / steps
        pts.append((big * math.cos(a), big * math.sin(a)))
    wedge = (
        cq.Workplane("XY")
        .polyline(pts)
        .close()
        .extrude(width + 4.0)
        .translate((0, 0, -(width + 4.0) / 2.0))
    )
    ring = ring.cut(wedge)

    # Round the two cut ends and outer rims for comfort (non-fatal).
    try:
        ring = ring.edges("|Z").fillet(min(band_t, 1.5))
    except Exception:
        pass
    return ring


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "signet_blank":
    result = build_signet_blank()
elif target_part == "bracelet":
    result = build_bracelet()
else:
    result = build_ring_band()
