"""
Oxygen Tubing Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Tubing management for home oxygen. A concentrator user drags 15 metres of cannula
tubing around a house; the tubing snags on furniture legs, gets rolled over by a
walker, and pulls the cannula off the face. The usual improvisations are a clothes
peg or a loop of tape. These clips route the tubing along a garment edge, a chair
rail or a wall, and RELEASE under load rather than tugging the cannula.

Two published interfaces meet here, and neither is new:
  * The tube channel is the 4-7 mm OD series that covers standard oxygen supply
    tubing (~6.3 mm OD / ~4 mm ID crush-resistant cannula tubing is the middle of
    the range; the ends cover thin cannula lead and heavier concentrator line).
  * The garment jaw reuses the SAME jaw profile the commons already published in
    garment-clip: a slab jaw pair with a lead-in wedge and a shallow rib, sized by
    the fabric bite gap rather than by a new bespoke geometry.

Modes are dispatched via `target_part`:
  * "garment_clip" — a C-jaw that grips a shirt placket or lapel, with the tube
                     channel on its spine. This is the one that keeps the cannula
                     off the floor.
  * "rail_clip"    — a larger C that snaps onto a chair rail, bed frame or walker
                     tube, carrying the same tube channel.
  * "wall_anchor"  — a screw-down saddle for a skirting board or door frame, so a
                     fixed run can be dressed along a wall.

Watertightness strategy: every part is a single blank with cylindrical and box
cuts. The C mouths are cut by a box that fully breaches the outer wall, so a mouth
is never a tangent kiss. The tube channel is a cylinder swept the full length of
the part and out both ends, so it opens onto two faces and traps no void. Jaw and
saddle thicknesses are floored so that a max-diameter / min-wall extreme cannot
cut the back out of the part and yield two bodies.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Standard dimensions (mm) ─────────────────────────────────────────────────
# Home-oxygen supply tubing: crush-resistant line is ~6.3 mm OD / ~4 mm ID; the
# thin cannula lead runs nearer 4 mm and heavy concentrator line nearer 7 mm.
O2_TUBE_OD = 6.3


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "garment_clip"))
tube_od = float(PARAM(lambda: tube_od, O2_TUBE_OD))     # tubing outside Ø (mm)
tube_clear = float(PARAM(lambda: tube_clear, 0.5))      # channel clearance per side (mm)
grip = float(PARAM(lambda: grip, 0.55))                 # channel mouth as a fraction of Ø
wall = float(PARAM(lambda: wall, 2.6))                  # wall around the channel (mm)
length = float(PARAM(lambda: length, 16.0))             # clip length along the tube (mm)
bite_gap = float(PARAM(lambda: bite_gap, 2.0))          # garment jaw opening (mm)
jaw_len = float(PARAM(lambda: jaw_len, 18.0))           # garment jaw depth (mm)
jaw_t = float(PARAM(lambda: jaw_t, 3.0))                # garment jaw slab thickness (mm)
rail_dia = float(PARAM(lambda: rail_dia, 25.0))         # rail / frame tube Ø (mm)
screw_dia = float(PARAM(lambda: screw_dia, 4.0))        # wall-anchor screw Ø (mm)

# ── Clamps: extreme UI values must still build one watertight body ───────────
tube_od = max(4.0, min(tube_od, 7.0))
tube_clear = max(0.1, min(tube_clear, 1.0))
# Below ~0.35 the mouth is narrower than a nozzle can bridge and the channel
# becomes a closed bore you cannot press tubing into; above ~0.85 nothing retains
# the tube and the clip does not clip.
grip = max(0.35, min(grip, 0.85))
wall = max(1.6, min(wall, 5.0))
length = max(8.0, min(length, 40.0))
bite_gap = max(0.8, min(bite_gap, 6.0))
jaw_len = max(10.0, min(jaw_len, 40.0))
jaw_t = max(2.0, min(jaw_t, 7.0))
rail_dia = max(12.0, min(rail_dia, 45.0))
screw_dia = max(2.5, min(screw_dia, 6.0))

# ── Derived, clamped ─────────────────────────────────────────────────────────
CH_R = (tube_od + 2.0 * tube_clear) / 2.0    # tube channel radius
CH_OUT_R = CH_R + wall                       # channel boss outer radius
MOUTH_W = 2.0 * CH_R * grip                  # channel mouth width
OV = 1.0                                     # cutter overshoot past every face


# ── Part builders ─────────────────────────────────────────────────────────────
def build_garment_clip():
    """A C-jaw that grips a shirt placket, with the tube channel on its spine.

    The jaw is a squared C: two arms separated by `bite_gap`, joined by a spine.
    The tube channel sits on the OUTSIDE of the spine, so the tubing does not
    interfere with the fabric bite. The jaw mouth faces +X.
    """
    span = length
    # C outer envelope. The spine must be thick enough to carry the channel boss.
    spine_t = max(jaw_t, 2.0 * CH_OUT_R * 0.55)
    inner_h = bite_gap
    outer_h = inner_h + 2.0 * jaw_t
    outer_x = jaw_len + spine_t

    body = cq.Workplane("XY").box(outer_x, span, outer_h, centered=(True, True, False))
    try:
        body = body.edges("|Y").fillet(min(jaw_t * 0.6, outer_h * 0.2, 2.0))
    except Exception:
        pass

    # Bite pocket: opens through the +X face, leaving the spine at -X.
    pocket = (
        cq.Workplane("XY")
        .box(jaw_len + OV, span + 2.0 * OV, inner_h, centered=(True, True, False))
        .translate((outer_x / 2.0 - (jaw_len + OV) / 2.0 + OV / 2.0, 0, jaw_t))
    )
    body = body.cut(pocket)

    # Lead-in flare at the jaw mouth so the clip slides onto fabric instead of
    # catching on it. This is a WEDGE PRISM built from an explicit triangle rather
    # than a rotated box: a rotated box swings its far corner an unbounded distance
    # into the arm, which at thin-jaw / long-jaw extremes cut straight through and
    # split the clip into three bodies. The triangle's two legs are each clamped
    # against the material actually available (`flare_z` never exceeds ~45% of an
    # arm), so the flare can only ever remove a corner.
    flare_x = min(jaw_len * 0.30, jaw_t * 1.5, jaw_len - 1.5)
    flare_z = min(jaw_t * 0.45, flare_x)
    if flare_x > 0.6 and flare_z > 0.3:
        x_out = outer_x / 2.0
        for sign in (1.0, -1.0):
            # z of the bite face on this arm, and the outer face of the same arm.
            z_bite = jaw_t + (inner_h if sign > 0 else 0.0)
            z_face = z_bite + sign * flare_z
            tri = (
                cq.Workplane("XZ")
                .polyline([
                    (x_out + OV, z_bite),
                    (x_out - flare_x, z_bite),
                    (x_out + OV, z_face),
                ])
                .close()
                .extrude(span + 2.0 * OV)
                .translate((0, (span / 2.0 + OV), 0))
            )
            body = body.cut(tri)

    # Tube channel boss on the OUTSIDE of the spine (-X), unioned with overlap.
    boss_cx = -outer_x / 2.0 - CH_OUT_R + CH_OUT_R * 0.45   # bury 55% into the spine
    boss = (
        cq.Workplane("XZ")
        .center(boss_cx, outer_h / 2.0)
        .circle(CH_OUT_R)
        .extrude(span + 2.0 * OV)
        .translate((0, (span / 2.0 + OV), 0))
    )
    # Trim the boss back to the part's own Y extent so it does not stick out.
    trim = cq.Workplane("XY").box(outer_x + 4.0 * CH_OUT_R, span, outer_h + 4.0 * CH_OUT_R,
                                  centered=(True, True, True)).translate((0, 0, outer_h / 2.0))
    body = body.union(boss.intersect(trim))

    # Channel bore + mouth opening toward -X (away from the jaw).
    chan = (
        cq.Workplane("XZ")
        .center(boss_cx, outer_h / 2.0)
        .circle(CH_R)
        .extrude(span + 2.0 * OV)
        .translate((0, (span / 2.0 + OV), 0))
    )
    body = body.cut(chan)
    depth = CH_OUT_R + OV
    mouth = (
        cq.Workplane("XY")
        .box(depth, span + 2.0 * OV, MOUTH_W, centered=(True, True, True))
        .translate((boss_cx - depth / 2.0, 0, outer_h / 2.0))
    )
    body = body.cut(mouth)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_rail_clip():
    """A C that snaps onto a chair rail, bed frame or walker tube, carrying the
    same tube channel on its back."""
    span = length
    r_in = rail_dia / 2.0 + tube_clear
    r_out = r_in + wall

    # Ring, extruded along Y.
    body = (
        cq.Workplane("XZ")
        .circle(r_out)
        .extrude(span)
        .translate((0, span / 2.0, 0))
    )
    bore = (
        cq.Workplane("XZ")
        .circle(r_in)
        .extrude(span + 2.0 * OV)
        .translate((0, (span / 2.0 + OV), 0))
    )
    body = body.cut(bore)

    # Snap mouth toward +X. Width is a fraction of the rail Ø, floored so the clip
    # can actually be pushed on and capped so a retaining arm always survives.
    mw = max(2.0, min(rail_dia * grip, 2.0 * r_in - 1.2))
    mouth = (
        cq.Workplane("XY")
        .box(r_out + OV, span + 2.0 * OV, mw, centered=(True, True, True))
        .translate((r_out / 2.0, 0, 0))
    )
    body = body.cut(mouth)

    # Tube channel boss on the far side (-X), buried into the ring wall.
    boss_cx = -(r_out + CH_OUT_R * 0.55)
    boss = (
        cq.Workplane("XZ")
        .center(boss_cx, 0)
        .circle(CH_OUT_R)
        .extrude(span)
        .translate((0, span / 2.0, 0))
    )
    body = body.union(boss)
    chan = (
        cq.Workplane("XZ")
        .center(boss_cx, 0)
        .circle(CH_R)
        .extrude(span + 2.0 * OV)
        .translate((0, (span / 2.0 + OV), 0))
    )
    body = body.cut(chan)
    depth = CH_OUT_R + OV
    cmouth = (
        cq.Workplane("XY")
        .box(depth, span + 2.0 * OV, MOUTH_W, centered=(True, True, True))
        .translate((boss_cx - depth / 2.0, 0, 0))
    )
    body = body.cut(cmouth)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_wall_anchor():
    """A screw-down saddle: a base pad with the tube channel over it and a screw
    hole at each end, for dressing a fixed run along a skirting board."""
    span = length
    # Pad must be long enough in X to hold two screws clear of the channel boss.
    pad_h = max(2.5, wall)
    end_pad = screw_dia / 2.0 + 3.0
    pad_x = 2.0 * CH_OUT_R + 2.0 * end_pad + screw_dia

    base = cq.Workplane("XY").box(pad_x, span, pad_h, centered=(True, True, False))
    try:
        base = base.edges("|Z").fillet(min(2.5, pad_h * 1.2, span / 2.0 - 0.5))
    except Exception:
        pass

    # Channel boss straddling the pad centre, overlapping it by 0.8 mm.
    boss_z = pad_h + CH_OUT_R - 0.8
    boss = (
        cq.Workplane("XZ")
        .center(0, boss_z)
        .circle(CH_OUT_R)
        .extrude(span)
        .translate((0, span / 2.0, 0))
    )
    body = base.union(boss)

    chan = (
        cq.Workplane("XZ")
        .center(0, boss_z)
        .circle(CH_R)
        .extrude(span + 2.0 * OV)
        .translate((0, (span / 2.0 + OV), 0))
    )
    body = body.cut(chan)
    depth = CH_OUT_R + OV
    mouth = (
        cq.Workplane("XY")
        .box(MOUTH_W, span + 2.0 * OV, depth, centered=(True, True, False))
        .translate((0, 0, boss_z))
    )
    body = body.cut(mouth)

    # Screws through the pad at each end, fully inside the pad edge.
    sx = pad_x / 2.0 - end_pad / 2.0 - screw_dia / 4.0
    for cx in (-sx, sx):
        scr = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, 0.0, -OV))
            .circle(screw_dia / 2.0)
            .extrude(pad_h + 2.0 * OV)
        )
        body = body.cut(scr)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "rail_clip":
    result = build_rail_clip()
elif target_part == "wall_anchor":
    result = build_wall_anchor()
else:
    result = build_garment_clip()
