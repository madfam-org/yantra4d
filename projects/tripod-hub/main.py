"""
Universal Tripod Hub — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A CAPSTONE multi-standard tripod hub that bridges the three interfaces every
photo/video and optics rig is built around but which never all meet in one part:
the 1/4"-20 UNC camera screw, the 3/8"-16 UNC heavy-mount screw, and the
Arca-Swiss 38 mm quick-release dovetail. Each mode fuses at least two of these
standards into one object so a rig built on one bolts onto another.

Modes (dispatched via `target_part`):
  * "hub_plate"       — a distribution plate: an Arca-Swiss 38 mm dovetail on the
                        underside (drops into any Arca clamp), a central 3/8-16
                        female socket, and a RING of 1/4-20 female sockets around
                        it — mount a cluster of 1/4-20 accessories on one Arca head.
  * "quarter_to_arca" — an Arca dovetail plate carrying a real male 1/4-20 stud on
                        top: an Arca head now drives any 1/4-20 device (camera,
                        ball head, magic arm).
  * "reducer_bushing" — the classic camera thread reducer: an external male 3/8-16
                        thread with an internal female 1/4-20 thread through it, so
                        a 3/8-16 stud/socket accepts a 1/4-20 fitting (and back).

Real thread geometry (nominal UNC, dimensionally real, all mm):
  1/4"-20 UNC: major Ø 6.35, 20 TPI → pitch 1.27, minor Ø ~4.976.
  3/8"-16 UNC: major Ø 9.525, 16 TPI → pitch 1.5875, minor Ø ~7.749.
  Arca-Swiss: 38.0 mm dovetail platform, ~45° flanks, ~9.0 mm block height.

Thread strategy (VERIFIED watertight + fast — four traps avoided):
  Threads are volumetric fused helical ribs (trapezoidal profile swept along a
  genuine `makeHelix` and unioned into the wall/shaft, root buried for a clean
  fusion). 1) Turn count snapped to a HALF-INTEGER (floor(n)+0.5) — an integer
  count degenerates the OCCT helical sweep to a null body — and then trimmed DOWN
  to what the socket depth can hold, so no rib ever overruns the hole it threads.
  2) The female 1/4-20 socket in `reducer_bushing` is stopped short of the far
  face so the bore is not open at both ends where it would tessellate
  non-watertight; the connecting clearance hole is a plain cylinder drilled into
  each component BEFORE its rib is fused on — driving that cylinder coaxially
  through a FINISHED thread is a boolean OCCT does not converge on, and it hangs
  rather than failing. 3) No flip-then-attach: studs and dovetails attach on
  closed faces, never on an open thread rim. 4) Turn count CAPPED at a validated
  half-integer ceiling (4.5) — a very tall thread on a thin wall can tessellate
  non-watertight even at a half-integer; real fittings engage a few turns so the
  cap costs nothing. 5) Socket depth is bounded by the material that actually
  exists, and the hub plate's slab is capped so a socket never outruns the depth
  at which its rib still fuses.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
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


# ── UNC thread standards (nominal envelopes, mm) ─────────────────────────────
UNC = {
    "1/4-20": {"major": 6.35, "pitch": 1.27, "minor": 4.976},
    "3/8-16": {"major": 9.525, "pitch": 1.5875, "minor": 7.749},
}

# Arca-Swiss nominal (mm)
ARCA_TOP_W = 38.00
ARCA_FLANK = 45.0
ARCA_H = 9.00


def half_int_turns(n, ceiling=4.5):
    """Half-integer turn count (floor(n)+0.5), clamped to [1.5, ceiling]. An
    integer count degenerates the helical sweep; the ceiling is the validated
    watertight limit for these wall thicknesses."""
    return max(1.5, min(ceiling, math.floor(n) + 0.5))


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "hub_plate"))
plate_w = float(PARAM(lambda: plate_w, 60.0))     # hub plate width / dia (mm)
plate_h = float(PARAM(lambda: plate_h, 9.0))      # Arca dovetail block height (mm)
n_quarter = int(PARAM(lambda: n_quarter, 6))      # count of 1/4-20 sockets in the ring
ring_dia = float(PARAM(lambda: ring_dia, 40.0))   # bolt-circle Ø of the 1/4-20 ring (mm)
thread_len = float(PARAM(lambda: thread_len, 8.0))  # stud height / socket depth (mm)
clearance = float(PARAM(lambda: clearance, 0.35))  # printed-thread fit (per side)
turns = float(PARAM(lambda: turns, 4.0))          # requested thread engagement turns

# Clamp to sane ranges so extreme UI values still build watertight.
plate_w = max(30.0, min(plate_w, 100.0))
plate_h = max(6.0, min(plate_h, 16.0))
n_quarter = max(2, min(n_quarter, 10))
ring_dia = max(16.0, min(ring_dia, plate_w - 10.0))
thread_len = max(4.0, min(thread_len, 16.0))
clearance = max(0.0, min(clearance, 0.8))
turns = max(1.5, min(turns, 4.5))


# ── Thread primitives (inlined — repo-lib imports are blocked in sandbox) ─────
def _helix_path(pitch, hgt):
    return cq.Wire.makeHelix(pitch=pitch, height=hgt, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal helical rib pointing INWARD from the bore wall (root buried in the
    wall for a clean watertight union)."""
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
    """External helical rib pointing OUTWARD from the shaft (root buried in the
    shaft for a clean watertight union)."""
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


def male_stud(size, clear, length, z0, thru_r=0.0):
    """A real male UNC stud rooted at z0, growing +Z. Returns (solid, top_z,
    shaft_r). A short plain lead-in below the thread buries the lower rib end.

    `thru_r` optionally drills an axial hole clean through the stud. Pass it here
    rather than cutting the hole afterwards: driving a cylinder coaxially through a
    finished helical thread is a boolean OCCT does not converge on — it hangs rather
    than failing, which is far worse than an error. Cut into the plain core BEFORE
    the rib is fused and the same hole costs milliseconds."""
    spec = UNC[size]
    pitch = spec["pitch"]
    t = half_int_turns(length / pitch if pitch else 3.5)
    thr_major = max(2.0, spec["major"] - 2.0 * clear)
    thr_depth = 0.5 * (spec["major"] - spec["minor"]) * 0.5 + 0.15
    shaft_r = thr_major / 2.0 - thr_depth
    overlap = 0.35
    thread_h = pitch * t
    core_h = thread_h + 1.5 * pitch
    core = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0))
        .circle(shaft_r + 0.15).extrude(core_h)
    )
    if thru_r > 0.2:
        core = core.cut(
            cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0 - 1.0))
            .circle(thru_r).extrude(core_h + 2.0)
        )
    core = core.union(male_thread(shaft_r, pitch, thread_h, thr_depth, overlap).translate((0, 0, z0)))
    return core, z0 + core_h, shaft_r


def female_socket_cut(size, clear, depth, z_top):
    """A cutter+rib pair for a female UNC socket bored DOWN from a top face at
    z_top. The socket has a CLOSED bottom (bore stops `depth` below z_top). Returns
    (bore_cutter, rib_solid): cut the bore, then union the rib."""
    spec = UNC[size]
    pitch = spec["pitch"]
    t = half_int_turns(depth / pitch if pitch else 3.5)
    thr_major = spec["major"] + 2.0 * clear
    bore_r = thr_major / 2.0
    thr_depth = 0.5 * (spec["major"] - spec["minor"]) * 0.5 + 0.15
    overlap = 0.35
    # Keep the rib INSIDE the bore it threads. `half_int_turns` snaps up to the next
    # half turn, so a socket whose depth falls just under a half-integer multiple of
    # the pitch gets a thread taller than the hole: the surplus spiral sticks out of
    # the closed bottom into solid plate, and each buried end tears off as its own
    # body (a 16 mm plate came out as FIVE). Trim the turn count down to what the
    # depth can actually hold, never up.
    # Round DOWN to a half-integer (n + 0.5): a whole-number turn count degenerates
    # the OCCT helical sweep, so 0.5, 1.5, 2.5 … are the only legal values.
    usable = max(0.0, depth - 0.4)
    if pitch > 0 and pitch * t > usable:
        t = max(0.5, math.floor(usable / pitch - 0.5) + 0.5)
    thread_h = pitch * t
    # Bore from z_top downward by `depth` (closed bottom — does not reach far face).
    bore = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z_top - depth))
        .circle(bore_r).extrude(depth + 0.5)
    )
    z0 = z_top - depth + 0.2
    rib = female_thread(bore_r, pitch, thread_h, thr_depth, overlap).translate((0, 0, z0))
    # TRIM the rib to the socket band. The swept helix runs thread_h + pitch/2 tall,
    # which for a socket cut near a shallow plate overhangs z_top — leaving a spiral
    # fragment hanging in free space above the face. Unioning that dangling sliver is
    # what returns a Null TopoDS_Shape from the OCCT fuse. Intersecting the rib with
    # the socket's own cylindrical band keeps every rib end buried in real material.
    #
    # The band must span the WHOLE bore, from its closed bottom to the top face:
    # clipping it to a shorter window can consume the rib entirely, and the caller
    # then unions an empty Workplane ("must have at least one solid on the stack").
    band_z0 = z_top - depth - 0.1
    band = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, band_z0))
        .circle(bore_r + overlap + 1.0)
        .extrude(max(0.4, z_top - band_z0))
    )
    rib = rib.intersect(band)
    # A socket too shallow for even half a turn legitimately has no rib left. Report
    # that with None rather than an empty Workplane so the caller can skip the union
    # instead of crashing — a plain unthreaded pilot bore is the honest result.
    if not rib.solids().vals():
        rib = None
    return bore, rib, bore_r


# ── Arca dovetail base (inlined) ─────────────────────────────────────────────
def arca_base(width, height, length):
    """An Arca-Swiss dovetail bar, dovetail DOWN (wide base at z=0), flat platform
    up at z=height. Centred on X and Y."""
    flank_dx = height * math.tan(math.radians(ARCA_FLANK))
    htw = width / 2.0
    hbw = htw + flank_dx
    # Cross-section in XZ (dovetail down): wide base at z=0, narrow top at z=height.
    pts = [(-hbw, 0.0), (hbw, 0.0), (htw, height), (-htw, height)]
    prof = cq.Workplane("XZ").polyline(pts).close()
    return prof.extrude(length / 2.0, both=True)


# ── Part builders ─────────────────────────────────────────────────────────────
def build_hub_plate():
    """A distribution plate: an Arca dovetail underside, a central 3/8-16 female
    socket, and a ring of `n_quarter` 1/4-20 female sockets. Mount a cluster of
    1/4-20 accessories on one Arca head, or bolt the plate to a 3/8-16 stud."""
    plate_len = plate_w
    # The DOVETAIL IS A FEATURE UNDER THE PLATE, not the plate itself. Using the
    # bare Arca bar as the body caps the work surface at the dovetail's narrow top
    # (38 mm), so at the default plate_w=60 / ring_dia=40 the socket ring sat at
    # r=20 while the platform only reached x=±19: every socket in the ring was
    # bored through thin air, and the dangling rib fragments are what returned
    # `Null TopoDS_Shape` from the fuse. A real slab of plate_w carries the ring;
    # the dovetail hangs beneath it, which is also how an actual Arca plate is made.
    arca_w = min(ARCA_TOP_W, plate_w)
    dove = arca_base(arca_w, plate_h, plate_len)
    # CAP the slab thickness. It only exists to carry the sockets, and a deeper slab
    # buys nothing but a deeper bore: past a socket depth of about 5.7 mm the ring's
    # helical ribs stop fusing into the plate and each one survives as its own body
    # (a 16 mm dovetail came out as SIX pieces — five loose ribs and the plate).
    # 7.2 mm of slab is a 5.7 mm socket, which is more than four turns of 1/4-20 —
    # far more engagement than any tripod fitting actually uses.
    slab_t = min(7.2, max(4.0, plate_h * 0.6))
    slab = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, plate_h))
        .rect(plate_w, plate_len).extrude(slab_t)
    )
    # The slab's underside sits ON the dovetail's flat platform → volumetric fuse.
    body = dove.union(slab)
    top_z = plate_h + slab_t

    # Sockets are bored into the SLAB only, so their depth is bounded by the slab.
    max_depth = slab_t - 1.5

    # Central 3/8-16 female socket down from the top (closed bottom).
    depth_c = max(2.0, min(thread_len, max_depth))
    bore_c, rib_c, br_c = female_socket_cut("3/8-16", clearance, depth_c, top_z)
    body = body.cut(bore_c)
    if rib_c is not None:
        body = body.union(rib_c)

    # Ring of 1/4-20 female sockets (closed bottoms). Keep the whole socket — bore
    # plus its rib overlap — inside the slab's own footprint with a real ligament of
    # material to the edge, and clear of the central 3/8-16 socket.
    depth_q = max(2.0, min(thread_len, max_depth))
    q_r = UNC["1/4-20"]["major"] / 2.0 + clearance + 0.35
    r_max = plate_w / 2.0 - q_r - 2.0
    r_min = br_c + q_r + 1.5
    r_ring = max(r_min, min(ring_dia / 2.0, r_max))
    if r_ring <= r_max:
        for i in range(n_quarter):
            ang = 2.0 * math.pi * i / n_quarter
            cx, cy = r_ring * math.cos(ang), r_ring * math.sin(ang)
            bore_q, rib_q, br_q = female_socket_cut("1/4-20", clearance, depth_q, top_z)
            body = body.cut(bore_q.translate((cx, cy, 0)))
            if rib_q is not None:
                body = body.union(rib_q.translate((cx, cy, 0)))

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_quarter_to_arca():
    """An Arca dovetail plate carrying a real male 1/4-20 stud on top — an Arca
    head now drives any 1/4-20 device. The stud roots on the (closed) plate top."""
    plate_len = max(40.0, plate_w * 0.7)
    body = arca_base(min(ARCA_TOP_W, plate_w), plate_h, plate_len)
    top_z = plate_h
    stud, stud_top, sr = male_stud("1/4-20", clearance, thread_len, top_z - 0.3)
    body = body.union(stud)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_reducer_bushing():
    """The classic camera thread reducer: external male 3/8-16 + internal female
    1/4-20 through it. A 3/8-16 stud/socket now accepts a 1/4-20 fitting.

    The 1/4-20 clearance hole is drilled into each component BEFORE its helical rib
    is fused on — never through the finished part, which does not converge — so the
    piece is watertight and vents both ends only via that one clean cylinder."""
    spec3 = UNC["3/8-16"]
    body_h = max(thread_len + 2.0, 8.0)
    # DERIVED CLAMP — the 1/4-20 socket must fit INSIDE the 3/8-16 shaft with a real
    # wall between them. A 3/8-16 male thread shrinks with clearance while the 1/4-20
    # female bore GROWS with it, so the two march toward each other: at clearance 0.8
    # the shaft radius is 3.37 mm and the bore radius 3.98 mm — the bore is wider than
    # the shaft it is supposed to sit in, and the "wall" is -0.6 mm. The result is not
    # a bushing at all, and the boolean returns torn shells. Cap the clearance at what
    # still leaves a 0.6 mm ligament; a reducer is a thin-walled part by nature and
    # simply cannot carry a sloppier fit on both threads at once.
    def _shaft_r_at(c):
        thr_depth = 0.5 * (spec3["major"] - spec3["minor"]) * 0.5 + 0.15
        return max(2.0, spec3["major"] - 2.0 * c) / 2.0 - thr_depth

    def _socket_r_at(c):
        return (UNC["1/4-20"]["major"] + 2.0 * c) / 2.0

    red_clear = clearance
    while red_clear > 0.15 and _shaft_r_at(red_clear) - _socket_r_at(red_clear) < 0.6:
        red_clear = round(red_clear - 0.05, 2)
    # FLOOR at 0.15 as well as capping from above. At a true zero clearance the male
    # thread grows to its full nominal major diameter at the same moment the female
    # bore shrinks to its own, and the socket's rib stops fusing into the shaft — the
    # part comes back as the bushing plus a loose thread coil rattling inside it. A
    # printed thread needs some fit allowance regardless; 0.15 mm is the tightest this
    # geometry builds, and it is still a firm press fit in practice.
    red_clear = min(max(red_clear, 0.15), 0.8)

    # The 1/4-20 clearance hole runs the whole length — a clean cylinder venting both
    # ends, the only through-void in the piece. It is drilled into every component
    # BEFORE any helical rib is fused on, never cut through the finished part: a
    # cylinder driven coaxially through a completed thread is a boolean OCCT does not
    # converge on, and this mode HUNG past a 400 s timeout rather than erroring.
    minor_q = UNC["1/4-20"]["minor"]
    socket_r = _socket_r_at(red_clear)
    thru_r = min(minor_q / 2.0 - 0.1, socket_r - 0.4)

    stud, stud_top, sr = male_stud("3/8-16", red_clear, body_h - 1.0, 0.0, thru_r)
    body = stud

    # Wrench flange, pre-drilled to the same axis so no cut ever crosses a thread.
    af = spec3["major"] + 6.0
    r_ac = (af / 2.0) / math.cos(math.radians(30.0))
    flange = (
        cq.Workplane("XY").polygon(6, 2.0 * r_ac).extrude(2.4)
        .cut(cq.Workplane("XY").workplane(offset=-1.0).circle(thru_r).extrude(4.4))
    )
    body = body.union(flange)

    # `male_stud` sizes itself from a half-integer turn count, so the real top of the
    # shaft is `stud_top` — NOT body_h, which is derived from thread_len and runs well
    # ahead of it. Asking for a 16 mm socket in a 9.5 mm stud drove the bore out
    # through the bottom face and took the closed base with it. Bore from the top down
    # to a floor that always leaves a solid base plate above z = 0.
    floor_z = 2.4 + 1.2                      # flange height plus a real base
    depth_i = max(1.5, min(thread_len, stud_top - 0.5 - floor_z))
    bore_i, rib_i, br_i = female_socket_cut("1/4-20", red_clear, depth_i, stud_top - 0.5)
    body = body.cut(bore_i)
    if rib_i is not None:
        body = body.union(rib_i)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "quarter_to_arca":
    result = build_quarter_to_arca()
elif target_part == "reducer_bushing":
    result = build_reducer_bushing()
else:
    result = build_hub_plate()
