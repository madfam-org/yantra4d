"""
Weather-Instrument Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Mounts a rain gauge, thermometer, anemometer, or other backyard weather sensor to
a pole or a fence. A split clamp wraps a round pole (the CDG "Pole Clamp" socket);
a flat plate screws to a fence; a cradle ring holds a cylindrical instrument. Three
parts: the pole clamp with a mounting boss, a fence mount plate with the same boss,
and a gauge cradle that plugs onto the boss.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `pole_dia`).
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


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "pole_clamp"))  # pole_clamp | fence_mount | gauge_cradle

pole_dia    = float(PARAM(lambda: pole_dia,   34.0))   # pole outer diameter the clamp wraps (mm)
clamp_wall  = float(PARAM(lambda: clamp_wall,  5.0))   # clamp band wall thickness (mm)
clamp_h     = float(PARAM(lambda: clamp_h,    30.0))   # clamp band height (mm)
bolt_dia    = float(PARAM(lambda: bolt_dia,    5.0))   # clamp / fence bolt diameter (mm)
boss_dia    = float(PARAM(lambda: boss_dia,   20.0))   # shared mounting-boss diameter (mm)
boss_len    = float(PARAM(lambda: boss_len,   22.0))   # mounting-boss length (mm)
clearance   = float(PARAM(lambda: clearance,  0.4))    # boss plug fit slop per side (mm)
cradle_dia  = float(PARAM(lambda: cradle_dia, 40.0))   # instrument body diameter (gauge_cradle)
cradle_h    = float(PARAM(lambda: cradle_h,   35.0))   # cradle ring height (gauge_cradle)
plate_w     = float(PARAM(lambda: plate_w,    60.0))   # fence plate width (fence_mount)
plate_h     = float(PARAM(lambda: plate_h,    80.0))   # fence plate height (fence_mount)

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
pole_dia   = max(12.0, min(pole_dia, 120.0))
clamp_wall = max(3.0, min(clamp_wall, 12.0))
clamp_h    = max(12.0, min(clamp_h, 80.0))
bolt_dia   = max(2.5, min(bolt_dia, 10.0))
boss_dia   = max(10.0, min(boss_dia, 50.0))
boss_len   = max(10.0, min(boss_len, 60.0))
clearance  = max(0.1, min(clearance, 1.0))
cradle_dia = max(15.0, min(cradle_dia, 120.0))
cradle_h   = max(12.0, min(cradle_h, 100.0))
plate_w    = max(30.0, min(plate_w, 200.0))
plate_h    = max(30.0, min(plate_h, 250.0))

pole_r = pole_dia / 2.0
clamp_or = pole_r + clamp_wall


def _mount_boss(y_face, z_center, embed=4.0):
    """The shared FEMALE mounting boss: a stub cylinder projecting along +Y from a
    carrier face at `y_face`, centered vertically on `z_center`. It starts `embed`
    mm INSIDE the carrier (y_face - embed) so the union is a solid volumetric
    overlap, never a fragile tangent kiss. A blind bore accepts the cradle plug.
    Returns the boss solid ready to union onto the carrier."""
    root_y = y_face - embed
    length = boss_len + embed
    # Solid stub grown along +Y from root_y. A cylinder on XY extruded in +Z,
    # rotated to lie along +Y, is robust and axis-clean.
    stub = (
        cq.Workplane("XY")
        .circle(boss_dia / 2.0).extrude(length)
        .rotate((0, 0, 0), (1, 0, 0), -90)          # +Z axis -> +Y axis
        .translate((0, root_y, z_center))
    )
    # Blind female bore from the OUTER end inward (does not reach the carrier).
    bore_r = max(3.0, boss_dia / 2.0 - 3.0)
    bore_depth = boss_len - 3.0
    bore = (
        cq.Workplane("XY")
        .circle(bore_r).extrude(bore_depth)
        .rotate((0, 0, 0), (1, 0, 0), -90)
        .translate((0, y_face + boss_len - bore_depth, z_center))
    )
    return stub.cut(bore)


def _split_clamp():
    """A C-shaped split band that wraps a round pole. Two ears with bolt holes pull
    it tight. Origin: pole axis on Z; the opening (gap) faces -Y, ears extend -Y."""
    band = (
        cq.Workplane("XY")
        .circle(clamp_or).circle(pole_r)
        .extrude(clamp_h)
    )
    # Cut the opening slot (a gap facing -Y) so the band can spring over the pole.
    gap = max(2.5, bolt_dia * 0.5)
    slot = (
        cq.Workplane("XY")
        .box(gap, clamp_or + 6.0, clamp_h + 2.0, centered=(True, False, False))
        .translate((0, -clamp_or - 3.0, -1.0))
    )
    band = band.cut(slot)

    # Clamping ears on both sides of the gap, extending -Y, with bolt holes.
    ear_l = clamp_wall + bolt_dia + 6.0
    ear_t = clamp_wall
    ears = []
    for sgn in (-1.0, 1.0):
        ear = (
            cq.Workplane("XY")
            .box(ear_t, ear_l, clamp_h, centered=(False, False, False))
            .translate((sgn * (gap / 2.0), -clamp_or - ear_l + (clamp_or - pole_r), 0))
        )
        ears.append((sgn, ear))
    body = band
    for sgn, ear in ears:
        # place ear flush to the gap edge
        ear = ear.translate((sgn * 0.0, 0, 0))
        body = body.union(ear)

    # Bolt hole through both ears (along X, through the gap).
    bolt_z = clamp_h / 2.0
    bolt_y = -clamp_or - ear_l / 2.0 + (clamp_or - pole_r)
    hole = (
        cq.Workplane("YZ")
        .circle(bolt_dia / 2.0).extrude(gap + 2.0 * ear_t + 4.0)
        .translate((-(gap / 2.0 + ear_t + 2.0), bolt_y, bolt_z))
    )
    body = body.cut(hole)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Part builders ─────────────────────────────────────────────────────────────
def build_pole_clamp():
    """Split pole clamp + a mounting boss on the +Y side (opposite the pole? no —
    boss projects outward on +X so it clears the clamp bolt on -Y). We place the
    boss on +Y past the band so the instrument sits beside the pole."""
    body = _split_clamp()
    # Boss on the +Y outer face of the band. The gap/ears are on -Y, so +Y is the
    # solid back of the band — ideal. The boss embeds through the band wall so the
    # union is one solid body; embed spans the full wall to guarantee overlap.
    boss = _mount_boss(y_face=clamp_or, z_center=clamp_h / 2.0, embed=clamp_wall + 1.0)
    body = body.union(boss)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_fence_mount():
    """A flat plate that screws to a fence board, carrying the same mounting boss on
    its front (+Y) face. Four corner screw holes."""
    plate_t = max(4.0, clamp_wall)
    plate = (
        cq.Workplane("XY")
        .box(plate_w, plate_t, plate_h, centered=(True, True, False))
        .edges("|Y").fillet(min(8.0, plate_w * 0.15, plate_h * 0.15))
    )
    # Corner screw holes (through the plate thickness, along Y; plate spans
    # y:[-plate_t/2, +plate_t/2], so extrude from y just behind the back face).
    ox = plate_w / 2.0 - max(8.0, bolt_dia * 1.6)
    oz = plate_h - max(10.0, bolt_dia * 2.0)
    for sx in (-ox, ox):
        for sz in (max(8.0, bolt_dia * 2.0), oz):
            hole = (
                cq.Workplane("XZ")
                .circle(bolt_dia / 2.0).extrude(plate_t + 4.0)
                .translate((sx, -plate_t / 2.0 - 2.0, sz))
            )
            plate = plate.cut(hole)
    # Mounting boss centered on the front (+Y) face, embedded through the plate.
    boss = _mount_boss(y_face=plate_t / 2.0, z_center=plate_h / 2.0, embed=plate_t)
    body = plate.union(boss)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_gauge_cradle():
    """A cradle that holds a cylindrical instrument, with a MALE plug that fits the
    mounting boss on the clamp or fence plate. The cradle is a C-ring so the gauge
    clips in from the front."""
    ring_or = cradle_dia / 2.0 + max(3.0, clamp_wall)
    ring_ir = cradle_dia / 2.0
    ring = (
        cq.Workplane("XY")
        .circle(ring_or).circle(ring_ir)
        .extrude(cradle_h)
    )
    # Front opening so the instrument clips in (gap faces +Y).
    gap = cradle_dia * 0.5
    slot = (
        cq.Workplane("XY")
        .box(gap, ring_or + 6.0, cradle_h + 2.0, centered=(True, False, False))
        .translate((0, ring_ir - 1.0, -1.0))
    )
    ring = ring.cut(slot)

    # Male plug on the -Y back of the ring that inserts into the female boss.
    plug_r = boss_dia / 2.0 - 3.0 - clearance
    plug_len = boss_len - 4.0
    plug = (
        cq.Workplane("XZ")
        .circle(max(2.5, plug_r)).extrude(-plug_len)   # projects toward -Y
        .translate((0, -ring_or + 1.0, cradle_h / 2.0))
    )
    # A neck pad joining plug to ring.
    pad = (
        cq.Workplane("XZ")
        .box(boss_dia + 4.0, min(cradle_h, boss_dia + 4.0), max(4.0, clamp_wall), centered=(True, True, True))
        .translate((0, -ring_or + 1.0, cradle_h / 2.0))
    )
    body = ring.union(pad).union(plug)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "fence_mount":
    result = build_fence_mount()
elif target_part == "gauge_cradle":
    result = build_gauge_cradle()
else:
    result = build_pole_clamp()
