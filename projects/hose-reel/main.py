"""
Hose / Cable / Cord Reel — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A parametric winder for garden hose, extension cord, string trimmer line, or
rope. A central drum with two retaining flanges holds the coil; a hollow core
hub (the CDG "Reel Core Hub" socket) accepts an axle or a printed crank. Three
modes: a bare reel drum, a wall-mounted reel with a back plate + keyholes, and a
hand winder with a folding-style crank arm and knob.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `drum_width`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "reel"))   # reel | wall_reel | hand_winder

hub_dia     = float(PARAM(lambda: hub_dia,     40.0))    # core hub outer diameter (mm)
axle_dia    = float(PARAM(lambda: axle_dia,    12.0))    # central axle bore diameter (mm)
drum_width  = float(PARAM(lambda: drum_width,  90.0))    # winding width between flanges (mm)
flange_dia  = float(PARAM(lambda: flange_dia, 150.0))    # retaining flange diameter (mm)
flange_th   = float(PARAM(lambda: flange_th,    5.0))    # flange thickness (mm)
hub_wall    = float(PARAM(lambda: hub_wall,     4.0))    # drum barrel wall thickness (mm)
spokes      = int(  PARAM(lambda: spokes,          6))   # lightening cut-outs per flange
crank_len   = float(PARAM(lambda: crank_len,   70.0))    # crank arm length (hand_winder)
crank_th    = float(PARAM(lambda: crank_th,    10.0))    # crank arm thickness (hand_winder)
mount_gap   = float(PARAM(lambda: mount_gap,   28.0))    # keyhole spacing on wall plate (mm)

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
hub_dia    = max(20.0, min(hub_dia, 120.0))
axle_dia   = max(4.0, min(axle_dia, hub_dia - 8.0))
drum_width = max(25.0, min(drum_width, 300.0))
flange_dia = max(hub_dia + 30.0, min(flange_dia, 400.0))
flange_th  = max(3.0, min(flange_th, 12.0))
hub_wall   = max(2.5, min(hub_wall, 10.0))
spokes     = max(0, min(spokes, 10))
crank_len  = max(30.0, min(crank_len, 160.0))
crank_th   = max(6.0, min(crank_th, 20.0))
mount_gap  = max(16.0, min(mount_gap, 120.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _flange(z0):
    """A retaining flange disk at z0..z0+flange_th with an axle bore, lightening
    spoke cut-outs, and a chamfered outer rim for a clean coil edge."""
    disk = cq.Workplane("XY").circle(flange_dia / 2.0).extrude(flange_th).translate((0, 0, z0))
    # Lightening pockets between hub and rim (kept clear of both rings).
    if spokes > 0:
        ring_r = (hub_dia / 2.0 + flange_dia / 2.0) / 2.0
        span = flange_dia / 2.0 - hub_dia / 2.0
        hole_r = max(3.0, min(span * 0.32, 18.0))
        try:
            cutter = (
                cq.Workplane("XY")
                .polarArray(radius=ring_r, startAngle=0, angle=360, count=spokes)
                .circle(hole_r)
                .extrude(flange_th + 2.0)
                .translate((0, 0, z0 - 1.0))
            )
            disk = disk.cut(cutter)
        except Exception:
            pass  # lightening is cosmetic — never fatal
    try:
        disk = disk.edges(">Z or <Z").edges("%CIRCLE").chamfer(min(1.2, flange_th * 0.25))
    except Exception:
        pass
    return disk


def _drum_core():
    """The winding barrel + both flanges + hollow core hub. Origin: barrel base at
    z=0, axis on Z. Returns the assembled solid."""
    barrel_r = hub_dia / 2.0
    total_h = drum_width + 2.0 * flange_th

    # Hollow barrel spanning the full height (flanges cap nothing — hub is open
    # so an axle passes right through: this is the "Reel Core Hub" socket).
    barrel = cq.Workplane("XY").circle(barrel_r).extrude(total_h)
    core = cq.Workplane("XY").circle(max(barrel_r - hub_wall, axle_dia / 2.0 + 1.0)).extrude(total_h + 2.0).translate((0, 0, -1.0))
    barrel = barrel.cut(core)

    body = barrel.union(_flange(0.0)).union(_flange(drum_width + flange_th))

    # Central axle bore straight through everything.
    bore = cq.Workplane("XY").circle(axle_dia / 2.0).extrude(total_h + 4.0).translate((0, 0, -2.0))
    body = body.cut(bore)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def _wall_bracket():
    """A back plate that stands the reel off a wall on a stub axle. The plate sits
    in the XZ plane behind the drum; two keyholes hang it on screws."""
    plate_w = flange_dia + 20.0
    plate_h = flange_dia + 24.0
    plate_t = 6.0
    total_h = drum_width + 2.0 * flange_th

    # Plate behind the drum (y < 0 face). Built on XY then stood up.
    plate = (
        cq.Workplane("XY")
        .box(plate_w, plate_h, plate_t, centered=(True, True, False))
        .edges("|Z").fillet(6.0)
    )
    plate = plate.rotate((0, 0, 0), (1, 0, 0), 90)
    # Position so its inner face is at y=0 and it is centered on the drum height.
    plate = plate.translate((0, -plate_t / 2.0, total_h / 2.0))

    # Keyhole slots (screw head enters the round, slides down into the narrow
    # slot). The cutters are extruded through the full plate depth (both ways from
    # y=0) so they pierce the plate wherever it sits in Y.
    for sgn in (-1.0, 1.0):
        cz = total_h / 2.0 + sgn * (plate_h / 2.0 - 16.0)
        head = (
            cq.Workplane("XZ").circle(5.0)
            .extrude(plate_t + 6.0, both=True).translate((0, 0, cz))
        )
        slot = (
            cq.Workplane("XZ").rect(6.0, 12.0)
            .extrude(plate_t + 6.0, both=True).translate((0, 0, cz - 8.0))
        )
        plate = plate.cut(head).cut(slot)

    # Stub axle rising from the plate through the drum core (slightly under the
    # bore so the drum spins freely on it). A conical collar at the root spreads
    # the load into the plate so the axle does not snap off — one clean revolve,
    # unioned with an overlap into both the axle and the plate.
    axle_r = axle_dia / 2.0 - 0.35
    axle = (
        cq.Workplane("XY")
        .circle(axle_r)
        .extrude(total_h + 4.0)
        .translate((0, 0, -2.0))
    )
    collar_r = axle_r + max(4.0, axle_r)
    collar_h = min(total_h * 0.3, collar_r)
    collar = (
        cq.Workplane("XY")
        .circle(collar_r)
        .workplane(offset=collar_h)
        .circle(axle_r)
        .loft(combine=True)
    )
    bracket = plate.union(axle).union(collar)
    try:
        bracket = bracket.clean()
    except Exception:
        pass
    return bracket


def _crank():
    """A crank arm + turning knob attached to one flange face for hand winding."""
    total_h = drum_width + 2.0 * flange_th
    arm_w = crank_th * 1.6

    # Arm lies flat just outside the top flange (z just above total_h).
    arm = (
        cq.Workplane("XY")
        .box(crank_len, arm_w, crank_th, centered=(False, True, False))
        .translate((hub_dia / 2.0 * 0.4, 0, total_h))
        .edges("|Z").fillet(arm_w * 0.4)
    )
    # Hub boss that keys the arm onto the axle bore.
    boss = (
        cq.Workplane("XY")
        .circle(axle_dia / 2.0 + 4.0).extrude(crank_th + 4.0)
        .translate((0, 0, total_h - 2.0))
    )
    axle_hole = cq.Workplane("XY").circle(axle_dia / 2.0).extrude(crank_th + 8.0).translate((0, 0, total_h - 4.0))

    # Vertical grip knob at the far end of the arm.
    knob_x = hub_dia / 2.0 * 0.4 + crank_len - arm_w * 0.6
    knob = (
        cq.Workplane("XY")
        .circle(crank_th * 0.9).extrude(crank_th * 2.2)
        .translate((knob_x, 0, total_h + crank_th))
    )
    knob_pin = (
        cq.Workplane("XY")
        .circle(crank_th * 0.55).extrude(crank_th)
        .translate((knob_x, 0, total_h))
    )
    arm = arm.union(boss).union(knob_pin).union(knob).cut(axle_hole)
    try:
        arm = arm.clean()
    except Exception:
        pass
    return arm


# ── Part builders ────────────────────────────────────────────────────────────
def build_reel():
    return _drum_core()


def build_wall_reel():
    # The drum spins FREELY on the bracket axle, so the two must NOT be fused into
    # one solid — a boolean union of the disjoint drum + bracket also leaves OCCT
    # sliver artifacts. Combine them as a COMPOUND: two clean watertight solids,
    # printed separately and assembled, carried as one result for the viewer.
    drum = _drum_core()
    bracket = _wall_bracket()
    solids = list(drum.solids().vals()) + list(bracket.solids().vals())
    return cq.Compound.makeCompound(solids)


def build_hand_winder():
    return _drum_core().union(_crank())


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "wall_reel":
    result = build_wall_reel()
elif target_part == "hand_winder":
    result = build_hand_winder()
else:
    result = build_reel()
