"""Lamp Socket Extender — E26/E27 Edison Screw Extender (Yantra4D Hyperobject).

Extends and adapts Edison lamp sockets around the REAL medium-screw-base
standard, so a bulb can be dropped lower, redirected, or an E26 fixture can carry
an E27 bulb (and vice-versa). The functional interface is a genuine single-start
helical Edison thread that mates with the same medium base the `lampshade` and
`socket-adapter` cartridges use, thickening the `e26-e27-lamp` family.

Real Edison geometry (nominal):
  * E26 — 26.05 mm thread major diameter (North-American medium base)
  * E27 — 26.40 mm thread major diameter (European medium base)
  * Both are 7-TPI single-start → 25.4 / 7 = 3.629 mm pitch.

Three distinct modes:
  * extender      — female Edison socket at the bottom (screws ONTO a lamp
    socket / accepts nothing) and a male Edison shell on top, separated by a
    drop tube, so a bulb sits `drop` mm lower / further out.
  * base_adapter  — female Edison thread (base A) below + male Edison thread
    (base B) above: an E26<->E27 translator with a wiring channel through it.
  * device_shell  — a hollow male Edison shell with a top collar, to screw a
    printed device / sensor / holder into a lamp socket.

THREAD TRAPS heeded (all four, learned the hard way):
  1. Turn count snapped to a HALF-INTEGER (floor+0.5, clamped ceiling) — an
     integer count degenerates the OCCT helical sweep to a negative-volume body.
  2. Female sockets get a CLOSED base disk (bore stops below a solid cap); the
     wiring channel is cut THROUGH the base afterward — open-both-ends bores
     tessellate non-watertight.
  3. No flip-then-attach: the unflipped socket already opens upward with its
     closed face down; features attach to solid, never to the open rim.
  4. Turn slider capped at a validated half-integer ceiling (4.5); the MAX case
     (all sliders max) is validated watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py): `cq` + `math` are
pre-injected globals; manifest parameters arrive as BARE globals — read them via
PARAM(lambda: name, default); assign the final solid to a top-level `result`.
NOTE: printed lamp parts carry NO current — this is a mechanical adapter only.
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


# ── Edison medium-screw-base standards (nominal real geometry) ───────────────
# major_d = male thread outer diameter (mm); pitch = 25.4/7 = 3.629 mm (7 TPI).
EDISON = {
    "E26": {"major_d": 26.05, "pitch": 3.629},
    "E27": {"major_d": 26.40, "pitch": 3.629},
}


def edison(name):
    return EDISON.get(str(name).strip(), EDISON["E26"])


def half_turns(n):
    """Half-integer turn count (floor(n)+0.5), clamped to a validated ceiling.
    An integer count degenerates the helical sweep to a negative-volume body;
    a too-tall sweep on a thin wall tessellates non-watertight (per-geometry
    ceiling found at 4.5 turns)."""
    return max(1.5, min(4.5, math.floor(max(0.5, n)) + 0.5))


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "extender"))   # extender|base_adapter|device_shell
edison_a = str(PARAM(lambda: edison_a, "E26"))              # lower / socket-side base
edison_b = str(PARAM(lambda: edison_b, "E26"))              # upper / bulb-side base
clearance = float(PARAM(lambda: clearance, 0.4))            # printed-thread fit (per side, mm)
wall = float(PARAM(lambda: wall, 2.6))                      # shell / socket wall thickness (mm)
turns = float(PARAM(lambda: turns, 3.0))                    # requested engagement turns
drop = float(PARAM(lambda: drop, 24.0))                     # extender drop-tube length (mm)
bore = float(PARAM(lambda: bore, 12.0))                     # central wiring bore (mm)
collar_h = float(PARAM(lambda: collar_h, 8.0))             # device-shell top collar height (mm)

# Clamp so extreme UI values still build watertight.
clearance = max(0.0, min(clearance, 1.0))
wall = max(1.8, min(wall, 5.0))
turns = max(1.5, min(turns, 4.5))
drop = max(6.0, min(drop, 80.0))
bore = max(4.0, min(bore, 22.0))
collar_h = max(3.0, min(collar_h, 20.0))


# ── Thread primitives (inlined — repo-lib imports are blocked in sandbox) ─────
def _helix_path(pitch, height):
    """A helical wire on Z. radius ~0 so the swept profile (already at its target
    radius in its own plane) traces the true helix."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal helical rib pointing INWARD from a bore wall. Root radius pushed
    `overlap` into the wall → clean volumetric union (not a fragile tangent kiss)."""
    root_r = bore_r + overlap
    crest_r = max(0.5, bore_r - thr_depth)
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -pitch * 0.32), (crest_r, -pitch * 0.14),
            (crest_r, pitch * 0.14), (root_r, pitch * 0.32),
        ]).close()
    )
    return prof.sweep(_helix_path(pitch, thread_h), isFrenet=True).translate((0, 0, pitch * 0.5))


def male_thread(shaft_r, pitch, thread_h, thr_depth, overlap):
    """External helical rib rising OUTWARD from a shaft. Root pushed into the
    shaft for a watertight fusion."""
    root_r = max(0.5, shaft_r - overlap)
    crest_r = shaft_r + thr_depth
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -pitch * 0.32), (crest_r, -pitch * 0.14),
            (crest_r, pitch * 0.14), (root_r, pitch * 0.32),
        ]).close()
    )
    return prof.sweep(_helix_path(pitch, thread_h), isFrenet=True).translate((0, 0, pitch * 0.5))


def male_shell(spec, clear, wall_th, req_turns, z0):
    """Hollow male Edison shell rooted at z0, opening upward. Returns
    (solid, top_z, shaft_r, inner_r). Core taller than the thread run so both
    rib ends are buried in solid (no free rim)."""
    pitch = spec["pitch"]
    t = half_turns(req_turns)
    thr_major = max(6.0, spec["major_d"] - 2.0 * clear)
    thr_depth = 0.55 * pitch
    shaft_r = thr_major / 2.0 - thr_depth
    overlap = 0.45
    thread_h = pitch * t
    core_h = thread_h + 2.0 * pitch
    inner_r = max(1.5, shaft_r - wall_th)
    core = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0))
        .circle(shaft_r + 0.2).extrude(core_h)
    )
    core = core.union(male_thread(shaft_r, pitch, thread_h, thr_depth, overlap).translate((0, 0, z0)))
    return core, z0 + core_h, shaft_r, inner_r


def knurl(solid, outer_d, height, teeth=24, depth=0.6):
    """Cosmetic outer grip flutes (one boolean, never fatal)."""
    r = outer_d / 2.0
    try:
        cutter = (
            cq.Workplane("XY").polarArray(radius=r, startAngle=0, angle=360, count=teeth)
            .rect(depth, depth * 3.0).extrude(height + 2.0).translate((0, 0, -1.0))
        )
        solid = solid.cut(cutter)
    except Exception:
        pass
    return solid


# ── extender ─────────────────────────────────────────────────────────────────
def build_extender():
    """Female Edison socket (screws onto the lamp socket) + a solid drop column +
    male Edison shell on top (accepts the bulb), bored straight through for
    wiring. The socket-outer wall AND the drop column are built as ONE extrude
    primitive so they can never desync; the male shell core overlaps the column
    top; the wiring channel is bored last. No trailing clean() on the assembled
    solid (which silently breaks watertightness on a feature-laden body)."""
    spec_a = edison(edison_a)
    spec_b = edison(edison_b)
    pitch = spec_a["pitch"]
    t = half_turns(turns)
    thread_h = pitch * t
    thr_major_f = spec_a["major_d"] + 2.0 * clearance
    bore_r = thr_major_f / 2.0
    thr_depth = 0.55 * pitch
    ov_f = min(0.6, wall * 0.35 + 0.2)
    outer_d = thr_major_f + 2.0 * wall
    base_th = wall
    sock_h = thread_h + base_th + 2.0

    # ONE solid: socket outer wall + drop column, a single extrude to column top.
    col_top = sock_h + drop
    body = cq.Workplane("XY").circle(outer_d / 2.0).extrude(col_top)

    # Female thread region: bore above the base, then union the inward rib.
    bore_cut = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, base_th))
        .circle(bore_r).extrude(thread_h + 0.8)
    )
    body = body.cut(bore_cut)
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, ov_f).translate((0, 0, base_th)))

    # Male shell on top, core overlapping 1 mm into the column so it fuses solid.
    shell, top_b, sr_b, ir_b = male_shell(spec_b, clearance, wall, turns, col_top - 1.0)
    body = body.union(shell)

    # Wiring channel straight through (opens bottom + top → no trapped void),
    # radius bounded by the narrowest solid section (male shaft & socket bore).
    chan_r = max(1.5, min(bore / 2.0, sr_b - 1.2, bore_r - 1.2))
    channel = cq.Workplane("XY").circle(chan_r).extrude(top_b + 2.0).translate((0, 0, -1.0))
    body = body.cut(channel)
    body = knurl(body, outer_d, top_b)
    return body


# ── base_adapter ─────────────────────────────────────────────────────────────
def build_base_adapter():
    """Female Edison thread (base A) on the bottom + male Edison thread (base B)
    on top: an E26<->E27 translator with a wiring channel through the middle.
    The female outer wall + shoulder disk are one extrude; the male core overlaps
    the shoulder; the channel is bored last; no trailing clean()."""
    spec_a = edison(edison_a)
    spec_b = edison(edison_b)
    pitch = spec_a["pitch"]
    t = half_turns(turns)
    thread_h = pitch * t
    thr_major_f = spec_a["major_d"] + 2.0 * clearance
    bore_r = thr_major_f / 2.0
    thr_depth = 0.55 * pitch
    ov_f = min(0.6, wall * 0.35 + 0.2)
    outer_d = thr_major_f + 2.0 * wall
    shoulder_th = max(1.8, wall)

    # ONE solid: female outer wall (thread run) + solid shoulder disk on top.
    stack_h = thread_h + shoulder_th
    body = cq.Workplane("XY").circle(outer_d / 2.0).extrude(stack_h)
    # Bore the female thread region from the bottom up to the shoulder.
    bore_cut = cq.Workplane("XY").circle(bore_r).extrude(thread_h + 0.8)
    body = body.cut(bore_cut)
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, ov_f))

    # Male shell above, core overlapping 1 mm into the shoulder disk.
    shell, top_b, sr_b, ir_b = male_shell(spec_b, clearance, wall, turns, stack_h - 1.0)
    body = body.union(shell)

    chan_r = max(1.5, min(bore_r, sr_b) - 1.6)
    channel = cq.Workplane("XY").circle(chan_r).extrude(top_b + 2.0).translate((0, 0, -1.0))
    body = body.cut(channel)
    body = knurl(body, outer_d, top_b)
    return body


# ── device_shell ─────────────────────────────────────────────────────────────
def build_device_shell():
    """A hollow male Edison shell with a top collar, to screw a printed device /
    sensor / holder into a lamp socket. Bored through for wiring. The collar core
    overlaps the shell core; the channel is bored last; no trailing clean()."""
    spec_a = edison(edison_a)
    shell, top_z, shaft_r, inner_r = male_shell(spec_a, clearance, wall, turns, 0.0)
    collar_od = (shaft_r + wall) * 2.0 + 4.0
    # Collar overlaps 1 mm into the shell core so the two cores fuse solid.
    collar = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, top_z - 1.0))
        .circle(collar_od / 2.0).extrude(collar_h + 1.0)
    )
    body = shell.union(collar)
    # Bore bounded by the narrowest section (male shaft, leave ≥1.2 mm).
    b_r = max(1.5, min(bore / 2.0, (collar_od - 2.0 * wall) / 2.0, shaft_r - 1.2))
    through = (
        cq.Workplane("XY").circle(b_r).extrude(top_z + collar_h + 2.0).translate((0, 0, -1.0))
    )
    body = body.cut(through)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "base_adapter":
    result = build_base_adapter()
elif target_part == "device_shell":
    result = build_device_shell()
else:
    result = build_extender()
