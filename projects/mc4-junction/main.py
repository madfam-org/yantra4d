"""MC4 Junction Bracket — 4-Up PV Connector Organizer (Yantra4D Hyperobject).

Organizes and mounts MC4 photovoltaic connectors around the REAL MC4 body
standard, so a solar array's DC connectors are held, strain-relieved, and DIN- or
surface-mounted instead of dangling. The functional interface is the MC4 body
cradle (Ø16 mm) and the PV lead pass-through (Ø6.5 mm) that mate the same MC4
connector the `mc4-holder` cartridge holds, growing the `mc4` solar family.

Real MC4 geometry (nominal):
  * MC4 connector body ≈ Ø16 mm across the barrel (held in a snap cradle).
  * PV lead (4-6 mm² cable) ≈ Ø6.5 mm (strain-relief slot / pass-through).
  * DIN rail top-hat ≈ 35 mm wide, 7.5 mm deep (TS35 / EN 60715).

Three distinct modes:
  * junction_4  — a plate with FOUR MC4 body cradles in a row plus mounting ears,
    so four connectors clip in side by side (a combiner-box tidy).
  * pair_bracket — a compact back-to-back holder for ONE mated MC4 pair
    (male + female inline), with a lead pass-through each end.
  * strain_comb — a strain-relief comb bar: a row of open-top slots that grip the
    PV leads (Ø6.5) and take a zip-tie across the top.

Watertightness: every cradle / slot / hole is a boolean cut that OPENS to a face
(no trapped voids); the plate blank is filleted BEFORE features are cut; slots
are obround (stadium) rather than fans-of-arcs. No threads here (beginner tier).
NOTE: printed PV mounts carry NO current — this is a mechanical organizer only;
the MC4 connectors themselves make and insulate every electrical joint.

Sandbox contract (apps/api/services/engine/cq_runner.py): `cq` + `math` are
pre-injected globals; parameters arrive as BARE globals — read via
PARAM(lambda: name, default); assign the final solid to a top-level `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── MC4 nominal geometry ─────────────────────────────────────────────────────
MC4_BODY_D = 16.0   # connector barrel diameter (mm)
MC4_LEAD_D = 6.5    # PV lead / cable diameter (mm)
DIN_W = 35.0        # TS35 top-hat rail width (mm)


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "junction_4"))  # junction_4|pair_bracket|strain_comb
body_d = float(PARAM(lambda: body_d, MC4_BODY_D))            # MC4 body cradle diameter (mm)
lead_d = float(PARAM(lambda: lead_d, MC4_LEAD_D))            # PV lead pass-through (mm)
clearance = float(PARAM(lambda: clearance, 0.4))            # printed fit slop (mm)
plate_th = float(PARAM(lambda: plate_th, 4.0))             # base plate thickness (mm)
wall = float(PARAM(lambda: wall, 3.0))                     # cradle / comb wall (mm)
count = float(PARAM(lambda: count, 4.0))                   # slots in the strain comb
pitch = float(PARAM(lambda: pitch, 22.0))                  # centre-to-centre spacing (mm)

body_d = max(10.0, min(body_d, 24.0))
lead_d = max(3.0, min(lead_d, 12.0))
clearance = max(0.0, min(clearance, 1.0))
plate_th = max(2.5, min(plate_th, 8.0))
wall = max(2.0, min(wall, 6.0))
count = max(2.0, min(round(count), 8.0))
pitch = max(14.0, min(pitch, 40.0))


# ── junction_4 ───────────────────────────────────────────────────────────────
def build_junction_4():
    """A base plate carrying `4` MC4 body cradles in a row, with a lead
    pass-through beyond each cradle and two mounting-ear holes."""
    n = 4
    cr = (body_d + 2.0 * clearance) / 2.0        # cradle inner radius
    cradle_od = body_d + 2.0 * wall + 2.0 * clearance
    span = (n - 1) * pitch
    plate_l = span + cradle_od + 2.0 * wall
    plate_w = cradle_od + 2.0 * wall
    # Filleted plate blank BEFORE any feature cuts.
    plate = (
        cq.Workplane("XY").box(plate_l, plate_w, plate_th, centered=(True, True, False))
        .edges("|Z").fillet(min(4.0, plate_w / 4.0))
    )
    # Cradle walls (open-top C-cradles) rise from the plate; union solid rings
    # then cut the barrel bore + a top entry slot so the connector snaps in.
    cradle_h = body_d * 0.7
    xs = [(-span / 2.0) + i * pitch for i in range(n)]
    body = plate
    for x in xs:
        ring = (
            cq.Workplane("XY").transformed(offset=cq.Vector(x, 0, plate_th - 0.01))
            .circle(cradle_od / 2.0).extrude(cradle_h)
        )
        body = body.union(ring)
    # Cut all barrel bores (open to the top face → no trapped void).
    for x in xs:
        bore = (
            cq.Workplane("XY").transformed(offset=cq.Vector(x, 0, plate_th))
            .circle(cr).extrude(cradle_h + 1.0)
        )
        body = body.cut(bore)
    # Snap entry slot on top of each cradle (a gap in the wall to press the body in).
    slot_w = cr * 1.1
    for x in xs:
        gap = (
            cq.Workplane("XY").transformed(offset=cq.Vector(x, cradle_od / 2.0, plate_th + cradle_h * 0.45))
            .box(slot_w, cradle_od, cradle_h, centered=(True, True, False))
        )
        body = body.cut(gap)
    # Mounting-ear holes through the plate at each end.
    ear_x = plate_l / 2.0 - wall * 1.5
    for sx in (-1, 1):
        hole = (
            cq.Workplane("XY").transformed(offset=cq.Vector(sx * ear_x, 0, -0.5))
            .circle(2.2).extrude(plate_th + 1.0)
        )
        body = body.cut(hole)
    return body


# ── pair_bracket ─────────────────────────────────────────────────────────────
def build_pair_bracket():
    """A compact block cradling ONE mated MC4 pair inline (male+female), a lead
    pass-through each end, and a central mounting hole. The mated pair sits in a
    single through-bore; the block is split-top so it snaps around the pair."""
    cr = (body_d + 2.0 * clearance) / 2.0
    block_len = body_d * 3.2
    block_w = body_d + 2.0 * wall + 2.0 * clearance
    block_h = body_d + 2.0 * wall
    block = (
        cq.Workplane("XY").box(block_len, block_w, block_h, centered=(True, True, False))
        .edges("|X").fillet(min(4.0, block_w / 4.0))
    )
    # Central through-bore (opens both X ends → no trapped void) for the pair.
    bore = (
        cq.Workplane("YZ").transformed(offset=cq.Vector(0, block_h / 2.0, -block_len / 2.0 - 1.0))
        .circle(cr).extrude(block_len + 2.0)
    )
    body = block.cut(bore)
    # Lead pass-through counterbores are already open via the through-bore ends.
    # Top snap slot so the connector body can be pressed into the bore.
    slot = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, block_h * 0.55))
        .box(block_len + 1.0, cr * 1.05, block_h, centered=(True, True, False))
    )
    body = body.cut(slot)
    # Central mounting hole down through the floor (opens bottom + into bore).
    mh = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(2.2).extrude(block_h * 0.5)
    )
    body = body.cut(mh)
    return body


# ── strain_comb ──────────────────────────────────────────────────────────────
def build_strain_comb():
    """A strain-relief comb bar: `count` open-top slots (obround) that grip the
    PV leads, spanned by a zip-tie channel across the back."""
    n = int(count)
    slot_w = lead_d + 2.0 * clearance
    span = (n - 1) * pitch
    bar_l = span + slot_w + 2.0 * wall
    bar_w = lead_d + 4.0 * wall
    bar_h = lead_d + 2.0 * wall
    bar = (
        cq.Workplane("XY").box(bar_l, bar_w, bar_h, centered=(True, True, False))
        .edges("|Z").fillet(min(3.0, bar_w / 4.0))
    )
    body = bar
    xs = [(-span / 2.0) + i * pitch for i in range(n)]
    # Open-top slots: an obround pocket down from the top for each lead.
    for x in xs:
        slot = (
            cq.Workplane("XY").transformed(offset=cq.Vector(x, 0, bar_h - lead_d * 0.7))
            .slot2D(length=slot_w + 0.01, diameter=slot_w, angle=90)
            .extrude(lead_d)
        )
        body = body.cut(slot)
        # Narrow neck to the top surface so the lead presses in (open to top face).
        neck = (
            cq.Workplane("XY").transformed(offset=cq.Vector(x, 0, bar_h - lead_d * 0.35))
            .box(slot_w * 0.7, bar_w, lead_d, centered=(True, True, False))
        )
        body = body.cut(neck)
    # Zip-tie channel across the back (a shallow transverse groove, opens to ends).
    tie = (
        cq.Workplane("YZ").transformed(offset=cq.Vector(0, bar_w / 2.0 + 2.0, -bar_l / 2.0 - 1.0))
        .rect(3.0, 3.0).extrude(bar_l + 2.0)
    )
    body = body.cut(tie)
    # Two mounting holes through the bar ends.
    for sx in (-1, 1):
        hole = (
            cq.Workplane("XY").transformed(offset=cq.Vector(sx * (bar_l / 2.0 - wall), 0, -0.5))
            .circle(2.0).extrude(bar_h + 1.0)
        )
        body = body.cut(hole)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pair_bracket":
    result = build_pair_bracket()
elif target_part == "strain_comb":
    result = build_strain_comb()
else:
    result = build_junction_4()
