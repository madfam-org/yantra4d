"""
Vacuum Suction Cup Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A compliant vacuum-suction gripper base. A suction cup is a thin flexible lip
that seals against a surface; pulling a vacuum through the central bore holds the
part. This cartridge builds the cup body + mount as PRINTABLE SINGLE-BODY solids
with a central vacuum bore that runs clean through (vented both ends → no trapped
void). Print the cup in TPU for a working seal, or rigid as a mold/geometry
master (see README).

The mount side carries a 1/4-20 UNC socket — the universal camera/optics/robot
thread — so the suction gripper mounts on any 1/4-20 post, arm or plate.

Modes:
  - cup_mount       : a single suction cup on a boss with a 1/4-20 threaded socket
                      and a barbed vacuum port teeing off the side.
  - bellows_cup     : a taller accordion-bellows suction cup (extra compliance /
                      Z-travel) on the same 1/4-20 boss.
  - vacuum_manifold : a flat manifold block that distributes one vacuum port to a
                      row of cup sockets — the base of a multi-cup array gripper.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use
    globals()/eval/getattr — they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "cup_mount"))
# "cup_mount" | "bellows_cup" | "vacuum_manifold"

cup_d = float(PARAM(lambda: cup_d, 40.0))         # suction cup outer diameter
cup_h = float(PARAM(lambda: cup_h, 16.0))         # cup height (dome rise + lip)
lip_t = float(PARAM(lambda: lip_t, 2.0))          # cup lip / wall thickness
bore_d = float(PARAM(lambda: bore_d, 6.0))        # central vacuum bore diameter
thread_d = float(PARAM(lambda: thread_d, 6.35))   # 1/4-20 socket major dia (1/4in)
boss_h = float(PARAM(lambda: boss_h, 12.0))       # mount boss height
n_conv = int(PARAM(lambda: n_conv, 3))            # bellows convolutions (bellows_cup)
n_cups = int(PARAM(lambda: n_cups, 3))            # cup sockets in the manifold row

# ── Clamp to sane ranges ─────────────────────────────────────────────────────
cup_d = max(16.0, min(cup_d, 80.0))
cup_h = max(8.0, min(cup_h, 34.0))
lip_t = max(1.2, min(lip_t, 4.0))
bore_d = max(2.5, min(bore_d, 12.0))
thread_d = max(3.0, min(thread_d, 12.0))
boss_h = max(6.0, min(boss_h, 24.0))
n_conv = max(2, min(n_conv, 6))
n_cups = max(2, min(n_cups, 6))

# 1/4-20 UNC reference: major dia 6.35 mm (1/4 in), 20 TPI. This cartridge mates
# the thread via a captive hex-nut trap + clearance hole (see _mount_socket),
# which is robust and always single-body — no swept helical thread needed.


# ── Cup profile (solid of revolution, flat bottom) ───────────────────────────
def _cup_body(outer_d, height, wall, hub_r):
    """A suction cup as a SINGLE filled solid of revolution: one closed
    cross-section, touching the axis (r = 0), so the whole cup — crown, central
    column, and flared skirt down to the sealing lip — is one connected solid.
    A filled profile (never a groove cut) revolved 360° is always a watertight
    single body. The dished sealing face is formed by the profile itself (a
    concave underside on the base), not by a separate recess boolean — which is
    what previously severed the skirt.

    Cross-section, traced as a closed loop in (r, z):
      axis-base → up the axis to the crown → out the crown → down the outer skirt
      to the lip rim → along the base underside back to a dished centre → to axis.
    The dish (concave base) gives the cup its suction pocket while keeping the
    part a single filled solid.
    """
    ro = outer_d / 2.0
    hub = max(hub_r + 1.5, ro * 0.30)          # solid central column radius
    base_z = 0.0
    dish_z = height * 0.4                        # how high the concave dish rises
    pts = [
        (0.0, base_z + dish_z),                 # axis, top of the concave dish
        (0.0, height),                          # axis, crown top
        (hub, height),                          # crown shoulder
        (ro, base_z + wall + 1.0),              # outer skirt down to the lip
        (ro, base_z),                           # lip rim, bottom
        (hub * 0.9, base_z),                    # along the base underside inward
        (hub * 0.5, base_z + dish_z),           # up into the concave dish
    ]
    prof = cq.Workplane("XZ").polyline(pts).close()
    cup = prof.revolve(360.0, (0, 0, 0), (0, 1, 0))
    return cup


def _mount_socket(body, boss_r):
    """Cut a 1/4-20 mount into the boss underside as a HEX NUT TRAP + clearance
    hole — a robust, single-body printable 1/4-20 interface (drop a standard
    1/4-20 nut into the hex recess; a 1/4-20 screw/post passes the clearance
    hole). This deliberately avoids a swept helical thread (the brittle case that
    can leave a disjoint rib). Only occupies the LOWER boss so the separately
    routed vacuum path never intersects it. Returns (body, socket_top_z)."""
    # 1/4-20 nut: ~11.1 mm across flats → across-corners ~12.8 mm. Recess from the
    # underside; clearance hole for the 1/4in (6.35 mm) screw above it.
    af = 11.5                       # across-flats pocket (nut + slop)
    across_corners = af / math.cos(math.radians(30.0))
    nut_depth = min(4.5, boss_h * 0.4)
    clr_d = thread_d + 0.6          # 1/4in screw clearance
    clr_depth = min(boss_h - nut_depth - 1.5, boss_h * 0.4)

    # hex pocket (a 6-gon prism) from the underside
    hexw = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -boss_h - 0.5))
        .polygon(6, across_corners)
        .extrude(nut_depth + 0.5)
    )
    body = body.cut(hexw)
    # clearance hole above the nut pocket
    clr = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -boss_h + nut_depth - 0.1))
        .circle(clr_d / 2.0)
        .extrude(clr_depth + 0.2)
    )
    body = body.cut(clr)
    socket_top_z = -boss_h + nut_depth + clr_depth
    return body, socket_top_z


def _vacuum_route(body, boss_r, crown_top_z, socket_top_z, port_z):
    """Route vacuum: a central bore from the cup crown DOWN to just above the
    socket, then a side cross-bore out to a barbed port. The central bore stops
    short of the socket so the two never intersect (avoids severing the thread).
    Every drilling vents to an exterior face → no trapped void."""
    stop_z = socket_top_z + 1.5      # keep the vacuum bore above the socket
    depth = crown_top_z - stop_z + 1.0
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, stop_z))
        .circle(bore_d / 2.0)
        .extrude(depth)
    )
    body = body.cut(bore)
    # side barbed port + cross bore meeting the central bore
    barb_od = max(4.0, bore_d + 1.0)
    port = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, port_z, boss_r - 0.5))
        .circle(barb_od / 2.0)
        .extrude(8.0)
    )
    body = body.union(port)
    xbore = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, port_z, boss_r + 7.0))
        .circle(max(1.2, bore_d / 2.0 - 0.6))
        .extrude(boss_r + 9.0)   # from the barb tip inward across the axis
    )
    body = body.cut(xbore)
    return body


def build_cup_mount():
    """A single suction cup on a mount boss with a 1/4-20 socket and a barbed
    side vacuum port. Vacuum runs cup crown → central bore → side barb; the
    1/4-20 socket is a separate blind hole in the lower boss (no intersection)."""
    boss_r = max(thread_d / 2.0 + 3.5, cup_d * 0.2)
    cup = _cup_body(cup_d, cup_h, lip_t, boss_r)
    boss = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -boss_h))
        .circle(boss_r)
        .extrude(boss_h + cup_h * 0.5)   # overlaps into the solid hub
    )
    body = cup.union(boss)

    body, socket_top_z = _mount_socket(body, boss_r)
    body = _vacuum_route(
        body, boss_r,
        crown_top_z=cup_h,
        socket_top_z=socket_top_z,
        port_z=-boss_h * 0.35,
    )
    return body


def build_bellows_cup():
    """A taller accordion-bellows suction cup (extra Z-compliance) on the same
    1/4-20 boss. The bellows is a stack of alternating-diameter rings unioned into
    one solid; central bore runs through."""
    ro = cup_d / 2.0
    ring_h = cup_h / n_conv
    body = None
    for i in range(n_conv):
        z = i * ring_h
        r = ro if i % 2 == 0 else ro * 0.72
        ring = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z))
            .circle(r)
            .extrude(ring_h + 0.6)   # overlap next ring so union is watertight
        )
        body = ring if body is None else body.union(ring)
    # solid crown cap on top
    cap = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cup_h - 0.6))
        .circle(ro * 0.5)
        .extrude(3.0)
    )
    body = body.union(cap)
    # mount boss below
    boss_r = max(thread_d / 2.0 + 3.5, cup_d * 0.22)
    boss = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -boss_h))
        .circle(boss_r)
        .extrude(boss_h + ring_h)
    )
    body = body.union(boss)
    body, socket_top_z = _mount_socket(body, boss_r)
    # crown_top_z sits just ABOVE the cap top (cup_h - 0.6 + 3.0) so the central
    # vacuum bore vents through the cap → no trapped void.
    body = _vacuum_route(
        body, boss_r,
        crown_top_z=cup_h + 2.5,
        socket_top_z=socket_top_z,
        port_z=-boss_h * 0.35,
    )
    return body


def build_vacuum_manifold():
    """A flat manifold block that tees one vacuum port to a ROW of cup sockets.
    Each socket is a shallow counterbore + through bore; a side barb feeds the
    shared internal channel (a through cross-drilling → vented, no trapped void)."""
    pitch = max(cup_d * 0.6, thread_d + 8.0)
    length = pitch * (n_cups - 1) + cup_d
    width = cup_d + 6.0
    height = boss_h
    block = (
        cq.Workplane("XY")
        .box(length, width, height, centered=(True, True, False))
    )
    try:
        block = block.edges("|Z").fillet(3.0)
    except Exception:
        pass
    body = block
    x0 = -pitch * (n_cups - 1) / 2.0
    # shared feed channel: a through cross-drilling along X near the top
    chan_z = height * 0.6
    chan = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, chan_z, 0))
        .circle(max(1.5, bore_d / 2.0))
        .extrude(length / 2.0 + 2.0, both=True)
    )
    body = body.cut(chan)
    for i in range(n_cups):
        cx = x0 + i * pitch
        # cup seat counterbore (shallow, from the top)
        seat = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, 0, height - 2.5))
            .circle(cup_d / 2.0 * 0.45)
            .extrude(3.0)
        )
        body = body.cut(seat)
        # vertical bore from the seat down to the feed channel (vented top+channel)
        vb = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, 0, chan_z - 1.0))
            .circle(max(1.2, bore_d / 2.0 - 0.5))
            .extrude(height - chan_z + 3.0)
        )
        body = body.cut(vb)
    # side barb into the channel end
    barb_od = max(4.0, bore_d)
    port = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, chan_z, width / 2.0 - 0.5))
        .circle(barb_od / 2.0)
        .extrude(8.0)
    )
    body = body.union(port)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bellows_cup":
    result = build_bellows_cup()
elif target_part == "vacuum_manifold":
    result = build_vacuum_manifold()
else:
    result = build_cup_mount()
