"""
Conduit Clip / Spacer — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Snap clips and standoffs that hold electrical conduit to a surface. The cradle
diameter lands on the real outside diameter of EMT (or metric) conduit, and the
snap mouth opens just under the OD so the conduit clicks in and stays put. Pick
the trade size and the clip grabs the standard tube.

Modes are dispatched via `target_part`:
  * "snap_clip"     — a flat-backed C snap clip with two screw ears; press the
                      conduit into the open mouth.
  * "standoff_clip" — the same clip lifted on a standoff post/base so the conduit
                      is spaced off the wall (heat / clearance), one center screw.
  * "gang_clip"     — a rail carrying several snap cradles to route parallel runs.

Conduit outside diameters encoded (mm):
  EMT 1/2"=17.9  3/4"=23.4  1"=29.5      (US EMT trade sizes, actual OD)
  M16=16.0  M20=20.0  M25=25.0           (metric conduit nominal OD)

Watertightness: the C mouth is ONE rectangular slot cut from a solid ring (never
an arc-fan, which crashes OCCT clean()). Stacked bodies OVERLAP so unions are
volumetric, not tangent kisses.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `conduit_size`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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


# ── Conduit outside diameters (mm) ───────────────────────────────────────────
_CONDUIT = {
    "EMT12": 17.9,   # EMT 1/2"
    "EMT34": 23.4,   # EMT 3/4"
    "EMT1":  29.5,   # EMT 1"
    "M16":   16.0,
    "M20":   20.0,
    "M25":   25.0,
}


def conduit_od(name):
    k = str(name).strip().upper().replace(" ", "").replace('"', "").replace("/", "")
    aliases = {
        "EMT12": "EMT12", "EMT120": "EMT12", "12": "EMT12",
        "EMT34": "EMT34", "34": "EMT34",
        "EMT1": "EMT1", "1": "EMT1",
        "M16": "M16", "16": "M16",
        "M20": "M20", "20": "M20",
        "M25": "M25", "25": "M25",
    }
    key = aliases.get(k, "EMT12")
    return _CONDUIT[key]


# ── Parameters ───────────────────────────────────────────────────────────────
target_part  = str(PARAM(lambda: target_part, "snap_clip"))
conduit_size = str(PARAM(lambda: conduit_size, "EMT12"))   # EMT12|EMT34|EMT1|M16|M20|M25
clearance    = float(PARAM(lambda: clearance,  0.3))       # cradle fit clearance (radius, mm)
wall         = float(PARAM(lambda: wall,       2.6))       # clip wall thickness (mm)
width        = float(PARAM(lambda: width,     10.0))       # clip width along the conduit (mm)
mouth_frac   = float(PARAM(lambda: mouth_frac, 0.62))      # snap mouth opening as frac of OD
screw_dia    = float(PARAM(lambda: screw_dia,  4.0))       # mounting screw clearance Ø (mm)
standoff     = float(PARAM(lambda: standoff,   8.0))       # standoff height (standoff_clip)
gang_count   = int(PARAM(lambda: gang_count,   3))         # cradles on the gang rail

# Clamp to sane ranges so extreme UI values still build watertight.
clearance = max(0.0, min(clearance, 1.2))
wall = max(1.6, min(wall, 6.0))
width = max(5.0, min(width, 30.0))
mouth_frac = max(0.45, min(mouth_frac, 0.85))
screw_dia = max(2.0, min(screw_dia, 8.0))
standoff = max(2.0, min(standoff, 40.0))
gang_count = max(2, min(gang_count, 8))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _cradle_ring(cx, od):
    """A solid ring (annulus, extruded along Y = the conduit axis) centered at x=cx.
    Outer wall = OD/2 + clearance + wall; bore = OD/2 + clearance. Built from two
    concentric cylinders (a volumetric cut), not a revolve of a cut profile."""
    bore_r = od / 2.0 + clearance
    outer_r = bore_r + wall
    ring = (
        cq.Workplane("XZ").workplane(offset=width / 2.0)
        .center(cx, outer_r)               # lift so the ring sits on z=0 tangentially? no -> we lift by outer_r
        .circle(outer_r).extrude(width)
    )
    bore = (
        cq.Workplane("XZ").workplane(offset=width / 2.0 + 1.0)
        .center(cx, outer_r)
        .circle(bore_r).extrude(width + 2.0)
    )
    return ring.cut(bore), bore_r, outer_r


def _snap_mouth(cx, od, outer_r, z_top_extra=0.0):
    """A rectangular slot opening the top of the cradle so the conduit snaps in.
    Width = mouth_frac * OD (a little narrower than OD → it grips). ONE box cut."""
    mouth_w = mouth_frac * od
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, 0.0, outer_r * 1.6 + z_top_extra))
        .box(mouth_w, width + 2.0, outer_r * 1.4, centered=(True, True, True))
    )
    return slot


def _back_plate(cx_list, outer_r, plate_w, plate_len, thick):
    """A flat mounting back plate under the cradle(s). Overlaps the cradle by
    `ov` so the union is volumetric."""
    ov = 0.8
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(sum(cx_list) / len(cx_list), 0.0, thick / 2.0 - ov / 2.0))
        .box(plate_len, plate_w, thick + ov, centered=(True, True, True))
    )
    return plate


# ── Part builders ─────────────────────────────────────────────────────────────
def build_snap_clip():
    """Flat-backed C snap clip with two screw ears flanking the cradle."""
    od = conduit_od(conduit_size)
    cx = 0.0
    ring, bore_r, outer_r = _cradle_ring(cx, od)

    # Back plate (the flat face that meets the wall). The cradle sits on top of it.
    plate_thick = max(2.0, wall * 0.8)
    ear = max(6.0, screw_dia * 2.2)
    plate_len = 2.0 * outer_r + 2.0 * ear
    plate = _back_plate([cx], outer_r, width, plate_len, plate_thick)

    body = ring.union(plate)
    # Open the snap mouth (top).
    body = body.cut(_snap_mouth(cx, od, outer_r))

    # Two screw holes in the ears.
    for sx in (-(outer_r + ear / 2.0), (outer_r + ear / 2.0)):
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx, 0.0, -1.0))
            .circle(screw_dia / 2.0).extrude(plate_thick + 2.0)
        )
        body = body.cut(hole)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_standoff_clip():
    """Cradle lifted on a solid standoff base with one center screw counterbore,
    spacing the conduit off the wall for heat / clearance."""
    od = conduit_od(conduit_size)
    cx = 0.0
    bore_r = od / 2.0 + clearance
    outer_r = bore_r + wall

    # Base foot.
    base_thick = max(2.5, wall)
    foot = 2.0 * outer_r
    base = (
        cq.Workplane("XY")
        .box(foot, foot, base_thick, centered=(True, True, False))
    )
    try:
        base = base.edges("|Z").fillet(min(3.0, outer_r * 0.4))
    except Exception:
        pass

    # Standoff post: a solid pillar from the base up INTO the cradle. SOLID (not a
    # hollow post on a solid base -> no trapped void). Overlaps base AND ring by
    # `ov` on both ends so both unions are volumetric (never tangent kisses).
    ov = 0.8
    post_w = min(foot - 2.0, outer_r * 1.4)
    lift = base_thick + standoff              # ring bottom sits here
    post_h = standoff + 2.0 * ov              # base_thick-ov .. lift+ov
    post = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_thick - ov))
        .box(post_w, width + 2.0, post_h, centered=(True, True, False))
    )

    # Cradle sits atop the post.
    ring, _, _ = _cradle_ring(cx, od)
    ring = ring.translate((0, 0, lift))
    mouth = _snap_mouth(cx, od, outer_r).translate((0, 0, lift))

    body = base.union(post).union(ring)
    body = body.cut(mouth)

    # Center screw counterbore through the base + post (open to a face top and
    # bottom -> no sealed cavity).
    screw = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(screw_dia / 2.0).extrude(lift + 2.0)
    )
    cbore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(screw_dia)
        .extrude(base_thick + 1.0)
    )
    body = body.cut(screw).cut(cbore)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_gang_clip():
    """A rail carrying several snap cradles to route parallel conduit runs."""
    od = conduit_od(conduit_size)
    bore_r = od / 2.0 + clearance
    outer_r = bore_r + wall

    pitch = 2.0 * outer_r + max(4.0, wall * 2.0)
    xs = [(-(gang_count - 1) * pitch / 2.0) + i * pitch for i in range(gang_count)]

    plate_thick = max(2.5, wall * 0.8)
    end_pad = outer_r + 4.0
    plate_len = (gang_count - 1) * pitch + 2.0 * end_pad
    plate = _back_plate(xs, outer_r, width, plate_len, plate_thick)

    body = plate
    for cx in xs:
        ring, _, _ = _cradle_ring(cx, od)
        body = body.union(ring)
    # Open every mouth.
    for cx in xs:
        body = body.cut(_snap_mouth(cx, od, outer_r))

    # Screw holes at both ends of the rail.
    for sx in (xs[0] - end_pad / 2.0, xs[-1] + end_pad / 2.0):
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx, 0.0, -1.0))
            .circle(screw_dia / 2.0).extrude(plate_thick + 2.0)
        )
        body = body.cut(hole)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "snap_clip": build_snap_clip,
    "standoff_clip": build_standoff_clip,
    "gang_clip": build_gang_clip,
}

result = _dispatch.get(target_part, build_snap_clip)()
