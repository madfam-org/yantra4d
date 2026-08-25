"""
Lens Filter Step Ring — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Adapts one photographic filter thread to another. Screw-in filters and lens
fronts share a small family of nominal thread diameters (M46/M49/M52/M58/M62/
M67/M72/M77/M82) at a fine 0.75 mm pitch. A step ring puts a female thread of one
size on the bottom and a male thread of another on top, so a filter made for one
diameter fits a lens made for another. This cartridge builds a step (female→male)
ring, a stacking coupler (female→female) and a reverse ring (male→male). Every
thread is a real filter thread, so it mates any filter-thread part (e.g. the
`lens-cap` snap cap and step ring).

Filter thread standard (nominal, dimensionally real):
  - major diameter = the nominal size (46/49/52/58/62/67/72/77/82 mm)
  - pitch          = 0.75 mm (the common fine filter-thread pitch)
  - male crest sits at the major diameter; female bore = major + fit clearance.

Thread strategy — COSMETIC serrated solids of revolution (as `lens-cap` ships):
  A sawtooth radial profile is revolved 360°, so male crests trace the nominal
  major diameter and the female bore relief traces a matching minor. One revolve
  per thread (no per-turn helical booleans) is fast AND inherently watertight —
  the right idiom for a light, quick-screwing filter thread. (A true makeHelix
  sweep at these 23-41 mm radii is both far slower and prone to severed
  non-watertight bodies here.)

Three modes (each geometrically distinct):
  - step_ring    : female A (bottom) → male B (top) — step-up / step-down.
  - coupler_ring : female A (bottom) → female B (top) — stacks two filters.
  - reverse_ring : male A (bottom) → male B (top) — joins two female threads.

Watertight strategy:
  Threads are single solids of revolution. The central light bore is a THROUGH
  hole (open both ends → vents to outside). No tangent unions, no post-cut
  fillets on complex features; a final .clean() wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Filter thread table (nominal major dia in mm; fine pitch) ────────────────
FILTER = {
    "46": {"major": 46.0, "pitch": 0.75},
    "49": {"major": 49.0, "pitch": 0.75},
    "52": {"major": 52.0, "pitch": 0.75},
    "58": {"major": 58.0, "pitch": 0.75},
    "62": {"major": 62.0, "pitch": 0.75},
    "67": {"major": 67.0, "pitch": 0.75},
    "72": {"major": 72.0, "pitch": 0.75},
    "77": {"major": 77.0, "pitch": 0.75},
    "82": {"major": 82.0, "pitch": 0.75},
}


def filt(name, fallback="58"):
    """Look up a filter-thread spec, defaulting to 58 mm."""
    return FILTER.get(str(name), FILTER[fallback])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "step_ring"))
# "step_ring" | "coupler_ring" | "reverse_ring"

thread_a = str(PARAM(lambda: thread_a, "58"))  # bottom size
thread_b = str(PARAM(lambda: thread_b, "52"))  # top size

clearance = float(PARAM(lambda: clearance, 0.3))       # printed-thread fit slop (per side)
wall = float(PARAM(lambda: wall, 2.4))                 # side wall thickness (mm)
top_th = float(PARAM(lambda: top_th, 2.2))             # web thickness (mm)
thread_turns = float(PARAM(lambda: thread_turns, 4.5))  # thread engagement turns
grip_teeth = int(PARAM(lambda: grip_teeth, 0))         # optional grip flutes (0=off)

# Clamp to sane ranges so extreme UI values never crash the kernel.
clearance = max(0.1, min(clearance, 0.8))
wall = max(1.6, min(wall, 6.0))
top_th = max(1.2, min(top_th, 6.0))
thread_turns = max(2.5, min(thread_turns, 8.0))
grip_teeth = max(0, min(grip_teeth, 80))


# ── Cosmetic thread solids of revolution ─────────────────────────────────────
def cosmetic_male_ring(major, pitch, length, z0, turns):
    """Male filter thread as a single solid of revolution (serrated profile
    revolved 360°): crest at major/2, root at major/2 - depth. Watertight."""
    depth = 0.55 * pitch
    r_maj = major / 2.0
    r_min = r_maj - depth
    n = max(1, int(round(min(turns, length / pitch))))
    tooth = length / n
    pts = [(0.0, 0.0), (r_min, 0.0)]
    for i in range(n):
        z_lo = i * tooth
        pts.append((r_maj, z_lo + tooth * 0.5))
        pts.append((r_min, z_lo + tooth))
    pts.append((0.0, length))
    section = cq.Workplane("XZ").polyline(pts).close()
    return section.revolve(360, (0, 0, 0), (0, 1, 0)).translate((0, 0, z0))


def female_bore_cutter(major, pitch, length, z0, turns, clear):
    """A cutter matching a female filter thread: subtract from a tube to leave
    internal threads whose crests sit near the male minor. Bore major = major +
    2*clear. Serrated solid of revolution → watertight cut."""
    bore_major = major + 2.0 * clear
    depth = 0.55 * pitch
    r_maj = bore_major / 2.0
    r_min = r_maj - depth
    n = max(1, int(round(min(turns, length / pitch))))
    tooth = length / n
    pts = [(0.0, 0.0), (r_maj, 0.0)]
    for i in range(n):
        z_lo = i * tooth
        pts.append((r_min, z_lo + tooth * 0.5))
        pts.append((r_maj, z_lo + tooth))
    pts.append((0.0, length))
    section = cq.Workplane("XZ").polyline(pts).close()
    return section.revolve(360, (0, 0, 0), (0, 1, 0)).translate((0, 0, z0))


def apply_flutes(solid, outer_d, height, teeth, depth=0.6):
    """Shallow vertical grip flutes around the outside (one polar-array cut)."""
    if teeth <= 0:
        return solid
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


def _light_bore(body, a_major, b_major, total_h):
    """A clear central through-bore so light passes (vents both ends)."""
    light_r = max(3.0, min(a_major, b_major) / 2.0 - wall - 1.0)
    channel = (
        cq.Workplane("XY")
        .circle(light_r)
        .extrude(total_h + 2.0)
        .translate((0, 0, -1.0))
    )
    return body.cut(channel)


# ── Part builders ────────────────────────────────────────────────────────────
def build_step_ring():
    """Female A (bottom, screws onto a lens) → male B (top, accepts a filter of
    size B). A short web joins them; a through-bore passes light."""
    ga, gb = filt(thread_a), filt(thread_b)
    pa, pb = ga["pitch"], gb["pitch"]
    thr_a_h = pa * thread_turns
    thr_b_h = pb * thread_turns

    a_bore_major = ga["major"] + 2.0 * clearance
    female_od = a_bore_major + 2.0 * wall
    b_major = gb["major"]
    male_root_od = b_major - 2.0 * (0.55 * pb) - 0.2

    female_h = thr_a_h + 1.0
    web_h = max(top_th, 1.6)
    male_h = thr_b_h + 1.0
    total_h = female_h + web_h + male_h

    female_body = cq.Workplane("XY").circle(female_od / 2.0).extrude(female_h + web_h)
    female_body = female_body.cut(
        female_bore_cutter(ga["major"], pa, female_h + 0.6, -0.01, thread_turns, clearance)
    )

    male_tube = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, female_h + web_h - 0.01))
        .circle(male_root_od / 2.0)
        .extrude(male_h + 0.01)
    )
    male_threads = cosmetic_male_ring(b_major, pb, male_h, female_h + web_h, thread_turns)
    ring = female_body.union(male_tube.union(male_threads))
    ring = _light_bore(ring, ga["major"], gb["major"], total_h)
    ring = apply_flutes(ring, female_od, female_h + web_h, grip_teeth)
    try:
        ring = ring.clean()
    except Exception:
        pass
    return ring


def build_coupler_ring():
    """Female A (bottom) → female B (top): a coupling ring that screws a
    male-threaded filter onto each face, stacking two filters back-to-back."""
    ga, gb = filt(thread_a), filt(thread_b)
    pa, pb = ga["pitch"], gb["pitch"]
    thr_a_h = pa * thread_turns
    thr_b_h = pb * thread_turns

    od = max(ga["major"], gb["major"]) + 2.0 * clearance + 2.0 * wall
    female_a_h = thr_a_h + 1.0
    female_b_h = thr_b_h + 1.0
    web_h = max(top_th, 1.6)
    total_h = female_a_h + web_h + female_b_h

    body = cq.Workplane("XY").circle(od / 2.0).extrude(total_h)
    # Bottom female bore + threads (open at bottom).
    body = body.cut(
        female_bore_cutter(ga["major"], pa, female_a_h + 0.6, -0.01, thread_turns, clearance)
    )
    # Top female bore + threads (open at top): build the cutter, flip it about X
    # so it opens upward, and place it at the top.
    top_cut = female_bore_cutter(gb["major"], pb, female_b_h + 0.6, -0.01, thread_turns, clearance)
    top_cut = top_cut.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, total_h + 0.01))
    body = body.cut(top_cut)

    body = _light_bore(body, ga["major"], gb["major"], total_h)
    body = apply_flutes(body, od, total_h, grip_teeth)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_reverse_ring():
    """Male A (bottom) → male B (top): a reverse ring that threads into a female
    filter thread on each end (e.g. couple a lens filter thread to another)."""
    ga, gb = filt(thread_a), filt(thread_b)
    pa, pb = ga["pitch"], gb["pitch"]
    thr_a_h = pa * thread_turns
    thr_b_h = pb * thread_turns

    a_root = ga["major"] / 2.0 - 0.55 * pa - 0.1
    b_root = gb["major"] / 2.0 - 0.55 * pb - 0.1
    a_h = thr_a_h + 1.0
    web_h = max(top_th, 1.6)
    b_h = thr_b_h + 1.0
    total_h = a_h + web_h + b_h

    a_tube = cq.Workplane("XY").circle(a_root + 0.05).extrude(a_h + web_h)
    a_thr = cosmetic_male_ring(ga["major"], pa, a_h, 0.0, thread_turns)
    b_tube = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, a_h + web_h - 0.01))
        .circle(b_root + 0.05)
        .extrude(b_h + 0.01)
    )
    b_thr = cosmetic_male_ring(gb["major"], pb, b_h, a_h + web_h, thread_turns)
    body = a_tube.union(a_thr).union(b_tube).union(b_thr)

    body = _light_bore(body, ga["major"], gb["major"], total_h)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "coupler_ring":
    result = build_coupler_ring()
elif target_part == "reverse_ring":
    result = build_reverse_ring()
else:  # "step_ring"
    result = build_step_ring()
