"""
Microphone Clip & Thread Adapter — Yantra4D Hyperobject Cartridge (CadQuery).

Mounts a microphone to any stand. The functional interface is the audio-industry
5/8"-27 mic-stand thread (the female socket that screws onto a stand), modelled at
its real nominal diameter and pitch as a short single-start helical rib.

Three parts (dispatched by `target_part`):
  * "mic_clip"        — a sprung C-clip that grips a mic body of `mic_dia`, on a
                        stem with a female 5/8"-27 socket for the stand.
  * "thread_adapter"  — a 5/8"-27 (female) to 3/8"-16 (male) reducer, the two most
                        common mic-stand thread sizes.
  * "shock_mount_ring"— an outer ring with an inner mic cradle suspended by thin
                        elastic-band posts (a printable shock mount), on a 5/8"
                        socket stem.

Thread strategy (fast + watertight): mic-stand threads are short, so a
trapezoidal profile is swept along a genuine `makeHelix` for only ~1.5-2 turns.
The rib root is pushed a little into the wall material (`overlap`) so the union
with the bore wall is a clean volumetric boolean instead of a fragile tangent
kiss — that is what keeps the mesh watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `mic_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Mic-stand thread standards (nominal geometry, mm) ────────────────────────
# 5/8"-27: 0.625 in major, 27 TPI → pitch 25.4/27 ≈ 0.94 mm (the mic-stand thread)
# 3/8"-16: 0.375 in major, 16 TPI → pitch 25.4/16 ≈ 1.5875 mm (light-stand thread)
THREADS = {
    "5/8-27": {"major_d": 15.88, "pitch": 0.94},
    "3/8-16": {"major_d": 9.53, "pitch": 1.5875},
}


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "mic_clip"))  # clip|adapter|shock

mic_dia    = float(PARAM(lambda: mic_dia,    50.0))  # mic body diameter (mm)
wall       = float(PARAM(lambda: wall,        3.0))  # body wall thickness (mm)
clearance  = float(PARAM(lambda: clearance,   0.4))  # printed thread fit slop (per side)
grip_wrap  = float(PARAM(lambda: grip_wrap, 250.0))  # clip wrap angle (deg of the C)
stem_len   = float(PARAM(lambda: stem_len,   26.0))  # socket-stem length (mm)
extra_turns = float(PARAM(lambda: extra_turns, 0.0)) # add thread engagement turns

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
mic_dia    = max(20.0, min(mic_dia, 70.0))
wall       = max(2.0, min(wall, 6.0))
clearance  = max(0.0, min(clearance, 1.0))
grip_wrap  = max(180.0, min(grip_wrap, 300.0))
stem_len   = max(14.0, min(stem_len, 50.0))
extra_turns = max(0.0, min(extra_turns, 2.0))


# ── Thread primitives (inlined — repo-lib imports are blocked in the sandbox) ─
def _helix(pitch, height):
    """A helical path centered on Z (radius ~0 so the profile traces the helix)."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal (female) helical rib pointing inward from the bore wall."""
    root_r = bore_r + overlap
    crest_r = max(0.4, bore_r - thr_depth)
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
    return prof.sweep(_helix(pitch, thread_h), isFrenet=True).translate((0, 0, pitch * 0.5))


def male_thread(shaft_r, pitch, thread_h, thr_depth, overlap):
    """External (male) helical rib whose crest sticks out past the shaft."""
    root_r = max(0.4, shaft_r - overlap)
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
    return prof.sweep(_helix(pitch, thread_h), isFrenet=True).translate((0, 0, pitch * 0.5))


def female_socket(std, clear, wall_th, sock_len, base_th):
    """A cylindrical stem with an internal female thread of `std`, closed at the
    top by `base_th`. Opens at z=0. Returns (solid, height, outer_d, bore_r)."""
    g = THREADS[std]
    pitch = g["pitch"]
    turns = min(3.0, sock_len / pitch, 2.0 + extra_turns)
    thr_major = g["major_d"] + 2.0 * clear
    bore_r = thr_major / 2.0
    thr_depth = 0.55 * pitch
    overlap = min(0.6, wall_th * 0.35 + 0.2)
    thread_h = pitch * turns

    outer_d = thr_major + 2.0 * wall_th
    body_h = sock_len + base_th
    body = cq.Workplane("XY").circle(outer_d / 2.0).extrude(body_h)
    bore = cq.Workplane("XY").circle(bore_r).extrude(sock_len + 0.6)
    body = body.cut(bore)
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, overlap))
    return body, body_h, outer_d, bore_r


def male_stud(std, clear, stud_len, embed=0.0):
    """A male-threaded stud of `std` rising from z=0. `embed` extends the plain
    core DOWN below z=0 by that much so the stud fuses volumetrically into the
    shoulder it is unioned onto (a core starting exactly at the shoulder plane
    would share a coincident face and stay a separate shell). Returns
    (solid, outer_d)."""
    g = THREADS[std]
    pitch = g["pitch"]
    turns = min(stud_len / pitch, 3.0)
    shaft_r = (g["major_d"] - 2.0 * clear) / 2.0 - 0.3 * pitch  # root shaft
    shaft_r = max(1.5, shaft_r)
    thr_depth = 0.55 * pitch
    overlap = 0.4
    thread_h = pitch * turns
    core = (
        cq.Workplane("XY")
        .circle(shaft_r + 0.1)
        .extrude(stud_len + embed)
        .translate((0, 0, -embed))
    )
    core = core.union(male_thread(shaft_r, pitch, thread_h, thr_depth, overlap))
    return core, (g["major_d"] + 2.0 * thr_depth)


# ── Part builders ────────────────────────────────────────────────────────────
def _pie_cutter(radius, start_deg, sweep_deg, height):
    """A pie-wedge prism from the origin spanning `sweep_deg` beginning at
    `start_deg`, tall `height`, radius `radius` — used to open the C mouth."""
    a0 = math.radians(start_deg)
    a1 = math.radians(start_deg + sweep_deg)
    am = math.radians(start_deg + sweep_deg / 2.0)
    return (
        cq.Workplane("XY")
        .moveTo(0, 0)
        .lineTo(radius * math.cos(a0), radius * math.sin(a0))
        .threePointArc(
            (radius * math.cos(am), radius * math.sin(am)),
            (radius * math.cos(a1), radius * math.sin(a1)),
        )
        .close()
        .extrude(height)
    )


def build_mic_clip():
    """A sprung C-clip gripping the mic body, on a stem with a 5/8"-27 socket."""
    r_in = mic_dia / 2.0 + clearance
    r_out = r_in + wall
    clip_h = max(18.0, mic_dia * 0.5)

    # Full ring, then cut the mouth opening to leave a C of `grip_wrap` degrees.
    ring = (
        cq.Workplane("XY")
        .circle(r_out).circle(r_in)
        .extrude(clip_h)
    )
    open_deg = 360.0 - grip_wrap
    if open_deg > 1.0:
        # Open the mouth centred on +X (from −open/2 to +open/2 about 0°).
        cutter = _pie_cutter(r_out + 5.0, -open_deg / 2.0, open_deg, clip_h)
        ring = ring.cut(cutter)

    # Vertical socket stem BELOW the clip (opening down onto an upright stand).
    # Building it vertical and merging through a solid pedestal that overlaps
    # both the socket wall and the ring keeps every boolean volumetric (a
    # sideways hollow socket butted to a neck leaves a fragile tangent seam).
    sock, sh, sod, sbr = female_socket("5/8-27", clearance, wall, stem_len, wall + 1.0)
    sx = -r_out + sod * 0.25
    sock = sock.translate((sx, 0, -sh))            # closed base at z=0, opens down
    pedestal = (                                    # bridges socket top ↔ ring wall
        cq.Workplane("XY")
        .box(sod, sod, clip_h * 0.5, centered=(True, True, False))
        .translate((sx, 0, 0))
    )
    body = ring.union(pedestal).union(sock)
    return body


def build_thread_adapter():
    """5/8"-27 female socket on the bottom, 3/8"-16 male stud on top."""
    sock, sh, sod, sbr = female_socket("5/8-27", clearance, wall, stem_len, wall + 1.0)
    # Flip so it opens downward (screws onto a 5/8 stand), closed shoulder up.
    sock = sock.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, sh))
    shoulder_z = sh
    stud_len = max(8.0, THREADS["3/8-16"]["pitch"] * 5.0)
    # embed=1.5 sinks the stud core into the shoulder so it fuses into one solid.
    stud, stud_od = male_stud("3/8-16", clearance, stud_len, embed=1.5)
    stud = stud.translate((0, 0, shoulder_z))
    body = sock.union(stud)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_shock_mount_ring():
    """An outer ring and an inner mic cradle joined by thin flexible posts (a
    printable shock mount), on a 5/8"-27 socket stem."""
    inner_r = mic_dia / 2.0 + clearance
    inner_wall = max(2.0, wall - 0.5)
    gap = max(10.0, mic_dia * 0.28)
    outer_in = inner_r + inner_wall + gap
    outer_out = outer_in + wall
    ring_h = max(14.0, mic_dia * 0.35)

    outer = cq.Workplane("XY").circle(outer_out).circle(outer_in).extrude(ring_h)
    inner = cq.Workplane("XY").circle(inner_r + inner_wall).circle(inner_r).extrude(ring_h)
    body = outer.union(inner)

    # Flexible posts: thin S-less straight webs at 4 points (printable "bands").
    post_t = max(1.6, wall * 0.5)
    for k in range(4):
        ang = 45.0 + 90.0 * k
        web = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, ang))
            .box(outer_out, post_t, ring_h * 0.5, centered=(True, True, False))
            .translate((0, 0, ring_h * 0.25))
        )
        body = body.union(web)

    # Vertical socket stem below the outer ring (opening down onto a stand),
    # merged through a solid pedestal that overlaps the ring wall.
    sock, sh, sod, sbr = female_socket("5/8-27", clearance, wall, stem_len, wall + 1.0)
    sx = -(outer_out - sod * 0.3)
    sock = sock.translate((sx, 0, -sh))
    # Pedestal spans from 2 mm INTO the socket top up into the ring so all three
    # (socket, pedestal, ring) fuse into one solid instead of merely touching.
    pedestal = (
        cq.Workplane("XY")
        .box(sod, sod, ring_h * 0.5 + 2.0, centered=(True, True, False))
        .translate((sx, 0, -2.0))
    )
    body = body.union(pedestal).union(sock)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "thread_adapter":
    result = build_thread_adapter()
elif target_part == "shock_mount_ring":
    result = build_shock_mount_ring()
else:
    result = build_mic_clip()
