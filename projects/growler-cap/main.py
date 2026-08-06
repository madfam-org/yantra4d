"""
Growler Cap / Handle — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A replacement sealing cap for standard 32 oz / 64 oz screw-top growlers, which
almost universally use the 38 mm "38-400" continuous-thread finish. Print a plain
sealing cap, a cap with an integral carry handle, or a carbonation cap with a
central boss bored for a gas-line grommet (home carbonation / serving). The
functional interface is a REAL 38-400 female helical thread (38 mm major diameter,
coarse ~4.2 mm pitch).

Thread strategy (verified watertight + fast):
  A trapezoidal rib is swept along a genuine `makeHelix` path and unioned into the
  bore wall, with the rib root pushed into the wall for a clean volumetric boolean.
  The socket has a CLOSED base — an open-ended threaded socket terminates the
  helical rib at a free rim and tessellates non-watertight; flow / gas bores are cut
  through the base afterward. Turn count is forced to a HALF-INTEGER (floor(n)+0.5):
  a whole-integer turn count degenerates the OCCT helical sweep into a null body.

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


# ── Growler 38-400 finish (nominal geometry) ─────────────────────────────────
# major_d = male thread outer (major) diameter; pitch = thread pitch; ~1.5 turns.
GROWLER = {"major_d": 38.0, "pitch": 4.2, "turns": 1.5}


def half_turns(n):
    """Nearest lower half-integer, never a whole integer (whole → null sweep)."""
    return math.floor(max(0.5, n)) + 0.5


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "sealing_cap"))  # sealing|handle|carbonation

clearance = float(PARAM(lambda: clearance, 0.5))   # printed-thread fit slop (per side, mm)
wall = float(PARAM(lambda: wall, 3.0))             # radial wall around the thread (mm)
top_th = float(PARAM(lambda: top_th, 3.0))         # cap top thickness (mm)
turns = float(PARAM(lambda: turns, 1.5))           # 38-400 engagement turns
grip_knurl = bool(PARAM(lambda: grip_knurl, True))  # outer grip flutes

# Handle options
handle_w = float(PARAM(lambda: handle_w, 12.0))    # handle strap width (mm)
handle_h = float(PARAM(lambda: handle_h, 34.0))    # handle loop height (mm)
handle_t = float(PARAM(lambda: handle_t, 8.0))     # handle strap thickness (mm)

# Carbonation options
port_dia = float(PARAM(lambda: port_dia, 9.5))     # gas-line grommet bore (mm)
boss_dia = float(PARAM(lambda: boss_dia, 20.0))    # raised central boss diameter (mm)
boss_h = float(PARAM(lambda: boss_h, 8.0))         # boss height above the cap (mm)

clearance = max(0.0, min(clearance, 1.2))
wall = max(2.0, min(wall, 6.0))
top_th = max(1.8, min(top_th, 6.0))
turns = max(1.5, min(turns, 3.5))
handle_w = max(6.0, min(handle_w, 30.0))
handle_h = max(15.0, min(handle_h, 70.0))
handle_t = max(4.0, min(handle_t, 16.0))
port_dia = max(2.0, min(port_dia, 20.0))
boss_dia = max(10.0, min(boss_dia, 34.0))
boss_h = max(3.0, min(boss_h, 25.0))


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


def growler_socket(clear, wall_th, base_th, n_turns):
    """A CLOSED-BASE cylindrical socket with an internal 38-400 female thread.
    Opens at z=0; a solid `base_th` disk caps the top. Returns
    (solid, height, outer_d, bore_r)."""
    g = GROWLER
    tt = half_turns(n_turns)
    pitch = g["pitch"]
    thr_major = g["major_d"] + 2.0 * clear
    bore_r = thr_major / 2.0
    thr_depth = 0.5 * pitch
    overlap = min(0.7, wall_th * 0.35 + 0.2)
    thread_h = pitch * tt

    outer_d = thr_major + 2.0 * wall_th
    body_h = thread_h + base_th + 1.5

    body = cq.Workplane("XY").circle(outer_d / 2.0).extrude(body_h)
    bore = cq.Workplane("XY").circle(bore_r).extrude(thread_h + 0.6)
    body = body.cut(bore)
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, overlap))
    return body, body_h, outer_d, bore_r


def apply_knurl(solid, outer_d, height, teeth=28, depth=0.8):
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
def build_sealing_cap():
    """Plain 38-400 growler sealing cap: female thread, sealed top, grip knurl."""
    body, body_h, outer_d, bore_r = growler_socket(clearance, wall, top_th, turns)
    # Socket opens DOWN at z=0 (screws onto the growler); sealed top at z≈body_h.
    if grip_knurl:
        body = apply_knurl(body, outer_d, body_h)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_handle_cap():
    """Growler cap with an integral D-handle loop across the top for carrying."""
    body, body_h, outer_d, bore_r = growler_socket(clearance, wall, top_th, turns)
    # Socket opens DOWN at z=0; the sealed top (z≈body_h) carries the handle feet.
    if grip_knurl:
        body = apply_knurl(body, outer_d, body_h)

    # Handle: an inverted-U loop rising from two feet on the cap top. Built as an
    # outer rounded slab minus an inner slot so it prints as a graspable loop.
    span = min(outer_d - handle_w, outer_d * 0.72)
    ht = handle_t
    hw = handle_w
    rise = handle_h
    outer_loop = (
        cq.Workplane("XZ")
        .workplane(offset=-hw / 2.0)
        .moveTo(-span / 2.0 - ht, 0)
        .lineTo(-span / 2.0 - ht, rise)
        .threePointArc((0, rise + span / 2.0 + ht), (span / 2.0 + ht, rise))
        .lineTo(span / 2.0 + ht, 0)
        .lineTo(span / 2.0, 0)
        .lineTo(span / 2.0, rise)
        .threePointArc((0, rise + span / 2.0), (-span / 2.0, rise))
        .lineTo(-span / 2.0, 0)
        .close()
        .extrude(hw)
        .translate((0, 0, body_h - 0.5))
    )
    body = body.union(outer_loop)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_carbonation_cap():
    """Growler cap with a raised central boss bored for a gas-line grommet — for
    home carbonation / low-pressure serving. The bore passes through into the
    growler; fit a rubber grommet + gas line (silicone parts are out of scope)."""
    body, body_h, outer_d, bore_r = growler_socket(clearance, wall, top_th, turns)
    # Socket opens DOWN at z=0; the sealed top (z≈body_h) carries the boss.
    if grip_knurl:
        body = apply_knurl(body, outer_d, body_h)

    bd = min(boss_dia, outer_d - 4.0)
    boss = (
        cq.Workplane("XY")
        .circle(bd / 2.0)
        .extrude(boss_h)
        .translate((0, 0, body_h))
    )
    body = body.union(boss)
    # Bore the gas port straight through the boss and cap top into the growler.
    pr = min(port_dia, bd - 3.0) / 2.0
    port = (
        cq.Workplane("XY")
        .circle(pr)
        .extrude(boss_h + top_th + 4.0)
        .translate((0, 0, body_h - top_th - 2.0))
    )
    body = body.cut(port)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "handle_cap":
    result = build_handle_cap()
elif target_part == "carbonation_cap":
    result = build_carbonation_cap()
else:
    result = build_sealing_cap()
