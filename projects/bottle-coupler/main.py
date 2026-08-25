"""
Bottle-to-Bottle Coupler — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Joins two PCO-1881 bottles neck-to-neck. Screw a bottle into each end and you get:
a sealed transfer/storage joint (decant, settle, store), a "tornado tube" vortex
demonstrator (a small central orifice spins the draining water into a vortex), or a
funnel coupler that threads onto one bottle and opens into a wide catch funnel for
pouring. The functional interface on every end is a REAL PCO-1881 female helical
thread, the same neck used by the `bottle-thread`, `bird-feeder`, `faircap-filter`,
and `pet-dispenser` cartridges (27.43 mm thread major diameter, 2.7 mm pitch).

Thread strategy (verified watertight + fast):
  A trapezoidal rib is swept along a genuine `makeHelix` path and unioned into the
  bore wall, with the rib root pushed into the wall for a clean volumetric boolean.
  Turn count is forced to a HALF-INTEGER (floor(n)+0.5): a whole-integer turn count
  degenerates the OCCT helical sweep into a negative-volume / null body. Modeled
  turns are also capped so the multi-turn sweep stays watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals; read them via
    PARAM(lambda: <name>, <default>).
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── PCO-1881 neck finish (nominal geometry) ──────────────────────────────────
PCO1881 = {"major_d": 27.43, "pitch": 2.7, "turns": 3.5}


def half_turns(n):
    """Nearest lower half-integer, never a whole integer (whole → null sweep)."""
    return math.floor(max(0.5, n)) + 0.5


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "straight_coupler"))  # straight|tornado|funnel

clearance = float(PARAM(lambda: clearance, 0.4))   # printed-thread fit slop (per side, mm)
wall = float(PARAM(lambda: wall, 2.8))             # radial wall around each thread (mm)
web_th = float(PARAM(lambda: web_th, 3.0))         # central web thickness between ends (mm)
turns = float(PARAM(lambda: turns, 3.5))           # PCO-1881 engagement turns per end
bore_margin = float(PARAM(lambda: bore_margin, 1.6))  # through-channel wall margin (mm)

# Tornado orifice
vortex_dia = float(PARAM(lambda: vortex_dia, 8.0))  # central vortex orifice (mm)

# Funnel options
funnel_dia = float(PARAM(lambda: funnel_dia, 90.0))  # funnel mouth diameter (mm)
funnel_h = float(PARAM(lambda: funnel_h, 55.0))      # funnel height (mm)
funnel_wall = float(PARAM(lambda: funnel_wall, 1.8))  # funnel cone wall (mm)

clearance = max(0.0, min(clearance, 1.0))
wall = max(1.8, min(wall, 6.0))
web_th = max(1.6, min(web_th, 8.0))
turns = max(1.5, min(turns, 3.5))
bore_margin = max(1.0, min(bore_margin, 5.0))
vortex_dia = max(2.0, min(vortex_dia, 18.0))
funnel_dia = max(40.0, min(funnel_dia, 160.0))
funnel_h = max(20.0, min(funnel_h, 120.0))
funnel_wall = max(1.2, min(funnel_wall, 4.0))


# ── Thread primitive (inlined — repo-lib imports blocked in sandbox) ──────────
def _helix_path(pitch, height):
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal female helical rib; root bites into the wall for a clean union."""
    root_r = bore_r + overlap
    crest_r = max(0.5, bore_r - thr_depth)
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -pitch * 0.32),
            (crest_r, -pitch * 0.14),
            (crest_r, pitch * 0.14),
            (root_r, pitch * 0.32),
        ])
        .close()
    )
    rib = prof.sweep(_helix_path(pitch, thread_h), isFrenet=True)
    return rib.translate((0, 0, pitch * 0.5))


def threaded_socket(clear, wall_th, base_th, n_turns):
    """A CLOSED-BASE cylindrical socket with an internal PCO-1881 female thread.
    Opens at z=0; a solid `base_th` disk caps the top. A closed base is REQUIRED for
    watertightness: an open-ended socket terminates the helical rib at a free rim,
    which tessellates non-watertight. Flow channels are cut through the base later.
    Returns (solid, socket_height, outer_d, bore_r, thread_h)."""
    g = PCO1881
    tt = half_turns(n_turns)
    pitch = g["pitch"]
    thr_major = g["major_d"] + 2.0 * clear
    bore_r = thr_major / 2.0
    thr_depth = 0.55 * pitch
    overlap = min(0.6, wall_th * 0.35 + 0.2)
    thread_h = pitch * tt

    outer_d = thr_major + 2.0 * wall_th
    body_h = thread_h + base_th + 1.5

    body = cq.Workplane("XY").circle(outer_d / 2.0).extrude(body_h)
    bore = cq.Workplane("XY").circle(bore_r).extrude(thread_h + 0.6)  # stops below base
    body = body.cut(bore)
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, overlap))
    return body, body_h, outer_d, bore_r, thread_h


def double_ended(clear, wall_th, base_th, n_turns):
    """Two closed-base female sockets stacked BASE-TO-BASE at the mid-plane (their
    two bases form the solid central web). Returns
    (coupler_solid, total_h, outer_d, bore_r, web_lo, web_hi), where [web_lo,
    web_hi] is the solid web band the flow must be cut through.

    `threaded_socket` opens at z=0 with its base disk at the TOP (z near hA).
    * Bottom socket = segA, left as-is: opening faces DOWN at z=0, base at z≈hA.
    * Top socket   = segB, flipped 180° so its base sits ON segA's base and its
      opening faces UP. The two bases butt together around z=hA → a solid web."""
    segA, hA, odA, brA, thA = threaded_socket(clear, wall_th, base_th, n_turns)
    segB, hB, odB, brB, thB = threaded_socket(clear, wall_th, base_th, n_turns)
    # Flip segB and lift it so its (now bottom) base lands on top of segA (height hA).
    segB = segB.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, hA + hB))
    coupler = segA.union(segB)
    total_h = hA + hB
    # Both bases sit in a band around the mid-plane z=hA. segA's base occupies
    # roughly [thA+0.6, hA]; segB's mirrored base occupies [hA, hA+(hB-thB-0.6)].
    web_lo = min(thA, thB) + 0.6
    web_hi = total_h - (min(thA, thB) + 0.6)
    return coupler, total_h, max(odA, odB), min(brA, brB), web_lo, web_hi


# ── Part builders ────────────────────────────────────────────────────────────
def build_straight_coupler():
    """Open through-channel joining two bottles neck-to-neck (transfer / storage)."""
    base_th = max(1.6, web_th * 0.5)
    coupler, total_h, od, bore_r, _, _ = double_ended(clearance, wall, base_th, turns)
    chan_r = max(1.0, bore_r - bore_margin)
    channel = (
        cq.Workplane("XY").circle(chan_r).extrude(total_h + 2.0).translate((0, 0, -1.0))
    )
    coupler = coupler.cut(channel)
    try:
        coupler = coupler.clean()
    except Exception:
        pass
    return coupler


def build_tornado_coupler():
    """A 'tornado tube': the solid central web keeps only a small orifice so
    draining water spins into a visible vortex passing between the two bottles."""
    base_th = max(1.6, web_th * 0.5)
    coupler, total_h, od, bore_r, web_lo, web_hi = double_ended(
        clearance, wall, base_th, turns
    )
    # Bore the wide channel through each socket, stopping AT the solid web band so
    # the web (the two fused bases) survives as the vortex plate.
    chan_r = max(1.0, bore_r - bore_margin)
    lower = (
        cq.Workplane("XY").circle(chan_r).extrude(web_lo + 1.0).translate((0, 0, -1.0))
    )
    upper = (
        cq.Workplane("XY")
        .circle(chan_r)
        .extrude(total_h - web_hi + 1.0)
        .translate((0, 0, web_hi))
    )
    coupler = coupler.cut(lower).cut(upper)
    # ...then punch a single small vortex orifice straight through the web.
    orifice_r = max(1.0, min(vortex_dia, 2.0 * chan_r - 1.0) / 2.0)
    orifice = (
        cq.Workplane("XY")
        .circle(orifice_r)
        .extrude(total_h + 2.0)
        .translate((0, 0, -1.0))
    )
    coupler = coupler.cut(orifice)
    try:
        coupler = coupler.clean()
    except Exception:
        pass
    return coupler


def build_funnel_coupler():
    """Female PCO thread on the bottom, opening up into a wide catch funnel for
    pouring / decanting into the bottle. Only the bottom end threads onto a bottle."""
    base_th = max(1.6, web_th * 0.5)
    # Socket opens DOWN at z=0 (receives the bottle neck); closed shoulder at z≈hA.
    segA, hA, odA, brA, thA = threaded_socket(clearance, wall, base_th, turns)

    # Throat must fit inside the shoulder disk (bounded by the bore radius) so the
    # funnel base is fully carried by solid material — otherwise the cone severs.
    throat_r = max(1.0, min(brA - bore_margin, brA - 1.5))
    mouth_r = funnel_dia / 2.0
    cone_h = funnel_h
    fw = funnel_wall
    # Funnel base outer radius seats on the socket outer wall so the union is solid.
    base_out_r = max(throat_r + fw, odA / 2.0 - 0.5)

    # Hollow cone = outer loft minus inner loft. Both start at the shoulder (z≈hA).
    outer = (
        cq.Workplane("XY")
        .circle(base_out_r)
        .workplane(offset=cone_h)
        .circle(mouth_r + fw)
        .loft(combine=True)
        .translate((0, 0, hA - 0.5))
    )
    body = segA.union(outer)
    inner = (
        cq.Workplane("XY")
        .circle(throat_r)
        .workplane(offset=cone_h + 1.0)
        .circle(mouth_r)
        .loft(combine=True)
        .translate((0, 0, hA))
    )
    body = body.cut(inner)
    # Open the throat straight down through the shoulder into the bottle bore.
    throat = (
        cq.Workplane("XY")
        .circle(throat_r)
        .extrude(hA + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(throat)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tornado_coupler":
    result = build_tornado_coupler()
elif target_part == "funnel_coupler":
    result = build_funnel_coupler()
else:
    result = build_straight_coupler()
