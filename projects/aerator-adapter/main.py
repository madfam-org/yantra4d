"""
Faucet Aerator Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Adapters that bridge a standard faucet-aerator thread to something else: a garden/utility
hose barb, or the opposite aerator gender. The family shares the real aerator thread
standards — M22 x 1 (male, 22.0 mm) and M24 x 1 (female, 24.0 mm) — so every part mates
the companion `aerator-cache` cartridge and any real tap aerator.

Real dimensions (faucet aerator threads, in mm):
  - M22 x 1: common MALE aerator thread — 22.0 mm major diameter, 1.0 mm pitch.
  - M24 x 1: common FEMALE aerator thread — 24.0 mm major diameter, 1.0 mm pitch.
  Hose barb sized ~13 mm nominal for 1/2" ID vinyl tubing (adjustable).

Three DISTINCT modes:
  - hose_barb: a female aerator collar on top that screws onto a male tap spout, a
    reducing cone, and a barbed spout below to push vinyl hose onto. Water runs through.
  - gender_changer: a double-ended coupler — female aerator thread at one end, male
    aerator spigot at the other — to convert an M24 female tap to an M22 male fitting
    (or vice-versa). Through-bore for flow.
  - quick_cap: a knurled female cap with an internal aerator thread and a fine screen
    grid across a recessed shoulder — a printable aerator/filter cap.

Thread & watertightness strategy (from the bottle-thread / aerator-cache idiom):
  Threads are single-start helical ribs swept along a genuine `cq.Wire.makeHelix` built
  at the MEAN thread radius (real-radius helix keeps the sweep frame non-singular ->
  fast + watertight), then UNIONED into the wall as positive material with the root
  pushed `overlap` into the wall (volumetric, never a tangent kiss). Turn counts are
  clamped to a HALF-INTEGER ceiling (4.5): an integer turn count degenerates the OCCT
  helical sweep (profile closes on itself -> negative/null body), and a very tall thread
  can tessellate non-watertight, so we cap turns and validate the MAX-slider extreme.
  Bores always OPEN onto a face (no sealed void). Barbs/collars are attached at the
  CLOSED/solid end of a body, never at an open rim (a flipped-then-attached feature gets
  severed).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected; params arrive as bare globals.
  - Read every param via PARAM(lambda: name, default); assign final solid to `result`.
  - No cross-file imports — every helper is inlined here.
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


# ── Thread standards (nominal geometry) ──────────────────────────────────────
THREAD_STD = {
    "M22": {"major_d": 22.0, "pitch": 1.0},
    "M24": {"major_d": 24.0, "pitch": 1.0},
}
_MAX_TURNS = 4.5  # HALF-INTEGER ceiling — integer turns degenerate the helical sweep


def std_geo(name):
    """Look up nominal thread geometry, defaulting to M24."""
    return THREAD_STD.get(name, THREAD_STD["M24"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "hose_barb"))
aerator_std = str(PARAM(lambda: aerator_std, "M24"))    # tap-side aerator thread
mate_std = str(PARAM(lambda: mate_std, "M22"))          # far-side aerator thread (gender_changer)
hose_id = float(PARAM(lambda: hose_id, 13.0))           # hose inner diameter for the barb (mm)
clearance = float(PARAM(lambda: clearance, 0.35))       # printed thread fit slop per side (mm)
wall = float(PARAM(lambda: wall, 2.6))                  # wall thickness (mm)
body_h = float(PARAM(lambda: body_h, 18.0))             # threaded collar height (mm)

# Clamp so extreme UI values still build watertight.
hose_id = max(6.0, min(hose_id, 25.0))
clearance = max(0.1, min(clearance, 0.7))
wall = max(1.6, min(wall, 5.0))
body_h = max(10.0, min(body_h, 30.0))


# ── Helical thread primitives (inlined; repo-lib imports blocked in sandbox) ──
def _helix_path(pitch, height, mean_r):
    """Helical wire on Z at the MEAN thread radius (non-singular sweep frame)."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=mean_r)


def female_thread(bore_radius, pitch, thread_h, overlap):
    """Internal helical rib pointing INWARD from a bore wall. Root at bore_radius+overlap
    (bites into the wall), crest at bore_radius-depth. Returns a solid rib."""
    depth = 0.5 * pitch
    outer_r = bore_radius + overlap
    crest_r = max(0.6, bore_radius - depth)
    mean_r = (outer_r + crest_r) / 2.0
    half_root = pitch * 0.28
    half_crest = max(0.05, half_root - depth * math.tan(math.radians(30.0)))
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (outer_r, -half_root),
            (crest_r, -half_crest),
            (crest_r, half_crest),
            (outer_r, half_root),
        ])
        .close()
    )
    rib = prof.sweep(_helix_path(pitch, thread_h + pitch, mean_r), isFrenet=True, makeSolid=True)
    return rib.translate((0, 0, -pitch * 0.5))


def male_thread(shaft_radius, pitch, thread_h, overlap):
    """External helical rib pointing OUTWARD from a spigot. Root at shaft_radius-overlap
    (bites in), crest at shaft_radius+depth. Returns a solid rib."""
    depth = 0.5 * pitch
    inner_r = max(0.6, shaft_radius - overlap)
    crest_r = shaft_radius + depth
    mean_r = (inner_r + crest_r) / 2.0
    half_root = pitch * 0.28
    half_crest = max(0.05, half_root - depth * math.tan(math.radians(30.0)))
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (inner_r, -half_root),
            (crest_r, -half_crest),
            (crest_r, half_crest),
            (inner_r, half_root),
        ])
        .close()
    )
    rib = prof.sweep(_helix_path(pitch, thread_h + pitch, mean_r), isFrenet=True, makeSolid=True)
    return rib.translate((0, 0, -pitch * 0.5))


def _turns_for(height, pitch):
    """Half-integer-safe turn count for a thread of `height`, capped at _MAX_TURNS."""
    raw = max(2.0, height / pitch - 1.0)
    return min(_MAX_TURNS, raw)


def _knurl_cut(body, radius, z0, height, do_knurl=True):
    """Grip flutes cut proud of the surface (radius + 0.3) so valleys never land tangent
    (a tangent kiss leaves zero-volume seams). Kept within (z0, z0+height)."""
    if not do_knurl:
        return body
    try:
        teeth = max(12, int(2 * math.pi * radius / 3.0))
        cutter = (
            cq.Workplane("XY")
            .polarArray(radius=radius + 0.3, startAngle=0, angle=360, count=teeth)
            .rect(0.9, 2.2)
            .extrude(height)
            .translate((0, 0, z0))
        )
        return body.cut(cutter)
    except Exception:
        return body


# ── Mode: hose_barb ──────────────────────────────────────────────────────────
def build_hose_barb():
    """Female aerator collar (top) → reducing cone → barbed hose spout (bottom), with a
    through-bore for water. The collar bore opens to the TOP face; the barb bore opens to
    the BOTTOM face; the two meet at the cone — one connected channel, no trapped void."""
    g = std_geo(aerator_std)
    pitch = g["pitch"]
    thr_major = g["major_d"] + 2.0 * clearance
    bore_r = thr_major / 2.0
    collar_or = bore_r + wall
    thread_h = pitch * _turns_for(body_h, pitch)

    # Threaded collar (outer knurled grip cylinder)
    collar = cq.Workplane("XY").circle(collar_or).extrude(body_h)
    collar = _knurl_cut(collar, collar_or, 0.0, body_h)

    # Reducing cone from collar OD down to the barb OD
    barb_or = hose_id / 2.0 + wall
    cone_h = max(6.0, wall * 3.0)
    cone = (
        cq.Workplane("XY").workplane(offset=-cone_h)
        .circle(barb_or).workplane(offset=cone_h).circle(collar_or)
        .loft(combine=True)
    )

    # Barbed spout: a stack of short frusta (barbs) — built from lofted rings, never a
    # revolve-of-a-cut. Each barb is a truncated cone that steps out then in.
    barb_len = max(14.0, hose_id * 1.1)
    spout = cq.Workplane("XY").workplane(offset=-cone_h).circle(barb_or).extrude(-barb_len)
    n_barbs = max(2, int(barb_len / 6.0))
    for i in range(n_barbs):
        z_top = -cone_h - (i + 0.35) * (barb_len / n_barbs)
        ridge_h = (barb_len / n_barbs) * 0.65
        ring = (
            cq.Workplane("XY").workplane(offset=z_top - ridge_h)
            .circle(barb_or + 1.4).workplane(offset=ridge_h).circle(barb_or)
            .loft(combine=True)
        )
        spout = spout.union(ring)

    body = collar.union(cone).union(spout)

    # Through-bore: from above the top face down through the whole barb, opening both ends
    flow_r = max(3.0, hose_id / 2.0 - 0.5)
    bore = (
        cq.Workplane("XY").workplane(offset=1.0)
        .circle(flow_r).extrude(-(body_h + cone_h + barb_len + 4.0))
    )
    body = body.cut(bore)

    # Widen the top to the thread bore for the threaded region, then add the female rib
    body = body.cut(
        cq.Workplane("XY").workplane(offset=body_h - thread_h - 1.5)
        .circle(bore_r).extrude(thread_h + 3.0)
    )
    start = body_h - thread_h - 1.0
    body = body.union(
        female_thread(bore_r, pitch, thread_h, min(0.6, wall * 0.4 + 0.2)).translate((0, 0, start))
    )
    # Trim any thread crest above the top face with a cheap slab cut.
    body = body.cut(
        cq.Workplane("XY").workplane(offset=body_h).circle(collar_or + 6.0).extrude(pitch + 2.0)
    )
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Mode: gender_changer (double-ended aerator coupler) ──────────────────────
def build_gender_changer():
    """A coupler: FEMALE aerator thread at the top (screws over a male spout of aerator_std)
    and a MALE aerator spigot at the bottom (screws into a female fitting of mate_std). A
    through-bore passes water. The two threaded ends share a central web so it is one solid
    with the bore opening both faces."""
    gt = std_geo(aerator_std)   # top: female
    gb = std_geo(mate_std)      # bottom: male
    pitch_t = gt["pitch"]
    pitch_b = gb["pitch"]

    # Top female collar
    bore_r = gt["major_d"] / 2.0 + clearance
    collar_or = bore_r + wall
    top_h = body_h
    thr_t = pitch_t * _turns_for(top_h, pitch_t)

    # Bottom male spigot
    thr_major_b = gb["major_d"] - 2.0 * clearance
    shaft_r = max(6.0, thr_major_b / 2.0 - 0.5 * pitch_b)
    spg_h = max(10.0, body_h * 0.8)
    thr_b = pitch_b * _turns_for(spg_h, pitch_b)

    # Bodies: top collar cylinder + bottom shaft cylinder + a hex-ish grip flange between.
    collar = cq.Workplane("XY").circle(collar_or).extrude(top_h)
    collar = _knurl_cut(collar, collar_or, 0.0, top_h)

    flange_r = max(collar_or, shaft_r + wall) + 2.0
    flange_h = 5.0
    flange = cq.Workplane("XY").workplane(offset=-flange_h).circle(flange_r).extrude(flange_h)
    flange = _knurl_cut(flange, flange_r, -flange_h, flange_h)

    shaft = cq.Workplane("XY").workplane(offset=-flange_h).circle(shaft_r).extrude(-spg_h)

    body = collar.union(flange).union(shaft)

    # Bottom external thread on the spigot
    body = body.union(
        male_thread(shaft_r, pitch_b, thr_b, 0.5).translate((0, 0, -flange_h - spg_h + 1.0))
    )
    # Through-bore (opens top and bottom)
    flow_r = max(3.0, shaft_r - wall)
    body = body.cut(
        cq.Workplane("XY").workplane(offset=1.0)
        .circle(flow_r).extrude(-(top_h + flange_h + spg_h + 4.0))
    )
    # Top thread counterbore + female rib
    body = body.cut(
        cq.Workplane("XY").workplane(offset=top_h - thr_t - 1.5)
        .circle(bore_r).extrude(thr_t + 3.0)
    )
    body = body.union(
        female_thread(bore_r, pitch_t, thr_t, min(0.6, wall * 0.4 + 0.2))
        .translate((0, 0, top_h - thr_t - 1.0))
    )
    # Slab-trim any crest above the top face.
    body = body.cut(
        cq.Workplane("XY").workplane(offset=top_h).circle(flange_r + 6.0).extrude(pitch_t + 2.0)
    )
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Mode: quick_cap (female aerator filter cap) ──────────────────────────────
def build_quick_cap():
    """A knurled cap with an internal aerator thread and a coarse screen grid across a
    recessed shoulder inside — a printable aerator/flow-straightener cap. Closed shoulder
    with drilled holes = one solid, cavity open to the bottom (threaded) face."""
    g = std_geo(aerator_std)
    pitch = g["pitch"]
    bore_r = g["major_d"] / 2.0 + clearance
    out_r = bore_r + wall
    skirt_h = max(8.0, body_h * 0.6)
    top_h = wall * 1.5
    total = skirt_h + top_h
    thr = pitch * _turns_for(skirt_h, pitch)

    body = cq.Workplane("XY").circle(out_r).extrude(total)
    body = _knurl_cut(body, out_r, 0.0, total)
    # Hollow the threaded skirt, opening to the BOTTOM face (solid top shoulder remains).
    body = body.cut(
        cq.Workplane("XY").workplane(offset=-1.0).circle(bore_r).extrude(skirt_h + 1.0)
    )
    # Female thread inside the skirt
    body = body.union(
        female_thread(bore_r, pitch, thr, min(0.6, wall * 0.4 + 0.2)).translate((0, 0, 1.0))
    )
    # Screen grid: drill a ring of small holes through the top shoulder (flow openings).
    # Holes open the top face to the cavity below -> no sealed void; grid stays a solid.
    hole_r = 1.4
    ring_n = max(6, int(2 * math.pi * (bore_r * 0.6) / 5.0))
    for i in range(ring_n):
        a = 2 * math.pi * i / ring_n
        hx = bore_r * 0.6 * math.cos(a)
        hy = bore_r * 0.6 * math.sin(a)
        body = body.cut(
            cq.Workplane("XY").transformed(offset=cq.Vector(hx, hy, skirt_h - 1.0))
            .circle(hole_r).extrude(top_h + 2.0)
        )
    # Centre hole
    body = body.cut(
        cq.Workplane("XY").transformed(offset=cq.Vector(0.0, 0.0, skirt_h - 1.0))
        .circle(hole_r).extrude(top_h + 2.0)
    )
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "gender_changer":
    result = build_gender_changer()
elif target_part == "quick_cap":
    result = build_quick_cap()
else:
    result = build_hose_barb()
