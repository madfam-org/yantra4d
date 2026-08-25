"""
Squeeze Bottle Nozzle — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A precision dispensing nozzle for squeeze / dispenser bottles that use the common
"410" personal-care neck finishes: 28-410 (28 mm) and 24-410 (24 mm). Print a
tapered precision cone tip, a long thin needle applicator (glue / oil / flux), or a
controlled drip dome. The functional interface is a REAL 410-series female helical
thread (28 or 24 mm major diameter, ~3.18 mm pitch) — the same 28 mm bottle neck the
`filter-straw` cartridge threads onto.

Thread strategy (verified watertight + fast):
  A trapezoidal rib is swept along a genuine `makeHelix` path and unioned into the
  bore wall, with the rib root pushed into the wall for a clean volumetric boolean.
  The socket has a CLOSED shoulder — an open-ended threaded socket terminates the
  helical rib at a free rim and tessellates non-watertight; the dispensing channel
  is bored through the shoulder afterward. Turn count is forced to a HALF-INTEGER
  (floor(n)+0.5): a whole-integer turn count degenerates the OCCT helical sweep into
  a negative-volume / null body.

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


# ── 410-series dispenser neck finishes (nominal geometry) ────────────────────
# major_d = male thread outer (major) diameter; pitch = thread pitch; ~1.5 turns
# ("410" is a tall single-lead thread).
NECKS = {
    "28-410": {"major_d": 28.0, "pitch": 3.18, "turns": 1.5},
    "24-410": {"major_d": 24.0, "pitch": 3.18, "turns": 1.5},
}


def neck_geo(name):
    return NECKS.get(name, NECKS["28-410"])


def half_turns(n):
    """Nearest lower half-integer, never a whole integer (whole → null sweep)."""
    return math.floor(max(0.5, n)) + 0.5


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "cone_nozzle"))  # cone|needle|drip
neck = str(PARAM(lambda: neck, "28-410"))                     # 28-410 | 24-410

clearance = float(PARAM(lambda: clearance, 0.4))   # printed-thread fit slop (per side, mm)
wall = float(PARAM(lambda: wall, 2.2))             # radial wall around the thread (mm)
top_th = float(PARAM(lambda: top_th, 2.2))         # shoulder thickness (mm)
turns = float(PARAM(lambda: turns, 1.5))           # 410 engagement turns
grip_knurl = bool(PARAM(lambda: grip_knurl, True))  # outer grip flutes

# Cone nozzle
cone_h = float(PARAM(lambda: cone_h, 18.0))        # cone height (mm)
tip_dia = float(PARAM(lambda: tip_dia, 2.0))       # tip orifice diameter (mm)

# Needle nozzle
needle_len = float(PARAM(lambda: needle_len, 30.0))  # needle length (mm)
needle_od = float(PARAM(lambda: needle_od, 4.0))     # needle outer diameter (mm)
needle_id = float(PARAM(lambda: needle_id, 1.5))     # needle bore (mm)

# Drip nozzle
drip_dia = float(PARAM(lambda: drip_dia, 1.2))     # drip orifice diameter (mm)
dome_h = float(PARAM(lambda: dome_h, 6.0))         # drip dome height (mm)

clearance = max(0.0, min(clearance, 1.0))
wall = max(1.6, min(wall, 5.0))
top_th = max(1.4, min(top_th, 5.0))
turns = max(1.5, min(turns, 3.5))
cone_h = max(6.0, min(cone_h, 45.0))
tip_dia = max(0.6, min(tip_dia, 10.0))
needle_len = max(10.0, min(needle_len, 70.0))
needle_od = max(2.5, min(needle_od, 10.0))
needle_id = max(0.6, min(needle_id, 6.0))
drip_dia = max(0.5, min(drip_dia, 6.0))
dome_h = max(2.0, min(dome_h, 20.0))


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


def neck_socket(neck_name, clear, wall_th, base_th, n_turns):
    """A CLOSED-SHOULDER cylindrical socket with an internal 410 female thread.
    Opens at z=0; a solid `base_th` shoulder caps the top. Returns
    (solid, height, outer_d, bore_r)."""
    g = neck_geo(neck_name)
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
    bore = cq.Workplane("XY").circle(bore_r).extrude(thread_h + 0.6)
    body = body.cut(bore)
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, overlap))
    return body, body_h, outer_d, bore_r


def apply_knurl(solid, outer_d, height, teeth=24, depth=0.6):
    """Cut shallow vertical flutes around the outside for grip (one boolean)."""
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


# ── Part builders ────────────────────────────────────────────────────────────
def build_cone_nozzle():
    """Female 410 thread + a tapered precision cone with a small tip orifice
    (cut the tip back with a knife to open the bore wider — a classic twist-cap)."""
    body, body_h, outer_d, bore_r = neck_socket(neck, clearance, wall, top_th, turns)
    if grip_knurl:
        body = apply_knurl(body, outer_d, body_h)

    base_r = min(outer_d / 2.0 - 1.0, bore_r + 1.5)
    tip_r = max(tip_dia / 2.0 + 0.8, 1.2)
    cone = (
        cq.Workplane("XY")
        .circle(base_r)
        .workplane(offset=cone_h)
        .circle(tip_r)
        .loft(combine=True)
        .translate((0, 0, body_h))
    )
    body = body.union(cone)
    # Dispensing channel: bore from the bottle bore up through the cone to the tip.
    tr = max(0.3, tip_dia / 2.0)
    channel = (
        cq.Workplane("XY")
        .circle(bore_r - 1.0)
        .workplane(offset=cone_h + top_th + 1.5)
        .circle(tr)
        .loft(combine=True)
        .translate((0, 0, body_h - top_th - 1.0))
    )
    body = body.cut(channel)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_needle_nozzle():
    """Female 410 thread + a long thin needle applicator for fine, precise flow
    (adhesives, oils, flux)."""
    body, body_h, outer_d, bore_r = neck_socket(neck, clearance, wall, top_th, turns)
    if grip_knurl:
        body = apply_knurl(body, outer_d, body_h)

    n_od = needle_od
    n_or = n_od / 2.0
    n_ir = min(needle_id, n_od - 1.4) / 2.0
    # A cone shoulder blends the socket up to the needle base (avoids a thin ledge).
    blend_h = 4.0
    base_r = min(outer_d / 2.0 - 1.0, bore_r + 1.5)
    blend = (
        cq.Workplane("XY")
        .circle(base_r)
        .workplane(offset=blend_h)
        .circle(n_or)
        .loft(combine=True)
        .translate((0, 0, body_h))
    )
    needle = (
        cq.Workplane("XY").circle(n_or).extrude(needle_len).translate((0, 0, body_h + blend_h))
    )
    body = body.union(blend).union(needle)
    # Bore the needle channel from the bottle bore all the way to the needle tip.
    channel = (
        cq.Workplane("XY")
        .circle(n_ir)
        .extrude(blend_h + needle_len + top_th + 2.0)
        .translate((0, 0, body_h - top_th - 1.0))
    )
    body = body.cut(channel)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_drip_nozzle():
    """Female 410 thread + a low dome with a single tiny centre orifice for a
    controlled drip / drop dispense (dropper-style)."""
    body, body_h, outer_d, bore_r = neck_socket(neck, clearance, wall, top_th, turns)
    if grip_knurl:
        body = apply_knurl(body, outer_d, body_h)

    # Low truncated-cone dome (a clean loft — avoids sphere-pole meshing artifacts).
    base_r = min(outer_d / 2.0 - 1.0, bore_r + 1.5)
    tip_r = max(drip_dia / 2.0 + 1.2, base_r * 0.45)
    dome = (
        cq.Workplane("XY")
        .circle(base_r)
        .workplane(offset=dome_h)
        .circle(tip_r)
        .loft(combine=True)
        .translate((0, 0, body_h))
    )
    body = body.union(dome)
    # A small blind reservoir under the dome, opened by a tiny drip orifice on top.
    dr = max(0.25, drip_dia / 2.0)
    reservoir = (
        cq.Workplane("XY")
        .circle(bore_r - 1.0)
        .extrude(top_th + 0.5)
        .translate((0, 0, body_h - top_th - 0.5))
    )
    body = body.cut(reservoir)
    orifice = (
        cq.Workplane("XY")
        .circle(dr)
        .extrude(dome_h + top_th + 3.0)
        .translate((0, 0, body_h - top_th - 1.0))
    )
    body = body.cut(orifice)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "needle_nozzle":
    result = build_needle_nozzle()
elif target_part == "drip_nozzle":
    result = build_drip_nozzle()
else:
    result = build_cone_nozzle()
