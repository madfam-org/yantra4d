"""
Refillable Spice Jar + Threaded Lid — Yantra4D Hyperobject Cartridge (CadQuery).

A refillable spice jar whose mouth carries a REAL single-start helical thread, and
matching screw-on lids (shaker / pour-spout / solid). The jar's external thread and
the lid's internal thread are cut from the SAME nominal envelope (`mouth_dia`,
`pitch`), so any lid printed at the same mouth diameter screws onto any jar.

Thread strategy (bottle-thread volumetric-rib idiom — watertight + fast):
  Sweep a trapezoidal profile along a genuine `makeHelix` path for ~1-2 turns. The
  rib ROOT is pushed a little into the surrounding wall (`overlap`) so the union is
  a clean volumetric boolean, not a fragile tangent kiss — that is what keeps the
  mesh watertight. Male crest sticks OUT; female crest points IN; the female bore
  is the male major diameter plus `clearance` per side, so they mate.

Modes (dispatched via `target_part`):
  * "jar"        — the jar body: solid floor, open threaded mouth (male thread).
  * "shaker_lid" — screw lid with a ring of shaker holes.
  * "pour_lid"   — screw lid with a single pour spout / larger opening.
  (lid_type=solid on either lid mode yields a sealed storage lid.)

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `mouth_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


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
jar_dia   = float(PARAM(lambda: jar_dia,   45.0))   # outer body diameter (mm)
jar_h     = float(PARAM(lambda: jar_h,     70.0))   # total jar height (mm)
mouth_dia = float(PARAM(lambda: mouth_dia, 34.0))   # thread major diameter at mouth
pitch     = float(PARAM(lambda: pitch,      3.0))   # thread pitch (mm)
turns     = float(PARAM(lambda: turns,      1.6))   # thread turns (engagement)
wall      = float(PARAM(lambda: wall,       2.4))   # body / lid wall thickness (mm)
floor     = float(PARAM(lambda: floor,      2.4))   # jar floor thickness (mm)
clearance = float(PARAM(lambda: clearance,  0.4))   # printed-thread fit slop (per side)
lid_h     = float(PARAM(lambda: lid_h,     14.0))   # lid skirt height (mm)
lid_type  = str(  PARAM(lambda: lid_type,     "auto"))  # auto|shaker-holes|pour-spout|solid
hole_dia  = float(PARAM(lambda: hole_dia,   3.5))   # shaker hole diameter (mm)
hole_ring = int(  PARAM(lambda: hole_ring,    7))   # number of shaker holes
spout_dia = float(PARAM(lambda: spout_dia, 12.0))   # pour spout opening diameter (mm)
knurl     = bool( PARAM(lambda: knurl,     True))   # grip flutes on the lid

target_part = str(PARAM(lambda: target_part, "jar"))  # jar | shaker_lid | pour_lid

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
jar_dia = max(24.0, min(jar_dia, 120.0))
mouth_dia = max(16.0, min(mouth_dia, jar_dia - 4.0))
pitch = max(1.5, min(pitch, 6.0))
turns = max(1.0, min(turns, 2.5))
wall = max(1.6, min(wall, 5.0))
floor = max(1.6, min(floor, 6.0))
clearance = max(0.0, min(clearance, 1.0))
jar_h = max(mouth_dia * 0.6 + floor + 10.0, min(jar_h, 200.0))
lid_h = max(pitch * turns + 3.0, min(lid_h, 40.0))

thr_depth = 0.55 * pitch
overlap = min(0.6, wall * 0.35 + 0.2)
thread_h = pitch * turns


# ── Thread primitives (inlined — repo imports are blocked in the sandbox) ─────
def _helix_path(p, h):
    """A helical wire centered on Z; radius ~0 so the swept profile traces it."""
    return cq.Wire.makeHelix(pitch=p, height=h, radius=1e-6)


def male_thread(shaft_r, p, h, depth, ov):
    """External helical rib. Root bites into shaft by `ov`; crest sticks OUT."""
    root_r = max(0.5, shaft_r - ov)
    crest_r = shaft_r + depth
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -p * 0.32),
            (crest_r, -p * 0.14),
            (crest_r, p * 0.14),
            (root_r, p * 0.32),
        ])
        .close()
    )
    rib = prof.sweep(_helix_path(p, h), isFrenet=True)
    return rib.translate((0, 0, p * 0.5))


def female_thread(bore_r, p, h, depth, ov):
    """Internal helical rib. Root bites into wall by `ov`; crest points IN."""
    root_r = bore_r + ov
    crest_r = max(0.5, bore_r - depth)
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -p * 0.32),
            (crest_r, -p * 0.14),
            (crest_r, p * 0.14),
            (root_r, p * 0.32),
        ])
        .close()
    )
    rib = prof.sweep(_helix_path(p, h), isFrenet=True)
    return rib.translate((0, 0, p * 0.5))


def apply_knurl(solid, outer_d, height, teeth=20, depth=0.7):
    """Shallow vertical grip flutes cut as one polar-array cutter (cheap, tight)."""
    try:
        cutter = (
            cq.Workplane("XY")
            .polarArray(radius=outer_d / 2.0, startAngle=0, angle=360, count=teeth)
            .rect(depth, depth * 3.0)
            .extrude(height + 2.0)
            .translate((0, 0, -1.0))
        )
        solid = solid.cut(cutter)
    except Exception:
        pass  # grip is cosmetic — never fatal
    return solid


# ── Part builders ────────────────────────────────────────────────────────────
def build_jar():
    """Jar body: cylindrical vessel, threaded male neck at the mouth."""
    neck_major = mouth_dia            # male major diameter
    shaft_r = neck_major / 2.0
    body_r = jar_dia / 2.0

    # Main body: floor + wall up to the neck shoulder.
    neck_len = thread_h + 2.0
    body_h = jar_h - neck_len
    body = cq.Workplane("XY").circle(body_r).extrude(body_h)

    # Neck: a shorter cylinder (mouth) rising from the shoulder, threaded outside.
    neck_wall = max(1.6, wall)
    neck_outer_r = shaft_r
    neck = (
        cq.Workplane("XY")
        .circle(neck_outer_r)
        .extrude(neck_len)
        .translate((0, 0, body_h))
    )
    body = body.union(neck)

    # Hollow the interior: bore up through the neck, leaving the floor.
    cav_r = max(2.0, shaft_r - neck_wall)
    cavity = (
        cq.Workplane("XY")
        .circle(cav_r)
        .extrude(jar_h)
        .translate((0, 0, floor))
    )
    body = body.cut(cavity)

    # Add the functional male thread on the neck.
    body = body.union(
        male_thread(neck_outer_r, pitch, thread_h, thr_depth, overlap)
        .translate((0, 0, body_h + 1.0))
    )

    # Soften the base edge for print adhesion / comfort (non-fatal).
    try:
        body = body.edges("<Z").fillet(min(0.8, floor * 0.4))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def _lid_body():
    """Common screw-lid shell: a top disk + downward skirt with a female thread
    matched to the jar mouth. Returns (lid, top_z, outer_d, bore_r)."""
    thr_major = mouth_dia + 2.0 * clearance     # female bore major = male + clearance
    bore_r = thr_major / 2.0
    outer_r = bore_r + wall
    outer_d = outer_r * 2.0

    # Skirt: outer cylinder, hollow bore, closed by a top disk.
    skirt = cq.Workplane("XY").circle(outer_r).extrude(lid_h)
    bore = cq.Workplane("XY").circle(bore_r).extrude(thread_h + 1.0)
    skirt = skirt.cut(bore)
    top = (
        cq.Workplane("XY")
        .circle(outer_r)
        .extrude(wall)
        .translate((0, 0, lid_h))
    )
    lid = skirt.union(top)

    # Female thread inside the skirt (opens at z=0).
    lid = lid.union(female_thread(bore_r, pitch, thread_h, thr_depth, overlap))
    top_z = lid_h + wall
    return lid, top_z, outer_d, bore_r


def _apply_shaker(lid, top_z, bore_r):
    """Punch a centered hole + a ring of shaker holes through the top disk."""
    hr = max(0.6, min(hole_dia, bore_r * 0.6) / 2.0)
    n = max(3, min(hole_ring, 16))
    ring_r = bore_r * 0.62
    z0 = top_z - wall - 2.0
    center = cq.Workplane("XY").circle(hr).extrude(wall + 4.0).translate((0, 0, z0))
    lid = lid.cut(center)
    for i in range(n):
        a = 2.0 * math.pi * i / n
        x = ring_r * math.cos(a)
        y = ring_r * math.sin(a)
        h = cq.Workplane("XY").circle(hr).extrude(wall + 4.0).translate((x, y, z0))
        lid = lid.cut(h)
    return lid


def _apply_pour(lid, top_z, bore_r):
    """Cut a single larger pour opening through the top disk."""
    sr = max(2.0, min(spout_dia, bore_r * 1.4) / 2.0)
    hole = cq.Workplane("XY").circle(sr).extrude(wall + 6.0).translate((0, 0, top_z - wall - 3.0))
    return lid.cut(hole)


def build_lid(opening):
    """Screw lid; `opening` picks the top: 'shaker' | 'pour' | 'solid'.
    The mode chooses the default opening; `lid_type` (if set) overrides it."""
    lid, top_z, outer_d, bore_r = _lid_body()
    # lid_type param, when explicitly one of the discrete values, wins.
    if lid_type == "shaker-holes":
        opening = "shaker"
    elif lid_type == "pour-spout":
        opening = "pour"
    elif lid_type == "solid":
        opening = "solid"

    if opening == "shaker":
        lid = _apply_shaker(lid, top_z, bore_r)
    elif opening == "pour":
        lid = _apply_pour(lid, top_z, bore_r)
    # 'solid' → sealed storage lid, no opening.

    if knurl:
        lid = apply_knurl(lid, outer_d, top_z)
    try:
        lid = lid.clean()
    except Exception:
        pass
    return lid


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "shaker_lid":
    result = build_lid("shaker")
elif target_part == "pour_lid":
    result = build_lid("pour")
else:
    result = build_jar()
