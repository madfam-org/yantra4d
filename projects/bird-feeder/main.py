"""
Bottle-Fed Bird Feeder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Turns a discarded PET soda bottle into a gravity bird / seed feeder. The feeder
cap screws onto a standard PCO-1881 bottle neck (the CDG "PET Bottle Neck" thread,
shared with the bottle-thread cartridge); seed flows down through ports onto a
catch tray with a perch. Three parts: a threaded feeder cap with seed ports, a
tray base with perch, and a self-contained tube feeder that does not need a bottle.

Thread strategy (verified watertight + fast, ~1-4 s):
  A trapezoidal rib is swept along a genuine `makeHelix` for ~1-1.5 turns. The
  rib's ROOT radius is pushed `overlap` into the surrounding wall, so the union is
  a clean volumetric boolean (a rib kissing the bore surface tessellates into
  cracks; overlapping it keeps the mesh watertight).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `wall`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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


# ── PCO-1881 bottle-neck finish (nominal geometry) ───────────────────────────
# The ubiquitous soda / water bottle finish. Short single-start thread, ~1 turn.
PCO_MAJOR = 27.4   # thread major (outer) diameter (mm)
PCO_PITCH = 2.7    # thread pitch (mm)


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "feeder_cap"))  # feeder_cap | tray_base | tube_feeder

clearance   = float(PARAM(lambda: clearance,  0.4))   # printed-thread fit slop per side (mm)
wall        = float(PARAM(lambda: wall,       2.6))   # side wall thickness (mm)
turns       = float(PARAM(lambda: turns,      1.5))   # thread engagement turns
tray_dia    = float(PARAM(lambda: tray_dia, 110.0))   # catch-tray outer diameter (mm)
tray_wall_h = float(PARAM(lambda: tray_wall_h, 16.0)) # tray lip height (mm)
port_count  = int(  PARAM(lambda: port_count,    3))  # seed ports around the cap/tube
port_size   = float(PARAM(lambda: port_size, 14.0))   # seed port width (mm)
perch_len   = float(PARAM(lambda: perch_len, 32.0))   # perch stick length beyond tray (mm)
perch_dia   = float(PARAM(lambda: perch_dia,  8.0))   # perch rod diameter (mm)
tube_h      = float(PARAM(lambda: tube_h,   140.0))   # tube-feeder body height (mm)
tube_dia    = float(PARAM(lambda: tube_dia,  60.0))   # tube-feeder body diameter (mm)

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
clearance   = max(0.1, min(clearance, 0.9))
wall        = max(2.0, min(wall, 5.0))
turns       = max(1.0, min(turns, 2.0))
tray_dia    = max(70.0, min(tray_dia, 220.0))
tray_wall_h = max(8.0, min(tray_wall_h, 40.0))
port_count  = max(2, min(port_count, 6))
port_size   = max(6.0, min(port_size, 26.0))
perch_len   = max(15.0, min(perch_len, 60.0))
perch_dia   = max(4.0, min(perch_dia, 16.0))
tube_h      = max(60.0, min(tube_h, 300.0))
tube_dia    = max(35.0, min(tube_dia, 120.0))


# ── Thread primitives (inlined — repo-lib imports are blocked in the sandbox) ─
def _helix_path(pitch, height):
    """A helical wire centered on Z (radius ~0 so the swept profile traces it)."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal (female) helical rib pointing INWARD from a bore wall. Root at
    bore_r + overlap (bites into the wall), crest at bore_r - thr_depth."""
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


def threaded_neck_socket(base_th, with_base):
    """A cylindrical socket with an internal PCO-1881 female thread. Opens at z=0.
    `with_base` closes the top with a `base_th` disk. Returns
    (solid, height, outer_d, bore_r)."""
    thr_turns = min(2.0, turns)
    thr_major = PCO_MAJOR + 2.0 * clearance
    bore_r = thr_major / 2.0
    thr_depth = 0.55 * PCO_PITCH
    overlap = min(0.6, wall * 0.35 + 0.2)
    thread_h = PCO_PITCH * thr_turns

    outer_d = thr_major + 2.0 * wall
    body_h = thread_h + (base_th if with_base else 0.0) + 1.5

    body = cq.Workplane("XY").circle(outer_d / 2.0).extrude(body_h)
    bore_depth = thread_h + (0.0 if with_base else 2.0) + 0.6
    bore = cq.Workplane("XY").circle(bore_r).extrude(bore_depth)
    body = body.cut(bore)
    body = body.union(female_thread(bore_r, PCO_PITCH, thread_h, thr_depth, overlap))
    return body, body_h, outer_d, bore_r


def _seed_ports(solid, ring_r, z_center, count, size):
    """Cut `count` seed openings radially around a body at height z_center. Each
    port is a rounded through-cut (a cylinder laid on its side, aimed radially)
    that breaches both walls; the swept interior is the seed channel. Rounded
    ports keep the boolean clean (no coincident box faces) so the mesh stays
    watertight even at extreme sizes."""
    port_r = size / 2.0
    for i in range(count):
        ang = (360.0 / count) * i
        port = (
            cq.Workplane("XY")
            .circle(port_r).extrude(ring_r * 2.0 + 8.0, both=True)  # cylinder along +Z
            .rotate((0, 0, 0), (1, 0, 0), 90)                       # lay it along Y
            .rotate((0, 0, 0), (0, 0, 1), ang)                      # aim radially
            .translate((0, 0, z_center))
        )
        solid = solid.cut(port)
    return solid


# ── Part builders ─────────────────────────────────────────────────────────────
def build_feeder_cap():
    """A PCO-1881 cap that screws onto an inverted bottle. Seed ports near the open
    rim let seed trickle out; a flared collar shelters the ports from rain."""
    body, body_h, outer_d, bore_r = threaded_neck_socket(base_th=0.0, with_base=False)

    # Flared skirt below the thread that spreads seed and sheds rain. Built as a
    # short frustum widening downward, unioned under the socket (which opens at
    # z=0 upward; the bottle screws in from the top).
    skirt_top_r = outer_d / 2.0
    skirt_bot_r = outer_d / 2.0 + 10.0
    skirt_h = 12.0
    skirt = (
        cq.Workplane("XY")
        .circle(skirt_bot_r)
        .workplane(offset=skirt_h)
        .circle(skirt_top_r)
        .loft(combine=True)
        .translate((0, 0, -skirt_h))
    )
    # Hollow the skirt so seed passes: bore continues down through it.
    skirt = skirt.cut(
        cq.Workplane("XY").circle(bore_r).extrude(skirt_h + 2.0).translate((0, 0, -skirt_h - 1.0))
    )
    body = body.union(skirt)

    # Seed ports through the skirt wall, near its bottom.
    body = _seed_ports(body, skirt_bot_r, -skirt_h * 0.45, port_count, port_size * 0.8)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def _perch_and_tray(tray_or):
    """A round catch tray of outer radius tray_or with a raised lip, a domed center
    to shed seed outward, and `port_count` radial perches. Returns the tray solid."""
    floor_t = max(2.5, wall)
    # Tray dish: outer wall ring + floor.
    outer = cq.Workplane("XY").circle(tray_or).extrude(tray_wall_h)
    cavity = (
        cq.Workplane("XY").circle(tray_or - wall)
        .extrude(tray_wall_h).translate((0, 0, floor_t))
    )
    tray = outer.cut(cavity)

    # Low central dome so seed migrates to the feeding ring.
    dome_r = tray_or * 0.5
    dome_h = min(tray_wall_h * 0.6, 10.0)
    try:
        dome = (
            cq.Workplane("XY")
            .circle(dome_r).workplane(offset=dome_h).circle(dome_r * 0.25)
            .loft(combine=True).translate((0, 0, floor_t))
        )
        tray = tray.union(dome)
    except Exception:
        pass  # dome is functional-nice but never fatal

    # Perches: rods sticking radially out through the tray lip.
    for i in range(port_count):
        ang = (360.0 / port_count) * i + (180.0 / port_count)
        rod = (
            cq.Workplane("YZ")
            .circle(perch_dia / 2.0).extrude(tray_or + perch_len)
            .rotate((0, 0, 0), (0, 0, 1), ang)
            .translate((0, 0, tray_wall_h * 0.5))
        )
        tray = tray.union(rod)

    # Central mounting boss so the cap/bottle sits over the tray (open bore lets a
    # hanging wire or the bottle spout pass).
    boss = (
        cq.Workplane("XY").circle(PCO_MAJOR / 2.0 + wall + 2.0)
        .extrude(tray_wall_h + 4.0).translate((0, 0, floor_t))
    )
    boss = boss.cut(
        cq.Workplane("XY").circle(PCO_MAJOR / 2.0 + clearance)
        .extrude(tray_wall_h + 8.0).translate((0, 0, floor_t - 1.0))
    )
    tray = tray.union(boss)
    try:
        tray = tray.clean()
    except Exception:
        pass
    return tray


def build_tray_base():
    """The catch tray + perch that the bottle feeds onto."""
    return _perch_and_tray(tray_dia / 2.0)


def build_tube_feeder():
    """A standalone tube feeder needing no bottle: a closed tube reservoir on top
    of a tray, with seed ports at the base and perches. A press-cap hole is left on
    top for refilling (a printed lid or a cork closes it)."""
    tray_or = tray_dia / 2.0
    tray = _perch_and_tray(tray_or)

    # Tube reservoir rising from the tray floor.
    t_r = tube_dia / 2.0
    floor_t = max(2.5, wall)
    tube_outer = cq.Workplane("XY").circle(t_r).extrude(tube_h).translate((0, 0, floor_t))
    tube_inner = (
        cq.Workplane("XY").circle(t_r - wall)
        .extrude(tube_h).translate((0, 0, floor_t + floor_t))
    )
    tube = tube_outer.cut(tube_inner)

    # Refill opening at the top.
    tube = tube.cut(
        cq.Workplane("XY").circle(t_r - wall).extrude(wall + 2.0).translate((0, 0, floor_t + tube_h - wall))
    )

    body = tray.union(tube)
    # Seed ports through the tube wall just above the tray floor.
    body = _seed_ports(body, t_r, floor_t + port_size * 0.7, port_count, port_size)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tray_base":
    result = build_tray_base()
elif target_part == "tube_feeder":
    result = build_tube_feeder()
else:
    result = build_feeder_cap()
