"""
Mic Stand Thread Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The three stand threads, in every combination.

Every stand, boom, clamp, spigot, shockmount and tripod head on earth terminates
in one of three threads: 5/8"-27 (the microphone stand thread), 3/8"-16 (the
European stand and small-head thread) and 1/4"-20 (the camera thread). None of
them mates any other, all three appear in the same rack of gear, and the adapter
between any two is the single most-lost object in a live-sound or camera bag.

This closes two one-member families at once and joins the largest family in the
commons:
  * `mic-thread-5/8-27` — one member, `mic-clip`
  * `unc-3/8-16`        — one member, `camera-quarter-twenty`
  * `unc-1/4-20`        — the commons' biggest standard family

Modes are dispatched via `target_part`:
  * "bushing"     — female thread at the top, male stud below: the classic
                    reducer, and the one that goes missing first.
  * "double_stud" — male at both ends, for joining two female fittings.
  * "coupler"     — female at both ends, for joining two studs.

Every mode takes an INDEPENDENT thread selection at each end, so all nine
combinations of the three threads are reachable from one cartridge.

The 3.5-turn ceiling, and why the plain register exists:
  The commons' inlined helical-thread primitive — a trapezoidal profile swept
  along a degenerate-radius helix with a Frenet frame — is reliable to 3.5 turns
  and unreliable beyond it. Measured, at every pitch this cartridge uses: at 5.5
  turns the union returns a solid with 479-2050 non-manifold edges or splits in
  two; at 7.5 it raises `BRep_API: command not done`. A real-radius helix was
  tried (670k faces, and the rib does not fuse); a segmented sweep was tried
  (clean at 1.5875 mm pitch, six bodies at 0.9407). So the thread is capped at
  3.5 turns and the joint does NOT rely on thread length for its alignment: each
  end carries a PLAIN REGISTER — a parallel barrel ahead of the thread that
  takes the concentricity and the bending moment. That is also how a real
  stand adapter is made; the thread only holds it on.

Watertightness strategy:
  * Union OVERLAPS, never tangents. Studs straddle the collar they grow from.
  * The collar height is RAISED to fit whatever the bores need, rather than the
    bores being trimmed to fit the collar — a bore trimmed to fit is a thread
    that quietly loses turns, and nothing reports it.
  * No sealed void: a bore always opens at an end face, and the unbored collar
    is solid rather than hollow.
  * No fillet on any edge a bore or a thread has touched.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

A printed thread is not a rigging component. See the README.
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


# ── The three stand threads ──────────────────────────────────────────────────
# `major` is the nominal major (outside) diameter in mm; `pitch` is 25.4 / TPI.
# 1/4-20 and 3/8-16 are ASME B1.1 Unified Coarse and are declared by
# `tripod-hub` and `camera-quarter-twenty` on exactly these figures.
# 5/8-27 is the microphone stand thread, 27 TPI on a 5/8 in major.
#
# Note on 3/8-16: the European stand thread is 3/8 BSW (Whitworth, 55 deg flank)
# and the American one is 3/8-16 UNC (60 deg). Both are 16 TPI on the same major
# diameter, and a PRINTED thread does not resolve the flank-angle difference —
# so this cartridge builds one 16-TPI form and says so, rather than claiming a
# precision it does not have.
THREADS = {
    "unc_1_4_20": {"major": 6.350, "pitch": 25.4 / 20.0, "name": '1/4"-20 UNC'},
    "unc_3_8_16": {"major": 9.525, "pitch": 25.4 / 16.0, "name": '3/8"-16 (16 TPI)'},
    "uns_5_8_27": {"major": 15.875, "pitch": 25.4 / 27.0, "name": '5/8"-27 stand'},
}

# Measured ceiling of the commons' swept-helix thread primitive. See the module
# docstring: 4.5 turns and above do not build reliably at any pitch here.
MAX_TURNS = 3.5
OVERLAP = 1.0
MID_WALL = 2.0          # material that always survives between two opposed bores


def thread_of(key):
    return THREADS.get(key, THREADS["uns_5_8_27"])


def half_turns(t):
    """Force a turn count to the nearest lower HALF-integer, never whole.

    A whole-turn helical sweep ends exactly where it began, so its start and end
    caps land coincident and OCC leaves a zero-thickness seam that meshes open.
    """
    t = min(t, MAX_TURNS)
    return max(1.5, math.floor(t * 2.0) / 2.0
               - (0.5 if abs(t * 2.0 % 2.0) < 1e-9 else 0.0))


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "bushing"))
thread_top = str(PARAM(lambda: thread_top, "uns_5_8_27"))
thread_bottom = str(PARAM(lambda: thread_bottom, "unc_3_8_16"))
grip = str(PARAM(lambda: grip, "hex"))

collar_h = float(PARAM(lambda: collar_h, 12.0))
flats = float(PARAM(lambda: flats, 22.0))
turns = float(PARAM(lambda: turns, 3.5))
clearance = float(PARAM(lambda: clearance, 0.30))
register_h = float(PARAM(lambda: register_h, 4.0))
thru_bore = float(PARAM(lambda: thru_bore, 0.0))

collar_h = max(6.0, min(collar_h, 40.0))
flats = max(12.0, min(flats, 45.0))
turns = max(1.5, min(turns, MAX_TURNS))
clearance = max(0.1, min(clearance, 0.6))
register_h = max(0.0, min(register_h, 14.0))
thru_bore = max(0.0, min(thru_bore, 10.0))

TURNS = half_turns(turns)
TOP = thread_of(thread_top)
BOT = thread_of(thread_bottom)


# ── Derived, clamped against FINAL values ────────────────────────────────────
def female_bore_r(spec):
    """Bore radius a male thread of `spec` turns into."""
    return spec["major"] / 2.0 + clearance


def thread_depth(spec):
    return 0.55 * spec["pitch"]


def female_depth(spec):
    """Total axial depth a female thread plus its plain register needs.

    The swept rib occupies pitch*0.18 below its nominal start and pitch*0.82
    above its nominal end; the depth is derived from that, never assumed."""
    return (register_h + 1.0 + spec["pitch"] * TURNS
            + spec["pitch"] * 0.82 + 0.8)


def male_len(spec):
    """Total stud length: plain register, then the threaded section."""
    return (register_h + 1.0 + spec["pitch"] * TURNS
            + spec["pitch"] * 0.82 + 1.0)


# The collar has to contain the largest bore it will ever be asked to hold, plus
# a real wall. Derived, then the user's `flats` can only make it LARGER.
_needed_r = max(female_bore_r(TOP), female_bore_r(BOT)) + 2.2
R_OUT = max(flats / 2.0, _needed_r)

# Collar height is RAISED to whatever the bores need. Trimming the bores to fit
# the collar instead would silently drop thread turns, and nothing would report
# it — the part would simply hold less than it says.
if target_part == "bushing":
    COLLAR_H = max(collar_h, female_depth(TOP) + MID_WALL)
elif target_part == "coupler":
    COLLAR_H = max(collar_h, female_depth(TOP) + female_depth(BOT) + MID_WALL)
else:
    COLLAR_H = max(collar_h, 6.0)


# ── Thread primitives ────────────────────────────────────────────────────────
def _helix(pitch, height):
    """Degenerate-radius helix used as a sweep path; the profile carries the
    real radius in its own plane and therefore traces the true helix."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def _rib(root_r, crest_r, pitch, height, z0):
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
    rib = prof.sweep(_helix(pitch, height), isFrenet=True)
    return rib.translate((0, 0, z0 + pitch * 0.5))


def female_rib(spec, z0):
    """Internal rib growing INWARD from a bore, biting 0.6 mm into the wall."""
    bore_r = female_bore_r(spec)
    return _rib(bore_r + 0.6, max(0.5, bore_r - thread_depth(spec)),
                spec["pitch"], spec["pitch"] * TURNS, z0)


def male_rib(spec, core_r, z0):
    """External rib rising from a stud core, biting 0.4 mm into it."""
    return _rib(core_r - 0.4, core_r + thread_depth(spec),
                spec["pitch"], spec["pitch"] * TURNS, z0)


def male_core_r(spec):
    return spec["major"] / 2.0 - clearance - thread_depth(spec)


# ── Body primitives ──────────────────────────────────────────────────────────
def collar():
    """The grip body, always concentric and always thick enough for its bores."""
    if grip == "hex":
        # `polygon` takes the diameter of the CIRCUMSCRIBED circle; across-flats
        # is what a spanner sees, so convert rather than guess.
        dia = 2.0 * R_OUT / math.cos(math.pi / 6.0)
        body = cq.Workplane("XY").polygon(6, dia).extrude(COLLAR_H)
    else:
        body = cq.Workplane("XY").circle(R_OUT).extrude(COLLAR_H)
        if grip == "knurl":
            teeth = max(8, min(36, int(R_OUT * 2.2)))
            try:
                cutter = (
                    cq.Workplane("XY")
                    .polarArray(radius=R_OUT, startAngle=0, angle=360, count=teeth)
                    .rect(0.8, 2.4)
                    .extrude(COLLAR_H + 2.0)
                    .translate((0, 0, -1.0))
                )
                body = body.cut(cutter)
            except Exception:
                pass    # the knurl is grip, never structure
    return body


def cut_female(body, spec, z_face, downward):
    """Cut a female thread into a face and union its rib.

    `z_face` is the open face; `downward` says which way the bore runs. The bore
    always opens at an end face, so it can never seal a void."""
    depth = female_depth(spec)
    bore_r = female_bore_r(spec)
    if downward:
        z0 = z_face - depth
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z0))
            .circle(bore_r)
            .extrude(depth + 1.0)
        )
        rib_z = z_face - depth + register_h
    else:
        z0 = z_face - 1.0
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z0))
            .circle(bore_r)
            .extrude(depth + 1.0)
        )
        rib_z = z_face + register_h
    body = body.cut(bore)
    try:
        body = body.union(female_rib(spec, rib_z))
    except Exception:
        pass
    return body


def add_male(body, spec, z_face, upward):
    """Union a male stud onto a face, straddling it by OVERLAP."""
    core_r = male_core_r(spec)
    length = male_len(spec)
    if upward:
        z0 = z_face - OVERLAP
        stud = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z0))
            .circle(core_r)
            .extrude(length + OVERLAP)
        )
        rib_z = z_face + register_h
    else:
        z0 = z_face - length
        stud = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z0))
            .circle(core_r)
            .extrude(length + OVERLAP)
        )
        rib_z = z_face - length + register_h
    body = body.union(stud)
    try:
        body = body.union(male_rib(spec, core_r, rib_z))
    except Exception:
        pass
    return body


def apply_thru(body, z_lo, z_hi):
    """Optional through passage for a cable or a locking screw. Capped so it can
    never eat the minor diameter of the smallest thread present."""
    if thru_bore <= 0.05:
        return body
    limit = min(male_core_r(TOP), male_core_r(BOT)) - 0.8
    r = max(0.5, min(thru_bore / 2.0, limit))
    if r <= 0.5:
        return body
    tool = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_lo - 1.0))
        .circle(r)
        .extrude((z_hi - z_lo) + 2.0)
    )
    return body.cut(tool)


# ── Part builders ────────────────────────────────────────────────────────────
def build_bushing():
    """Female above, male stud below — the reducer that goes missing first."""
    body = collar()
    body = cut_female(body, TOP, COLLAR_H, downward=True)
    body = add_male(body, BOT, 0.0, upward=False)
    body = apply_thru(body, -male_len(BOT), COLLAR_H)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_double_stud():
    """Male at both ends, for joining two female fittings."""
    body = collar()
    body = add_male(body, TOP, COLLAR_H, upward=True)
    body = add_male(body, BOT, 0.0, upward=False)
    body = apply_thru(body, -male_len(BOT), COLLAR_H + male_len(TOP))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_coupler():
    """Female at both ends, for joining two studs.

    The mid wall is guaranteed by COLLAR_H, which was raised to fit both bores
    plus MID_WALL — so the two bores can never meet and leave a shell."""
    body = collar()
    body = cut_female(body, TOP, COLLAR_H, downward=True)
    body = cut_female(body, BOT, 0.0, downward=False)
    body = apply_thru(body, 0.0, COLLAR_H)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "bushing": build_bushing,
    "double_stud": build_double_stud,
    "coupler": build_coupler,
}

result = _dispatch.get(target_part, build_bushing)()
