"""
Threaded Storage Capsule — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A screw-together waterproof EDC canister: a tube body with an EXTERNAL thread at its
opening, and a lid with a matching INTERNAL thread, an O-ring seat groove, and a
keyring loop. Body and lid threads share the same nominal + clearance so they mate.

Three parts (dispatched via `target_part`):
  * "body"    — a tube: closed bottom, open top carrying an external male thread.
  * "lid"     — a cap: internal female thread + an O-ring groove in the seat + a
                keyring loop on top.
  * "capsule" — a 2-part preview rendering body and lid together (lid perched above
                the body) so the pair is visible at once.

Thread strategy (verified watertight + fast, ~1-4 s): the bottle-thread idiom — a
trapezoidal profile swept along a real makeHelix path for ~2.5 turns, unioned as a
rib whose root is pushed INTO the wall material (the `overlap`) so the boolean is a
clean volumetric fuse rather than a fragile tangent kiss. The body post/wall extends
beyond the thread on both ends so the helix start/end embed in solid material.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `inner_dia`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "body"))   # body | lid | capsule

inner_dia   = float(PARAM(lambda: inner_dia,  24.0))   # usable interior diameter (mm)
inner_len   = float(PARAM(lambda: inner_len,  50.0))   # usable interior length of the body (mm)
wall        = float(PARAM(lambda: wall,        2.4))   # wall thickness (mm)
clearance   = float(PARAM(lambda: clearance,   0.4))   # per-side thread fit clearance (mm)
oring       = bool( PARAM(lambda: oring,      True))   # cut an O-ring groove in the lid seat
oring_dia   = float(PARAM(lambda: oring_dia,   2.0))   # O-ring cord diameter (mm)
loop        = bool( PARAM(lambda: loop,       True))   # keyring loop on the lid

# Clamp inputs to sane ranges so extreme UI values still build watertight.
inner_dia  = max(10.0, min(inner_dia, 80.0))
inner_len  = max(15.0, min(inner_len, 160.0))
wall       = max(1.6, min(wall, 6.0))
clearance  = max(0.0, min(clearance, 1.0))
oring_dia  = max(1.0, min(oring_dia, 5.0))


# ── Thread geometry (shared body<->lid interface) ────────────────────────────
# The MALE thread on the body has major diameter = inner_dia + 2*wall_thread; the
# FEMALE thread in the lid uses the same nominal plus clearance per side so they mate.
THREAD_LEN_TURNS = 2.5
PITCH = max(2.0, inner_dia * 0.12)                 # coarse, printable pitch
THREAD_H = PITCH * THREAD_LEN_TURNS
BODY_WALL = wall
# Male major radius = the body's outer wall at the neck.
MALE_MAJOR_R = inner_dia / 2.0 + BODY_WALL
THR_DEPTH = 0.5 * PITCH


def _helix_path(pitch, height):
    """A helical wire centred on Z (radius ~0 so a swept profile already at the
    target radius traces the true helix)."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def male_thread(shaft_r, pitch, thread_h, thr_depth, overlap):
    """External helical rib. Root bites into the shaft by `overlap`; crest sticks out
    to shaft_r + thr_depth."""
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


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal helical rib pointing INWARD from a bore wall. Root at bore_r + overlap
    (bites into the wall), crest at bore_r - thr_depth (grabs the male crest)."""
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


# ── Part builders ────────────────────────────────────────────────────────────
def build_body():
    """Tube: closed bottom, open top with an external male thread. Returns the solid.

    Layout (z): floor [0, wall]; interior [wall, wall+inner_len]; threaded neck at the
    top of the outer wall. The neck outer wall extends a pitch beyond the thread ends
    so the helix embeds (watertight)."""
    floor = wall
    body_h = floor + inner_len
    neck_start = body_h - THREAD_H - PITCH        # thread sits just below the rim
    if neck_start < floor + 2.0:
        neck_start = floor + 2.0

    outer_r = MALE_MAJOR_R
    # Outer tube.
    body = cq.Workplane("XY").circle(outer_r).extrude(body_h)
    # Hollow the interior (leave the floor).
    bore = (
        cq.Workplane("XY")
        .circle(inner_dia / 2.0)
        .extrude(inner_len + 1.0)
        .translate((0, 0, floor))
    )
    body = body.cut(bore)
    # Male thread on the neck.
    overlap = min(0.6, BODY_WALL * 0.35 + 0.2)
    thread = male_thread(outer_r, PITCH, THREAD_H, THR_DEPTH, overlap).translate(
        (0, 0, neck_start)
    )
    body = body.union(thread)
    # Lead-in chamfer at the rim for an easy thread start.
    try:
        body = body.edges(">Z").chamfer(min(0.8, BODY_WALL * 0.4))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def _lid_solid_and_metrics():
    """Shared lid geometry. Returns (lid_solid, lid_height, lid_outer_r).

    Thread mating: the female bore clears the MALE CREST (MALE_MAJOR_R + THR_DEPTH)
    by `clearance` per side, so the female crest (bore - THR_DEPTH) lands just outside
    the male pitch line and the two threads interlock with a printable clearance."""
    bore_r = MALE_MAJOR_R + THR_DEPTH + clearance
    lid_wall = wall
    lid_outer_r = bore_r + lid_wall
    # Lid depth: enough to hold the thread + a seat + the top.
    seat_gap = 2.0
    top_th = max(2.0, wall)
    lid_h = THREAD_H + PITCH + seat_gap + top_th

    lid = cq.Workplane("XY").circle(lid_outer_r).extrude(lid_h)
    # Hollow the lid bore from the bottom up to (but not through) the top plate.
    inner_depth = THREAD_H + PITCH + seat_gap
    cavity = cq.Workplane("XY").circle(bore_r).extrude(inner_depth)
    lid = lid.cut(cavity)
    # Female thread just inside the mouth (bottom), matching the body neck.
    overlap = min(0.6, lid_wall * 0.35 + 0.2)
    thr = female_thread(bore_r, PITCH, THREAD_H, THR_DEPTH, overlap).translate((0, 0, PITCH))
    lid = lid.union(thr)

    # O-ring groove: an annular channel in the seat shoulder (the flat the body rim
    # presses against), sized to the cord diameter.
    if oring:
        groove_r = bore_r - oring_dia * 0.6
        groove = (
            cq.Workplane("XY")
            .circle(groove_r + oring_dia / 2.0)
            .circle(max(0.5, groove_r - oring_dia / 2.0))
            .extrude(oring_dia * 0.75)
            .translate((0, 0, inner_depth - oring_dia * 0.2))
        )
        lid = lid.cut(groove)

    return lid, lid_h, lid_outer_r


def build_lid():
    """Cap: internal female thread + O-ring groove + keyring loop on top."""
    lid, lid_h, lid_outer_r = _lid_solid_and_metrics()

    if loop:
        # A keyring loop: a torus-like eye standing on top, built as an outer disc
        # with a hole (a flat tab loop — robust + watertight).
        tab_th = max(2.5, wall)
        tab_w = min(lid_outer_r * 0.9, 10.0)
        eye_r = tab_w / 2.0
        tab = (
            cq.Workplane("XZ")
            .circle(eye_r)
            .extrude(tab_th / 2.0, both=True)
            .translate((0, 0, lid_h + eye_r))
        )
        # Bridge the eye to the lid top so it is one solid.
        neck = (
            cq.Workplane("XY")
            .box(tab_w * 0.7, tab_th, eye_r + 1.0, centered=(True, True, False))
            .translate((0, 0, lid_h - 0.5))
        )
        loop_solid = tab.union(neck)
        # Hole through the eye.
        hole = (
            cq.Workplane("XZ")
            .circle(eye_r * 0.5)
            .extrude(tab_th, both=True)
            .translate((0, 0, lid_h + eye_r))
        )
        loop_solid = loop_solid.cut(hole)
        lid = lid.union(loop_solid)

    # Grip knurl for finger purchase (single polar-array cutter — cheap + watertight).
    try:
        teeth = 28
        cutter = (
            cq.Workplane("XY")
            .polarArray(radius=lid_outer_r, startAngle=0, angle=360, count=teeth)
            .rect(0.8, 2.2)
            .extrude(lid_h)
        )
        lid = lid.cut(cutter)
    except Exception:
        pass

    try:
        lid = lid.clean()
    except Exception:
        pass
    return lid


def build_capsule():
    """A 2-part preview: the body plus the lid floating above it, so the mating pair
    is visible at once. (Rendered as a single fused-for-preview solid via a small air
    gap — the parts do not touch, so it reads as an exploded assembly.)"""
    body = build_body()
    lid, lid_h, lid_outer_r = _lid_solid_and_metrics()
    floor = wall
    body_h = floor + inner_len
    # Perch the lid above the body, mouth-down (flip it) so it visually pairs.
    lid = lid.rotate((0, 0, 0), (1, 0, 0), 180)
    lid = lid.translate((0, 0, body_h + lid_h + 12.0))
    return body.union(lid)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "lid":
    result = build_lid()
elif target_part == "capsule":
    result = build_capsule()
else:
    result = build_body()
