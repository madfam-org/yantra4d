"""
PCO-1881 Bottle Cap — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A reusable screw cap for the world's most abundant standardized vessel: the
PCO-1881 soda / water bottle neck (27.43 mm thread major diameter, 2.7 mm pitch,
single-start). Print a replacement cap for a bottle whose cap was lost, or upgrade
a plain bottle into a tethered (anti-loss) or sport-spout drinking bottle. The
functional interface is a REAL helical female thread that mates with the same
PCO-1881 neck the `bottle-thread`, `bird-feeder`, `faircap-filter`, and
`pet-dispenser` cartridges use.

Thread strategy (verified watertight + fast):
  A trapezoidal rib is swept along a genuine `makeHelix` path and unioned into the
  bore wall. The rib ROOT is pushed `overlap` mm into the wall so the boolean is a
  clean volumetric fusion, not a fragile tangent kiss (a rib whose root sits
  exactly on the bore surface tessellates into cracks). The turn count is forced to
  a HALF-INTEGER (floor(n)+0.5): an integer turn count degenerates the OCCT helical
  sweep — the swept profile closes back on itself, the orientation flips, and the
  boolean yields a negative-volume / null body. A half-integer is well-conditioned
  and far faster.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `clearance`).
  - Access them via PARAM(lambda: <name>, <default>) — globals()/eval/getattr are
    not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default. `except Exception`
    catches the NameError raised for an unbound param name."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── PCO-1881 neck finish (nominal geometry) ──────────────────────────────────
# major_d = male thread outer (major) diameter; pitch = thread pitch.
# ~3 physical turns of engagement; modeled at 3.5 (half-integer, see module doc).
PCO1881 = {"major_d": 27.43, "pitch": 2.7, "turns": 3.5}


def half_turns(n):
    """Force a thread turn count to the nearest lower half-integer (never whole).
    Whole-integer turns degenerate the OCCT helical sweep into a null body."""
    return math.floor(max(0.5, n)) + 0.5


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "simple_cap"))  # simple|tethered|sport

clearance = float(PARAM(lambda: clearance, 0.4))   # printed-thread fit slop (per side, mm)
wall = float(PARAM(lambda: wall, 2.6))             # radial wall around the thread (mm)
top_th = float(PARAM(lambda: top_th, 2.4))         # cap top thickness (mm)
turns = float(PARAM(lambda: turns, 3.5))           # PCO-1881 engagement turns
grip_knurl = bool(PARAM(lambda: grip_knurl, True))  # outer grip flutes
skirt_h = float(PARAM(lambda: skirt_h, 3.0))       # extra skirt below the thread (mm)

# Tethered-cap options
tether_len = float(PARAM(lambda: tether_len, 26.0))  # tether strap length (mm)
ring_id = float(PARAM(lambda: ring_id, 26.0))        # anchor-ring inner diameter (mm)

# Sport-cap options
spout_dia = float(PARAM(lambda: spout_dia, 7.0))   # drink-spout bore (mm)
spout_h = float(PARAM(lambda: spout_h, 14.0))      # drink-spout height above cap (mm)

# Clamp inputs so extreme UI values still build watertight.
clearance = max(0.0, min(clearance, 1.0))
wall = max(1.6, min(wall, 6.0))
top_th = max(1.2, min(top_th, 6.0))
turns = max(1.5, min(turns, 4.5))
skirt_h = max(0.0, min(skirt_h, 10.0))
tether_len = max(10.0, min(tether_len, 60.0))
ring_id = max(15.0, min(ring_id, 45.0))
spout_dia = max(2.0, min(spout_dia, 18.0))
spout_h = max(4.0, min(spout_h, 40.0))


# ── Thread primitive (inlined — repo-lib imports are blocked in sandbox) ──────
def _helix_path(pitch, height):
    """A helical wire on Z. radius ~0 so the swept profile (already at its target
    radius in its own plane) traces the true helix."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal (female) helical rib. Ridges point INWARD from the bore wall to
    grab the male bottle thread. Root radius = bore_r + overlap (bites into wall
    → clean watertight union); crest at bore_r - thr_depth."""
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


def threaded_socket(clear, wall_th, base_th, with_base, n_turns, skirt=0.0):
    """A cylindrical socket with an internal PCO-1881 female thread.

    Returns (solid, socket_height, outer_d, bore_r, thread_h). Opens at z=0
    (bottom); `with_base` closes the top with a `base_th` disk. `skirt` adds plain
    wall below the thread start for a longer grip / seal lead-in."""
    g = PCO1881
    tt = half_turns(n_turns)
    pitch = g["pitch"]
    thr_major = g["major_d"] + 2.0 * clear
    bore_r = thr_major / 2.0
    thr_depth = 0.55 * pitch
    overlap = min(0.6, wall_th * 0.35 + 0.2)
    thread_h = pitch * tt

    outer_d = thr_major + 2.0 * wall_th
    body_h = thread_h + skirt + (base_th if with_base else 0.0) + 1.5

    body = cq.Workplane("XY").circle(outer_d / 2.0).extrude(body_h)
    bore_depth = thread_h + skirt + (0.0 if with_base else 2.0) + 0.6
    bore = cq.Workplane("XY").circle(bore_r).extrude(bore_depth)
    body = body.cut(bore)
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, overlap))
    return body, body_h, outer_d, bore_r, thread_h


def apply_knurl(solid, outer_d, height, teeth=24, depth=0.7):
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
        pass  # knurl is cosmetic — never fatal
    return solid


# ── Part builders ────────────────────────────────────────────────────────────
def build_simple_cap():
    """Plain PCO-1881 screw cap: female thread, flat sealed top, grip knurl."""
    body, body_h, outer_d, bore_r, thread_h = threaded_socket(
        clearance, wall, top_th, with_base=True, n_turns=turns, skirt=skirt_h
    )
    if grip_knurl:
        body = apply_knurl(body, outer_d, body_h)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_tethered_cap():
    """Anti-loss cap: a screw cap joined by a flexible strap to an anchor ring
    that slips over the bottle neck below the thread, so the cap can't be lost."""
    body, body_h, outer_d, bore_r, thread_h = threaded_socket(
        clearance, wall, top_th, with_base=True, n_turns=turns, skirt=skirt_h
    )
    if grip_knurl:
        body = apply_knurl(body, outer_d, body_h)

    cap_r = outer_d / 2.0
    strap_w = min(8.0, cap_r * 0.9)
    strap_t = max(1.6, top_th * 0.7)
    # Anchor ring: an annulus that captures the bottle neck under the support ledge.
    ring_r_in = ring_id / 2.0
    ring_r_out = ring_r_in + max(3.0, wall)
    ring_h = max(3.0, strap_t + 1.0)
    gap = tether_len  # centre-to-centre gap between cap and ring
    ring_cx = cap_r + gap + ring_r_out

    ring = (
        cq.Workplane("XY")
        .circle(ring_r_out).circle(ring_r_in)
        .extrude(ring_h)
        .translate((ring_cx, 0, 0))
    )
    # Flexible strap bridging cap wall → ring, overlapping both so it fuses solid.
    strap_len = (ring_cx - ring_r_out) - (cap_r - 1.0) + 1.0
    strap = (
        cq.Workplane("XY")
        .box(strap_len, strap_w, strap_t, centered=(False, True, False))
        .translate((cap_r - 1.0, 0, 0))
    )
    body = body.union(strap).union(ring)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_sport_cap():
    """Sport / drink cap: female thread onto the bottle, a raised nozzle with a
    narrow bore you drink through. The bore passes through the sealed top into the
    bottle; a printed silicone-free valve is out of scope — this is the pour spout."""
    body, body_h, outer_d, bore_r, thread_h = threaded_socket(
        clearance, wall, top_th, with_base=True, n_turns=turns, skirt=skirt_h
    )
    if grip_knurl:
        body = apply_knurl(body, outer_d, body_h)

    # Nozzle: a slightly tapered tube rising from the cap top.
    s_bore = min(spout_dia, outer_d - 4.0) / 2.0
    s_len = spout_h
    noz_wall = max(1.4, wall - 0.8)
    base_r = min(outer_d / 2.0 - 1.0, s_bore + noz_wall + 2.5)
    tip_r = s_bore + noz_wall
    nozzle = (
        cq.Workplane("XY")
        .circle(base_r)
        .workplane(offset=s_len)
        .circle(tip_r)
        .loft(combine=True)
        .translate((0, 0, body_h))
    )
    body = body.union(nozzle)
    # Bore the drink channel through the nozzle and the cap top into the bottle.
    channel = (
        cq.Workplane("XY")
        .circle(s_bore)
        .extrude(s_len + top_th + 2.0)
        .translate((0, 0, body_h - top_th - 1.0))
    )
    body = body.cut(channel)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tethered_cap":
    result = build_tethered_cap()
elif target_part == "sport_cap":
    result = build_sport_cap()
else:
    result = build_simple_cap()
