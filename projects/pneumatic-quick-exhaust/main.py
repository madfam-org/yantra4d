"""
Pneumatic Quick Exhaust — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A three-port shuttle valve on the commons' own barb series.

A soft actuator inflates as fast as the supply can push air in, and deflates as
slowly as that same air can crawl back out through the whole length of the
supply line. Retraction speed is the stated weakness of the entire soft-robotics
family in this commons: `bellows-actuator`, `pneu-net-finger` and
`suction-cup-bellows` all inflate briskly and all release slowly, and the reason
is plumbing rather than material.

A quick-exhaust valve fixes that with three ports and one loose disc:

  * supply pressurised  — the shuttle is pushed down, sealing the EXHAUST seat;
                          air flows supply -> actuator.
  * supply vented       — the actuator's own pressure lifts the shuttle, sealing
                          the SUPPLY seat; air dumps straight out of the large
                          exhaust aperture instead of back up the supply line.

Nothing about it is clever. It is a cup, a lid and a disc, and it is the
difference between an actuator that releases in a second and one that releases
in ten.

Modes are dispatched via `target_part`:
  * "valve_body"   — the cup: actuator port in the wall, exhaust seat and a
                     shrouded aperture in the floor, open at the top.
  * "valve_cap"    — the lid: supply port and the supply seat, on a spigot that
                     enters the cup.
  * "shuttle_disc" — the moving element, sized to seal against either seat.

Series discipline: every barb dimension comes from the SAME expressions as
`pneumatic-barb-port` and `hose-barb-tee`. A supply stem built here at
`tube_id` = 3 grips the same tube as a port built there at `tube_id` = 3.

Watertightness strategy:
  * Both seats are built as SOLID rings and the bore through them is cut LAST,
    so a seat is never a thin annulus fused to a floor face-to-face.
  * The actuator passage is cut from outside to the chamber AXIS only — never
    through to the far wall, which would open the body into a tube.
  * The exhaust shroud's windows are counted from the space that survives the
    end margins, and skipped entirely when there is none.
  * The three parts are three OPEN or SOLID shapes: the cup is open at its top,
    the cap has a through port, the disc is solid. Nothing anywhere seals a
    void, and a sealed void meshes as two bodies whatever the kernel reports.
  * No spheres: a pole is a degenerate point where every meridian meets, and the
    tessellator splits the result while OCC calls the solid valid.
  * No fillet on any edge a bore has touched.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

This is a low-pressure valve for soft pneumatics. See the README.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "valve_body"))
supply_form = str(PARAM(lambda: supply_form, "barb"))

tube_id = float(PARAM(lambda: tube_id, 3.0))
barb_count = float(PARAM(lambda: barb_count, 3.0))
barb_pitch = float(PARAM(lambda: barb_pitch, 3.0))
barb_rise = float(PARAM(lambda: barb_rise, 0.7))
bore = float(PARAM(lambda: bore, 1.6))
wall = float(PARAM(lambda: wall, 2.0))
chamber_dia = float(PARAM(lambda: chamber_dia, 18.0))
chamber_h = float(PARAM(lambda: chamber_h, 10.0))
seat_dia = float(PARAM(lambda: seat_dia, 8.0))
clearance = float(PARAM(lambda: clearance, 0.30))
shroud_windows = float(PARAM(lambda: shroud_windows, 4.0))
push_od = float(PARAM(lambda: push_od, 6.0))

tube_id = max(1.5, min(tube_id, 10.0))
barb_count = int(max(1, min(round(barb_count), 6)))
barb_pitch = max(1.6, min(barb_pitch, 8.0))
barb_rise = max(0.2, min(barb_rise, 2.0))
bore = max(0.8, min(bore, 8.0))
wall = max(1.2, min(wall, 5.0))
chamber_dia = max(10.0, min(chamber_dia, 40.0))
chamber_h = max(5.0, min(chamber_h, 30.0))
seat_dia = max(3.0, min(seat_dia, 24.0))
clearance = max(0.1, min(clearance, 0.6))
shroud_windows = int(max(2, min(round(shroud_windows), 8)))
push_od = max(3.0, min(push_od, 10.0))


# ── The shared barb series (identical expressions to pneumatic-barb-port) ────
def stem_r(tid):
    return max(tid / 2.0, bore / 2.0 + wall)


def barb_r(tid):
    return stem_r(tid) + barb_rise


def bore_r(tid):
    return max(0.35, min(bore / 2.0, stem_r(tid) - 0.6))


def ridge_h():
    return min(barb_pitch * 0.75, barb_rise * 3.0 + 0.8)


def stem_len(tid):
    return barb_pitch * (barb_count + 0.6) + 1.5


# ── Derived, clamped against FINAL values ────────────────────────────────────
CH_R = chamber_dia / 2.0
OUT_R = CH_R + wall
FLOOR = wall

# The chamber height is RAISED to whatever the actuator port needs. The port's
# stem radius comes from the tube series, not from this cartridge, so a large
# tube on a short chamber put the stem's lowest generator EXACTLY on the chamber
# floor plane — tangent, one non-manifold edge, and a kernel reporting success.
# Growing the chamber is the honest fix; shrinking the port would silently break
# the series the port belongs to.
#
# The margin is 4.4 mm and every millimetre of it is answering a measured
# failure. A first fix used 2.4, which put the stem's lowest generator at
# FLOOR + 1.2 — and the seat ring's top face is at FLOOR + SEAT_H, where SEAT_H
# caps at exactly 1.2. The tangency simply MOVED from the floor to the seat, and
# three more sweep cases failed the same silent way. 4.4 = 2 x the seat cap
# (1.2) + 2.0 of real clearance, so the stem clears the seat by at least 1.0 mm
# at every combination. Clearance has to be measured against the TALLEST thing
# in the chamber, not against the chamber's own floor.
SEAT_H_MAX = 1.2
CH_H = max(chamber_h, 2.0 * stem_r(tube_id) + 2.0 * SEAT_H_MAX + 2.0)

# The seat must fit inside the chamber with room for the disc to overlap it, and
# it must be larger than the bore it surrounds. Derived from both, so no slider
# combination can produce a seat wider than the chamber or narrower than its own
# hole.
SEAT_W = max(0.8, wall * 0.5)
SEAT_R = max(bore_r(tube_id) + 0.8, min(seat_dia / 2.0, CH_R - SEAT_W - 1.6))
SEAT_H = max(0.6, min(SEAT_H_MAX, CH_H * 0.12))

# The disc has to cover BOTH seats and still slide in the chamber.
DISC_R = min(CH_R - clearance, CH_R - 0.25)
DISC_R = max(DISC_R, SEAT_R + SEAT_W + 0.6)
DISC_R = min(DISC_R, CH_R - 0.2)
DISC_T = max(1.2, min(2.4, CH_H * 0.22))

CAP_TH = max(1.6, wall)
SPIGOT_H = max(2.0, wall * 1.2)
BODY_H = FLOOR + CH_H + SPIGOT_H + 0.6
SHROUD_H = max(3.0, wall * 2.0)

OVERLAP = 0.8


# ── Primitives ───────────────────────────────────────────────────────────────
def barbed_stem(tid, length):
    """A stem along +Z from z=0 with tapered ridges, clamped inside its span."""
    body = cq.Workplane("XY").circle(stem_r(tid)).extrude(length)
    rh = ridge_h()
    for i in range(barb_count):
        zb = length - (1.0 + i * barb_pitch) - rh
        zb = max(0.2, min(zb, length - rh - 0.2))
        if zb < 0.2 or zb + rh > length - 0.1:
            continue
        ridge = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, zb))
            .circle(barb_r(tid))
            .workplane(offset=rh)
            .circle(stem_r(tid))
            .loft(ruled=True)
        )
        body = body.union(ridge)
    return body


def supply_port(length):
    """(solid along +Z from z=0, passage radius, counterbore radius or None)."""
    if supply_form == "socket":
        sr = barb_r(tube_id) + clearance
        return (cq.Workplane("XY").circle(sr + wall).extrude(length),
                bore_r(tube_id), sr)
    if supply_form == "push_in":
        pr = push_od / 2.0
        return (cq.Workplane("XY").circle(pr).extrude(length),
                max(0.35, min(bore / 2.0, pr - 0.8)), None)
    return barbed_stem(tube_id, length), bore_r(tube_id), None


def seat_ring(z0):
    """A SOLID ring blank at z0. The bore through it is cut later, by the caller,
    so the seat is never a thin annulus fused to a face."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0 - OVERLAP))
        .circle(SEAT_R + SEAT_W)
        .extrude(SEAT_H + OVERLAP)
    )


def axial_bore(r, z_lo, z_hi):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_lo))
        .circle(r)
        .extrude(z_hi - z_lo)
    )


# ── Part builders ────────────────────────────────────────────────────────────
def build_valve_body():
    """The cup: actuator port in the wall, exhaust seat and shrouded aperture in
    the floor, open at the top for the shuttle and the cap."""
    body = cq.Workplane("XY").circle(OUT_R).extrude(BODY_H)

    # Exhaust shroud below the floor: a skirt with side windows, so the aperture
    # cannot be blindfolded by whatever the valve is lying on.
    shroud = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -SHROUD_H))
        .circle(min(OUT_R, SEAT_R + SEAT_W + wall))
        .extrude(SHROUD_H + OVERLAP)
    )
    body = body.union(shroud)

    # Chamber: a plain bore from the floor to the top face, open at the top.
    body = body.cut(axial_bore(CH_R, FLOOR, BODY_H + 1.0))

    # Cap register: a shallow counterbore at the mouth so the cap spigot lands
    # square. Bounded by SPIGOT_H, never run to the floor.
    body = body.cut(axial_bore(min(CH_R + wall * 0.45, OUT_R - 0.8),
                               BODY_H - SPIGOT_H, BODY_H + 1.0))

    # The exhaust seat, as a solid ring on the chamber floor.
    body = body.union(seat_ring(FLOOR))

    # Actuator port in the wall, at mid-chamber height. Its passage is cut to
    # the chamber AXIS only: running it through would open the body into a tube.
    a_z = FLOOR + CH_H * 0.5
    a_len = stem_len(tube_id)
    stem = (
        barbed_stem(tube_id, a_len + OUT_R)
        .rotate((0, 0, 0), (0, 1, 0), 90)
        .translate((0, 0, a_z))
    )
    body = body.union(stem)
    a_cut = (
        cq.Workplane("XY")
        .circle(bore_r(tube_id))
        .extrude(a_len + OUT_R + 1.0)
        .rotate((0, 0, 0), (0, 1, 0), 90)
        .translate((0, 0, a_z))
    )
    body = body.cut(a_cut)

    # Windows in the shroud, counted from the space that survives the margins.
    n = shroud_windows
    win_h = SHROUD_H - 1.6
    if win_h >= 1.2 and n >= 2:
        win_w = max(1.0, (2.0 * math.pi * (SEAT_R + SEAT_W)) / (2.0 * n))
        for i in range(n):
            ang = 360.0 * i / n
            tool = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, -SHROUD_H + 0.8))
                .box(OUT_R * 4.0, win_w, win_h, centered=(True, True, False))
                .rotate((0, 0, 0), (0, 0, 1), ang)
            )
            try:
                body = body.cut(tool)
            except Exception:
                pass

    # The exhaust bore, cut LAST, through the seat ring, the floor and the
    # shroud — open at both ends.
    body = body.cut(axial_bore(SEAT_R, -SHROUD_H - 1.0, FLOOR + SEAT_H + 1.0))

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_valve_cap():
    """The lid: supply port on top, supply seat underneath, on a spigot that
    enters the cup."""
    disc = cq.Workplane("XY").circle(OUT_R).extrude(CAP_TH)

    # Spigot hanging below, straddling the disc it grows from.
    spigot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -SPIGOT_H))
        .circle(max(1.0, CH_R - clearance))
        .extrude(SPIGOT_H + OVERLAP)
    )
    body = disc.union(spigot)

    # The supply seat, a solid ring on the spigot's underside, pointing DOWN.
    ring = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -SPIGOT_H - SEAT_H))
        .circle(SEAT_R + SEAT_W)
        .extrude(SEAT_H + OVERLAP)
    )
    body = body.union(ring)

    # Supply port on top.
    p_len = (stem_len(tube_id) if supply_form == "barb"
             else max(8.0, stem_len(tube_id) * 0.8))
    port, pr, cr = supply_port(p_len + OVERLAP)
    body = body.union(port.translate((0, 0, CAP_TH - OVERLAP)))

    top_z = CAP_TH + p_len
    if cr is not None:
        # A BOUNDED counterbore: it stops inside the cap, so it can never break
        # through into the seat below and swallow the whole supply passage.
        stop = CAP_TH - max(0.8, CAP_TH * 0.4)
        body = body.cut(axial_bore(cr, stop, top_z + 1.0))
    body = body.cut(axial_bore(pr, -SPIGOT_H - SEAT_H - 1.0, top_z + 1.0))

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_shuttle_disc():
    """The moving element: a solid disc that seals against either seat.

    Solid, not shelled. A shelled disc would trap a void, and a trapped void is
    a second body in the mesh however valid the kernel reports the solid."""
    body = cq.Workplane("XY").circle(DISC_R).extrude(DISC_T)

    # A shallow lead-in chamfer on both faces so the disc cannot cock in the
    # bore. Built as two lofts to a slightly smaller radius, each OVERLAPPING
    # the disc rather than sitting on its face.
    ch = min(0.6, DISC_T * 0.25)
    if ch >= 0.2 and DISC_R > ch + 1.0:
        try:
            body = body.cut(
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, -0.01))
                .circle(DISC_R + 2.0)
                .workplane(offset=ch)
                .circle(DISC_R + 2.0 - ch)
                .loft(ruled=True)
                .cut(cq.Workplane("XY")
                     .transformed(offset=cq.Vector(0, 0, -1.0))
                     .circle(DISC_R - ch)
                     .extrude(ch + 2.0))
            )
        except Exception:
            pass

    # Three low ribs on one face: they hold the disc off the seat's flat land
    # just enough that the FIRST puff of supply air can get under it, which is
    # what makes a light printed shuttle move at all.
    rib_h = min(0.5, DISC_T * 0.2)
    if rib_h >= 0.2:
        for i in range(3):
            ang = math.radians(120.0 * i)
            rr = DISC_R * 0.6
            rib = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(rr * math.cos(ang),
                                              rr * math.sin(ang),
                                              DISC_T - OVERLAP))
                .circle(max(0.5, DISC_R * 0.12))
                .extrude(rib_h + OVERLAP)
            )
            body = body.union(rib)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "valve_body": build_valve_body,
    "valve_cap": build_valve_cap,
    "shuttle_disc": build_shuttle_disc,
}

result = _dispatch.get(target_part, build_valve_body)()
