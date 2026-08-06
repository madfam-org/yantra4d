"""Thread Adapter Kit — Universal Any-to-Any Threaded Adapter (Yantra4D Hyperobject).

A parametric "translator" for threaded connections. Pick a thread standard for
each end and get a printable adapter that mates the two — the universal fitting
for plumbing, garden hose, lab, and pneumatic threads. Every thread is a REAL
single-start helical rib (makeHelix + swept trapezoid fused into the wall), sized
to nominal standard geometry so the mating interface is genuine.

Thread standards (nominal major Ø in mm + pitch in mm):
  * GHT34  — Garden Hose Thread 3/4" (26.44 mm major, 11.5 TPI → 2.209 mm pitch,
    straight). The ubiquitous hose / spigot / filter thread.
  * NPT12  — NPT 1/2" pipe (21.34 mm major, 14 TPI → 1.814 mm; modelled straight
    for printability — real NPT is 1:16 tapered, note in docs).
  * BSP12  — BSPP / G 1/2" (20.96 mm major, 14 TPI → 1.814 mm, straight/parallel).
  * M20    — ISO metric M20 x 2.5 (20 mm major, 2.5 mm pitch).
  * M24    — ISO metric M24 x 3.0 (24 mm major, 3.0 mm pitch).

Three distinct modes:
  * male_to_female — male thread (end A) on the bottom + female thread (end B) on
    top: the core any-to-any translator, with a through bore.
  * double_male    — male thread A + male thread B (two male ends via a hex body):
    joins two female fittings.
  * hose_bib       — female thread A (drops onto a spigot / bib) + male thread B:
    the common garden-hose-to-pipe / tap adapter, with a hex grip.

CRITICAL thread rule: the turn count is snapped to a HALF-INTEGER
(floor(n)+0.5, clamped 1.5-3.5). An integer turn count degenerates the OCCT
helical sweep — the profile closes on itself, orientation flips, and the boolean
yields a negative-volume / null body. A half-integer count is well-conditioned
and fast; the cap bounds the multi-thread boolean.

Sandbox contract (cq_runner.py): `cq`+`math` pre-injected; params bare globals
via PARAM(lambda: name, default); final solid assigned to `result`.
"""

import cadquery as cq
import math


def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Thread standards (nominal real geometry) ─────────────────────────────────
THREADS = {
    "GHT34": {"major_d": 26.44, "pitch": 2.209, "label": "Garden Hose 3/4\""},
    "NPT12": {"major_d": 21.34, "pitch": 1.814, "label": "NPT 1/2\""},
    "BSP12": {"major_d": 20.96, "pitch": 1.814, "label": "BSP/G 1/2\""},
    "M20":   {"major_d": 20.00, "pitch": 2.500, "label": "M20 x 2.5"},
    "M24":   {"major_d": 24.00, "pitch": 3.000, "label": "M24 x 3.0"},
}


def spec(name):
    return THREADS.get(str(name).strip(), THREADS["GHT34"])


def half_int_turns(n):
    """Half-integer turn count (floor(n)+0.5), clamped to [1.5, 3.5]. An integer
    count degenerates the helical sweep to a negative-volume body."""
    return max(1.5, min(3.5, math.floor(n) + 0.5))


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "male_to_female"))
thread_a    = str(PARAM(lambda: thread_a, "GHT34"))    # end A standard
thread_b    = str(PARAM(lambda: thread_b, "NPT12"))    # end B standard
clearance   = float(PARAM(lambda: clearance, 0.4))     # printed-thread fit (per side)
wall        = float(PARAM(lambda: wall,      3.0))     # radial wall around thread
turns       = float(PARAM(lambda: turns,     3.0))     # requested engagement turns
bore        = float(PARAM(lambda: bore,     10.0))     # through bore Ø (fluid path)
hex_grip    = bool(PARAM(lambda: hex_grip,   True))    # hex wrench flats on the body

clearance = max(0.0, min(clearance, 1.0))
wall      = max(1.6, min(wall, 6.0))
turns     = max(1.5, min(turns, 4.0))
bore      = max(3.0, min(bore, 24.0))


# ── Thread primitives (inlined) ──────────────────────────────────────────────
def _helix_path(pitch, hgt):
    return cq.Wire.makeHelix(pitch=pitch, height=hgt, radius=1e-6)


def _thread_profile(root_r, crest_r, pitch):
    return (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -pitch * 0.32), (crest_r, -pitch * 0.14),
            (crest_r, pitch * 0.14), (root_r, pitch * 0.32),
        ]).close()
    )


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    rib = _thread_profile(bore_r + overlap, max(0.5, bore_r - thr_depth), pitch)
    return rib.sweep(_helix_path(pitch, thread_h), isFrenet=True).translate((0, 0, pitch * 0.5))


def male_thread(shaft_r, pitch, thread_h, thr_depth, overlap):
    rib = _thread_profile(max(0.5, shaft_r - overlap), shaft_r + thr_depth, pitch)
    return rib.sweep(_helix_path(pitch, thread_h), isFrenet=True).translate((0, 0, pitch * 0.5))


def _hex_mid(body_od, across_flats, height, z0):
    """Build the central body as a HEX prism (wrench flats) instead of a plain
    cylinder. Returns the hex solid spanning [z0, z0+height]. The threaded ends
    stay round; only this middle section carries flats — intersecting the whole
    part with a hex would truncate the round ends, so the mid is hexed in
    isolation and unioned with the ends."""
    r_circ = across_flats / math.sqrt(3.0)
    try:
        return (
            cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0))
            .polygon(6, 2.0 * r_circ).extrude(height)
        )
    except Exception:
        return (
            cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0))
            .circle(body_od / 2.0).extrude(height)
        )


def male_end(std, clear, wall_th, req_turns, z0):
    """Solid male-threaded end rooted at z0. Returns (solid, top_z, shaft_r,
    thr_major, outer_hint). Core taller than the thread run so both rib ends are
    buried in the cylinder body."""
    s = spec(std)
    pitch = s["pitch"]
    t = half_int_turns(req_turns)
    thr_major = max(6.0, s["major_d"] - 2.0 * clear)
    thr_depth = 0.55 * pitch
    shaft_r = thr_major / 2.0 - thr_depth
    overlap = 0.45
    thread_h = pitch * t
    core_h = thread_h + 2.0 * pitch

    core = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0))
        .circle(shaft_r + 0.2).extrude(core_h)
    )
    core = core.union(male_thread(shaft_r, pitch, thread_h, thr_depth, overlap).translate((0, 0, z0)))
    return core, z0 + core_h, shaft_r, thr_major, s["major_d"] + 2.0 * wall_th


def female_end(std, clear, wall_th, req_turns, z0):
    """Female-threaded socket rooted at z0 opening upward. Returns (solid, top_z,
    outer_d, bore_r)."""
    s = spec(std)
    pitch = s["pitch"]
    t = half_int_turns(req_turns)
    thr_major = s["major_d"] + 2.0 * clear
    bore_r = thr_major / 2.0
    thr_depth = 0.55 * pitch
    overlap = min(0.6, wall_th * 0.35 + 0.2)
    thread_h = pitch * t
    outer_d = thr_major + 2.0 * wall_th
    body_h = thread_h + 2.0

    body = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0))
        .circle(outer_d / 2.0).extrude(body_h)
    )
    bore_cut = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0 - 0.5))
        .circle(bore_r).extrude(thread_h + 2.5)
    )
    body = body.cut(bore_cut)
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, overlap).translate((0, 0, z0)))
    return body, z0 + body_h, outer_d, bore_r


def _through_bore(body, bore_r, z_top):
    channel = cq.Workplane("XY").circle(bore_r).extrude(z_top + 2.0).translate((0, 0, -1.0))
    return body.cut(channel)


# ── male_to_female ───────────────────────────────────────────────────────────
def build_male_to_female():
    """Male thread A on the bottom + female thread B on top, joined by a hex body,
    with a through bore."""
    male, topM, srM, majM, outM = male_end(thread_a, clearance, wall, turns, 0.0)
    # Central body between the two ends — a hex prism (wrench flats) or cylinder.
    body_od = max(outM, spec(thread_b)["major_d"] + 2.0 * wall) + 2.0
    body_h = max(6.0, wall * 2.0 + 3.0)
    if hex_grip:
        mid = _hex_mid(body_od, body_od * 0.98, body_h + 0.5, topM - 0.5)
    else:
        mid = (
            cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, topM - 0.5))
            .circle(body_od / 2.0).extrude(body_h + 0.5)
        )
    fem, topF, odF, brF = female_end(thread_b, clearance, wall, turns, topM + body_h)
    body = male.union(mid).union(fem)

    # Through bore last (opens both ends → no trapped void).
    b_r = max(1.5, min(bore, min(srM * 2.0, brF * 2.0) - 1.6) / 2.0)
    body = _through_bore(body, b_r, topF)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── double_male ──────────────────────────────────────────────────────────────
def build_double_male():
    """Male thread A + male thread B, joined by a central hex body. Joins two
    female fittings of possibly-different standards."""
    maleA, topA, srA, majA, outA = male_end(thread_a, clearance, wall, turns, 0.0)
    body_od = max(outA, spec(thread_b)["major_d"] + 2.0 * wall) + 2.0
    body_h = max(7.0, wall * 2.0 + 4.0)
    if hex_grip:
        mid = _hex_mid(body_od, body_od * 0.98, body_h + 0.5, topA - 0.5)
    else:
        mid = (
            cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, topA - 0.5))
            .circle(body_od / 2.0).extrude(body_h + 0.5)
        )
    maleB, topB, srB, majB, outB = male_end(thread_b, clearance, wall, turns, topA + body_h)
    body = maleA.union(mid).union(maleB)

    b_r = max(1.5, min(bore, min(srA * 2.0, srB * 2.0) - 1.6) / 2.0)
    body = _through_bore(body, b_r, topB)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── hose_bib ─────────────────────────────────────────────────────────────────
def build_hose_bib():
    """Female thread A on the bottom (drops onto a spigot / hose bib) + male
    thread B on top: the garden-hose-to-pipe / tap adapter, hex grip in the
    middle, through bore."""
    fem, topF, odF, brF = female_end(thread_a, clearance, wall, turns, 0.0)
    body_od = max(odF, spec(thread_b)["major_d"] + 2.0 * wall) + 2.0
    body_h = max(7.0, wall * 2.0 + 4.0)
    if hex_grip:
        mid = _hex_mid(body_od, body_od * 0.98, body_h + 0.5, topF - 0.5)
    else:
        mid = (
            cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, topF - 0.5))
            .circle(body_od / 2.0).extrude(body_h + 0.5)
        )
    male, topM, srM, majM, outM = male_end(thread_b, clearance, wall, turns, topF + body_h)
    body = fem.union(mid).union(male)

    b_r = max(1.5, min(bore, min(brF * 2.0, srM * 2.0) - 1.6) / 2.0)
    body = _through_bore(body, b_r, topM)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "double_male":
    result = build_double_male()
elif target_part == "hose_bib":
    result = build_hose_bib()
else:
    result = build_male_to_female()
