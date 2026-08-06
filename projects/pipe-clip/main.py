"""
Pipe Insulation Clip / Standoff — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Pipe supports for copper and PEX runs: a C-shaped snap clip that grips the pipe, a
saddle standoff that holds the pipe off the wall on a screw post, and a two-hole
saddle band clamp. Bores are sized to real copper / PEX outside diameters so the
grip matches the pipe you actually have.

Real dimensions (US tube ODs, expressed in mm):
  - Copper 1/2" (type L/M) OD = 0.625" = 15.875 mm.
  - Copper 3/4" OD = 0.875" = 22.225 mm.
  - Copper 1"  OD = 1.125" = 28.575 mm.
  - PEX 1/2" OD = 0.625" = 15.875 mm; PEX 3/4" OD = 0.875" = 22.225 mm.
  A snap clip's mouth is opened to a chord narrower than the diameter so the pipe
  clicks in and is retained; a saddle cradle is a clean half-round.

Watertightness strategy (open-jaw clips as closed manifolds):
  Each clip is a SOLID body from which the pipe bore is cut. A snap clip's mouth is
  cut with a rectangular slot that OPENS the bore to the outside — the bore is never
  a sealed internal void, and removing the mouth chord leaves one connected solid
  (a C-section), not two pieces. Saddle cradles cut a half-round pocket that opens to
  the top face. The screw post / base is unioned to the cradle with real volumetric
  overlap (a co-located pillar on the shared plane), never a tangent kiss, so no
  severed body appears. Fillets are applied to the blank BEFORE the bore is cut.

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


# ── Pipe outside diameters (mm) ──────────────────────────────────────────────
PIPE_OD = {
    "cu_1/2": 15.875,
    "cu_3/4": 22.225,
    "cu_1": 28.575,
    "pex_1/2": 15.875,
    "pex_3/4": 22.225,
}


def pipe_od(name):
    """Pipe outside diameter (mm), defaulting to copper 1/2\"."""
    return PIPE_OD.get(name, PIPE_OD["cu_1/2"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "snap_clip"))
pipe = str(PARAM(lambda: pipe, "cu_1/2"))         # pipe spec key
clearance = float(PARAM(lambda: clearance, 0.3))  # bore slop over pipe OD (mm)
wall = float(PARAM(lambda: wall, 3.0))            # clip wall thickness (mm)
depth = float(PARAM(lambda: depth, 16.0))         # clip length along the pipe (mm)
standoff = float(PARAM(lambda: standoff, 18.0))   # how far the pipe stands off the wall (mm)
mouth = float(PARAM(lambda: mouth, 0.72))         # snap mouth opening as a fraction of OD

# Clamp so extreme UI values still build watertight.
clearance = max(0.1, min(clearance, 0.7))
wall = max(2.0, min(wall, 6.0))
depth = max(8.0, min(depth, 40.0))
standoff = max(6.0, min(standoff, 50.0))
mouth = max(0.5, min(mouth, 0.9))


# ── Derived radii ────────────────────────────────────────────────────────────
def _radii():
    """Return (bore_r, out_r): pipe bore radius (OD + clearance) and clip outer radius."""
    bore_r = pipe_od(pipe) / 2.0 + clearance
    out_r = bore_r + wall
    return bore_r, out_r


# ── Part builders ─────────────────────────────────────────────────────────────
def build_snap_clip():
    """A C-shaped snap clip on a flat screw base. The ring grips the pipe; a mouth
    slot narrower than the diameter opens upward so the pipe clicks in. One solid:
    the ring OVERLAPS the base volumetrically, and the mouth is cut only in the upper
    ring so the C stays connected to the base at the bottom."""
    bore_r, out_r = _radii()
    base_w = 2.0 * out_r + 8.0
    base_t = wall + 1.0
    overlap = 1.5
    ring_z = out_r + base_t - overlap   # ring dips into the base -> volumetric bond

    # Base plate with two screw holes (no fillet: the |Y selector is unreliable on
    # this orientation and a crashed fillet aborts the whole build).
    base = cq.Workplane("XY").box(base_w, depth, base_t, centered=(True, True, False))
    for sx in (-1, 1):
        hole = (
            cq.Workplane("XY").workplane(offset=-1.0)
            .center(sx * (out_r + 2.5), 0).circle(2.4).extrude(base_t + 2.0)
        )
        base = base.cut(hole)

    # Ring (solid cylinder) sitting on/into the base, axis along Y.
    ring = (
        cq.Workplane("XZ").workplane(offset=-depth / 2.0)
        .center(0, ring_z).circle(out_r).extrude(depth)
    )
    body = base.union(ring)

    # Bore the pipe channel (axis Y).
    bore = (
        cq.Workplane("XZ").workplane(offset=-depth / 2.0 - 1.0)
        .center(0, ring_z).circle(bore_r).extrude(depth + 2.0)
    )
    body = body.cut(bore)

    # Snap mouth: a slot narrower than the diameter, cut only through the UPPER ring
    # (from the very top down to just past the bore centre) so the C opens upward but
    # stays joined to the base below.
    mouth_w = 2.0 * bore_r * mouth
    slot_bottom = ring_z            # stop at the bore centre height
    slot_h = (ring_z + out_r + 2.0) - slot_bottom
    slot = (
        cq.Workplane("XY").workplane(offset=slot_bottom)
        .center(0, 0).rect(mouth_w, depth + 2.0).extrude(slot_h)
    )
    body = body.cut(slot)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_saddle_standoff():
    """A half-round saddle cradle raised on a screw post so the pipe stands off the
    wall. The cradle pocket opens to the top face; post fuses into the cradle base."""
    bore_r, out_r = _radii()
    post_w = 2.0 * out_r
    post_d = depth
    cradle_z = standoff + out_r

    # Post from the wall up to the cradle.
    post = cq.Workplane("XY").box(post_w, post_d, standoff + out_r, centered=(True, True, False))
    post = post.edges("|Y").fillet(min(4.0, out_r * 0.4))
    # Screw holes through the post base (into the wall).
    for sy in (-1, 1):
        hole = (
            cq.Workplane("YZ").workplane(offset=-post_w / 2.0 - 1.0)
            .center(sy * (post_d / 2.0 - 5.0), standoff * 0.5).circle(2.4).extrude(post_w + 2.0)
        )
        post = post.cut(hole)

    # Cradle: a solid block at the top, then a half-round pocket cut from above.
    cradle = (
        cq.Workplane("XY").workplane(offset=standoff)
        .box(post_w, post_d, out_r, centered=(True, True, False))
    )
    body = post.union(cradle)

    # Half-round pocket open to the top (cut a full cylinder centred at cradle_z, the
    # slot above it removes the top half -> an open cradle, no trapped void).
    bore = (
        cq.Workplane("XZ").workplane(offset=-post_d / 2.0 - 1.0)
        .center(0, cradle_z).circle(bore_r).extrude(post_d + 2.0)
    )
    body = body.cut(bore)
    # Remove everything above the cradle centre to open the pocket upward.
    top_cut = (
        cq.Workplane("XY").workplane(offset=cradle_z)
        .box(post_w + 4.0, post_d + 4.0, out_r + 4.0, centered=(True, True, False))
    )
    body = body.cut(top_cut)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_band_clamp():
    """A full-ring saddle band with two screw ears (a split-ring pipe clamp). The
    ring fully surrounds the pipe; ears extend to each side with screw holes."""
    bore_r, out_r = _radii()
    ear_w = 14.0
    ear_t = wall

    # Full ring, axis Y.
    ring = (
        cq.Workplane("XZ").workplane(offset=-depth / 2.0)
        .center(0, out_r).circle(out_r).extrude(depth)
    )
    ring = ring.cut(
        cq.Workplane("XZ").workplane(offset=-depth / 2.0 - 1.0)
        .center(0, out_r).circle(bore_r).extrude(depth + 2.0)
    )

    # Two flat ears at the ring's mid height, one each side, with screw holes.
    ears = None
    for sx in (-1, 1):
        ex = sx * (out_r + ear_w / 2.0 - 0.5)  # overlap the ring by 0.5 mm
        ear = (
            cq.Workplane("XY").workplane(offset=out_r - ear_t / 2.0)
            .center(ex, 0).box(ear_w, depth, ear_t, centered=(True, True, True))
        )
        hole = (
            cq.Workplane("XY").workplane(offset=out_r - ear_t / 2.0 - 2.0)
            .center(sx * (out_r + ear_w / 2.0), 0).circle(2.4).extrude(ear_t + 4.0)
        )
        ear = ear.cut(hole)
        ears = ear if ears is None else ears.union(ear)
    body = ring.union(ears)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "saddle_standoff":
    result = build_saddle_standoff()
elif target_part == "band_clamp":
    result = build_band_clamp()
else:
    result = build_snap_clip()
