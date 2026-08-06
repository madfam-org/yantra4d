"""
Gravity Pet Dispenser — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Turns an inverted PET bottle into a self-refilling water or feed station. A base
screws onto the bottle neck (real PCO-1881 finish thread) and holds an inverted
bottle over a trough; as the animal drinks/eats, gravity refills the trough to
the bottle-mouth level. Shares the bottle-neck thread interface with the
`bottle-thread` cartridge.

  * "water_base"    — a threaded socket over a broad drinking trough; water
                      refills by gravity (target_part == "water_base").
  * "feed_hopper"   — the same neck thread over a steeper kibble chute so dry
                      food slides down as it is eaten (target_part ==
                      "feed_hopper").
  * "bird_dispenser"— a compact perch-and-cup version for a bird feeder
                      (target_part == "bird_dispenser").

Thread strategy (verified watertight + fast, mirrors bottle-thread): sweep a
trapezoidal rib along a genuine `makeHelix` path for ~1-1.5 turns. The rib root
is pushed into the wall (`overlap`) so the union is a clean volumetric boolean
rather than a fragile tangent kiss. The trough/hopper is a solid pool with a
gravity gap under the bottle mouth so liquid/kibble can flow out.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
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


# ── Bottle-neck finish standards (nominal geometry, shared with bottle-thread) ─
NECK_STANDARDS = {
    "PCO-1881": {"major_d": 27.4, "pitch": 2.7, "turns": 1.0},
    "PCO-1810": {"major_d": 27.4, "pitch": 2.7, "turns": 1.5},
    "28-410":   {"major_d": 28.0, "pitch": 3.18, "turns": 1.5},
    "38-400":   {"major_d": 38.0, "pitch": 4.2, "turns": 1.25},
}


def neck_geo(name):
    return NECK_STANDARDS.get(name, NECK_STANDARDS["PCO-1881"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part   = str(PARAM(lambda: target_part,  "water_base"))  # water_base | feed_hopper | bird_dispenser
neck_standard = str(PARAM(lambda: neck_standard, "PCO-1881"))    # bottle neck finish

clearance   = float(PARAM(lambda: clearance,   0.4))   # printed-thread fit slop (per side)
wall        = float(PARAM(lambda: wall,        3.0))   # socket / trough wall
trough_dia  = float(PARAM(lambda: trough_dia, 95.0))   # drinking / feed pool diameter (mm)
trough_h    = float(PARAM(lambda: trough_h,   32.0))   # pool wall height (mm)
gap         = float(PARAM(lambda: gap,         9.0))   # gravity gap under the bottle mouth (mm)
extra_turns = float(PARAM(lambda: extra_turns, 0.0))   # extra engagement turns

# ── Clamps ───────────────────────────────────────────────────────────────────
clearance   = max(0.0,  min(clearance, 1.0))
wall        = max(2.0,  min(wall, 6.0))
trough_dia  = max(45.0, min(trough_dia, 220.0))
trough_h    = max(12.0, min(trough_h, 90.0))
gap         = max(4.0,  min(gap, 30.0))
extra_turns = max(0.0,  min(extra_turns, 2.0))


# ── Thread primitives (inlined — imports of repo libs are blocked in sandbox) ─
def _helix_path(pitch, height):
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal (female) helical rib pointing inward from the bore wall to grab a
    male bottle thread. Root at bore_r + overlap (bites into the wall)."""
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


def threaded_socket(std_name, extra_t, clear, wall_th, base_th):
    """A cylindrical socket with an internal female thread for `std_name`, closed
    at the top by a `base_th` disk (the bottle screws in from below). Returns
    (solid, height, outer_d, bore_r)."""
    g = neck_geo(std_name)
    turns = min(2.5, g["turns"] + extra_t)
    pitch = g["pitch"]
    thr_major = g["major_d"] + 2.0 * clear
    bore_r = thr_major / 2.0
    thr_depth = 0.55 * pitch
    overlap = min(0.6, wall_th * 0.35 + 0.2)
    thread_h = pitch * turns

    outer_d = thr_major + 2.0 * wall_th
    body_h = thread_h + base_th + 1.5

    body = cq.Workplane("XY").circle(outer_d / 2.0).extrude(body_h)
    bore = cq.Workplane("XY").circle(bore_r).extrude(thread_h + 0.6)
    body = body.cut(bore)
    body = body.union(female_thread(bore_r, pitch, thread_h, thr_depth, overlap))
    return body, body_h, outer_d, bore_r


# ── Trough / pool ────────────────────────────────────────────────────────────
def pool(dia, height, floor_th):
    """An open cylindrical pool: solid disc floor + ring wall."""
    outer_r = dia / 2.0 + wall
    body = cq.Workplane("XY").circle(outer_r).extrude(floor_th)
    ring = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor_th))
        .circle(outer_r)
        .circle(dia / 2.0)
        .extrude(height)
    )
    body = body.union(ring)
    return body, outer_r


# ── Part builders ────────────────────────────────────────────────────────────
def build_station(pool_dia, pool_h, chute):
    """Common builder: a pool with a central threaded socket held above the floor
    on legs, leaving a `gap` for gravity flow. If `chute` is True, the neck flares
    into a cone so kibble slides out (feed hopper)."""
    floor_th = wall
    body, outer_r = pool(pool_dia, pool_h, floor_th)

    # Threaded socket, closed top, placed above the pool floor by `gap`.
    socket, sh, sod, sbr = threaded_socket(neck_standard, extra_turns, clearance, wall, wall)
    # The socket's OPEN end (bore) must face DOWN so the bottle screws up into it.
    socket = socket.rotate((0, 0, 0), (1, 0, 0), 180)
    socket_z = floor_th + gap
    socket = socket.translate((0, 0, socket_z + sh))

    # Central column/legs joining socket to floor while leaving the gravity gap.
    # Use three legs around the rim so liquid/kibble flows out between them.
    legs = None
    for k in range(3):
        ang = k * 120.0
        leg = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, floor_th))
            .transformed(rotate=cq.Vector(0, 0, ang))
            .transformed(offset=cq.Vector(sod / 2.0 - wall, 0, 0))
            .box(wall * 2.0, wall * 2.2, gap + 1.0, centered=(True, True, False))
        )
        legs = leg if legs is None else legs.union(leg)
    body = body.union(legs).union(socket)

    if chute:
        # Cone flare under the socket bore so food slides down and out.
        cone = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, floor_th + 0.5))
            .circle(sod / 2.0 + 4.0)
            .workplane(offset=gap + sh * 0.5)
            .circle(sbr * 0.6)
            .loft(combine=True)
        )
        # Hollow the cone so it's a chute, not a plug.
        cone_bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, floor_th - 1.0))
            .circle(sbr - 0.5)
            .extrude(gap + sh)
        )
        cone = cone.cut(cone_bore)
        body = body.union(cone)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_water_base():
    return build_station(trough_dia, trough_h, chute=False)


def build_feed_hopper():
    # A deeper, narrower pool with a chute for dry food.
    return build_station(max(60.0, trough_dia * 0.8), max(trough_h, 40.0), chute=True)


def build_bird_dispenser():
    """A compact perch-and-cup bird version: a small pool with a perch ring and
    the neck socket over it."""
    body = build_station(max(45.0, trough_dia * 0.55), max(18.0, trough_h * 0.7), chute=False)
    # Add a perch ring around the pool rim.
    pool_r = max(45.0, trough_dia * 0.55) / 2.0 + wall
    perch = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall + max(18.0, trough_h * 0.7) - wall))
        .circle(pool_r + 8.0)
        .circle(pool_r + 3.0)
        .extrude(wall)
    )
    body = body.union(perch)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "feed_hopper":
    result = build_feed_hopper()
elif target_part == "bird_dispenser":
    result = build_bird_dispenser()
else:  # "water_base"
    result = build_water_base()
