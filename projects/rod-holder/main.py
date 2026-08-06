"""
Fishing Rod Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Holds a fishing rod by its handle/butt in a cradle socket sized to the rod
diameter. The socket is the shared interface; three mounts present it three ways.

Three parts (dispatched by `target_part`):
  * "wall_holder"  — a screw plate with an angled rod socket, for garage/wall
                     storage; the rod rests butt-down at a slight lean.
  * "rail_holder"  — a clamp that grips a boat/rail tube of `rail_dia`, with the
                     rod socket angled out over the water.
  * "ground_stake" — a spike you push into the ground/sand, with a vertical rod
                     socket, so the rod stands by itself while bank fishing.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `rod_dia`).
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


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "wall_holder"))  # wall|rail|stake

rod_dia    = float(PARAM(lambda: rod_dia,   26.0))  # rod handle/butt diameter (mm)
socket_len = float(PARAM(lambda: socket_len, 70.0)) # socket depth (mm)
wall       = float(PARAM(lambda: wall,       4.0))  # body wall thickness (mm)
lean       = float(PARAM(lambda: lean,      15.0))  # socket lean angle (deg)
plate_w    = float(PARAM(lambda: plate_w,   50.0))  # wall plate width (mm)
screw_dia  = float(PARAM(lambda: screw_dia,  4.5))  # wall screw clearance (mm)
rail_dia   = float(PARAM(lambda: rail_dia,  25.0))  # boat rail tube diameter (mm)
stake_len  = float(PARAM(lambda: stake_len, 160.0)) # ground stake length (mm)

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
rod_dia    = max(10.0, min(rod_dia, 45.0))
socket_len = max(35.0, min(socket_len, 140.0))
wall       = max(2.5, min(wall, 8.0))
lean       = max(0.0, min(lean, 35.0))
plate_w    = max(rod_dia + 2.0 * wall + 6.0, min(plate_w, 120.0))
screw_dia  = max(2.5, min(screw_dia, 8.0))
rail_dia   = max(12.0, min(rail_dia, 45.0))
stake_len  = max(90.0, min(stake_len, 300.0))

sock_r = rod_dia / 2.0 + 0.6      # rod clearance
sock_ro = sock_r + wall           # socket outer radius


# ── Helpers ──────────────────────────────────────────────────────────────────
def rod_socket(depth, closed_bottom=True):
    """A tube socket for the rod: open at the top (z=depth), closed at z=0 by a
    `wall` floor if `closed_bottom`. Built vertical; the caller rotates/places."""
    outer = cq.Workplane("XY").circle(sock_ro).extrude(depth)
    floor_z = wall if closed_bottom else 0.0
    bore = (
        cq.Workplane("XY")
        .circle(sock_r)
        .extrude(depth - floor_z + 0.1)
        .translate((0, 0, floor_z))
    )
    return outer.cut(bore)


def wall_plate(w, h, t):
    """Vertical wall plate in the XZ face; thickness along +Y into wall (y:0→−t)."""
    return (
        cq.Workplane("XY")
        .box(w, t, h, centered=(True, True, False))
        .translate((0, -t / 2.0, 0))
    )


# ── Part builders ────────────────────────────────────────────────────────────
def build_wall_holder():
    """A screw plate carrying a rod socket that leans out from the wall by `lean`,
    so the rod butt seats and the rod tips slightly forward."""
    plate_h = socket_len * 0.9 + 2.0 * wall
    plate_t = wall + 2.0
    body = wall_plate(plate_w, plate_h, plate_t)

    # Build the socket leaning forward (+Y) by `lean` degrees, attached to the
    # plate front face. Rotate about X so the open end tips toward +Y.
    sock = rod_socket(socket_len, closed_bottom=True)
    sock = sock.rotate((0, 0, 0), (1, 0, 0), lean)
    # Position: butt near the plate bottom, standing up the plate face.
    sock = sock.translate((0, sock_ro * 0.6, wall))
    body = body.union(sock)
    # A gusset connecting socket back to the plate for strength.
    gusset = (
        cq.Workplane("XY")
        .box(sock_ro * 2.0, wall * 2.0, plate_h * 0.5, centered=(True, True, False))
        .translate((0, wall, wall))
    )
    body = body.union(gusset)

    # Two screw holes through the plate (bored +Y).
    r = screw_dia / 2.0
    inset = max(10.0, screw_dia + 5.0)
    for zc in [inset, plate_h - inset]:
        cutter = (
            cq.Workplane("XZ")
            .circle(r)
            .extrude(plate_t + 6.0)
            .translate((0, 3.0, zc))
        )
        body = body.cut(cutter)
    return body


def build_rail_holder():
    """A C-clamp gripping a boat/rail tube of `rail_dia`, with the rod socket
    angled out over the water."""
    clamp_r = rail_dia / 2.0 + 0.5
    clamp_ro = clamp_r + wall
    clamp_h = max(24.0, rail_dia * 1.1)

    # C-clamp: a ring with a mouth cut so it snaps over the rail.
    ring = cq.Workplane("XY").circle(clamp_ro).circle(clamp_r).extrude(clamp_h)
    mouth_w = max(2.0, clamp_r * 0.8)
    mouth = (
        cq.Workplane("XY")
        .box(mouth_w, clamp_ro * 2.5, clamp_h + 2.0, centered=(True, False, False))
        .translate((0, 0, -1.0))
    )
    body = ring.cut(mouth)

    # Rod socket on the back of the clamp (−X), leaning up-and-out.
    sock = rod_socket(socket_len, closed_bottom=True)
    sock = sock.rotate((0, 0, 0), (0, 1, 0), -(90.0 - lean))  # tilt from horizontal
    sock = sock.translate((-clamp_ro - sock_ro * 0.4, 0, clamp_h * 0.5))
    # Boss connecting clamp to socket.
    boss = (
        cq.Workplane("XY")
        .box(sock_ro * 1.6, sock_ro * 2.0, clamp_h * 0.7, centered=(True, True, False))
        .translate((-clamp_ro, 0, clamp_h * 0.15))
    )
    body = body.union(boss).union(sock)
    return body


def build_ground_stake():
    """A stake pushed into ground/sand with a vertical rod socket on top so the
    rod stands by itself. A tapered spike + a socket cup."""
    # Tapered spike pointing down (−Z).
    spike_top_r = sock_ro
    spike = (
        cq.Workplane("XY")
        .circle(spike_top_r)
        .workplane(offset=-stake_len)
        .circle(max(1.5, spike_top_r * 0.15))
        .loft(combine=True)
    )
    # Rod socket sitting on top of the spike (opening up).
    sock = rod_socket(socket_len, closed_bottom=True)
    body = spike.union(sock)
    # A foot flange to push against with a boot.
    flange = (
        cq.Workplane("XY")
        .circle(sock_ro + wall * 1.5).circle(sock_ro * 0.6)
        .extrude(wall)
        .translate((0, 0, -wall - 1.0))
    )
    # Ensure flange overlaps the spike (spike top r = spike_top_r at z=0).
    flange = flange.translate((0, 0, 1.0))
    body = body.union(flange)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "rail_holder":
    result = build_rail_holder()
elif target_part == "ground_stake":
    result = build_ground_stake()
else:
    result = build_wall_holder()
