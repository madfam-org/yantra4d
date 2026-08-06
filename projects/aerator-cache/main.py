"""
Faucet Aerator / Cache — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A faucet-aerator housing that screws onto a standard tap, a matching screw-together
stash capsule (the "cache"), and a knurled key for installing or removing either.
The whole family shares the aerator thread standards so parts interchange and also
mate with the companion `hose-adapter` cartridge.

Real dimensions (faucet aerator threads, expressed in mm):
  - M22 x 1: the common MALE aerator thread (22.0 mm major, 1.0 mm pitch).
  - M24 x 1: the common FEMALE aerator thread (24.0 mm major, 1.0 mm pitch).
  Male housings carry the thread outward on a spigot; female housings carry it
  inward on a bore. Clearance is subtracted (male) / added (female) so printed
  threads mate without a tap.

Watertightness strategy (threads as positive material, closed manifolds):
  Threads are single-start helical ribs swept along a genuine `cq.Wire.makeHelix`
  path built at the MEAN thread radius (a real-radius helix keeps the sweep frame
  non-singular, which is what makes the fuse both fast and watertight). Each rib is
  UNIONED into the wall as positive material — its root is pushed `overlap` into the
  wall so the boolean is fully volumetric, never a fragile tangent kiss. This is the
  opposite of cutting a groove with a helical tool, which leaves zero-volume seams
  and severed slivers. Bodies that must be hollow (housing bore, cache cup) are
  hollowed by a bore that OPENS onto a face — no sealed internal void. The cache lid
  and cup are separate printed parts (a mode each), each an independently closed
  solid.

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


# ── Thread standards (nominal geometry) ──────────────────────────────────────
# major_d = thread major (outer) diameter (mm); pitch = axial thread pitch (mm).
THREAD_STD = {
    "M22": {"major_d": 22.0, "pitch": 1.0},
    "M24": {"major_d": 24.0, "pitch": 1.0},
}
_MAX_TURNS = 4.0


def std_geo(name):
    """Look up nominal thread geometry, defaulting to M22."""
    return THREAD_STD.get(name, THREAD_STD["M22"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "aerator_housing"))
thread_std = str(PARAM(lambda: thread_std, "M24"))    # aerator thread family
thread_mode = str(PARAM(lambda: thread_mode, "female"))  # male | female
clearance = float(PARAM(lambda: clearance, 0.35))     # printed thread fit slop per side (mm)
wall = float(PARAM(lambda: wall, 2.4))                # wall thickness (mm)
housing_h = float(PARAM(lambda: housing_h, 20.0))     # housing / cache body height (mm)
cache_depth = float(PARAM(lambda: cache_depth, 22.0))  # inner stash depth of the cache cup (mm)
knurl = bool(PARAM(lambda: knurl, True))              # grip flutes on the outside

# Clamp so extreme UI values still build watertight.
clearance = max(0.1, min(clearance, 0.7))
wall = max(1.6, min(wall, 5.0))
housing_h = max(10.0, min(housing_h, 40.0))
cache_depth = max(8.0, min(cache_depth, 45.0))


# ── Helical thread primitives (inlined; repo-lib imports blocked in sandbox) ──
def _helix_path(pitch, height, mean_r):
    """Helical wire centered on Z at the MEAN thread radius (non-singular frame)."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=mean_r)


def female_thread(bore_radius, pitch, thread_h, overlap):
    """Internal (female) helical rib pointing INWARD from a bore wall. Root at
    bore_radius + overlap (bites into the wall), crest at bore_radius - depth."""
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
    """External (male) helical rib pointing OUTWARD from a spigot. Root at
    shaft_radius - overlap (bites in), crest at shaft_radius + depth."""
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


def _knurl_cut(body, radius, z0, height):
    """Optional grip flutes cut around the outside of a cylinder of `radius`.
    The cutter teeth sit slightly PROUD of the surface (radius + 0.3) so their
    valleys never land exactly tangent to the cylinder — a tangent kiss would leave
    zero-volume seams. Kept within (z0, z0 + height) so it never breaches an end face."""
    if not knurl:
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


# ── Part builders ─────────────────────────────────────────────────────────────
def build_aerator_housing():
    """A threaded aerator cap. In female mode it screws DOWN over a male tap spout
    and holds a screen (open bore top and bottom, annular rims -> watertight). In
    male mode it presents an external spigot thread to screw INTO a female tap."""
    g = std_geo(thread_std)
    pitch = g["pitch"]
    turns = min(_MAX_TURNS, max(2.0, housing_h / pitch - 1.0))
    thread_h = pitch * turns

    if thread_mode == "male":
        # External thread on a spigot; a bore runs through for water/screen.
        thr_major = g["major_d"] - 2.0 * clearance
        shaft_r = thr_major / 2.0 - 0.5 * pitch
        shaft_r = max(6.0, shaft_r)
        out_r = shaft_r + 0.5 * pitch + wall * 0.0  # crest defines the widest point
        body_r = shaft_r
        bore_r = max(4.0, shaft_r - wall)
        body = cq.Workplane("XY").circle(body_r).extrude(housing_h)
        body = body.union(male_thread(shaft_r, pitch, thread_h, 0.5).translate((0, 0, 2.0)))
        # A hex-ish grip flange at the base (wider) for finger torque.
        flange_r = body_r + wall + 1.5
        flange = cq.Workplane("XY").circle(flange_r).extrude(4.0)
        flange = _knurl_cut(flange, flange_r, 0.0, 4.0)
        body = body.union(flange)
        body = body.cut(
            cq.Workplane("XY").workplane(offset=-1.0).circle(bore_r).extrude(housing_h + 2.0)
        )
        _ = out_r
    else:
        # Internal thread inside a cap bore; outside is a knurled grip cylinder.
        thr_major = g["major_d"] + 2.0 * clearance
        bore_r = thr_major / 2.0
        out_r = bore_r + wall
        body = cq.Workplane("XY").circle(out_r).extrude(housing_h)
        # Through water bore is narrower than the thread bore -> internal shoulder.
        flow_r = max(4.0, bore_r - 1.5)
        body = body.cut(
            cq.Workplane("XY").workplane(offset=-1.0).circle(flow_r).extrude(housing_h + 2.0)
        )
        # Thread counterbore region (wider) at the mouth so the tap seats.
        body = body.cut(
            cq.Workplane("XY").workplane(offset=housing_h - thread_h - 2.0)
            .circle(bore_r).extrude(thread_h + 3.0)
        )
        # Bury the thread so the rib (thread_h + pitch tall) stays inside the top face.
        start = housing_h - thread_h - 1.5
        body = body.union(
            female_thread(bore_r, pitch, thread_h, min(0.6, wall * 0.4 + 0.2)).translate((0, 0, start))
        )
        body = _knurl_cut(body, out_r, 0.0, housing_h)

    # Trim any thread protrusion above the top face with a cheap slab cut (an
    # intersect against a full cylinder is far more expensive on threaded geometry).
    body = body.cut(
        cq.Workplane("XY").workplane(offset=housing_h).circle(out_r + 6.0).extrude(pitch + 2.0)
    )
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_cache_cup():
    """The stash cup: a closed-bottom cylinder with a MALE external thread at its
    mouth so the lid screws on. Solid bottom + open top = one closed solid with a
    blind cavity that opens to the top face (no sealed void)."""
    g = std_geo(thread_std)
    pitch = g["pitch"]
    thr_major = g["major_d"] - 2.0 * clearance
    shaft_r = thr_major / 2.0 - 0.5 * pitch
    shaft_r = max(8.0, shaft_r)
    out_r = shaft_r + wall
    total = cache_depth + wall  # cavity depth + closed bottom

    body = cq.Workplane("XY").circle(out_r).extrude(total)
    body = _knurl_cut(body, out_r, 0.0, total - 6.0)
    # Reduce the mouth to the thread shaft for the last stretch so the lid clears.
    lip_h = 8.0
    body = body.cut(
        cq.Workplane("XY").workplane(offset=total - lip_h)
        .circle(out_r + 1.0).extrude(lip_h + 1.0)
        .cut(cq.Workplane("XY").workplane(offset=total - lip_h - 1.0).circle(shaft_r).extrude(lip_h + 3.0))
    )
    # External thread on the reduced lip.
    thread_h = pitch * min(_MAX_TURNS, 4.0)
    body = body.union(
        male_thread(shaft_r, pitch, thread_h, 0.5).translate((0, 0, total - thread_h - 1.0))
    )
    # Hollow the cavity, opening to the TOP face (blind bottom keeps wall = floor).
    cav_r = max(4.0, shaft_r - wall)
    body = body.cut(
        cq.Workplane("XY").workplane(offset=wall).circle(cav_r).extrude(cache_depth + 2.0)
    )
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_cache_lid():
    """The stash lid: a shallow cap with a FEMALE internal thread that screws onto
    the cup mouth. Closed top + threaded skirt = one closed solid, cavity open down."""
    g = std_geo(thread_std)
    pitch = g["pitch"]
    thr_major = g["major_d"] + 2.0 * clearance
    bore_r = thr_major / 2.0
    out_r = bore_r + wall
    skirt_h = 10.0
    top_h = 3.0
    total = skirt_h + top_h

    body = cq.Workplane("XY").circle(out_r).extrude(total)
    body = _knurl_cut(body, out_r, 0.0, total)
    # Hollow the threaded skirt (opens to the BOTTOM face; solid top cap remains).
    body = body.cut(
        cq.Workplane("XY").workplane(offset=-1.0).circle(bore_r).extrude(skirt_h + 1.0)
    )
    thread_h = pitch * min(_MAX_TURNS, 4.0)
    body = body.union(
        female_thread(bore_r, pitch, thread_h, min(0.6, wall * 0.4 + 0.2)).translate((0, 0, 1.0))
    )
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "cache_cup":
    result = build_cache_cup()
elif target_part == "cache_lid":
    result = build_cache_lid()
else:
    result = build_aerator_housing()
