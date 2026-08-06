"""
Solar MC4 / Connector Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Holders and strain reliefs that organize MC4 photovoltaic connectors. The socket
bore lands on the real MC4 body / panel-cutout diameter, so a printed holder grips
a standard MC4 coupling and dresses PV leads on a panel edge, combiner box or rail.
Pick the socket count and the holder carries that many connectors on a fixed pitch.

Modes are dispatched via `target_part`:
  * "panel_mount"    — a single panel-mount socket collar: a boss with the MC4
                       body bore and a flange that seats on a panel cutout.
  * "rail_organizer" — a strip carrying several MC4 sockets on a pitch, with a
                       screw-mount base rail.
  * "strain_block"   — a strain-relief block that captures the MC4 body and its
                       cable in a socket + cable groove (two poles, +/-).

Standards encoded (mm):
  MC4 connector body Ø ~ 16.0 at the widest coupling (Staubli MC4 family), panel
  cutout Ø ~ 17.0. Coupled pair overall length ~ 85; single body length ~ 50.
  Cable Ø for 4-6 mm2 PV lead ~ 6.0-7.2.

Watertightness: socket bores are single cylinder cuts from solid, filleted blanks;
stacked bodies OVERLAP (never tangent). Bores open to a face -> no trapped voids.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `socket_count`).
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


# ── Standard dimensions (mm) ─────────────────────────────────────────────────
MC4_BODY_D = 16.0      # MC4 coupling body Ø (Staubli MC4 family, widest)
MC4_PANEL_D = 17.0     # MC4 panel-cutout Ø
MC4_CABLE_D = 6.5      # 4-6 mm2 PV lead Ø


# ── Parameters ───────────────────────────────────────────────────────────────
target_part  = str(PARAM(lambda: target_part, "panel_mount"))
socket_dia   = float(PARAM(lambda: socket_dia, MC4_BODY_D))  # MC4 body bore Ø (mm)
clearance    = float(PARAM(lambda: clearance, 0.4))          # socket clearance per side (mm)
wall         = float(PARAM(lambda: wall, 3.0))               # holder wall (mm)
socket_count = int(PARAM(lambda: socket_count, 4))           # sockets on the rail
pitch        = float(PARAM(lambda: pitch, 22.0))             # socket center pitch (mm)
depth        = float(PARAM(lambda: depth, 18.0))             # socket / block depth (mm)
cable_dia    = float(PARAM(lambda: cable_dia, MC4_CABLE_D))  # PV lead Ø (mm)
screw_dia    = float(PARAM(lambda: screw_dia, 4.0))          # mount screw Ø (mm)

# Clamp to sane ranges.
socket_dia = max(8.0, min(socket_dia, 30.0))
clearance = max(0.0, min(clearance, 1.2))
wall = max(2.0, min(wall, 8.0))
socket_count = max(2, min(socket_count, 8))
pitch = max(socket_dia + 2.0, min(pitch, 60.0))
depth = max(8.0, min(depth, 50.0))
cable_dia = max(3.0, min(cable_dia, 12.0))
screw_dia = max(2.0, min(screw_dia, 8.0))


# ── Part builders ─────────────────────────────────────────────────────────────
def build_panel_mount():
    """A single panel-mount socket collar: a boss with the MC4 body bore and a
    seating flange that sits against the panel cutout."""
    bore_r = (socket_dia + 2.0 * clearance) / 2.0
    boss_r = bore_r + wall
    flange_r = boss_r + wall
    boss_h = depth
    flange_h = max(2.0, wall)
    ov = 0.8

    # Flange (seats on the panel) at the bottom.
    flange = cq.Workplane("XY").circle(flange_r).extrude(flange_h)
    try:
        flange = flange.edges(">Z").fillet(min(1.5, wall * 0.5))
    except Exception:
        pass

    # Boss rises from the flange; overlap into the flange by `ov`.
    boss = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, flange_h - ov))
        .circle(boss_r).extrude(boss_h + ov)
    )
    body = flange.union(boss)

    # MC4 body bore all the way through (open both faces).
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(bore_r).extrude(flange_h + boss_h + 2.0)
    )
    body = body.cut(bore)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_rail_organizer():
    """A strip carrying several MC4 sockets on a pitch, on a screw-mount base."""
    bore_r = (socket_dia + 2.0 * clearance) / 2.0
    boss_r = bore_r + wall
    # Keep a clear gap between adjacent bosses so they never touch tangentially
    # (a tangent boss-to-boss kiss leaves a zero-area seam -> non-watertight).
    eff_pitch = max(pitch, 2.0 * boss_r + 1.5)
    # End pad must fully contain a mounting screw with margin (screw radius +
    # 3 mm) so the screw hole never runs tangent to the base edge (a tangent
    # hole leaves a knife-edge sliver -> non-watertight).
    end_pad = screw_dia / 2.0 + 3.0
    x0 = -(socket_count - 1) * eff_pitch / 2.0
    span = (socket_count - 1) * eff_pitch + 2.0 * boss_r + 2.0 * end_pad
    base_d = 2.0 * boss_r + 2.0 * wall
    base_h = max(3.0, wall)
    boss_h = depth
    ov = 0.8

    base = cq.Workplane("XY").box(span, base_d, base_h, centered=(True, True, False))
    try:
        base = base.edges("|Z").fillet(min(3.0, wall))
    except Exception:
        pass

    body = base
    # Bosses (overlap into base by ov).
    for i in range(socket_count):
        cx = x0 + i * eff_pitch
        boss = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, 0.0, base_h - ov))
            .circle(boss_r).extrude(boss_h + ov)
        )
        body = body.union(boss)
    # Bores through each boss + base.
    for i in range(socket_count):
        cx = x0 + i * eff_pitch
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, 0.0, -1.0))
            .circle(bore_r).extrude(base_h + boss_h + 2.0)
        )
        body = body.cut(bore)

    # Mounting screws centered in the end pads (safely inside the base edge).
    x_last = x0 + (socket_count - 1) * eff_pitch
    for cx in (x0 - boss_r - end_pad / 2.0, x_last + boss_r + end_pad / 2.0):
        scr = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, 0.0, -1.0))
            .circle(screw_dia / 2.0).extrude(base_h + 2.0)
        )
        body = body.cut(scr)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_strain_block():
    """A two-pole strain-relief block: two MC4 body sockets side by side, each
    continuing into a cable groove so the lead is captured behind the connector."""
    bore_r = (socket_dia + 2.0 * clearance) / 2.0
    cbl_r = (cable_dia + 2.0 * clearance) / 2.0
    poles = 2
    p = max(pitch, socket_dia + wall + 2.0)

    span = (poles - 1) * p + 2.0 * bore_r + 2.0 * wall
    block_d = depth + 2.0 * wall
    block_h = 2.0 * bore_r + 2.0 * wall
    body = cq.Workplane("XY").box(span, block_d, block_h, centered=(True, True, False))
    try:
        body = body.edges("|Y").fillet(min(3.0, wall))
    except Exception:
        pass

    x0 = -(poles - 1) * p / 2.0
    zc = block_h / 2.0
    for i in range(poles):
        cx = x0 + i * p
        # Socket bore (front half of the block, along Y).
        sock = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(cx, zc, -(block_d / 2.0) - 1.0))
            .circle(bore_r).extrude(depth + 1.0)
        )
        body = body.cut(sock)
        # Cable groove continuing out the back (smaller Ø).
        groove = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(cx, zc, -(block_d / 2.0) + depth - 1.0))
            .circle(cbl_r).extrude(block_d - depth + 3.0)
        )
        body = body.cut(groove)

    # A pair of mounting screws through the block (vertical, open both faces).
    for cx in (x0, x0 + (poles - 1) * p):
        scr = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, block_d / 2.0 - wall, -1.0))
            .circle(screw_dia / 2.0).extrude(block_h + 2.0)
        )
        body = body.cut(scr)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "panel_mount": build_panel_mount,
    "rail_organizer": build_rail_organizer,
    "strain_block": build_strain_block,
}

result = _dispatch.get(target_part, build_panel_mount)()
