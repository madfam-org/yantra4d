"""Pump Adapter — Soap Dispenser / Pump Bottle Adapter (Yantra4D Hyperobject).

Refill and pump adapters for soap / lotion / sanitizer dispensers, built around
the REAL SPI "410" continuous-thread bottle-neck finishes that pump dispensers
and refill bottles use: 20-410, 24-410, and 28-410 (major Ø 20 / 24 / 28 mm,
8-TPI continuous thread → 3.175 mm pitch). Threads are FUNCTIONAL single-start
helical ribs, not cosmetic grooves.

Three distinct thread modes:
  * pump_collar  — a female-threaded collar that screws onto a bottle neck and
    presents a top opening for a standard pump-stem insert.
  * neck_reducer — female thread on the bottom (fits neck A) + male thread on top
    (fits a pump/cap sized for neck B): a 410-to-410 size translator.
  * travel_cap   — a sealing screw cap (female thread + solid top) that closes a
    dispenser bottle for travel.

Thread strategy (verified watertight + fast): sweep a trapezoidal profile along
a genuine `cq.Wire.makeHelix` path. The rib ROOT is pushed into the wall
(`overlap`) so the union is a clean volumetric boolean (watertight), never a
tangent kiss. CRITICAL: the turn count is snapped to a HALF-INTEGER
(floor(n)+0.5). An integer turn count degenerates the OCCT helical sweep — the
profile closes on itself, orientation flips, and the boolean yields a
negative-volume/null body. A half-integer count is well-conditioned and fast.

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


# ── SPI 410 continuous-thread neck finishes (nominal) ────────────────────────
# major_d = male thread outer (major) diameter (mm); pitch = thread pitch (mm).
# 410 finishes are 8 TPI → 25.4/8 = 3.175 mm pitch. These are the finishes on
# pump / lotion / sanitizer bottles and their refill counterparts.
NECK_SPECS = {
    "20-410": {"major_d": 20.0, "pitch": 3.175},
    "24-410": {"major_d": 24.0, "pitch": 3.175},
    "28-410": {"major_d": 28.0, "pitch": 3.175},
}


def neck_spec(name):
    return NECK_SPECS.get(str(name).strip(), NECK_SPECS["28-410"])


def half_int_turns(n):
    """Snap to a half-integer (floor(n) + 0.5), clamped to [1.5, 3.5].

    A half-integer turn count keeps the OCCT helical sweep well-conditioned (an
    integer count degenerates to a negative-volume/null body). The upper clamp
    keeps the helical-rib boolean fast and robust: beyond ~3.5 turns the fuse
    grows super-linearly and can exhaust OCCT on a dual-thread part — and real
    410 pump necks only engage ~2-3 turns anyway, so 3.5 is ample engagement."""
    base = math.floor(n)
    return max(1.5, min(3.5, base + 0.5))


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "pump_collar"))
neck_a      = str(PARAM(lambda: neck_a,       "28-410"))   # bottom / primary neck
neck_b      = str(PARAM(lambda: neck_b,       "24-410"))   # top neck (reducer)
clearance   = float(PARAM(lambda: clearance,   0.4))       # printed-thread fit (per side)
wall        = float(PARAM(lambda: wall,        2.6))       # radial wall around thread
top_th      = float(PARAM(lambda: top_th,      2.4))       # cap / shoulder thickness
turns       = float(PARAM(lambda: turns,       3.0))       # requested engagement turns
pump_bore   = float(PARAM(lambda: pump_bore,  20.0))       # pump-stem opening Ø (collar)
knurl       = bool(PARAM(lambda: knurl,        True))      # outer grip flutes

clearance = max(0.0, min(clearance, 1.0))
wall      = max(1.6, min(wall, 6.0))
top_th    = max(1.2, min(top_th, 6.0))
turns     = max(1.5, min(turns, 6.0))
pump_bore = max(6.0, min(pump_bore, 34.0))


# ── Thread primitives (inlined; repo libs cannot be imported in the sandbox) ─
def _helix_path(pitch, height):
    """Helical wire on Z; radius ~0 so the swept profile (already at radius in
    its own plane) traces the true helix."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal (female) helical rib. Root at bore_r + overlap (bites into the
    wall → watertight union); crest points inward to bore_r - thr_depth."""
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


def male_thread(shaft_r, pitch, thread_h, thr_depth, overlap):
    """External (male) helical rib. Root bites in by overlap; crest sticks out to
    shaft_r + thr_depth."""
    root_r = max(0.5, shaft_r - overlap)
    crest_r = shaft_r + thr_depth
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


def _knurl(solid, outer_d, height, teeth=26, depth=0.7):
    """Shallow vertical grip flutes (single polar-array cut). Cosmetic → never
    fatal."""
    r = outer_d / 2.0
    try:
        cutter = (
            cq.Workplane("XY")
            .polarArray(radius=r, startAngle=0, angle=360, count=teeth)
            .rect(depth, depth * 3.0)
            .extrude(height + 2.0)
            .translate((0, 0, -1.0))
        )
        solid = solid.cut(cutter)
    except Exception:
        pass
    return solid


def female_socket(spec, clear, wall_th, base_th, with_base, req_turns):
    """A cylindrical socket with an internal female thread for `spec`.
    Returns (solid, height, outer_d, bore_r). Opens at z=0 (bottom); `with_base`
    closes the top with a base_th disk."""
    pitch = spec["pitch"]
    t = half_int_turns(req_turns)
    thr_major = spec["major_d"] + 2.0 * clear
    bore_r = thr_major / 2.0
    thr_depth = 0.55 * pitch
    overlap = min(0.6, wall_th * 0.35 + 0.2)
    thread_h = pitch * t

    outer_d = thr_major + 2.0 * wall_th
    body_h = thread_h + (base_th if with_base else 0.0) + 2.0

    body = cq.Workplane("XY").circle(outer_d / 2.0).extrude(body_h)
    bore_depth = thread_h + (0.0 if with_base else 2.0) + 0.8
    bore = cq.Workplane("XY").circle(bore_r).extrude(bore_depth)
    body = body.cut(bore)
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, overlap))
    return body, body_h, outer_d, bore_r


def male_plug(spec, clear, req_turns):
    """A solid male-threaded plug for `spec` (fits a female cap/pump of that
    finish). Returns (solid, height, shaft_r, thr_major). Rooted at z=0.

    The core is made TALLER than the thread run (thread_h + 2*pitch) and the
    thread is swept starting ~half a pitch up, so BOTH rib ends are buried inside
    the solid cylinder — an exposed helical rib end would leave the mesh open."""
    pitch = spec["pitch"]
    t = half_int_turns(req_turns)
    # Male major = nominal major minus clearance per side (so a printed male fits
    # a real female / this project's female socket).
    thr_major = max(6.0, spec["major_d"] - 2.0 * clear)
    thr_depth = 0.55 * pitch
    shaft_r = thr_major / 2.0 - thr_depth
    overlap = 0.45
    thread_h = pitch * t
    core_h = thread_h + 2.0 * pitch

    core = cq.Workplane("XY").circle(shaft_r + 0.2).extrude(core_h)
    # male_thread already lifts the rib +pitch/2; the rib then spans
    # [pitch/2, thread_h + pitch/2], safely inside [0, core_h].
    core = core.union(male_thread(shaft_r, pitch, thread_h, thr_depth, overlap))
    return core, core_h, shaft_r, thr_major


# ── pump_collar ──────────────────────────────────────────────────────────────
def build_pump_collar():
    """Female thread onto neck A + a shoulder with a pump-stem opening on top."""
    body, body_h, outer_d, bore_r = female_socket(
        neck_spec(neck_a), clearance, wall, top_th, with_base=True, req_turns=turns
    )
    # Bore the pump-stem opening through the closed shoulder.
    stem_r = max(1.5, min(pump_bore, outer_d - 2.0 * wall) / 2.0)
    stem = cq.Workplane("XY").circle(stem_r).extrude(body_h + 2.0).translate((0, 0, -1.0))
    body = body.cut(stem)
    if knurl:
        body = _knurl(body, outer_d, body_h)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── neck_reducer ─────────────────────────────────────────────────────────────
def build_neck_reducer():
    """Female thread (neck A) on the bottom + male thread (neck B) on top: a
    410-to-410 size translator. A through channel passes product between them."""
    seg_a, hA, odA, brA = female_socket(
        neck_spec(neck_a), clearance, wall, 0.0, with_base=False, req_turns=turns
    )
    # Flip A so it screws DOWN onto the bottle; closed shoulder faces up.
    shoulder_th = max(1.6, top_th)
    seg_a = seg_a.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, hA))

    # Shoulder disk between the two ends.
    plug_b, hB, srB, majB = male_plug(neck_spec(neck_b), clearance, turns)
    shoulder_od = max(odA, majB + 2.0 * wall)
    shoulder = (
        cq.Workplane("XY").circle(shoulder_od / 2.0).extrude(shoulder_th).translate((0, 0, hA))
    )
    # Male plug rises above the shoulder.
    plug_b = plug_b.translate((0, 0, hA + shoulder_th))

    body = seg_a.union(shoulder).union(plug_b)

    # Through channel so product flows between neck A and the pump on neck B.
    chan_r = max(1.5, min(brA, srB) - 1.4)
    channel = (
        cq.Workplane("XY").circle(chan_r).extrude(hA + shoulder_th + hB + 2.0).translate((0, 0, -1.0))
    )
    body = body.cut(channel)
    if knurl:
        body = _knurl(body, shoulder_od, hA + shoulder_th)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── travel_cap ───────────────────────────────────────────────────────────────
def build_travel_cap():
    """A sealing screw cap: female thread onto neck A + a solid domed-flat top."""
    body, body_h, outer_d, bore_r = female_socket(
        neck_spec(neck_a), clearance, wall, top_th, with_base=True, req_turns=turns
    )
    # A small sealing lip inside the top (a short ring that presses the neck rim).
    lip_r = max(1.0, bore_r - 1.2)
    lip = (
        cq.Workplane("XY")
        .circle(bore_r - 0.2).circle(lip_r)
        .extrude(1.2)
        .translate((0, 0, body_h - top_th - 1.2))
    )
    body = body.union(lip)
    if knurl:
        body = _knurl(body, outer_d, body_h)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "neck_reducer":
    result = build_neck_reducer()
elif target_part == "travel_cap":
    result = build_travel_cap()
else:
    result = build_pump_collar()
