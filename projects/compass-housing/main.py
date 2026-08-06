"""
Compass / Whistle Housing — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Housings and EDC bodies for button compasses and emergency whistles. Button
compass capsules are sold as sealed liquid-filled buttons in two common
diameters — 20 mm and 25 mm — that need a bezel to carry them. This cartridge
sockets that capsule into a clip-on bezel, a whistle body, or an EDC storage pod.

  - compass_housing : a bezel that press-fits a button-compass capsule (blind bore
                      from the top face, open to that face → vents) on a paddle
                      with a lanyard hole and a belt/pack clip slot.
  - whistle_body    : a flat pealess emergency-whistle body — a mouthpiece air
                      inlet channel that vents across a sound window (open air
                      passages → watertight), plus a lanyard hole.
  - edc_capsule     : a pocket pod with a compass socket in the lid and a deep
                      storage bore (tinder, matches, pills), both open to a face.

Real dimensions:
  - button compass capsule diameters: 20 mm and 25 mm (default cap_d = 25 mm);
    the socket is bored `cap_d + fit` so the sealed capsule press-fits.

Watertight strategy:
  Every part is ONE solid. The capsule socket and storage bore are blind bores
  drilled from an exterior FACE (open to that face → they vent, not trapped
  voids). The whistle's air channel enters at the mouthpiece face and exits at
  the sound window (open passage → watertight). The clip slot and lanyard holes
  are through-cuts. Overlaps are unioned; fillets clean the blank BEFORE feature
  cuts, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  `cq` and `math` are pre-injected globals; manifest parameters arrive as bare
  globals (e.g. `target_part`). Read them via PARAM(lambda: name, default).
  Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else default. `except Exception`
    catches the NameError the sandbox raises for an unbound parameter name."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "compass_housing"))
# "compass_housing" | "whistle_body" | "edc_capsule"

cap_d = float(PARAM(lambda: cap_d, 25.0))         # button compass capsule diameter
cap_depth = float(PARAM(lambda: cap_depth, 9.0))  # capsule seat depth (mm)
fit = float(PARAM(lambda: fit, 0.3))              # capsule press-fit clearance (mm)
wall = float(PARAM(lambda: wall, 3.0))            # wall / floor thickness (mm)
lanyard_d = float(PARAM(lambda: lanyard_d, 5.0))  # lanyard hole (mm)
clip_w = float(PARAM(lambda: clip_w, 26.0))       # belt/pack clip mouth width (mm)
store_depth = float(PARAM(lambda: store_depth, 26.0))  # EDC storage bore depth (mm)

# Clamp to sane ranges so extreme UI values never crash the kernel.
cap_d = max(14.0, min(cap_d, 40.0))
cap_depth = max(5.0, min(cap_depth, 16.0))
fit = max(0.1, min(fit, 0.8))
wall = max(2.0, min(wall, 6.0))
lanyard_d = max(3.0, min(lanyard_d, 8.0))
clip_w = max(18.0, min(clip_w, 60.0))
store_depth = max(12.0, min(store_depth, 60.0))

bore_d = cap_d + fit
bezel_d = bore_d + 2.0 * wall                     # bezel outer diameter


# ── Shared helpers ───────────────────────────────────────────────────────────
def _top_bore(diameter, depth, z_top):
    """Cutting cylinder for a blind bore DOWN from the top face at z_top (opens to
    that exterior face → vents). Over-cuts 0.5 past the face; leaves a solid
    floor `depth` below."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_top - depth))
        .circle(diameter / 2.0)
        .extrude(depth + 0.5)
    )


def _through_z(diameter, thickness, cx=0.0, cy=0.0):
    """A through-hole in Z (vents top+bottom)."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, -0.5))
        .circle(diameter / 2.0)
        .extrude(thickness + 1.0)
    )


def _fillet_z(solid, r):
    try:
        return solid.edges("|Z").fillet(r)
    except Exception:
        return solid


# ── Part builders ────────────────────────────────────────────────────────────
def build_compass_housing():
    """A round bezel that press-fits the compass capsule (blind bore from the top
    face) with a lanyard hole and a flat spring belt-clip. The clip is a solid U:
    a back spine unioned to a return lip, forming a channel open on one side that
    springs over a belt, strap or pack edge — built from solid bars (no thin
    annulus), so it is unconditionally manifold. One solid."""
    bezel_h = cap_depth + wall
    bezel = (
        cq.Workplane("XY")
        .circle(bezel_d / 2.0)
        .extrude(bezel_h)
    )
    try:
        bezel = bezel.edges("%Circle").fillet(min(1.5, wall * 0.4))
    except Exception:
        pass
    body = bezel

    # Flat spring clip on the −Y side of the bezel. Geometry (in Y/Z):
    #   spine   : a vertical plate rising from the bezel top, flush at −Y edge.
    #   lip     : a horizontal plate returning back toward the bezel, forming a
    #             gap `gap` above the bezel top that grips an edge.
    gap = max(2.5, wall + 1.0)                 # jaw opening the clip grips
    clip_t = wall                              # clip material thickness
    clip_len = min(clip_w, bezel_d) * 0.9      # clip width in X
    spine_h = gap + clip_t + 4.0
    y_edge = -bezel_d / 2.0 + 1.0              # overlap into the bezel by 1 mm

    spine = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, y_edge, 0))
        .box(clip_len, clip_t, bezel_h + spine_h, centered=(True, True, False))
    )
    body = body.union(spine)
    # return lip at the top of the spine, reaching back over the bezel (+Y).
    lip_len = bezel_d * 0.5
    lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, y_edge + lip_len / 2.0,
                                      bezel_h + spine_h - clip_t))
        .box(clip_len, lip_len, clip_t, centered=(True, True, False))
    )
    body = body.union(lip)

    # Capsule socket (blind bore from the top of the bezel → vents).
    body = body.cut(_top_bore(bore_d, cap_depth, bezel_h))
    # Lanyard hole through the bezel rim on the +Y side (through Z, vents).
    body = body.cut(_through_z(lanyard_d, bezel_h, cx=0.0, cy=bezel_d / 2.0 - wall * 0.8))
    return body


def build_whistle_body():
    """A flat pealess emergency whistle. A solid block with a mouthpiece air inlet
    bored in from the −Y face; the air jet crosses a sound window (a slot open to
    the top face) and exits — the split airstream over the window edge makes the
    tone. All air passages open to exterior faces, so the mesh is watertight.
    A lanyard hole passes through."""
    body_w = max(18.0, cap_d * 0.8)
    body_len = 58.0
    body_h = 14.0
    body = (
        cq.Workplane("XY")
        .box(body_w, body_len, body_h, centered=(True, True, False))
    )
    body = _fillet_z(body, min(5.0, body_w * 0.25))
    try:
        body = body.edges("|X").fillet(min(2.5, body_h * 0.2))
    except Exception:
        pass

    # Mouthpiece air inlet: a flattened channel bored from the −Y end face along
    # +Y into the body (opens to that face → vents). Modeled as a slot solid.
    chan_w = body_w * 0.5
    chan_h = 3.2
    chan_len = body_len * 0.55
    inlet = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, body_h * 0.42, -body_len / 2.0 - 0.5))
        .slot2D(chan_w, chan_h, angle=0)
        .extrude(chan_len + 0.5)
    )
    body = body.cut(inlet)

    # Sound window: a rectangular opening from the TOP face down into the channel
    # near the far end of the inlet (this is the whistle mouth). It intersects the
    # inlet channel, so air vents up and out — one connected open passage.
    win_y = -body_len / 2.0 + chan_len - 4.0
    window = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, win_y, body_h * 0.42))
        .box(chan_w * 0.85, 7.0, body_h, centered=(True, True, False))
    )
    body = body.cut(window)

    # Lanyard hole through the far (+Y) solid end.
    body = body.cut(_through_z(lanyard_d, body_h, cx=0.0, cy=body_len / 2.0 - 6.0))
    return body


def build_edc_capsule():
    """A pocket EDC pod: a round body with the compass socket recessed in the top
    (blind bore from the top face) and a deep storage bore below it, opening to
    the BOTTOM face (screw-cap or friction-plug your own lid). Both bores open to
    a face → vented. A cross lanyard hole passes through the top rim."""
    body_d = bezel_d + 2.0
    body_h = wall + store_depth + wall + cap_depth
    body = (
        cq.Workplane("XY")
        .circle(body_d / 2.0)
        .extrude(body_h)
    )
    try:
        body = body.edges("%Circle").fillet(min(2.0, wall * 0.5))
    except Exception:
        pass

    # Compass socket recessed into the TOP face (vents up).
    body = body.cut(_top_bore(bore_d, cap_depth, body_h))

    # Storage bore from the BOTTOM face upward (opens to bottom face → vents),
    # stopping below the compass socket floor.
    store = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle((body_d - 2.0 * wall) / 2.0)
        .extrude(store_depth + 0.5)
    )
    body = body.cut(store)

    # Cross lanyard hole through the upper rim (above the storage bore).
    lz = body_h - cap_depth - wall * 0.5
    lan = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, lz, 0))
        .circle(lanyard_d / 2.0)
        .extrude(body_d / 2.0 + 1.0, both=True)
    )
    body = body.cut(lan)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "whistle_body":
    result = build_whistle_body()
elif target_part == "edc_capsule":
    result = build_edc_capsule()
else:
    result = build_compass_housing()
