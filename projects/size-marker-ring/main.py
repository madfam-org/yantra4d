"""Size Marker Ring — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The rack size divider: a C-ring that snaps over a closet or shop rail and carries a size
label, so a rail of mixed stock reads at a glance and stays sorted after a customer has been
through it. The ring is split by a mouth narrower than the rod, so it springs on and stays
put; the label is DEBOSSED (cut into the face), never embossed, because a raised character
on a rack divider snags knitwear.

Modes (dispatched via `target_part`):
  * "ring"  — a single labelled divider.
  * "blank" — the same ring with no text, for hand-marking or for a size the select list
              does not carry.
  * "set"   — three dividers laid out on one plate, so a size run prints in one job.

Geometry: the ring is a revolved rounded profile (never a cylinder plus a sphere cap), the
mouth is one oversized box cut, and the label is `Workplane.text` cut into the face. Every
text operation is wrapped in try/except with a plain-ring fallback — a font that does not
render must degrade to a usable blank, not to a failed render.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `rod_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
rod_dia    = float(PARAM(lambda: rod_dia,    32.0))   # rail outside diameter (mm)
size_label = str(  PARAM(lambda: size_label, "M"))    # the size shown on the tab
ring_t     = float(PARAM(lambda: ring_t,     5.0))    # ring wall thickness (mm)
ring_w     = float(PARAM(lambda: ring_w,     10.0))   # ring width along the rail (mm)
tab_h      = float(PARAM(lambda: tab_h,      24.0))   # label tab height below the ring (mm)
mouth_pct  = float(PARAM(lambda: mouth_pct,  62.0))   # snap mouth width, % of rod diameter
text_depth = float(PARAM(lambda: text_depth, 0.9))    # deboss depth (mm)

target_part = str(PARAM(lambda: target_part, "ring"))


# ── Safe clamps ──────────────────────────────────────────────────────────────
# 19 / 25 / 32 mm are the common closet and shop rails; allow a little either way.
rod_dia    = max(12.0, min(rod_dia, 50.0))
ring_t     = max(2.0,  min(ring_t, 10.0))
ring_w     = max(4.0,  min(ring_w, 25.0))
tab_h      = max(10.0, min(tab_h, 60.0))
# A mouth wider than the rod does not snap; narrower than half the rod cannot be sprung
# on without cracking a printed ring.
mouth_pct  = max(45.0, min(mouth_pct, 92.0))
text_depth = max(0.3,  min(text_depth, min(2.0, ring_t * 0.4)))

# The select list carries the sizes; anything else is treated as a blank so a stray
# value can never inject an unbounded string into a text operation.
ALLOWED = ("XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL",
           "0", "2", "4", "6", "8", "10", "12", "14", "16", "18", "20",
           "28", "30", "32", "34", "36", "38", "40", "42", "44", "46")
label = size_label.strip().upper()
if label not in ALLOWED:
    label = ""

r_in = rod_dia / 2.0 + 0.5          # 0.5 mm running clearance on the rail
r_out = r_in + ring_t
mouth_w = rod_dia * (mouth_pct / 100.0)

# Tab: a rounded paddle hanging below the ring, wide enough for two characters.
tab_w = max(r_out * 1.5, 16.0)
tab_t = min(ring_w, max(2.4, ring_t * 0.75))
# Text height fits inside the tab with a margin all round.
txt_h = min(tab_h * 0.52, tab_w * 0.44)


def _ring_blank():
    """The ring body: a revolved section with its rims softened on the clean blank.

    Revolved rather than assembled from a cylinder and a sphere cap — that union is
    banned, because the cap's pole is a singularity and the seam reads non-watertight.

    The revolve axis is Z, so the RAIL passes along Z and the ring lies flat in XY.
    The mouth therefore opens along +Y and the label tab hangs along -Y.
    """
    hw = ring_w / 2.0
    # A plain rectangular section, revolved about Z. Hand-building a rounded-rect wire
    # from threePointArc segments is how this first went wrong — a mid-point that is
    # not actually on the arc yields a non-planar, non-closed wire, and the revolve
    # returns a zero-volume shell rather than raising. A rectangle cannot go wrong.
    #
    # `revolve`'s axis is expressed in the WORKPLANE's frame, not the global one — a
    # profile drawn on "XZ" and revolved about (0, 0, 1) silently returns a
    # zero-volume shell rather than raising. Draw on XY, revolve about the in-plane Y
    # axis (which produces a ring whose hole axis is global Y), then rotate the ring so
    # its hole axis is Z.
    prof = (
        cq.Workplane("XY")
        .moveTo(r_in, -hw)
        .lineTo(r_in, hw)
        .lineTo(r_out, hw)
        .lineTo(r_out, -hw)
        .close()
    )
    ring = prof.revolve(360, (0, 0, 0), (0, 1, 0)).rotate((0, 0, 0), (1, 0, 0), 90)
    # Soften the outer rims. This is a fillet on a CLEAN BLANK — before the mouth cut,
    # the tab union, and the text deboss — which is the only safe place for one.
    cr = max(0.2, min(min(ring_t, ring_w) * 0.28, min(ring_t, ring_w) / 2.0 - 0.2))
    try:
        ring = ring.edges("%CIRCLE").fillet(cr)
    except Exception:
        pass
    return ring


def _open_mouth(solid):
    """Cut the snap mouth in the ring's top, so it springs onto the rail.

    One oversized box cut, overshooting the ring in every direction, so no cut face is
    ever coincident with the revolved skin. The mouth faces +Z (up), which is what puts
    the tab below the rail where the label reads.
    """
    over = r_out * 2.0 + 20.0
    # A single box: `mouth_w` wide in X, oversized in Z (clean through the ring's
    # width), and oversized in Y but sitting entirely at Y > 0, so only the ring's +Y
    # arc is opened and the -Y arc that carries the tab survives intact.
    cut = (
        cq.Workplane("XY")
        .box(mouth_w, over, over)
        .translate((0, over / 2.0, 0))
    )
    return solid.cut(cut)


def _tab_center_y():
    """Y of the label tab's centre — used by both the tab and the deboss."""
    return -(r_in - ring_t * 1.2) - tab_h / 2.0


def _tab():
    """The label paddle hanging below the ring in -Y, a flat plate thin along Z.

    Its top edge is buried `ring_t * 1.2` inside the ring's -Y arc, so the union is a
    real overlap rather than a tangent touch at the ring's inner face.
    """
    top_y = -(r_in - ring_t * 1.2)
    plate = (
        cq.Workplane("XY")
        .rect(tab_w, tab_h)
        .extrude(tab_t)
        .translate((0, top_y - tab_h / 2.0, -tab_t / 2.0))
        .edges("|Z")
        .fillet(min(tab_w, tab_h) * 0.18)
    )
    return plate


def _deboss(body):
    """Cut the size label into BOTH faces of the tab.

    Debossed, never embossed: a raised character on a rack divider catches knitwear.
    Both faces are marked so the divider reads from either side of the rail.

    Guarded: a font that fails to render must degrade to a plain ring, not to a failed
    render, so every text op is wrapped and the un-debossed body is returned on error.
    """
    if not label:
        return body
    # Size the glyph to the tab, then shrink for longer labels so "3XL" still fits.
    h = txt_h * (1.0 if len(label) <= 1 else (0.78 if len(label) == 2 else 0.62))
    y_mid = _tab_center_y()
    marked = body
    for sign in (1.0, -1.0):
        try:
            # The glyph solid stands proud of the tab face and is cut in, so the cutter
            # overshoots the face rather than sitting flush with it.
            glyph = (
                cq.Workplane("XY")
                .workplane(offset=sign * (tab_t / 2.0 - text_depth))
                .center(0, y_mid)
                .text(label, h, sign * text_depth * 2.0, combine=False)
            )
            candidate = marked.cut(glyph)
            # A cut that removed nothing, or everything, is not a usable deboss.
            vol = candidate.val().Volume()
            if vol > 0.0:
                marked = candidate
        except Exception:
            # Font unavailable, glyph out of range, or a degenerate cut — keep the
            # plain tab. A blank divider is usable; a failed render is not.
            return marked
    return marked


def build_ring():
    """One labelled divider: ring, snap mouth, tab, debossed label."""
    body = _open_mouth(_ring_blank())
    body = body.union(_tab())
    return _deboss(body)


def build_blank():
    """The same divider with no label, for hand-marking or an unlisted size."""
    return _open_mouth(_ring_blank()).union(_tab())


def build_set():
    """Three dividers side by side on one plate, so a size run prints in one job.

    Genuinely separate solids, combined as a Compound — never `.union()` of
    non-touching bodies, which yields one shape with disjoint shells.
    """
    one = build_ring()
    gap = max(r_out * 0.35, 6.0)
    # Laid out along X: the divider is tall in Y (ring plus tab) and narrow in X, so
    # X is the axis with room to spare on a bed.
    pitch = max(r_out * 2.0, tab_w) + gap
    solids = []
    for i in (-1, 0, 1):
        for s in one.translate((i * pitch, 0, 0)).vals():
            solids.append(s)
    return cq.Workplane(obj=cq.Compound.makeCompound(solids))


# ── Dispatch ─────────────────────────────────────────────────────────────────
# Mode ids and part ids match the manifest exactly:
#   ring  -> parts ["ring"]
#   blank -> parts ["blank"]
#   set   -> parts ["set"]
if target_part == "blank":
    result = build_blank()
elif target_part == "set":
    result = build_set()
else:
    result = build_ring()
