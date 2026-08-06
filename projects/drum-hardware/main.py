"""
Drum / Cymbal Sleeve & Wingnut — Yantra4D Hyperobject Cartridge (CadQuery).

Tension-rod and cymbal hardware. The functional interface is the drum tension-rod
THREAD: the near-universal 12-24 (major 5.49 mm, 24 TPI → pitch 1.058 mm) on
American/Asian kits, or M5 (DW/PDP). This cartridge builds a threaded wingnut, a
male-threaded printed tension rod with a 7 mm square key drive, and a smooth
stepped cymbal sleeve that protects the cymbal bell from the metal rod.

Modes:
  - wingnut       : a female-threaded wingnut for cymbal-stand tilters / hi-hat
    clutches (internal helical thread + two wings).
  - tension_rod   : a printed tension rod — a male-threaded shaft under a flanged
    head with a 7 mm square drum-key drive socket.
  - cymbal_sleeve : a smooth stepped sleeve (no thread) with a felt-seat flange
    that isolates the cymbal from the metal rod.

Thread strategy (verified watertight + fast, all turn counts):
  Threads are a trapezoidal profile SWEPT along a genuine makeHelix path built at
  the REAL mean thread radius (NOT radius~0 — a near-zero helix gives a degenerate
  sweep frame that cracks or fails), with makeSolid=True and one extra pitch of
  sweep so the rib crosses the end faces. Two rules keep every render watertight:
    - FEMALE thread: an inward trapezoidal rib UNIONED into the bore (root pushed
      `overlap` into the wall → clean volumetric fuse).
    - MALE thread: a helical groove CUT from a solid rod at the crest radius
      (subtractive) — this is watertight at ANY length (a full ~40-turn rod), where
      an additive outward male rib leaves an unsealed spiral crest.
  The helix TURN COUNT is also snapped to a HALF-INTEGER (floor(n)+0.5): an integer
  turn count degenerates the OCCT helical sweep (profile closes on itself → a
  null/negative-volume body), and is much slower.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` pre-injected; params arrive as bare globals.
  - Read each via PARAM(lambda: name, default). No globals()/eval/getattr.
  - Assign the final solid to `result`.
"""

import cadquery as cq
import math


def PARAM(getter, default):
    """Injected global if present else default; `except` catches the unbound-name
    NameError the sandbox raises (globals()/NameError are hidden)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Tension-rod thread standards (nominal, mm) ───────────────────────────────
THREAD_STD = {
    # major_d = male outer (major) diameter; pitch = thread pitch.
    "12-24": {"major_d": 5.49, "pitch": 1.058},   # 0.216 in, 24 TPI — US/Asian std
    "M5":    {"major_d": 5.0, "pitch": 0.8},       # DW / PDP metric
}


def thread_geo(name):
    return THREAD_STD.get(name, THREAD_STD["12-24"])


def _half_int_turns(height, pitch):
    """Turns needed to cover `height`, snapped to floor(n)+0.5. A half-integer
    turn count keeps the OCCT helical sweep non-degenerate (an INTEGER turn count
    closes the swept profile on itself → a null/negative-volume body)."""
    raw = max(1.0, height / pitch)
    return math.floor(raw) + 0.5


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "wingnut"))
# "wingnut" | "tension_rod" | "cymbal_sleeve"

thread_std = str(PARAM(lambda: thread_std, "12-24"))  # 12-24 | M5
clearance  = float(PARAM(lambda: clearance, 0.35))    # printed-thread fit slop (per side)
rod_len    = float(PARAM(lambda: rod_len, 42.0))      # tension-rod threaded length (mm)
sleeve_len = float(PARAM(lambda: sleeve_len, 40.0))   # cymbal sleeve length (mm)
post_d     = float(PARAM(lambda: post_d, 6.0))        # cymbal-stand post / rod clearance bore (mm)
wall       = float(PARAM(lambda: wall, 3.0))          # wall thickness (mm)
sq_drive   = float(PARAM(lambda: sq_drive, 7.0))      # drum-key square drive across flats (mm)

# Clamp to sane ranges so extreme UI values still build watertight.
thread_std = thread_std if thread_std in THREAD_STD else "12-24"
clearance  = max(0.0, min(clearance, 0.8))
rod_len    = max(16.0, min(rod_len, 80.0))
sleeve_len = max(20.0, min(sleeve_len, 70.0))
post_d     = max(5.0, min(post_d, 12.7))
wall       = max(2.0, min(wall, 6.0))
sq_drive   = max(5.0, min(sq_drive, 9.0))

_g = thread_geo(thread_std)


# ── Thread primitives (inlined — repo-lib imports blocked in sandbox) ────────
# Thread radial depth as a fraction of pitch. 0.4 (not 0.5) with a FLAT-topped
# crest keeps the fine-pitch (M5) mesh from tessellating into separated crest
# slivers — verified 1 mesh body vs 9 for a sharper/deeper thread.
_THR_DEPTH_FRAC = 0.4


# Trapezoidal flank half-widths (wide root, FLAT crest). The crest keeps a real
# flat (>= 0.12*pitch) so the STL never tessellates it to a knife edge.
def _flank_halves(pitch, thr_depth):
    half_root = pitch * 0.28
    half_crest = max(pitch * 0.12, half_root - thr_depth * math.tan(math.radians(30.0)))
    return half_root, half_crest


def _helix_path(pitch, height, mean_r):
    """Helical wire on Z built at the REAL mean thread radius `mean_r`. A
    real-radius helix keeps the pipe (sweep) frame non-singular — that is what
    makes the fuse fast AND watertight; a radius~0 helix is degenerate."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=mean_r)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal (female) helical rib to UNION into a bore: a wide root pushed
    `overlap` into the wall, narrowing to a crest at bore_r - thr_depth (points
    toward the axis). Real-radius helix + makeSolid → watertight at any length."""
    root_r = bore_r + overlap
    crest_r = max(0.4, bore_r - thr_depth)
    half_root, half_crest = _flank_halves(pitch, thr_depth)
    mean_r = (root_r + crest_r) / 2.0
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -half_root),
            (crest_r, -half_crest),
            (crest_r, half_crest),
            (root_r, half_root),
        ])
        .close()
    )
    rib = prof.sweep(_helix_path(pitch, thread_h + pitch, mean_r), isFrenet=True, makeSolid=True)
    return rib.translate((0, 0, -pitch * 0.5))


def male_thread_groove(crest_r, pitch, thread_h, thr_depth):
    """Male thread as a helical GROOVE to CUT from a solid rod of radius crest_r.
    The groove opens from just outside the rod surface and narrows to the root
    radius. Subtractive → watertight at ANY length (a full multi-turn rod), where
    an additive outward rib leaves an unsealed spiral crest."""
    root_r = max(0.4, crest_r - thr_depth)
    half_root, half_crest = _flank_halves(pitch, thr_depth)
    mean_r = (crest_r + root_r) / 2.0
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (crest_r + 0.6, -half_crest),
            (root_r, -half_root),
            (root_r, half_root),
            (crest_r + 0.6, half_crest),
        ])
        .close()
    )
    groove = prof.sweep(_helix_path(pitch, thread_h + pitch, mean_r), isFrenet=True, makeSolid=True)
    return groove.translate((0, 0, -pitch * 0.5))


def _square_socket(across_flats, depth, z_top):
    """A square drive socket (for a drum key) bored down from z_top. Returns a
    cutter box; the socket is open at the top (vented)."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_top - depth))
        .rect(across_flats, across_flats)
        .extrude(depth + 1.0)
    )


# ── Part builders ────────────────────────────────────────────────────────────
def build_wingnut():
    """A female-threaded wingnut: a hex-ish hub with an internal helical thread
    for the tension rod, plus two flat wings to finger-tighten."""
    pitch = _g["pitch"]
    thr_major = _g["major_d"] + 2.0 * clearance
    bore_r = thr_major / 2.0
    thr_depth = _THR_DEPTH_FRAC * pitch
    overlap = 0.4
    hub_h = max(8.0, pitch * _half_int_turns(9.0, pitch) + 2.0)
    turns = _half_int_turns(hub_h - 1.0, pitch)
    thread_h = pitch * turns

    hub_r = bore_r + wall + 1.0
    # Build the SOLID hub + wings FIRST, then bore and thread LAST. Keeping the
    # thread as the final op — confined to the bore — stops the wing/hub join from
    # tessellating the fine thread into separated mesh shells (verified 1 mesh
    # body vs several when the wing union happens after the thread).
    hub = cq.Workplane("XY").circle(hub_r).extrude(hub_h)

    # Two wings: a flat paddle bar across the hub (solid, overlaps the hub).
    wing_l = hub_r + 12.0
    wing = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, hub_h * 0.5 - 2.0))
        .box(wing_l * 2.0, 5.0, 4.0, centered=(True, True, False))
    )
    try:
        wing = wing.edges("|Z").fillet(2.0)
    except Exception:
        pass
    body = hub.union(wing)

    # Now bore the through-hole (open both ends → vented) and fuse the thread.
    bore = cq.Workplane("XY").circle(bore_r).extrude(hub_h + 2.0).translate((0, 0, -1.0))
    body = body.cut(bore)
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, overlap))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_tension_rod():
    """A printed tension rod: a flanged head with a 7 mm square drum-key drive on
    top, and a FULL-LENGTH male-threaded shaft (12-24 or M5). The thread is a
    helical groove cut from the shaft, so the whole rod length threads and stays
    watertight regardless of turn count."""
    pitch = _g["pitch"]
    crest_r = max(1.2, _g["major_d"] / 2.0 - clearance)   # male crest (fit clearance)
    thr_depth = _THR_DEPTH_FRAC * pitch

    # Thread the full rod length; turns snapped to a half-integer (never integer).
    turns = _half_int_turns(rod_len, pitch)
    thread_h = pitch * turns

    # Head: a flanged disc the rod pulls against, with the square key socket.
    head_r = _g["major_d"] / 2.0 + 3.0
    head_h = max(5.0, wall + 3.0)
    head = cq.Workplane("XY").circle(head_r).extrude(head_h)
    try:
        head = head.edges("|Z").fillet(1.5)
    except Exception:
        pass

    # Solid shaft at the crest radius from the head down (one cylinder), then cut
    # the helical thread groove into it → a real full-length male thread.
    core = cq.Workplane("XY").circle(crest_r).extrude(rod_len).translate((0, 0, -rod_len))
    body = head.union(core)
    groove = male_thread_groove(crest_r, pitch, thread_h, thr_depth).translate((0, 0, -rod_len))
    body = body.cut(groove)

    # Square drum-key drive socket down from the top of the head (vented).
    socket = _square_socket(sq_drive, head_h - 0.5, head_h)
    body = body.cut(socket)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_cymbal_sleeve():
    """A smooth stepped cymbal sleeve (no thread) with a wide felt-seat flange
    that isolates the cymbal bell from the metal rod. A through-bore takes the
    stand's threaded post; the cymbal rides the smooth outer step."""
    bore_r = post_d / 2.0 + 0.3
    step_r = bore_r + wall            # slim upper step (through the cymbal hole)
    flange_r = step_r + 5.0           # wide felt-seat flange at the bottom
    flange_h = max(3.0, wall)
    step_h = sleeve_len - flange_h

    # Flange (bottom) + slim step (top) as a stepped solid.
    flange = cq.Workplane("XY").circle(flange_r).extrude(flange_h)
    step = cq.Workplane("XY").circle(step_r).extrude(step_h).translate((0, 0, flange_h))
    body = flange.union(step)
    try:
        body = body.edges("|Z").fillet(1.0)
    except Exception:
        pass

    # Through-bore for the stand post (open both ends → vented).
    bore = cq.Workplane("XY").circle(bore_r).extrude(sleeve_len + 2.0).translate((0, 0, -1.0))
    body = body.cut(bore)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tension_rod":
    result = build_tension_rod()
elif target_part == "cymbal_sleeve":
    result = build_cymbal_sleeve()
else:
    result = build_wingnut()
