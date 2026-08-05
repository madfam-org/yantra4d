"""
Parametric Pipe Fitting — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A slip-fit coupler, elbow, or tee for repairing PVC / poly pipe runs. Each fitting
is a hollow socket that slides OVER the pipe outer diameter (slip fit): the socket
bore is the pipe OD plus a printable clearance, and the fitting wall wraps that bore.
Sized either by a nominal PVC schedule (1/2" / 3/4" / 1") or by a raw measured pipe
outer diameter, so a broken run can be spliced without a trip to the store.

Design idiom (shared socket helper):
  `pipe_socket()` builds ONE straight hollow stub — an outer tube of length
  socket_depth whose bore is drilled to (pipe_od/2 + clearance). Couplers stack two
  stubs back-to-back through a central web; elbows rotate the second stub by the
  elbow angle around a shared corner; tees add a third stub on the side. Booleans
  are volumetric (stubs overlap into a solid hub before the through-channel is bored)
  so the mesh stays watertight.

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


# ── Nominal PVC pipe outer diameters (mm) ────────────────────────────────────
# US nominal PVC pipe OD is larger than the "size" name (iron-pipe legacy sizing):
# 1/2" ≈ 21.3 mm, 3/4" ≈ 26.7 mm, 1" ≈ 33.4 mm actual OD. Values let the socket
# match a real pipe; the user still tunes `clearance` for the printed slip fit.
PVC_OD = {
    "1/2in": 21.3,
    "3/4in": 26.7,
    "1in": 33.4,
}


# ── Parameters ───────────────────────────────────────────────────────────────
target_part  = str(  PARAM(lambda: target_part, "coupler"))   # coupler | elbow | tee
pipe_size    = str(  PARAM(lambda: pipe_size,   "3/4in"))       # nominal PVC size or "custom"
pipe_od      = float(PARAM(lambda: pipe_od,      26.7))         # used when pipe_size == "custom"
wall         = float(PARAM(lambda: wall,          3.0))         # fitting wall thickness (mm)
socket_depth = float(PARAM(lambda: socket_depth, 22.0))        # slip-socket engagement depth (mm)
clearance    = float(PARAM(lambda: clearance,     0.4))        # slip-fit gap over pipe OD, per side
elbow_angle  = float(PARAM(lambda: elbow_angle,  90.0))        # elbow bend angle (deg)
stop_ring    = bool( PARAM(lambda: stop_ring,    True))        # internal shoulder so pipe seats to depth

# Resolve the working pipe OD: nominal table overrides the raw value unless custom.
if pipe_size in PVC_OD:
    pipe_od = PVC_OD[pipe_size]

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
pipe_od = max(8.0, min(pipe_od, 120.0))
wall = max(1.6, min(wall, 8.0))
clearance = max(0.0, min(clearance, 1.2))
socket_depth = max(8.0, min(socket_depth, 80.0))
elbow_angle = max(15.0, min(elbow_angle, 165.0))

bore_r = pipe_od / 2.0 + clearance        # socket inner radius (slides over pipe)
outer_r = bore_r + wall                    # socket outer radius
# Through-channel radius (fluid path) — pipe inner bore approx; keep a wall.
chan_r = max(1.5, bore_r - wall)
# Stop-ring inner radius: a shoulder the pipe end butts against (smaller than bore).
stop_r = max(chan_r, bore_r - min(wall * 0.8, 2.0))


# ── Shared socket helper ──────────────────────────────────────────────────────
def pipe_socket(depth, hub_extra=0.0):
    """One straight hollow slip stub aligned to +Z, base at z=0.

    Length = depth + hub_extra (the hub_extra buries the stub base into the
    central hub so unions are volumetric). The bore is left for the caller to cut
    as a single through-channel across the whole assembly."""
    return cq.Workplane("XY").circle(outer_r).extrude(depth + hub_extra)


def _stub_along(direction_deg_from_z, depth):
    """A socket stub whose axis is rotated `direction_deg_from_z` degrees away from
    +Z within the XZ plane, sharing the origin as the bend corner. Returns the
    solid stub (outer only). Used for elbow legs."""
    stub = pipe_socket(depth, hub_extra=outer_r)
    # Rotate about Y so the stub leans within the XZ plane.
    stub = stub.rotate((0, 0, 0), (0, 1, 0), direction_deg_from_z)
    return stub


# ── Part builders ────────────────────────────────────────────────────────────
def build_coupler():
    """Straight coupler: two slip sockets sharing a central web, one through-bore.
    A pipe enters each end and butts the central stop ring (if enabled)."""
    web = max(2.5, wall)
    total_h = 2.0 * socket_depth + web

    # Solid outer body: single cylinder spanning both sockets + web.
    body = cq.Workplane("XY").circle(outer_r).extrude(total_h)

    # Bore each socket from its open end to the web (leaving the web as a stop).
    top_bore = (
        cq.Workplane("XY")
        .circle(bore_r)
        .extrude(socket_depth + 0.5)
        .translate((0, 0, total_h - socket_depth - 0.5))
    )
    bot_bore = cq.Workplane("XY").circle(bore_r).extrude(socket_depth + 0.5).translate((0, 0, -0.5))
    body = body.cut(top_bore).cut(bot_bore)

    # Through fluid channel across the web.
    channel = cq.Workplane("XY").circle(chan_r).extrude(total_h + 2.0).translate((0, 0, -1.0))
    body = body.cut(channel)

    if stop_ring:
        # Widen the channel through the web to the stop radius but keep a lip.
        body = _seat_ring(body, socket_depth, total_h - socket_depth, web)

    try:
        body = body.edges(">Z or <Z").chamfer(min(wall * 0.4, 1.0))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def _seat_ring(body, z_low_face, z_high_face, web):
    """Open the web bore out to `stop_r` on each side, leaving a thin central lip
    that a pipe end seats against. Non-fatal if it fails."""
    try:
        low = cq.Workplane("XY").circle(stop_r).extrude(web * 0.5 + 0.1).translate((0, 0, z_low_face))
        high = (
            cq.Workplane("XY")
            .circle(stop_r)
            .extrude(web * 0.5 + 0.1)
            .translate((0, 0, z_high_face - web * 0.5 - 0.1))
        )
        body = body.cut(low).cut(high)
    except Exception:
        pass
    return body


def build_elbow():
    """Elbow: two sockets meeting at `elbow_angle`, joined by a filleted corner hub.
    The through-channel is bored along each leg's axis and the two bores meet in the
    hub, giving a continuous fluid path around the bend."""
    a = elbow_angle
    # Leg 1 points +Z (vertical). Leg 2 leans by (180 - a) so the included pipe
    # angle between the two open ends equals `a`.
    lean = 180.0 - a

    leg1 = pipe_socket(socket_depth, hub_extra=outer_r)
    leg2 = _stub_along(lean, socket_depth)

    # Corner hub: a sphere at the origin fuses the two legs into a smooth bend and
    # guarantees the union is a single watertight solid (not a tangent kiss).
    hub = cq.Workplane("XY").sphere(outer_r)
    body = leg1.union(hub).union(leg2)

    # Bore each leg along its own axis; both reach past the origin so they meet.
    reach = socket_depth + outer_r + 2.0
    b1 = cq.Workplane("XY").circle(bore_r).extrude(socket_depth + 0.5).translate((0, 0, outer_r - 0.5))
    # Fluid channel down leg 1 into the hub.
    c1 = cq.Workplane("XY").circle(chan_r).extrude(reach).translate((0, 0, -outer_r))
    # Leg-2 bores, built along +Z then rotated with the leg.
    b2 = (
        cq.Workplane("XY")
        .circle(bore_r)
        .extrude(socket_depth + 0.5)
        .translate((0, 0, outer_r - 0.5))
        .rotate((0, 0, 0), (0, 1, 0), lean)
    )
    c2 = (
        cq.Workplane("XY")
        .circle(chan_r)
        .extrude(reach)
        .translate((0, 0, -outer_r))
        .rotate((0, 0, 0), (0, 1, 0), lean)
    )
    body = body.cut(b1).cut(b2).cut(c1).cut(c2)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_tee():
    """Tee: a straight run (two collinear sockets) plus a branch socket at 90° on
    the side. Three slip sockets, one shared hub, a cross-shaped fluid channel."""
    web = max(2.5, wall)
    run_h = 2.0 * socket_depth + web

    # Straight run body (like the coupler) centered on Z.
    run = cq.Workplane("XY").circle(outer_r).extrude(run_h)

    # Branch: a socket on +X at the run's mid-height.
    mid = run_h / 2.0
    branch = (
        pipe_socket(socket_depth, hub_extra=outer_r)
        .rotate((0, 0, 0), (0, 1, 0), 90.0)   # lay it along +X
        .translate((0, 0, mid))
    )
    body = run.union(branch)

    # Run through-channel.
    run_chan = cq.Workplane("XY").circle(chan_r).extrude(run_h + 2.0).translate((0, 0, -1.0))
    body = body.cut(run_chan)
    # Run socket bores.
    top_bore = (
        cq.Workplane("XY").circle(bore_r).extrude(socket_depth + 0.5).translate((0, 0, run_h - socket_depth - 0.5))
    )
    bot_bore = cq.Workplane("XY").circle(bore_r).extrude(socket_depth + 0.5).translate((0, 0, -0.5))
    body = body.cut(top_bore).cut(bot_bore)

    # Branch bore + channel along +X into the run.
    reach = socket_depth + outer_r + 2.0
    br_bore = (
        cq.Workplane("XY")
        .circle(bore_r)
        .extrude(socket_depth + 0.5)
        .translate((0, 0, outer_r - 0.5))
        .rotate((0, 0, 0), (0, 1, 0), 90.0)
        .translate((0, 0, mid))
    )
    br_chan = (
        cq.Workplane("XY")
        .circle(chan_r)
        .extrude(reach)
        .translate((0, 0, -outer_r))
        .rotate((0, 0, 0), (0, 1, 0), 90.0)
        .translate((0, 0, mid))
    )
    body = body.cut(br_bore).cut(br_chan)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "elbow":
    result = build_elbow()
elif target_part == "tee":
    result = build_tee()
else:
    result = build_coupler()
