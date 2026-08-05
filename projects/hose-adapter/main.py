"""
Hose / Faucet Thread Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Bridges the mismatched threads people fight with every summer: garden-hose thread
(GHT 3/4"), faucet-aerator threads (M22 male / M24 female), and plain hose barbs.
Pick a thread standard for each end; the adapter carries a real helical thread (or a
barbed nozzle) on each side so a hose reaches a sink, a filter, or another hose.

Thread strategy (verified watertight + fast, ~2-6 s per render):
  Threads are single-start helical ribs swept along a genuine `cq.Wire.makeHelix`
  path built at the MEAN thread radius (not radius≈0 — a real-radius helix keeps the
  sweep frame non-singular, which is what makes the fuse both fast and watertight).
  Each rib is UNIONED into the wall as positive material: its root is pushed `overlap`
  into the wall so the boolean is fully volumetric (not a fragile tangent kiss).
  Turns are capped (~2.5) because the helical fuse grows super-linearly and hose
  fittings only need a couple of engagement turns. Male threads point outward from a
  spigot; female threads point inward from a bore.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `wall`).
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


# ── Thread standards (nominal geometry) ──────────────────────────────────────
# major_d = thread major (outer) diameter (mm); pitch = axial thread pitch (mm).
# GHT 3/4": ~26.4 mm major, 11.5 TPI ≈ 2.209 mm pitch (NH / garden-hose finish).
# M22×1: faucet aerator MALE outer thread. M24×1: aerator FEMALE (larger housing).
THREAD_STD = {
    "GHT_3/4": {"major_d": 26.4, "pitch": 2.209},
    "M22":     {"major_d": 22.0, "pitch": 1.0},
    "M24":     {"major_d": 24.0, "pitch": 1.0},
}
_MAX_TURNS = 2.5


def std_geo(name):
    """Look up nominal thread geometry, defaulting to GHT 3/4"."""
    return THREAD_STD.get(name, THREAD_STD["GHT_3/4"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "ght_to_barb"))  # ght_to_barb | faucet_to_ght | coupler
thread_a    = str(PARAM(lambda: thread_a,    "GHT_3/4"))       # end A standard
thread_b    = str(PARAM(lambda: thread_b,    "barb"))          # end B standard ("barb" allowed)
clearance   = float(PARAM(lambda: clearance,   0.35))          # printed thread fit slop per side (mm)
wall        = float(PARAM(lambda: wall,        2.6))           # side wall thickness (mm)
bore_dia    = float(PARAM(lambda: bore_dia,   12.0))           # central through-bore (fluid path, mm)
barb_dia    = float(PARAM(lambda: barb_dia,   13.0))           # hose-barb nominal OD (mm)
barb_count  = int(  PARAM(lambda: barb_count,    3))           # number of barb ridges
grip_knurl  = bool( PARAM(lambda: grip_knurl, True))           # grip flutes around the middle

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
clearance = max(0.1, min(clearance, 0.8))
wall = max(1.6, min(wall, 5.0))
bore_dia = max(3.0, min(bore_dia, 24.0))
barb_dia = max(6.0, min(barb_dia, 24.0))
barb_count = max(1, min(barb_count, 6))

bore_r = bore_dia / 2.0


# ── Thread primitives (inlined — repo-lib imports are blocked in the sandbox) ─
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


# ── Feature builders (each returns solid + top-of-feature z) ──────────────────
def female_socket(std_name, z0):
    """A female-threaded socket sitting on z0, opening upward. Bore = thread major
    + clearance; the wall wraps it. Returns (solid, top_z, outer_r)."""
    g = std_geo(std_name)
    pitch = g["pitch"]
    thr_major = g["major_d"] + 2.0 * clearance
    b_r = thr_major / 2.0
    turns = min(_MAX_TURNS, max(1.5, 6.0 / pitch))
    thread_h = pitch * turns
    outer_r = b_r + wall
    h = thread_h + 2.0
    body = cq.Workplane("XY").circle(outer_r).extrude(h).translate((0, 0, z0))
    bore = cq.Workplane("XY").circle(b_r).extrude(h + 1.0).translate((0, 0, z0 - 0.5))
    body = body.cut(bore)
    overlap = min(0.6, wall * 0.35 + 0.2)
    thr = female_thread(b_r, pitch, thread_h, overlap).translate((0, 0, z0 + 0.5))
    body = body.union(thr)
    return body, z0 + h, outer_r


def male_spigot(std_name, z0):
    """A male-threaded spigot rising from z0. Returns (solid, top_z, outer_r).
    outer_r is the crest radius (the widest point of the male thread)."""
    g = std_geo(std_name)
    pitch = g["pitch"]
    # Male major diameter reduced by clearance so it fits the mating female.
    thr_major = g["major_d"] - 2.0 * clearance
    shaft_r = thr_major / 2.0 - 0.5 * pitch   # shaft under the thread
    shaft_r = max(bore_r + 1.2, shaft_r)
    turns = min(_MAX_TURNS, max(1.5, 6.0 / pitch))
    thread_h = pitch * turns
    h = thread_h + 2.0
    body = cq.Workplane("XY").circle(shaft_r).extrude(h).translate((0, 0, z0))
    overlap = 0.5
    thr = male_thread(shaft_r, pitch, thread_h, overlap).translate((0, 0, z0 + 0.8))
    body = body.union(thr)
    return body, z0 + h, shaft_r + 0.5 * pitch


def barb_nozzle(z0):
    """A barbed hose nozzle rising from z0: a stack of tapered ridges that grip the
    inside of a push-on hose. Returns (solid, top_z, base_r)."""
    tip_r = barb_dia / 2.0 - 1.0
    tip_r = max(bore_r + 1.0, tip_r)
    ridge_r = barb_dia / 2.0
    ridge_h = 4.0
    gap = 1.2
    body = None
    z = z0
    for _ in range(barb_count):
        # Each ridge: a cone flaring out then a step back (loft big->small).
        ring = (
            cq.Workplane("XY")
            .circle(tip_r)
            .workplane(offset=ridge_h * 0.7)
            .circle(ridge_r)
            .workplane(offset=ridge_h * 0.3)
            .circle(tip_r)
            .loft(combine=True)
            .translate((0, 0, z))
        )
        body = ring if body is None else body.union(ring)
        z += ridge_h + gap
    # Fill the core so barbs share a solid column (before boring the channel).
    core = cq.Workplane("XY").circle(tip_r).extrude(z - z0).translate((0, 0, z0))
    body = core if body is None else body.union(core)
    return body, z, ridge_r


def add_hub(z_bottom, z_top, r):
    """A central hex-ish grip hub between two ends: a cylinder of radius r spanning
    [z_bottom, z_top], optionally fluted for grip. Returns solid."""
    hub = cq.Workplane("XY").circle(r).extrude(z_top - z_bottom).translate((0, 0, z_bottom))
    if grip_knurl:
        try:
            teeth = 18
            cutter = (
                cq.Workplane("XY")
                .polarArray(radius=r, startAngle=0, angle=360, count=teeth)
                .rect(0.9, 2.4)
                .extrude(z_top - z_bottom + 2.0)
                .translate((0, 0, z_bottom - 1.0))
            )
            hub = hub.cut(cutter)
        except Exception:
            pass
    return hub


def bore_through(body, z_low, z_high):
    """Cut the fluid channel through the whole adapter."""
    chan = cq.Workplane("XY").circle(bore_r).extrude(z_high - z_low + 4.0).translate((0, 0, z_low - 2.0))
    body = body.cut(chan)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Part builders ─────────────────────────────────────────────────────────────
def _end_feature(kind, z0, upward=True):
    """Build an end feature by kind name. `upward=False` flips it so it points down
    from z0 (for the bottom end). Returns (solid, extent_top_or_bottom, radius)."""
    if kind == "barb":
        solid, top, r = barb_nozzle(0.0)
    elif kind in ("M22",):
        solid, top, r = male_spigot(kind, 0.0)
    else:
        # GHT and M24 read most naturally as female sockets/housings here.
        solid, top, r = female_socket(kind, 0.0)
    height = top
    if upward:
        solid = solid.translate((0, 0, z0))
        return solid, z0 + height, r
    else:
        # Mirror about XY then drop to z0.
        solid = solid.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, z0))
        return solid, z0 - height, r


def build_adapter(kind_bottom, kind_top):
    """Generic two-ended adapter: bottom feature, central grip hub, top feature,
    one fluid channel through everything."""
    hub_r = max(std_geo(thread_a)["major_d"], std_geo(thread_b)["major_d"], barb_dia) / 2.0 + wall + 1.0
    hub_h = 6.0

    # Central hub occupies [0, hub_h].
    bottom, z_bot, _ = _end_feature(kind_bottom, 0.0, upward=False)   # extends below 0
    top, z_top, _ = _end_feature(kind_top, hub_h, upward=True)         # extends above hub_h
    hub = add_hub(0.0, hub_h, hub_r)

    body = hub.union(bottom).union(top)
    body = bore_through(body, z_bot, z_top)
    return body


def build_ght_to_barb():
    """Garden-hose thread (female housing) on one end, a hose barb on the other —
    the classic 'connect a hose to bare tubing' adapter."""
    return build_adapter("barb", thread_a if thread_a != "barb" else "GHT_3/4")


def build_faucet_to_ght():
    """Faucet aerator (M22 male spigot) to garden-hose thread — put a hose on a
    kitchen/bathroom tap."""
    return build_adapter("M22", "GHT_3/4")


def build_coupler():
    """Garden-hose thread on BOTH ends — joins two hoses together."""
    return build_adapter("GHT_3/4", "GHT_3/4")


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "faucet_to_ght":
    result = build_faucet_to_ght()
elif target_part == "coupler":
    result = build_coupler()
else:
    result = build_ght_to_barb()
