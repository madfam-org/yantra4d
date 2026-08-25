"""
Grafting Union Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A spring clip that holds a graft union closed while it knits. Grafting joins a
`scion` (the shoot you want fruit from) to a `rootstock` (the roots you want it on).
The join only takes if the two cambium layers — the thin living cylinder just under
the bark — stay pressed together, immobile, for the weeks it takes them to fuse. A
clip is what supplies that pressure. It is a genuine consumable: nurseries and
smallholders buy them by the hundred, they are lost in the field, and they are
priced per unit for a piece of moulded plastic that a printer can make.

The clip is parameterised on the two diameters that actually matter:
  * `scion_diameter_mm`     — the shoot going on.
  * `rootstock_diameter_mm` — the stem it goes onto.
A matched graft (both equal) is the easy case. The real world is mismatched, and the
jaw is therefore built around the LARGER of the two so it can close over the union
where the two stems overlap, while the spring gap is sized from the SMALLER so the
clip still grips when it reaches past the join.

Interchange: the jaw profile is the same C-jaw the published `plant-clip` uses for
trellis work — same stem-Ø series, same fraction-of-bore mouth convention — so a
grower stocking one is stocking the geometry of the other.

Modes are dispatched via `target_part`:
  * "clip"       — the spring clip itself: a C-jaw with a live-hinge back and a
                   flared mouth that walks onto the stem instead of splitting it.
  * "wrap_band"  — a slotted band for a union too big or too irregular for the jaw;
                   it takes a strip of grafting tape or a rubber band in tension.
  * "taper_gauge"— a go/no-go gauge for cutting a matched whip: the taper slot
                   tells you when the scion and rootstock cuts are the same angle,
                   which is what makes the cambium lines meet along their length.

Watertightness strategy:
  Every part is one blank with THROUGH cuts. The C-jaw is a cut annulus with a mouth
  slot that runs PAST the outside of the blank, so it is a real opening and never a
  sealed void. Both the bore and the mouth are clamped against the blank that must
  contain them: the blank is sized FROM the bore radius plus a full wall, and the
  mouth width is capped at `2*r - 0.8` so two retaining legs always survive. That
  cap is the difference between a clip and three loose arcs.

  The wrap band's tape slots are RADIAL windows bounded to their own flank, never
  boxes spanning the band — see build_wrap_band, where the first draft's spanning
  cut is recorded as a found-and-fixed defect.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "clip"))
taper_style = str(PARAM(lambda: taper_style, "whip"))   # whip | cleft | saddle

scion_diameter_mm = float(PARAM(lambda: scion_diameter_mm, 8.0))
rootstock_diameter_mm = float(PARAM(lambda: rootstock_diameter_mm, 10.0))
clip_wall = float(PARAM(lambda: clip_wall, 2.2))        # jaw wall thickness (mm)
spring_gap = float(PARAM(lambda: spring_gap, 0.55))     # mouth opening as fraction of bore Ø
clip_length_mm = float(PARAM(lambda: clip_length_mm, 22.0))  # jaw length along the stem

# Clamp so extreme UI values still build watertight.
scion_diameter_mm = max(3.0, min(scion_diameter_mm, 25.0))
rootstock_diameter_mm = max(3.0, min(rootstock_diameter_mm, 30.0))
clip_wall = max(1.2, min(clip_wall, 5.0))
spring_gap = max(0.25, min(spring_gap, 0.85))
clip_length_mm = max(8.0, min(clip_length_mm, 60.0))


# ── Derived graft geometry ───────────────────────────────────────────────────
def union_dia():
    """The diameter the jaw must actually close over.

    A graft union is not a clean cylinder: where the scion lies against the
    rootstock the pair is wider than either alone. Building the jaw around the
    larger stem plus a share of the smaller is the honest approximation, and it is
    why a clip sized only to the scion pops off a mismatched union."""
    big = max(scion_diameter_mm, rootstock_diameter_mm)
    small = min(scion_diameter_mm, rootstock_diameter_mm)
    return big + small * 0.25


def mismatch_ratio():
    """How unequal the pair is; 1.0 is a matched graft."""
    big = max(scion_diameter_mm, rootstock_diameter_mm)
    small = min(scion_diameter_mm, rootstock_diameter_mm)
    return big / small


# ── Part builders ─────────────────────────────────────────────────────────────
def build_clip():
    """The spring clip: a C-jaw whose mouth is a fraction of the bore.

    The blank is derived FROM the bore — outer radius is bore plus a full wall — so
    no cut can reach an edge at any parameter combination. The mouth is capped at
    `2*bore_r - 0.8` so two legs always survive; without that cap a wide spring_gap
    on a small bore severs the C into loose arcs that still tessellate but are not
    one body."""
    bore_r = union_dia() / 2.0
    out_r = bore_r + clip_wall
    length = clip_length_mm

    body = cq.Workplane("XY").circle(out_r).extrude(length)

    # Bore, opened past both faces so it can never be a blind pocket.
    bore = (
        cq.Workplane("XY").workplane(offset=-1.0)
        .circle(bore_r).extrude(length + 2.0)
    )
    body = body.cut(bore)

    # Mouth slot: runs PAST the outside of the blank in +X, so it is a real opening.
    reach = out_r * 3.0 + 20.0
    mouth_w = spring_gap * 2.0 * bore_r
    mouth_w = max(1.2, min(mouth_w, 2.0 * bore_r - 0.8))
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(reach / 2.0, 0.0, -1.0))
        .box(reach, mouth_w, length + 2.0, centered=(True, True, False))
    )
    body = body.cut(slot)

    # Flared lead-in lips at the mouth, so the clip WALKS onto a stem instead of
    # having to be forced over it — forcing is what tears bark off a soft scion and
    # kills the graft before it starts. Built as two wedge cuts, each running past
    # the outside; a fillet on the mouth edges here would be an OCC coin-flip.
    # Capped against the leg it lands on as well as the bore: at a wide mouth the
    # surviving leg is short, and a flare wider than it removes the leg outright.
    leg_y = max(0.0, bore_r - mouth_w / 2.0)
    flare = min(clip_wall * 1.6, bore_r * 0.7, max(0.0, leg_y * 0.6))
    if flare >= 0.4:
        for sign in (1.0, -1.0):
            y0 = sign * (mouth_w / 2.0)
            wedge = (
                cq.Workplane("XY")
                .polyline([
                    (out_r - flare * 0.2, y0),
                    (out_r + reach, y0),
                    (out_r + reach, y0 + sign * (flare + reach * 0.25)),
                    (out_r - flare * 0.2, y0 + sign * flare),
                ])
                .close()
                .extrude(length + 2.0)
                .translate((0, 0, -1.0))
            )
            try:
                body = body.cut(wedge)
            except Exception:
                pass

    # Live-hinge thinning at the back (opposite the mouth) so the C springs there
    # rather than cracking at a random point.
    #
    # The groove is measured INWARD FROM THE OUTER SURFACE and its depth is a
    # fraction of the wall, so a stated ligament always survives. The first draft
    # sized the cut box independently of the wall and merely asserted in a comment
    # that it was "capped well under the wall" — at a 30 mm rootstock with a 1.2 mm
    # wall the groove ran from x = -17.47 to -16.39 while the wall occupied only
    # -17.2 to -16.0, so it cut clean through and the clip shattered into 23 loose
    # pieces. A comment is not a clamp.
    hinge_lig = max(0.6, clip_wall * 0.5)               # material that must remain
    hinge_d = min(clip_wall - hinge_lig, 1.2)
    if hinge_d >= 0.25:
        # Cut box spans x in [-(out_r + 1.0), -(out_r - hinge_d)]: it starts safely
        # outside the part and stops `hinge_lig` short of the bore.
        x_lo = -(out_r + 1.0)
        x_hi = -(out_r - hinge_d)
        groove = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector((x_lo + x_hi) / 2.0, 0.0, -1.0))
            .box(x_hi - x_lo, max(1.2, clip_wall * 1.4), length + 2.0, centered=(True, True, False))
        )
        try:
            body = body.cut(groove)
        except Exception:
            pass

    # Break the bore's top and bottom rims so the clip does not score bark as it is
    # slid onto a soft green stem.
    #
    # This is a CUT, not a fillet, and the choice is load-bearing. A blend was tried
    # first, both as `edges("%CIRCLE")` and narrowed to `faces(">Z"|"<Z")`. Neither
    # selector means "the rims": by this point the solid's circular edges include
    # every arc where the mouth slot, the flare wedges and the hinge groove meet the
    # bore, and those arcs land on the end faces too. OCC does not refuse to blend
    # them — at a 30 mm rootstock the filleted result came back non-watertight and
    # split into 13 pieces at 2.2 mm wall, 39 at 1.2 mm, WITHOUT raising, so the
    # surrounding try/except never fired. Step-by-step assessment confirmed the
    # solid was sound (watertight, one body) immediately before the blend and
    # destroyed immediately after it.
    #
    # Two cut cones do the same job with no selector and no kernel gamble.
    cham = min(0.6, clip_wall * 0.3, hinge_lig * 0.4, length * 0.15)
    if cham >= 0.15:
        for z0, direction in ((length - cham, 1.0), (0.0, -1.0)):
            cone = (
                cq.Workplane("XY")
                .workplane(offset=z0 if direction > 0 else cham)
                .circle(bore_r)
                .workplane(offset=cham * direction)
                .circle(bore_r + cham)
                .loft()
            )
            try:
                body = body.cut(cone)
            except Exception:
                pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_wrap_band():
    """A slotted band for a union the jaw cannot span — a big cleft graft, or a
    healed-over stem that is no longer round. It carries grafting tape or a rubber
    band in tension rather than supplying spring force itself."""
    bore_r = union_dia() / 2.0
    out_r = bore_r + clip_wall
    height = max(6.0, min(clip_length_mm * 0.55, 26.0))

    body = cq.Workplane("XY").circle(out_r).extrude(height)
    bore = (
        cq.Workplane("XY").workplane(offset=-1.0)
        .circle(bore_r).extrude(height + 2.0)
    )
    body = body.cut(bore)

    # Open it to +X so it can be placed on a stem already in the ground.
    reach = out_r * 3.0 + 20.0
    mouth_w = max(1.2, min(bore_r * 0.9, 2.0 * bore_r - 0.8))
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(reach / 2.0, 0.0, -1.0))
        .box(reach, mouth_w, height + 2.0, centered=(True, True, False))
    )
    body = body.cut(slot)

    # Tape slots through the wall on both flanks: a band threads them and is drawn
    # tight. Each slot is a RADIAL through-cut of the wall only — bounded in X to a
    # short window around its own flank — and its height is capped so a stated
    # ligament of material survives above and below it.
    #
    # The first draft cut these as a box spanning `out_r * 4` in X, which is not a
    # slot at all: it slices straight across the band and takes the far wall with
    # it. At minimum wall that left a zero-thickness ligament and the part came back
    # non-watertight while still reading as one body — so body_count alone did not
    # catch it. The window is now sized from the wall it must not exceed.
    lig = max(1.0, height * 0.22)                       # material kept above and below
    slot_h = max(1.2, min(height - 2.0 * lig, height * 0.32))
    slot_x = max(1.2, min(clip_wall * 0.9, 3.0))        # slot width along the band
    if slot_h >= 1.0:
        for sign in (1.0, -1.0):
            cut = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0.0, sign * (bore_r + clip_wall / 2.0),
                                              (height - slot_h) / 2.0))
                .box(slot_x, clip_wall * 4.0, slot_h, centered=(True, True, False))
            )
            try:
                body = body.cut(cut)
            except Exception:
                pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_taper_gauge():
    """A go/no-go gauge for cutting a matched whip.

    A whip graft only takes if the scion's cut face and the rootstock's cut face are
    the SAME angle — otherwise the cambium lines cross instead of running together
    and only a point of the join is live. The gauge is a wedge slot of the declared
    angle: lay the cut against it, and a cut that beds flat is right."""
    styles = {
        # Long shallow cut: maximum cambium contact, the classic whip-and-tongue.
        "whip": 20.0,
        # Steeper, for splitting a rootstock and inserting a wedged scion.
        "cleft": 35.0,
        # Shallower still, for a saddle over a matched stem.
        "saddle": 14.0,
    }
    angle = styles.get(taper_style, 20.0)

    big = max(scion_diameter_mm, rootstock_diameter_mm)
    plate_t = max(3.0, clip_wall * 1.8)
    # Slot must be long enough to bed the whole cut face: a cut at `angle` degrees
    # across a stem of diameter `big` has face length big / sin(angle).
    face_len = big / max(0.2, math.sin(math.radians(angle)))
    slot_len = min(face_len * 1.15, 120.0)

    width = big * 2.4 + 12.0
    length = slot_len + 16.0

    body = cq.Workplane("XY").box(length, width, plate_t, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(4.0, width * 0.15, length * 0.1))
    except Exception:
        pass

    # The reference wedge: a triangular trough of the declared angle, cut THROUGH
    # the plate's side so it is an open channel rather than a pocket.
    depth = min(plate_t * 0.65, big * 0.6)
    half_open = depth / max(0.2, math.tan(math.radians(angle)))
    half_open = min(half_open, width * 0.4)
    wedge = (
        cq.Workplane("XZ")
        .polyline([
            (-half_open, plate_t + 0.5),
            (half_open, plate_t + 0.5),
            (0.0, plate_t - depth),
        ])
        .close()
        .extrude(length * 2.0, both=True)
    )
    try:
        body = body.cut(wedge)
    except Exception:
        pass

    # Two round go/no-go bores: one at each stem diameter, so the gauge also sizes
    # the pair before you cut. Through-cut, opened past both faces.
    for (sign, dia) in ((-1.0, scion_diameter_mm), (1.0, rootstock_diameter_mm)):
        r = dia / 2.0
        x = sign * (length * 0.5 - r - 5.0)
        y = width * 0.5 - r - 3.0
        # Keep the bore inside the blank with a full wall, whatever the diameters.
        if r + 2.0 > width * 0.5 or r * 2.0 + 10.0 > length * 0.5:
            continue
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, -1.0))
            .circle(r).extrude(plate_t + 2.0)
        )
        try:
            body = body.cut(bore)
        except Exception:
            pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "clip": build_clip,
    "wrap_band": build_wrap_band,
    "taper_gauge": build_taper_gauge,
}

result = _dispatch.get(target_part, build_clip)()
