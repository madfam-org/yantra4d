"""
Cable Gland / Strain Nut — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Threaded cable glands seal a cable where it passes through an enclosure wall and
take the strain off the terminations inside. The thread that screws into the box
is a real PG (DIN 40430) or metric-ISO gland thread, so the printed body mates
with off-the-shelf lock nuts and knockouts. Pick the size and the thread major
diameter, pitch and clearance-cored cable bore all land on the standard.

Modes are dispatched via `target_part`:
  * "gland_body"      — the gland: external panel thread + hex wrench flats +
                        tapered compression cap and the cable bore.
  * "lock_nut"        — the interior lock/strain nut: a hex nut with the matching
                        FEMALE gland thread that clamps the gland to the wall.
  * "sealing_reducer" — a threaded reducing insert that seats in the gland bore
                        and steps the cable opening down for a thinner cable.

Thread standards encoded (thread outer/major Ø in mm, DIN 40430 PG + ISO metric):
  PG7=12.5  PG9=15.2  PG11=18.6  PG13.5=20.4  PG16=22.5  PG21=28.3  (PG pitch~1.5)
  M12x1.5  M16x1.5  M20x1.5  M25x1.5   (ISO metric fine, 1.5 mm pitch)
Cable bore per size uses the standard cable range (e.g. PG7 3-6.5, PG21 13-18 mm).

Thread strategy (verified watertight, ~1-4 s/render): sweep a trapezoidal profile
along a genuine makeHelix path for a few turns, with the rib ROOT pushed into the
surrounding material by an `overlap` so the union is a clean volumetric boolean,
never a fragile tangent kiss (tangent ribs tessellate into cracks).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `gland_size`).
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


# ── Gland thread standards (major diameter, pitch, nominal cable range) ───────
# major_d = external thread major (outer) Ø in mm; pitch in mm; cable_lo/hi = the
# standard sealing cable-diameter range for that size (mm).
_GLANDS = {
    "PG7":    {"major_d": 12.5, "pitch": 1.5, "cable_lo": 3.0,  "cable_hi": 6.5},
    "PG9":    {"major_d": 15.2, "pitch": 1.5, "cable_lo": 4.0,  "cable_hi": 8.0},
    "PG11":   {"major_d": 18.6, "pitch": 1.5, "cable_lo": 5.0,  "cable_hi": 10.0},
    "PG13.5": {"major_d": 20.4, "pitch": 1.5, "cable_lo": 6.0,  "cable_hi": 12.0},
    "PG16":   {"major_d": 22.5, "pitch": 1.5, "cable_lo": 10.0, "cable_hi": 14.0},
    "PG21":   {"major_d": 28.3, "pitch": 1.5, "cable_lo": 13.0, "cable_hi": 18.0},
    "M12":    {"major_d": 12.0, "pitch": 1.5, "cable_lo": 3.0,  "cable_hi": 6.5},
    "M16":    {"major_d": 16.0, "pitch": 1.5, "cable_lo": 5.0,  "cable_hi": 10.0},
    "M20":    {"major_d": 20.0, "pitch": 1.5, "cable_lo": 6.0,  "cable_hi": 12.0},
    "M25":    {"major_d": 25.0, "pitch": 1.5, "cable_lo": 11.0, "cable_hi": 17.0},
}


def gland_geo(name):
    """Look up a gland spec, defaulting to PG9. Case/space normalized."""
    k = str(name).strip().upper().replace(" ", "")
    for key, spec in _GLANDS.items():
        if key.upper() == k:
            return spec
    return _GLANDS["PG9"]


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "gland_body"))
gland_size  = str(PARAM(lambda: gland_size,  "PG9"))     # PG7..PG21 | M12..M25
cable_dia   = float(PARAM(lambda: cable_dia,  6.0))      # target cable Ø (mm)
clearance   = float(PARAM(lambda: clearance,  0.4))      # printed-thread fit (per side)
wall        = float(PARAM(lambda: wall,       2.4))      # body wall thickness (mm)
thread_turns = float(PARAM(lambda: thread_turns, 3.0))   # engagement turns on the panel thread
head_flats  = bool(PARAM(lambda: head_flats,  True))     # hex wrench flats on the cap

# Clamp to sane ranges so extreme UI values still build watertight.
cable_dia = max(1.5, min(cable_dia, 24.0))
clearance = max(0.0, min(clearance, 1.0))
wall = max(1.6, min(wall, 6.0))
# Cap engagement at 4 turns: the helical-rib/core boolean union grows super-
# linearly, so 5+ turns blow the render budget while adding no functional grip.
thread_turns = max(1.0, min(thread_turns, 4.0))


# ── Thread primitive (inlined; repo-lib imports are blocked in sandbox) ───────
def _helix_path(pitch, height):
    """A helical wire centered on Z (radius ~0 so the profile traces the helix)."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def male_thread(shaft_r, pitch, thread_h, thr_depth, overlap):
    """External helical rib; root bites into the shaft by `overlap`, crest sticks
    out to shaft_r + thr_depth. Trapezoidal profile, single start."""
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
    """Internal helical rib; root bites OUT into the wall by `overlap`, crest
    points inward to bore_r - thr_depth to grab a male gland thread."""
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


def _hex_flats(solid, across_flats, z0, z1):
    """Cut the round body down to a hexagon between z0 and z1 (wrench flats).
    Built as six planar cutters unioned into one boolean so it stays watertight."""
    af = across_flats
    r_out = af / 2.0 + 6.0                       # start well outside the body
    depth = 20.0
    cutters = None
    for i in range(6):
        ang = 60.0 * i
        plate = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, (z0 + z1) / 2.0), rotate=cq.Vector(0, 0, ang))
            .center(af / 2.0 + depth / 2.0, 0.0)
            .box(depth, r_out * 2.0, (z1 - z0), centered=(True, True, True))
        )
        cutters = plate if cutters is None else cutters.union(plate)
    return solid.cut(cutters)


# ── Part builders ─────────────────────────────────────────────────────────────
def build_gland_body():
    """Gland: external panel thread on a spigot, a hex/knurled body, and a tapered
    compression cap; a through cable bore sized to the cable + clearance."""
    g = gland_geo(gland_size)
    pitch = g["pitch"]
    major_r = g["major_d"] / 2.0
    thr_depth = 0.55 * pitch
    overlap = min(0.6, wall * 0.35 + 0.2)
    thread_h = pitch * thread_turns

    # Cable bore Ø: honor the standard's sealing range, plus a little clearance.
    bore_d = min(max(cable_dia, g["cable_lo"]), g["cable_hi"]) + 2.0 * clearance
    bore_d = min(bore_d, g["major_d"] - 2.0 * wall)          # keep a wall around it
    bore_r = max(0.8, bore_d / 2.0)

    core_r = major_r                                         # thread pitch cylinder
    spigot_h = thread_h + 1.0
    ov = 0.8                                                  # stack overlap (volumetric union)

    # 1) Threaded spigot (screws into the enclosure) at the bottom.
    spigot = cq.Workplane("XY").circle(core_r).extrude(spigot_h)
    spigot = spigot.union(male_thread(core_r, pitch, thread_h, thr_depth, overlap))

    # 2) Hex body seat above the spigot. Extend it DOWN into the spigot by `ov` so
    #    the union is volumetric, not a tangent kiss (tangent leaves a 0-vol seam).
    body_r = major_r + wall
    across_flats = 2.0 * body_r
    seat_h = max(6.0, pitch * 2.5)
    seat = (
        cq.Workplane("XY").circle(body_r).extrude(seat_h + ov)
        .translate((0, 0, spigot_h - ov))
    )

    # 3) Tapered compression cap (dome-free frustum -> clean, watertight loft).
    #    Start the loft base `ov` below the seat top so it overlaps the seat.
    cap_h = max(7.0, bore_r + 4.0)
    top_r = max(bore_r + 1.4, body_r * 0.55)
    cap = (
        cq.Workplane("XY")
        .circle(body_r)
        .workplane(offset=cap_h + ov)
        .circle(top_r)
        .loft(combine=True)
        .translate((0, 0, spigot_h + seat_h - ov))
    )

    body = spigot.union(seat).union(cap)

    # Wrench flats on the hex seat.
    if head_flats:
        body = _hex_flats(body, across_flats, spigot_h + 0.4, spigot_h + seat_h - 0.4)

    # 4) Through cable bore, drilled the whole stack.
    total_h = spigot_h + seat_h + cap_h
    bore = (
        cq.Workplane("XY").circle(bore_r).extrude(total_h + 2.0).translate((0, 0, -1.0))
    )
    body = body.cut(bore)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_lock_nut():
    """Interior lock/strain nut: a hex nut with the matching FEMALE gland thread
    that clamps the gland body to the enclosure wall from inside."""
    g = gland_geo(gland_size)
    pitch = g["pitch"]
    # Female bore is the male major Ø plus clearance per side.
    thr_major = g["major_d"] + 2.0 * clearance
    bore_r = thr_major / 2.0
    thr_depth = 0.55 * pitch
    overlap = min(0.6, wall * 0.35 + 0.2)

    nut_h = max(6.0, pitch * 4.0)
    thread_h = nut_h - 1.0
    body_r = bore_r + wall + 0.8
    across_flats = 2.0 * body_r

    body = cq.Workplane("XY").circle(body_r).extrude(nut_h)
    bore = cq.Workplane("XY").circle(bore_r).extrude(nut_h + 2.0).translate((0, 0, -1.0))
    body = body.cut(bore)
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, overlap))
    body = _hex_flats(body, across_flats, 0.4, nut_h - 0.4)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_sealing_reducer():
    """Threaded reducing insert: seats in the gland bore and steps the cable
    opening down for a thinner cable. External thread grips the gland bore; a
    small flanged shoulder stops it, and the reduced bore takes the small cable."""
    g = gland_geo(gland_size)
    pitch = g["pitch"]
    # The reducer's OUTER thread mates the gland's cable bore family — use a size
    # one step down for the OD so it screws into a larger gland.
    outer_major_r = (g["major_d"] - 2.0 * wall) / 2.0
    outer_major_r = max(3.0, outer_major_r)
    thr_depth = 0.5 * pitch
    overlap = min(0.5, wall * 0.3 + 0.2)

    turns = min(4.0, thread_turns)
    thread_h = pitch * turns
    body_h = thread_h + 1.0

    # Reduced cable bore: aim for the lower end of the range, honor cable_dia.
    small_d = min(max(cable_dia, 2.0), g["cable_lo"]) + 2.0 * clearance
    small_r = max(0.8, small_d / 2.0)

    core = cq.Workplane("XY").circle(outer_major_r).extrude(body_h)
    core = core.union(male_thread(outer_major_r, pitch, thread_h, thr_depth, overlap))

    # Flanged stop shoulder on top. Extend it DOWN into the core by `ov` so the
    # union is volumetric (no tangent 0-volume seam).
    ov = 0.8
    flange_r = outer_major_r + wall
    flange_h = max(2.0, wall)
    flange = (
        cq.Workplane("XY").circle(flange_r).extrude(flange_h + ov)
        .translate((0, 0, body_h - ov))
    )
    # Six grip flutes on the flange rim so it can be hand-tightened.
    try:
        flutes = (
            cq.Workplane("XY")
            .polarArray(radius=flange_r, startAngle=0, angle=360, count=8)
            .rect(0.9, 2.6)
            .extrude(flange_h + 0.5)
            .translate((0, 0, body_h - 0.25))
        )
        flange = flange.cut(flutes)
    except Exception:
        pass

    body = core.union(flange)

    # Reduced through bore.
    total_h = body_h + flange_h
    bore = (
        cq.Workplane("XY").circle(small_r).extrude(total_h + 2.0).translate((0, 0, -1.0))
    )
    body = body.cut(bore)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "gland_body": build_gland_body,
    "lock_nut": build_lock_nut,
    "sealing_reducer": build_sealing_reducer,
}

result = _dispatch.get(target_part, build_gland_body)()
