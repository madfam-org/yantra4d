"""
Sprinkler / Nozzle Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Puts a real Garden-Hose-Thread (GHT 3/4") interface on the front of a hose so any
sprinkler, spray nozzle, or drip line screws on. Three parts: a straight GHT
coupler (female↔female), a nozzle adapter (GHT female → reduced push/barb spout),
and a Y-splitter that feeds two GHT outlets from one inlet.

Thread strategy (verified watertight + fast):
  Single-start helical ribs swept along a genuine `cq.Wire.makeHelix` path built at
  the MEAN thread radius (a real-radius helix keeps the sweep frame non-singular →
  fast + watertight). Each rib is UNIONED into the wall as positive material with
  its root pushed `overlap` into the wall, so the boolean is fully volumetric, not
  a fragile tangent kiss. Turns are capped (~2.5) because the helical fuse grows
  super-linearly and hose fittings only engage a couple of turns.
  GHT 3/4": ~26.4 mm major, 11.5 TPI ≈ 2.209 mm pitch (NH garden-hose finish).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `wall`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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


# ── Garden-hose thread (nominal geometry) ────────────────────────────────────
GHT_MAJOR = 26.4        # GHT 3/4" thread major (outer) diameter (mm)
GHT_PITCH = 25.4 / 11.5  # 11.5 TPI -> ~2.209 mm pitch
_MAX_TURNS = 2.5


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "ght_coupler"))  # ght_coupler | nozzle_adapter | y_splitter

clearance  = float(PARAM(lambda: clearance,   0.35))   # printed-thread fit slop per side (mm)
wall       = float(PARAM(lambda: wall,         3.0))   # side wall thickness (mm)
bore_dia   = float(PARAM(lambda: bore_dia,    14.0))   # central through-bore (fluid path, mm)
turns      = float(PARAM(lambda: turns,        2.0))   # thread engagement turns
grip_knurl = bool( PARAM(lambda: grip_knurl,  True))   # grip flutes around the body
spout_dia  = float(PARAM(lambda: spout_dia,   13.0))   # nozzle-adapter push/barb OD (mm)
barb_count = int(  PARAM(lambda: barb_count,     3))   # barb ridges on nozzle adapter
split_ang  = float(PARAM(lambda: split_ang,   35.0))   # half-angle of each Y outlet (deg)

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
clearance  = max(0.1, min(clearance, 0.8))
wall       = max(2.0, min(wall, 6.0))
bore_dia   = max(4.0, min(bore_dia, 22.0))
turns      = max(1.0, min(turns, _MAX_TURNS))
spout_dia  = max(6.0, min(spout_dia, 24.0))
barb_count = max(1, min(barb_count, 6))
split_ang  = max(15.0, min(split_ang, 55.0))

bore_r = bore_dia / 2.0


# ── Thread primitives (inlined — repo-lib imports are blocked in the sandbox) ─
def _helix_path(pitch, height, mean_r):
    """Helical wire centered on Z at the MEAN thread radius (non-singular frame)."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=mean_r)


def female_thread(bore_radius, pitch, thread_h, overlap):
    """Internal (female) helical rib pointing INWARD from a bore wall. Root at
    bore_radius + overlap (bites into the wall), crest at bore_radius - depth."""
    depth = 0.5 * pitch
    outer_r = bore_radius + overlap
    crest_r = max(0.6, bore_radius - depth)
    mean_r = (outer_r + crest_r) / 2.0
    half_root = pitch * 0.28
    half_crest = max(0.05, half_root - depth * math.tan(math.radians(30.0)))
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (outer_r, -half_root),
            (crest_r, -half_crest),
            (crest_r, half_crest),
            (outer_r, half_root),
        ])
        .close()
    )
    rib = prof.sweep(_helix_path(pitch, thread_h + pitch, mean_r), isFrenet=True, makeSolid=True)
    return rib.translate((0, 0, -pitch * 0.5))


# ── Feature builders ──────────────────────────────────────────────────────────
def female_socket(z0, thr_turns):
    """A GHT female-threaded socket sitting on z0, opening upward. Bore = thread
    major + clearance; the wall wraps it. Returns (solid, top_z, outer_r)."""
    pitch = GHT_PITCH
    thr_major = GHT_MAJOR + 2.0 * clearance
    b_r = thr_major / 2.0
    thread_h = pitch * thr_turns
    outer_r = b_r + wall
    h = thread_h + 2.5
    body = cq.Workplane("XY").circle(outer_r).extrude(h).translate((0, 0, z0))
    hole = cq.Workplane("XY").circle(b_r).extrude(h + 1.0).translate((0, 0, z0 - 0.5))
    body = body.cut(hole)
    overlap = min(0.6, wall * 0.35 + 0.2)
    thr = female_thread(b_r, pitch, thread_h, overlap).translate((0, 0, z0 + 0.6))
    body = body.union(thr)
    return body, z0 + h, outer_r


def barb_nozzle(z0):
    """A barbed / push-fit spout rising from z0: a stack of tapered ridges. Returns
    (solid, top_z, ridge_r)."""
    tip_r = max(bore_r + 1.0, spout_dia / 2.0 - 1.0)
    ridge_r = spout_dia / 2.0
    ridge_h = 4.0
    gap = 1.4
    body = None
    z = z0
    for _ in range(barb_count):
        ring = (
            cq.Workplane("XY")
            .circle(tip_r)
            .workplane(offset=ridge_h * 0.7).circle(ridge_r)
            .workplane(offset=ridge_h * 0.3).circle(tip_r)
            .loft(combine=True)
            .translate((0, 0, z))
        )
        body = ring if body is None else body.union(ring)
        z += ridge_h + gap
    core = cq.Workplane("XY").circle(tip_r).extrude(z - z0).translate((0, 0, z0))
    body = core if body is None else body.union(core)
    return body, z, ridge_r


def add_hub(z_bottom, z_top, r):
    """A central grip hub spanning [z_bottom, z_top], optionally fluted for grip."""
    hub = cq.Workplane("XY").circle(r).extrude(z_top - z_bottom).translate((0, 0, z_bottom))
    if grip_knurl:
        try:
            cutter = (
                cq.Workplane("XY")
                .polarArray(radius=r, startAngle=0, angle=360, count=18)
                .rect(1.0, 2.6).extrude(z_top - z_bottom + 2.0)
                .translate((0, 0, z_bottom - 1.0))
            )
            hub = hub.cut(cutter)
        except Exception:
            pass  # knurl is cosmetic — never fatal
    return hub


def bore_through(body, z_low, z_high):
    """Cut the fluid channel through the whole adapter (axis-aligned)."""
    chan = cq.Workplane("XY").circle(bore_r).extrude(z_high - z_low + 4.0).translate((0, 0, z_low - 2.0))
    body = body.cut(chan)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Part builders ─────────────────────────────────────────────────────────────
def build_ght_coupler():
    """GHT female thread on BOTH ends — joins two hoses, or a hose to a sprinkler
    with a GHT male tail. A central knurled hub sits between the sockets."""
    hub_r = GHT_MAJOR / 2.0 + wall + 1.0
    hub_h = 8.0

    bottom, _, _ = female_socket(0.0, turns)
    bottom = bottom.rotate((0, 0, 0), (1, 0, 0), 180)  # opens downward
    bh = GHT_PITCH * turns + 2.5
    bottom = bottom.translate((0, 0, bh))              # sit on z in [0, bh]
    hub = add_hub(bh, bh + hub_h, hub_r)
    top, z_top, _ = female_socket(bh + hub_h, turns)

    body = bottom.union(hub).union(top)
    body = bore_through(body, 0.0, z_top)
    return body


def build_nozzle_adapter():
    """GHT female socket on the bottom, a reduced push/barb spout on top — adapt a
    hose down to a sprinkler head, spray gun, or drip tube."""
    sock, z_top_sock, sock_or = female_socket(0.0, turns)
    sock = sock.rotate((0, 0, 0), (1, 0, 0), 180)
    sh = GHT_PITCH * turns + 2.5
    sock = sock.translate((0, 0, sh))                  # socket opens down, [0, sh]

    # Shoulder disk closes the top of the socket and carries the spout.
    shoulder_t = max(2.2, wall)
    shoulder = cq.Workplane("XY").circle(sock_or).extrude(shoulder_t).translate((0, 0, sh))

    nozzle, ntop, _ = barb_nozzle(sh + shoulder_t)
    body = sock.union(shoulder).union(nozzle)
    body = bore_through(body, 0.0, ntop)
    return body


def build_y_splitter():
    """One GHT inlet at the bottom feeding two GHT outlets that fan out at
    ±split_ang. Each outlet is a female socket on the end of an angled tube."""
    ang = split_ang
    inlet, in_top, in_or = female_socket(0.0, turns)  # opens up at z=0

    # Manifold body: a stubby cylinder above the inlet that the arms sprout from.
    man_r = in_or
    man_h = 14.0
    manifold = cq.Workplane("XY").circle(man_r).extrude(man_h).translate((0, 0, in_top))

    body = inlet.union(manifold)

    arm_len = 26.0
    arm_r = GHT_MAJOR / 2.0 + wall
    branch_z = in_top + man_h * 0.5
    outlets_top = []
    for sgn in (-1.0, 1.0):
        # Straight arm tube built along +Z, then rotated about Y by ±ang and
        # dropped onto the branch point.
        arm = cq.Workplane("XY").circle(arm_r).extrude(arm_len)
        sock, sock_top, _ = female_socket(arm_len, turns)
        limb = arm.union(sock)
        limb = limb.rotate((0, 0, 0), (0, 1, 0), sgn * ang)
        limb = limb.translate((0, 0, branch_z))
        body = body.union(limb)
        # Track the far end for the channel bore.
        outlets_top.append((sgn, sock_top + arm_len))

    try:
        body = body.clean()
    except Exception:
        pass

    # Bore the inlet channel up through the manifold.
    body = body.cut(
        cq.Workplane("XY").circle(bore_r).extrude(in_top + man_h + 2.0).translate((0, 0, -2.0))
    )
    # Bore each angled outlet channel: a rod along +Z rotated to match the arm.
    for sgn, reach in outlets_top:
        chan = cq.Workplane("XY").circle(bore_r).extrude(reach + 6.0)
        chan = chan.rotate((0, 0, 0), (0, 1, 0), sgn * ang)
        chan = chan.translate((0, 0, branch_z - 4.0))
        body = body.cut(chan)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "nozzle_adapter":
    result = build_nozzle_adapter()
elif target_part == "y_splitter":
    result = build_y_splitter()
else:
    result = build_ght_coupler()
